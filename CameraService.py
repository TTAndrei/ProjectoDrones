# =====================================================
#  CAMERA SERVICE
#  pip install opencv-python aiortc paho-mqtt av requests
# =====================================================

import asyncio, cv2, json, ssl, requests
import logging

# aioice es la librería interna de ICE que usa aiortc. Genera logs propios
# que no aportan información útil en uso normal — los silenciamos.
logging.getLogger("aioice").setLevel(logging.CRITICAL)
logging.getLogger("aioice.turn").setLevel(logging.CRITICAL)

from aiortc import (RTCPeerConnection, RTCSessionDescription,
                    VideoStreamTrack, RTCConfiguration, RTCIceServer)
from av import VideoFrame
import paho.mqtt.client as mqtt

# ── Configuración MQTT (HiveMQ Cloud) ────────────────────────────────────────
BROKER  = "554f19f1f4944c978dd30b509d24afc0.s1.eu.hivemq.cloud"
PORT    = 8884
USER    = "InterfazGlobal"
PASS    = "Kb2avDJmV2aj!Jz"

# Topics usados para el intercambio de señalización WebRTC:
#   - T_OFFER:  camera_service publica aquí su SDP offer al arrancar
#   - T_ANSWER: dashboard publica aquí su SDP answer como respuesta
T_OFFER  = "webrtc/offer"
T_ANSWER = "webrtc/answer"

# URL de la API de Metered para obtener credenciales TURN dinámicas.
# Metered devuelve STUN + TURN con credenciales temporales firmadas —
# más seguro y fiable que usar servidores TURN públicos sin autenticación.
METERED_API = "https://testconection1.metered.live/api/v1/turn/credentials?apiKey=57312a00508de97f6ca0758cce3935fe7670"

# ── Variables globales ────────────────────────────────────────────────────────
pc          = None   # RTCPeerConnection — gestiona la conexión WebRTC
loop        = None   # event loop asyncio (necesario para llamadas desde callbacks MQTT)
mqtt_client = None


# ── ICE / TURN ────────────────────────────────────────────────────────────────

def get_ice_config():
    """Obtiene la lista de servidores ICE desde la API de Metered.

    WebRTC necesita servidores ICE para descubrir cómo conectar dos peers:
      - STUN: descubre la IP pública del dispositivo (gratis, sin relay)
      - TURN: relaya el tráfico cuando NAT/firewall bloquea la conexión directa

    Sin TURN, la conexión solo funciona en la misma red local.
    Con TURN, funciona en cualquier red — el tráfico pasa por el servidor Metered.
    """
    print("[ICE] Obteniendo credenciales TURN de Metered...")
    try:
        resp = requests.get(METERED_API, timeout=10)
        servers = resp.json()
        print(f"[ICE] {len(servers)} servidores obtenidos:")
        for s in servers:
            print(f"  {s.get('urls')}")

        ice_servers = []
        for s in servers:
            urls = s.get("urls")
            if isinstance(urls, str):
                urls = [urls]
            username   = s.get("username")
            credential = s.get("credential")
            # Los servidores TURN requieren usuario/contraseña; STUN no
            if username and credential:
                ice_servers.append(RTCIceServer(urls=urls, username=username, credential=credential))
            else:
                ice_servers.append(RTCIceServer(urls=urls))
        return RTCConfiguration(iceServers=ice_servers)

    except Exception as e:
        # Si Metered no responde, caemos a STUN básico de Google como respaldo.
        # En ese caso la conexión solo funcionará en la misma red local.
        print(f"[ICE] Error obteniendo credenciales: {e}")
        print("[ICE] Usando solo STUN de respaldo...")
        return RTCConfiguration(iceServers=[
            RTCIceServer(urls="stun:stun.l.google.com:19302"),
        ])


# ── Track de vídeo ────────────────────────────────────────────────────────────

class CameraTrack(VideoStreamTrack):
    """Track de vídeo que captura frames de la webcam y los envía por WebRTC.

    aiortc necesita un objeto VideoStreamTrack para enviar vídeo.
    Sobrescribimos recv() para que en cada llamada devuelva el siguiente frame
    de la cámara en el formato que aiortc espera (VideoFrame de PyAV).
    """

    def __init__(self):
        super().__init__()
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise RuntimeError("No se pudo abrir la cámara")
        print("[CAM] Cámara abierta")

    async def recv(self):
        # next_timestamp() genera el pts (presentation timestamp) correcto
        # para que el receptor pueda sincronizar y reproducir el vídeo
        pts, time_base = await self.next_timestamp()
        ret, frame = self.cap.read()
        if not ret:
            await asyncio.sleep(0.033)
            return await self.recv()
        # OpenCV usa BGR; aiortc/PyAV esperan RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        vf = VideoFrame.from_ndarray(frame, format="rgb24")
        vf.pts, vf.time_base = pts, time_base
        return vf


# ── MQTT callbacks ────────────────────────────────────────────────────────────

def on_connect(client, userdata, flags, rc):
    print("[MQTT] Conectado" if rc == 0 else f"[MQTT] Error {rc}")
    # Suscribirse a la answer del dashboard nada más conectar
    client.subscribe(T_ANSWER)

def on_message(client, userdata, msg):
    if msg.topic != T_ANSWER:
        return
    data = json.loads(msg.payload)
    print("[SIG] Answer recibida")

    # on_message corre en el hilo MQTT, pero pc.setRemoteDescription es async.
    # run_coroutine_threadsafe() programa la corrutina en el event loop asyncio
    # del hilo principal de forma segura entre hilos.
    async def apply():
        await pc.setRemoteDescription(
            RTCSessionDescription(sdp=data["sdp"], type=data["type"])
        )
        print("[WebRTC] Answer aplicada ✓")
    asyncio.run_coroutine_threadsafe(apply(), loop)


# ── WebRTC ────────────────────────────────────────────────────────────────────

async def run():
    global pc

    ice_config = get_ice_config()
    pc = RTCPeerConnection(configuration=ice_config)
    pc.addTrack(CameraTrack())  # añadir el track de cámara a la conexión

    @pc.on("connectionstatechange")
    async def _(): print(f"[WebRTC] {pc.connectionState}")

    @pc.on("iceconnectionstatechange")
    async def _(): print(f"[ICE] {pc.iceConnectionState}")

    # Crear la offer SDP con la descripción de los medios que vamos a enviar
    await pc.setLocalDescription(await pc.createOffer())

    # aiortc no implementa trickle ICE (envío de candidates uno a uno).
    # En su lugar, espera a que el gathering esté completo y embute
    # todos los candidates directamente en el SDP de la offer.
    print("[WebRTC] Esperando ICE gathering (STUN + TURN)...")
    while pc.iceGatheringState != "complete":
        await asyncio.sleep(0.2)

    # Mostrar candidates para diagnóstico:
    # 'host'  = IP local (solo misma red)
    # 'srflx' = IP pública via STUN (puede fallar con NAT simétrico)
    # 'relay' = tráfico por TURN (funciona en cualquier red) ← lo que queremos
    candidates = [l for l in pc.localDescription.sdp.splitlines() if l.startswith("a=candidate")]
    print(f"[WebRTC] {len(candidates)} candidates:")
    for c in candidates:
        tipo = "✓ RELAY" if "relay" in c else "  host/srflx"
        print(f"  {tipo}: {c[12:80]}")

    if not any("relay" in c for c in candidates):
        print("[WARN] Sin candidates relay — TURN no respondió.")
    else:
        print("[OK] Candidates relay presentes — debería funcionar en cualquier red ✓")

    # Publicar la offer con retain=True para que el dashboard la reciba aunque
    # se conecte a MQTT después de que el camera_service la haya publicado.
    mqtt_client.publish(T_OFFER, json.dumps({
        "sdp":  pc.localDescription.sdp,
        "type": pc.localDescription.type,
    }), retain=True)
    print("[SIG] Offer enviada — esperando dashboard...")

    try:
        # Mantener el proceso vivo esperando la answer del dashboard
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await pc.close()


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    global loop, mqtt_client
    loop = asyncio.get_running_loop()

    # Silenciar errores internos de aioice TURN ("Task exception was never retrieved").
    # aioice intenta optimizar la conexión con CHANNEL_BIND y a veces falla con 401,
    # pero el vídeo sigue llegando correctamente — es ruido, no un error real.
    def _silence_aioice(loop, context):
        exc = context.get("exception", None)
        if "TransactionFailed" in str(type(exc).__name__) or "aioice" in str(exc):
            return  # silenciar silenciosamente
        loop.default_exception_handler(context)

    loop.set_exception_handler(_silence_aioice)

    # Conectar MQTT en modo websocket TLS (puerto 8884 — requerido por HiveMQ Cloud)
    mqtt_client = mqtt.Client(client_id="CameraService", transport="websockets")
    mqtt_client.ws_set_options(path="/mqtt")
    mqtt_client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
    mqtt_client.username_pw_set(USER, PASS)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(BROKER, PORT)
    mqtt_client.loop_start()  # loop_start() corre MQTT en su propio hilo

    await asyncio.sleep(1)  # esperar a que MQTT confirme la conexión
    await run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[MAIN] Cerrando...")