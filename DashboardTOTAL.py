# =====================================================
#  DASHBOARD INTEGRADO
#  Incluye Dashboard + AutopilotService + CameraService
#  T0do en un solo archivo — no hay que ejecutar nada más
#
#  Modo Global: MQTT (HiveMQ) + WebRTC + TURN (Metered)
#  Modo Local:  dronLink directo + TcpSocketSignaling
#
#  pip install aiortc paho-mqtt av opencv-python requests
# =====================================================

import asyncio, json, ssl, threading, time, requests
import logging, warnings

# Silenciar FutureWarning de torch en YOLOv5
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Silenciar logs internos de aioice (ICE/STUN/TURN)
logging.getLogger("aioice").setLevel(logging.CRITICAL)
logging.getLogger("aioice.turn").setLevel(logging.CRITICAL)

import cv2, tkinter as tk
import tkintermapview
import paho.mqtt.client as mqtt
from aiortc import (RTCPeerConnection, RTCSessionDescription,
                    RTCConfiguration, RTCIceServer, VideoStreamTrack)
from av import VideoFrame
from dronLink.Dron import Dron

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════

# ── Dashboard / MQTT ──────────────────────────────────────────────────────────
BROKER_DASHBOARD  = "554f19f1f4944c978dd30b509d24afc0.s1.eu.hivemq.cloud"
PORT              = 8884
USER_DASHBOARD    = "InterfazGlobal"
PASS_DASHBOARD    = "Kb2avDJmV2aj!Jz"

T_OFFER  = "webrtc/offer"
T_ANSWER = "webrtc/answer"

METERED_API = "https://testconection1.metered.live/api/v1/turn/credentials?apiKey=57312a00508de97f6ca0758cce3935fe7670"

# ── AutopilotService / MQTT ───────────────────────────────────────────────────
# Credenciales propias del servicio de autopiloto — distintas a las del dashboard
USER_AUTOPILOT = "autopilotServiceDemo"
PASS_AUTOPILOT = "qkdb!LasqvHfy9V"

# ── TCP (Modo Local) ──────────────────────────────────────────────────────────
TCP_HOST = "localhost"
TCP_PORT = 9999

# ══════════════════════════════════════════════════════════════════════════════
#  ESTADO GLOBAL
# ══════════════════════════════════════════════════════════════════════════════

pc            = None   # RTCPeerConnection del dashboard (receptor de vídeo)
loop_dashboard = None  # event loop asyncio del hilo WebRTC del dashboard
client_dashboard = None   # cliente MQTT del dashboard
pending_offer = None   # offer recibida antes de pulsar el botón de vídeo
previousBtn   = None
MODE          = None   # "global" o "local"

dron          = Dron() # instancia del dron — compartida entre autopiloto y dashboard local

altShowLbl = headingShowLbl = stateShowLbl = None
speedShowLbl = battShowLbl = gpsShowLbl = None
connectBtn = arm_takeOffBtn = landBtn = RTLBtn = None
speedSldr  = gradesSldr = None

# ── Mapa ──────────────────────────────────────────────────────────────────────
map_widget     = None   # widget tkintermapview
drone_marker   = None   # marcador del dron en el mapa
target_marker  = None   # marcador del destino (al hacer clic)
drone_path     = []     # lista de (lat, lon) para trazar la ruta
drone_path_line = None  # línea de ruta en el mapa
drone_lat      = None   # última latitud conocida del dron
drone_lon      = None   # última longitud conocida del dron
_goto_callback = None   # función go_to_gps según el modo (global/local)

# YOLOv5
detect_object_id = None
yolo_model       = None


# ══════════════════════════════════════════════════════════════════════════════
#  PANTALLA DE SELECCIÓN DE MODO
# ══════════════════════════════════════════════════════════════════════════════

def selector_modo():
    """Ventana inicial para elegir entre Modo Global y Modo Local."""
    modo_elegido = {"valor": None}

    sel = tk.Tk()
    sel.title("Dashboard Dron — Selecciona modo")
    sel.resizable(False, False)
    sel.configure(bg="#212121")

    w, h = 440, 340
    x = (sel.winfo_screenwidth()  - w) // 2
    y = (sel.winfo_screenheight() - h) // 2
    sel.geometry(f"{w}x{h}+{x}+{y}")

    tk.Label(sel, text="Dashboard Dron",
             font=("Arial", 18, "bold"), bg="#212121", fg="white").pack(pady=(28, 4))
    tk.Label(sel, text="Selecciona el modo de conexión",
             font=("Arial", 10), bg="#212121", fg="#aaaaaa").pack(pady=(0, 24))

    btn_frame = tk.Frame(sel, bg="#212121")
    btn_frame.pack(fill="x", padx=40)

    def elegir(modo):
        modo_elegido["valor"] = modo
        sel.destroy()

    # Modo Global
    f_global = tk.Frame(btn_frame, bg="#212121")
    f_global.pack(fill="x", pady=6, ipady=2)
    tk.Button(f_global, text="Modo Global",
              font=("Arial", 12, "bold"), bg="#e94560", fg="white",
              activebackground="#c73652", relief="flat", cursor="hand2", pady=10,
              command=lambda: elegir("global")).pack(fill="x", padx=2, pady=2)
    tk.Label(f_global, text="MQTT + WebRTC + TURN",
             font=("Arial", 8), bg="#212121", fg="#aaaaaa").pack(pady=(0, 4))

    # Modo Local
    f_local = tk.Frame(btn_frame, bg="#212121")
    f_local.pack(fill="x", pady=6, ipady=2)
    tk.Button(f_local, text="Modo Local",
              font=("Arial", 12, "bold"), bg="#2196f3", fg="white",
              activebackground="#1976d2", relief="flat", cursor="hand2", pady=10,
              command=lambda: elegir("local")).pack(fill="x", padx=2, pady=2)
    tk.Label(f_local, text="Conexión directa (dronLink + TCP)",
             font=("Arial", 8), bg="#212121", fg="#aaaaaa").pack(pady=(0, 4))

    sel.protocol("WM_DELETE_WINDOW", sel.destroy)
    sel.mainloop()

    if modo_elegido["valor"] is None:
        import sys; sys.exit(0)

    return modo_elegido["valor"]


# ── Asignar MODE global al arrancar ──────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
#  AUTOPILOT SERVICE (integrado)
#  Escucha comandos MQTT y los traduce a llamadas dronLink.
#  En modo global corre en su propio hilo con su propio cliente MQTT.
#  En modo local el dashboard habla directamente con dronLink.
# ══════════════════════════════════════════════════════════════════════════════

autopilot_sending_topic = None  # topic de respuesta, se construye por mensaje
client_autopilot        = None  # cliente MQTT del autopiloto (distinto al del dashboard)


def autopilot_publish_event(event):
    """Publica un evento de estado de vuelta al dashboard que originó el comando."""
    client_autopilot.publish(autopilot_sending_topic + '/' + event)
    print(f"[AUTOPILOT] → {autopilot_sending_topic}/{event}")


def autopilot_publish_telemetry(telemetry_info):
    """Publica datos de telemetría en tiempo real."""
    client_autopilot.publish(autopilot_sending_topic + '/telemetryInfo',
                              json.dumps(telemetry_info))


def autopilot_on_message(cli, userdata, message):
    """Procesa los comandos que llegan del dashboard via MQTT.

    Topic format:  <origen>/autopilotServiceDemo/<comando>
    Ejemplo:       interfazGlobal/autopilotServiceDemo/arm_takeOff
    """
    global autopilot_sending_topic

    parts   = message.topic.split("/")
    origin  = parts[0]   # quién envió el comando
    command = parts[2]   # qué hay que hacer

    autopilot_sending_topic = "autopilotServiceDemo/" + origin
    print(f"[AUTOPILOT] {origin} → {command}")

    if command == 'connect':
        dron.connect('tcp:127.0.0.1:5763', 115200, freq=10)
        autopilot_publish_event('connected')

    elif command == 'arm_takeOff':
        if dron.state == 'connected':
            dron.arm()
            altura = int(message.payload.decode("utf-8"))
            dron.takeOff(altura, blocking=False,
                         callback=autopilot_publish_event, params='flying')

    elif command == 'go':
        if dron.state == 'flying':
            dron.go(message.payload.decode("utf-8"))

    elif command == 'Land':
        if dron.state == 'flying':
            dron.Land(blocking=False,
                      callback=autopilot_publish_event, params='landed')

    elif command == 'RTL':
        if dron.state == 'flying':
            dron.RTL(blocking=False,
                     callback=autopilot_publish_event, params='atHome')

    elif command == 'startTelemetry':
        dron.send_telemetry_info(autopilot_publish_telemetry)

    elif command == 'stopTelemetry':
        dron.stop_sending_telemetry_info()

    elif command == 'changeHeading':
        dron.changeHeading(float(message.payload.decode("utf-8")))

    elif command == 'changeNavSpeed':
        dron.changeNavSpeed(float(message.payload.decode("utf-8")))

    elif command == 'goto':
        # Payload: {"lat": float, "lon": float, "alt": float}
        # dronLink.goto() navega al punto GPS con la altitud indicada.
        # blocking=False para no bloquear el hilo MQTT mientras el dron viaja.
        coords = json.loads(message.payload.decode("utf-8"))
        dron.goto(coords["lat"], coords["lon"], coords.get("alt", 5.0),
                  blocking=False)
        print(f"[AUTOPILOT] goto → {coords['lat']:.6f}, {coords['lon']:.6f}, {coords.get('alt',5)}m")


def autopilot_on_connect(cli, userdata, flags, rc):
    print("[AUTOPILOT] Conectado" if rc == 0 else f"[AUTOPILOT] Error MQTT {rc}")


def start_autopilot_service():
    """Arranca el AutopilotService en su propio hilo.
    Usa un cliente MQTT separado con credenciales propias del servicio.
    """
    global client_autopilot

    def _run():
        global client_autopilot
        client_autopilot = mqtt.Client("autopilotServiceDemo", transport="websockets")
        client_autopilot.ws_set_options(path="/mqtt")
        client_autopilot.tls_set(cert_reqs=mqtt.ssl.CERT_REQUIRED,
                                  tls_version=mqtt.ssl.PROTOCOL_TLSv1_2)
        client_autopilot.tls_insecure_set(False)
        client_autopilot.username_pw_set(USER_AUTOPILOT, PASS_AUTOPILOT)
        client_autopilot.on_connect = autopilot_on_connect
        client_autopilot.on_message = autopilot_on_message
        client_autopilot.connect(BROKER_DASHBOARD, PORT)
        # Escuchar comandos de cualquier origen dirigidos a este servicio
        client_autopilot.subscribe('+/autopilotServiceDemo/#')
        print("[AUTOPILOT] Servicio listo — esperando comandos")
        client_autopilot.loop_forever()

    threading.Thread(target=_run, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
#  CAMERA SERVICE (integrado)
#  Captura la webcam y emite el stream por WebRTC.
#  Señalización via MQTT (modo global) o TCP (modo local).
# ══════════════════════════════════════════════════════════════════════════════

class CameraTrack(VideoStreamTrack):
    """Track de vídeo que captura frames de la webcam para enviarlos por WebRTC.

    Usa fractions.Fraction(1, 30) para time_base — compatible con aiortc y
    con el formato original del camera_service independiente.
    """
    def __init__(self):
        super().__init__()
        import fractions
        self._fractions = fractions
        self.cap = cv2.VideoCapture(0)
        self.frame_count = 0
        if not self.cap.isOpened():
            raise RuntimeError("No se pudo abrir la cámara")
        print("[CAM] Cámara abierta")

    async def recv(self):
        self.frame_count += 1
        ret, frame = self.cap.read()
        if not ret:
            await asyncio.sleep(0.033)
            return await self.recv()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        vf = VideoFrame.from_ndarray(frame, format="rgb24")
        vf.pts       = self.frame_count
        vf.time_base = self._fractions.Fraction(1, 30)
        return vf


def get_ice_config():
    """Obtiene servidores ICE (STUN + TURN) desde Metered.
    Sin TURN solo funciona en LAN; con TURN funciona en cualquier red."""
    print("[ICE] Obteniendo credenciales TURN de Metered...")
    try:
        servers = requests.get(METERED_API, timeout=10).json()
        print(f"[ICE] {len(servers)} servidores:")
        ice_servers = []
        for s in servers:
            urls = s.get("urls")
            if isinstance(urls, str): urls = [urls]
            u, c = s.get("username"), s.get("credential")
            print(f"  {urls[0]}")
            if u and c:
                ice_servers.append(RTCIceServer(urls=urls, username=u, credential=c))
            else:
                ice_servers.append(RTCIceServer(urls=urls))
        return RTCConfiguration(iceServers=ice_servers)
    except Exception as e:
        print(f"[ICE] Error: {e} — usando STUN de respaldo")
        return RTCConfiguration(iceServers=[RTCIceServer(urls="stun:stun.l.google.com:19302")])


def _silence_aioice_handler(loop, context):
    """Handler que silencia errores internos de aioice TURN (CHANNEL_BIND 401).
    No afectan al funcionamiento — el vídeo sigue llegando por relay."""
    exc = context.get("exception", None)
    msg = context.get("message", "")
    if "TransactionFailed" in str(type(exc).__name__) or "aioice" in str(exc):
        return
    if "CHANNEL_BIND" in msg or "TransactionFailed" in msg:
        return
    loop.default_exception_handler(context)


async def run_camera_global(mqtt_cam_client):
    """Crea la conexión WebRTC del emisor (camera) y publica la offer via MQTT."""
    pc_cam = RTCPeerConnection(configuration=get_ice_config())
    pc_cam.addTrack(CameraTrack())

    @pc_cam.on("connectionstatechange")
    async def _(): print(f"[CAM] WebRTC {pc_cam.connectionState}")

    # Evento para recibir la answer del dashboard
    answer_event = asyncio.Event()
    answer_data  = {}

    # Capturamos el loop AQUÍ, dentro de la corrutina asyncio donde sí existe.
    # on_answer se ejecutará en el hilo MQTT que no tiene loop propio —
    # por eso hay que pasárselo explícitamente via run_coroutine_threadsafe.
    cam_loop = asyncio.get_event_loop()

    def on_answer(cli, userdata, msg):
        if msg.topic == T_ANSWER:
            answer_data["sdp"] = json.loads(msg.payload)
            asyncio.run_coroutine_threadsafe(
                _apply_answer(pc_cam, answer_data["sdp"], answer_event),
                cam_loop   # loop capturado desde el contexto asyncio correcto
            )

    mqtt_cam_client.on_message = on_answer
    mqtt_cam_client.subscribe(T_ANSWER)

    # Crear offer y esperar ICE gathering completo
    await pc_cam.setLocalDescription(await pc_cam.createOffer())
    print("[CAM] Esperando ICE gathering...")
    while pc_cam.iceGatheringState != "complete":
        await asyncio.sleep(0.2)

    candidates = [l for l in pc_cam.localDescription.sdp.splitlines()
                  if l.startswith("a=candidate")]
    has_relay = any("relay" in c for c in candidates)
    print(f"[CAM] {len(candidates)} candidates — {'✓ relay presente' if has_relay else '⚠ sin relay'}")

    # Publicar offer con retain=True — el dashboard la recibe aunque arranque después
    mqtt_cam_client.publish(T_OFFER, json.dumps({
        "sdp":  pc_cam.localDescription.sdp,
        "type": pc_cam.localDescription.type,
    }), retain=True)
    print("[CAM] Offer publicada — esperando answer del dashboard...")

    await answer_event.wait()  # bloquear hasta recibir la answer
    print("[CAM] Conexión establecida ✓")

    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await pc_cam.close()


async def _apply_answer(pc_cam, data, event):
    await pc_cam.setRemoteDescription(
        RTCSessionDescription(sdp=data["sdp"], type=data["type"])
    )
    print("[CAM] Answer aplicada ✓")
    event.set()


def start_camera_service_global():
    """Arranca el CameraService en modo global en su propio hilo asyncio."""
    def _run():
        # Cliente MQTT propio para el camera service
        cam_client = mqtt.Client(client_id="CameraService", transport="websockets")
        cam_client.ws_set_options(path="/mqtt")
        cam_client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
        cam_client.username_pw_set(USER_DASHBOARD, PASS_DASHBOARD)
        cam_client.connect(BROKER_DASHBOARD, PORT)
        cam_client.loop_start()

        loop = asyncio.new_event_loop()
        loop.set_exception_handler(_silence_aioice_handler)
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_camera_global(cam_client))

    threading.Thread(target=_run, daemon=True).start()
    print("[CAM] CameraService iniciado (modo global)")


async def run_camera_local():
    """CameraService en modo local — actúa de SERVIDOR TCP.

    El emisor abre el socket y espera a que el dashboard (cliente) se conecte.
    Una vez conectado, crea la offer, la envía por TCP y espera la answer.
    La señalización TCP usa TcpSocketSignaling de aiortc — no necesita MQTT ni TURN.
    """
    import fractions
    from aiortc.contrib.signaling import TcpSocketSignaling

    # "0.0.0.0" = escuchar en todas las interfaces del PC
    # El dashboard se conectará a TCP_HOST:TCP_PORT como cliente
    signaling = TcpSocketSignaling("0.0.0.0", TCP_PORT)
    pc_cam    = RTCPeerConnection()
    pc_cam.addTrack(CameraTrack())

    @pc_cam.on("connectionstatechange")
    async def _(): print(f"[CAM] WebRTC {pc_cam.connectionState}")

    try:
        print(f"[CAM] Esperando cliente en 0.0.0.0:{TCP_PORT}...")
        await signaling.connect()   # bloquea hasta que el dashboard se conecta

        # Crear y enviar offer al dashboard
        offer = await pc_cam.createOffer()
        await pc_cam.setLocalDescription(offer)
        await signaling.send(pc_cam.localDescription)
        print("[CAM] Offer enviada — esperando answer...")

        # Esperar la answer del dashboard
        while True:
            obj = await signaling.receive()
            if isinstance(obj, RTCSessionDescription):
                await pc_cam.setRemoteDescription(obj)
                print("[CAM] Conexión local establecida ✓")
                break
            elif obj is None:
                print("[CAM] Fallo en la coordinación TCP")
                break

        # Mantener la conexión activa
        while pc_cam.connectionState not in ("failed", "closed"):
            await asyncio.sleep(1)

    except Exception as e:
        print(f"[CAM] Error local: {e}")
    finally:
        await pc_cam.close()


def start_camera_service_local():
    """Arranca el CameraService local en su propio hilo asyncio."""
    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_camera_local())

    threading.Thread(target=_run, daemon=True).start()
    print("[CAM] CameraService iniciado (modo local)")


# ══════════════════════════════════════════════════════════════════════════════
#  DETECCIÓN YOLO (compartida entre modos)
# ══════════════════════════════════════════════════════════════════════════════

def load_yolo():
    """Carga YOLOv5s en memoria (solo la primera vez, en hilo separado)."""
    global yolo_model
    if yolo_model is None:
        print("[DET] Cargando YOLOv5...")
        import torch
        yolo_model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
        yolo_model.eval()
        print("[DET] Modelo listo")

def set_detect(obj_id):
    global detect_object_id
    threading.Thread(target=load_yolo, daemon=True).start()
    detect_object_id = obj_id
    print(f"[DET] Detectando objeto ID={obj_id}")

def run_detect(frame):
    """Inferencia YOLO en executor — no bloquea el event loop asyncio."""
    if yolo_model is None or detect_object_id is None:
        return []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        results = yolo_model(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    return [tuple(map(int, box)) for *box, conf, cls in results.xyxy[0]
            if int(cls.item()) == detect_object_id]


# ══════════════════════════════════════════════════════════════════════════════
#  WEBRTC DASHBOARD (receptor de vídeo)
# ══════════════════════════════════════════════════════════════════════════════

async def show_video(track):
    """Recibe frames WebRTC y los muestra. YOLO cada 30 frames en executor."""
    print("[VIDEO] Mostrando frames...")
    frame_count, last_boxes = 0, []

    while True:
        try:
            frame = await asyncio.wait_for(track.recv(), timeout=5.0)
            if isinstance(frame, VideoFrame):
                img = frame.to_ndarray(format="bgr24")
                frame_count += 1
                if frame_count % 30 == 0 and detect_object_id is not None:
                    last_boxes = await asyncio.get_event_loop().run_in_executor(
                        None, run_detect, img.copy()
                    )
                for (x1, y1, x2, y2) in last_boxes:
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(img, "detected", (x1, y1-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.imshow("Video Dron", img)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        except asyncio.TimeoutError:
            print(f"[VIDEO] Timeout — ICE={pc.iceConnectionState}")
        except Exception as e:
            print(f"[VIDEO] {e}"); break
    cv2.destroyAllWindows()


def webrtc_thread_dashboard():
    """Hilo asyncio del dashboard — modo GLOBAL: espera offer via MQTT."""
    global pc, loop_dashboard, pending_offer

    loop_dashboard = asyncio.new_event_loop()
    asyncio.set_event_loop(loop_dashboard)
    loop_dashboard.set_exception_handler(_silence_aioice_handler)

    pc = RTCPeerConnection(configuration=get_ice_config())

    @pc.on("track")
    def on_track(track):
        if track.kind == "video":
            print("[VIDEO] ✓ Track recibido")
            asyncio.run_coroutine_threadsafe(show_video(track), loop_dashboard)

    @pc.on("connectionstatechange")
    async def _(): print(f"[WebRTC] {pc.connectionState}")

    @pc.on("iceconnectionstatechange")
    async def _(): print(f"[ICE] {pc.iceConnectionState}")

    print("[WebRTC] Dashboard listo (global)")
    if pending_offer:
        asyncio.run_coroutine_threadsafe(
            handle_offer_dashboard(pending_offer), loop_dashboard)
        pending_offer = None

    loop_dashboard.run_forever()


async def webrtc_receive_local():
    """Modo LOCAL: replica exactamente el videoReceiver() del dashboard original.

    El dashboard actúa de CLIENTE TCP — se conecta al CameraService que
    hace de servidor. No usa MQTT, no usa TURN, no usa ICE de Metered.
    Solo TcpSocketSignaling + RTCPeerConnection() básico, igual que el original.
    """
    from aiortc.contrib.signaling import TcpSocketSignaling
    from aiortc import MediaStreamTrack

    # Pequeña espera para asegurar que el servidor TCP del CameraService está listo
    await asyncio.sleep(0.8)

    signaling = TcpSocketSignaling(TCP_HOST, TCP_PORT)
    pc_local  = RTCPeerConnection()  # SIN ICE config — conexión local pura

    @pc_local.on("track")
    def on_track(track):
        if isinstance(track, MediaStreamTrack) and track.kind == "video":
            print("[VIDEO] ✓ Track recibido (local)")
            # ensure_future como en el original — no run_coroutine_threadsafe
            asyncio.ensure_future(show_video_local(track))

    @pc_local.on("connectionstatechange")
    async def _():
        print(f"[WebRTC] {pc_local.connectionState}")

    try:
        print(f"[VIDEO] Conectando al CameraService en {TCP_HOST}:{TCP_PORT}...")
        await signaling.connect()

        # Recibir offer del CameraService (servidor TCP)
        print("[VIDEO] Esperando offer...")
        offer = await signaling.receive()
        print("[VIDEO] Offer recibida")
        await pc_local.setRemoteDescription(offer)

        answer = await pc_local.createAnswer()
        await pc_local.setLocalDescription(answer)
        await signaling.send(pc_local.localDescription)
        print("[VIDEO] Answer enviada — esperando conexión...")

        # Esperar a que se establezca la conexión (igual que el original)
        while pc_local.connectionState != "connected":
            await asyncio.sleep(0.1)
        print("[VIDEO] Conexión establecida ✓")

        # Mantener activo
        while pc_local.connectionState not in ("failed", "closed"):
            await asyncio.sleep(1)

    except Exception as e:
        print(f"[VIDEO] Error local: {e}")
    finally:
        await pc_local.close()


async def show_video_local(track):
    """Muestra vídeo en modo local — misma lógica que show_video pero
    usando una pc_local independiente, sin referenciar la pc global."""
    print("[VIDEO] Mostrando frames (local)...")
    frame_count, last_boxes = 0, []

    while True:
        try:
            frame = await asyncio.wait_for(track.recv(), timeout=5.0)
            if isinstance(frame, VideoFrame):
                img = frame.to_ndarray(format="bgr24")
                frame_count += 1
                if frame_count % 30 == 0 and detect_object_id is not None:
                    last_boxes = await asyncio.get_event_loop().run_in_executor(
                        None, run_detect, img.copy()
                    )
                for (x1, y1, x2, y2) in last_boxes:
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(img, "detected", (x1, y1-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.imshow("Video Dron", img)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        except asyncio.TimeoutError:
            print("[VIDEO] Timeout esperando frame (local)")
        except Exception as e:
            print(f"[VIDEO] {e}"); break
    cv2.destroyAllWindows()


def webrtc_thread_dashboard_local():
    """Hilo asyncio del dashboard — modo LOCAL.
    Crea su propio event loop limpio, sin nada de ICE/TURN/MQTT."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(webrtc_receive_local())
    except Exception as e:
        print(f"[VIDEO] Hilo local terminó: {e}")


async def handle_offer_dashboard(data):
    """Procesa la offer del CameraService y responde con answer via MQTT."""
    await pc.setRemoteDescription(
        RTCSessionDescription(sdp=data["sdp"], type=data["type"])
    )
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    print("[WebRTC] Esperando ICE gathering...")
    while pc.iceGatheringState != "complete":
        await asyncio.sleep(0.2)

    candidates = [l for l in pc.localDescription.sdp.splitlines()
                  if l.startswith("a=candidate")]
    has_relay = any("relay" in c for c in candidates)
    print(f"[WebRTC] Answer lista — {'✓ relay' if has_relay else '⚠ sin relay'}")

    client_dashboard.publish(T_ANSWER, json.dumps({
        "sdp":  pc.localDescription.sdp,
        "type": pc.localDescription.type,
    }))
    print("[WebRTC] Answer enviada ✓")


def start_webrtc_dashboard():
    if MODE == "local":
        threading.Thread(target=webrtc_thread_dashboard_local, daemon=True).start()
    else:
        threading.Thread(target=webrtc_thread_dashboard, daemon=True).start()


def on_mqtt_message_dashboard(cli, userdata, msg):
    """Callback MQTT del dashboard: gestiona señalización WebRTC y telemetría."""
    global pending_offer
    topic = msg.topic
    try:
        data = json.loads(msg.payload)
    except:
        return

    if topic == T_OFFER:
        print("[SIG] Offer recibida")
        if loop_dashboard is None or pc is None:
            pending_offer = data
        else:
            asyncio.run_coroutine_threadsafe(
                handle_offer_dashboard(data), loop_dashboard)
        return

    if topic == 'autopilotServiceDemo/interfazGlobal/telemetryInfo':
        altShowLbl['text']     = f"{round(data.get('alt', 0), 1)} m"
        headingShowLbl['text'] = f"{round(data.get('heading', 0), 1)}°"
        stateShowLbl['text']   = data.get('state', '')
        speedShowLbl['text']   = f"{round(data.get('groundSpeed', 0), 1)} m/s"
        batt = data.get('battery_remaining')
        battShowLbl['text']    = f"{batt}%" if batt is not None else '--'
        lat = data.get('lat'); lon = data.get('lon')
        if lat and lon:
            gpsShowLbl['text'] = f"{lat:.5f}\n{lon:.5f}"
            update_map(lat, lon)
        else:
            gpsShowLbl['text'] = 'sin GPS'
    elif topic == 'autopilotServiceDemo/interfazGlobal/connected':
        connectBtn.configure(text='Conectado', fg='white', bg='green')
    elif topic == 'autopilotServiceDemo/interfazGlobal/flying':
        arm_takeOffBtn.configure(text='En el aire', fg='white', bg='green')
    elif topic == 'autopilotServiceDemo/interfazGlobal/landed':
        landBtn.configure(text='En tierra', fg='white', bg='green')
        threading.Thread(target=lambda: (time.sleep(5), _reset_btns()), daemon=True).start()
    elif topic == 'autopilotServiceDemo/interfazGlobal/atHome':
        RTLBtn.configure(text='En tierra', fg='white', bg='green')
        threading.Thread(target=lambda: (time.sleep(5), _reset_btns()), daemon=True).start()



# ══════════════════════════════════════════════════════════════════════════════
#  MAPA — lógica compartida entre ambos modos
# ══════════════════════════════════════════════════════════════════════════════

DEFAULT_LAT = 41.3851   # Barcelona — posición inicial si el dron aún no reporta GPS
DEFAULT_LON =  2.1734

def update_map(lat, lon):
    """Actualiza la posición del dron en el mapa.

    Llamada cada vez que llegan datos de telemetría con lat/lon.
    Mueve el marcador y añade el punto a la ruta trazada.
    Se llama desde el hilo MQTT (global) o dronLink (local) —
    usa after() para actualizar el widget Tkinter desde el hilo principal.
    """
    global drone_marker, drone_path, drone_path_line, drone_lat, drone_lon

    drone_lat, drone_lon = lat, lon
    drone_path.append((lat, lon))

    def _update():
        global drone_marker, drone_path_line
        if map_widget is None:
            return
        # Mover o crear el marcador del dron
        if drone_marker is None:
            drone_marker = map_widget.set_marker(
                lat, lon,
                text="🚁 Dron",
                marker_color_circle="red",
                marker_color_outside="darkred"
            )
        else:
            drone_marker.set_position(lat, lon)

        # Centrar el mapa en el dron (solo si está lejos del centro visible)
        drone_marker.set_position(lat, lon)

        # Actualizar la línea de ruta
        if len(drone_path) >= 2:
            if drone_path_line:
                drone_path_line.delete()
            drone_path_line = map_widget.set_path(
                drone_path[-200:],  # últimos 200 puntos para no saturar
                color="dodger blue",
                width=2
            )

    # Tkinter no es thread-safe — usar after(0, ...) para ejecutar en el hilo principal
    if map_widget:
        map_widget.after(0, _update)


def on_map_click(coords):
    """Callback al hacer clic en el mapa.

    Coloca un marcador de destino y envía al dron las coordenadas GPS
    usando el comando go_to_gps del dronLink o via MQTT según el modo.
    """
    global target_marker
    lat, lon = coords

    # Marcador de destino
    def _mark():
        global target_marker
        if target_marker:
            target_marker.delete()
        target_marker = map_widget.set_marker(
            lat, lon,
            text="📍 Destino",
            marker_color_circle="green",
            marker_color_outside="darkgreen"
        )

    if map_widget:
        map_widget.after(0, _mark)

    # Enviar al dron
    if _goto_callback:
        _goto_callback(lat, lon)
    print(f"[MAP] Ir a → lat={lat:.6f}, lon={lon:.6f}")


# ── Callbacks go_to_gps según modo ───────────────────────────────────────────

def goto_gps_global(lat, lon):
    """Envía el comando goto al dron via MQTT.

    El AutopilotService recibirá lat, lon y alt y llamará a dron.goto().
    La altitud se lee de la label de telemetría para mantener la altitud actual.
    """
    if client_dashboard:
        try:
            alt_str = altShowLbl['text'].replace(' m', '').strip()
            alt = float(alt_str) if alt_str else 5.0
        except:
            alt = 5.0
        payload = json.dumps({"lat": lat, "lon": lon, "alt": alt})
        client_dashboard.publish(
            'interfazGlobal/autopilotServiceDemo/goto', payload)
        print(f"[MAP] MQTT goto → lat={lat:.6f}, lon={lon:.6f}, alt={alt}m")


def goto_gps_local(lat, lon):
    """Navega al punto GPS indicado via dronLink.

    Usa dron.goto(lat, lon, alt) — la altitud se toma de la última
    telemetría recibida para mantener la altitud de vuelo actual.
    Si aún no hay telemetría, usa 5 m como valor por defecto.
    blocking=False para no bloquear el hilo de la GUI.
    """
    try:
        alt = drone_lat and drone_lon  # reutilizamos la alt de telemetría
        # Obtener la altitud actual del dron desde la label si está disponible
        try:
            alt_str = altShowLbl['text'].replace(' m', '').strip()
            alt = float(alt_str) if alt_str else 5.0
        except:
            alt = 5.0
        dron.goto(lat, lon, alt, blocking=False)
        print(f"[MAP] dronLink goto → lat={lat:.6f}, lon={lon:.6f}, alt={alt}m")
    except Exception as e:
        print(f"[MAP] Error goto: {e}")

# ══════════════════════════════════════════════════════════════════════════════
#  CONTROL DEL DRON
# ══════════════════════════════════════════════════════════════════════════════

def _reset_btns():
    for b, t in [(arm_takeOffBtn,'Armar'),(landBtn,'Aterrizar'),(RTLBtn,'RTL')]:
        b.configure(text=t, fg='black', bg='dark orange')

# Modo Global — publica comandos MQTT que recibe el AutopilotService integrado
def connect_global():
    client_dashboard.publish('interfazGlobal/autopilotServiceDemo/connect')
    connectBtn.configure(text='Conectado', fg='white', bg='green')
    speedSldr.set(1)

def takeoff_global():
    client_dashboard.publish('interfazGlobal/autopilotServiceDemo/arm_takeOff', '5')
    arm_takeOffBtn.configure(text='Despegando...', fg='black', bg='yellow')

def land_global():
    client_dashboard.publish('interfazGlobal/autopilotServiceDemo/Land')
    landBtn.configure(text='Aterrizando...', fg='black', bg='yellow')

def RTL_global():
    client_dashboard.publish('interfazGlobal/autopilotServiceDemo/RTL')
    RTLBtn.configure(text='Retornando...', fg='black', bg='yellow')

def go_global(direction, btn):
    global previousBtn
    if previousBtn: previousBtn.configure(fg='black', bg='dark orange')
    client_dashboard.publish('interfazGlobal/autopilotServiceDemo/go', direction)
    btn.configure(fg='white', bg='green')
    previousBtn = btn

def startTelem_global(): client_dashboard.publish('interfazGlobal/autopilotServiceDemo/startTelemetry')
def stopTelem_global():  client_dashboard.publish('interfazGlobal/autopilotServiceDemo/stopTelemetry')
def changeHeading_global(e): client_dashboard.publish('interfazGlobal/autopilotServiceDemo/changeHeading', str(gradesSldr.get()))
def changeNavSpeed_global(e): client_dashboard.publish('interfazGlobal/autopilotServiceDemo/changeNavSpeed', str(speedSldr.get()))

# Modo Local — habla directamente con dronLink
def connect_local():
    dron.connect('tcp:127.0.0.1:5763', 115200)
    connectBtn.configure(text='Conectado', fg='white', bg='green')
    speedSldr.set(1)

def takeoff_local():
    dron.arm()
    dron.takeOff(5, blocking=False,
                 callback=lambda: arm_takeOffBtn.configure(text='En el aire', fg='white', bg='green'))
    arm_takeOffBtn.configure(text='Despegando...', fg='black', bg='yellow')

def land_local():
    dron.Land()
    landBtn.configure(text='Aterrizando...', fg='black', bg='yellow')

def RTL_local():
    dron.RTL()
    RTLBtn.configure(text='Retornando...', fg='black', bg='yellow')

def go_local(direction, btn):
    global previousBtn
    if previousBtn: previousBtn.configure(fg='black', bg='dark orange')
    dron.go(direction)
    btn.configure(fg='white', bg='green')
    previousBtn = btn

def startTelem_local():
    def _update(info):
        altShowLbl['text']     = f"{round(info.get('alt', 0), 1)} m"
        headingShowLbl['text'] = f"{round(info.get('heading', 0), 1)}°"
        stateShowLbl['text']   = info.get('state', '')
        speedShowLbl['text']   = f"{round(info.get('groundSpeed', 0), 1)} m/s"
        batt = info.get('battery_remaining')
        battShowLbl['text']    = f"{batt}%" if batt is not None else '--'
        lat = info.get('lat'); lon = info.get('lon')
        if lat and lon:
            gpsShowLbl['text'] = f"{lat:.5f}\n{lon:.5f}"
            update_map(lat, lon)
        else:
            gpsShowLbl['text'] = 'sin GPS'
    dron.send_telemetry_info(_update)

def stopTelem_local():  dron.stop_sending_telemetry_info()
def changeHeading_local(e):  dron.changeHeading(int(gradesSldr.get()))
def changeNavSpeed_local(e): dron.changeNavSpeed(float(speedSldr.get()))


# ══════════════════════════════════════════════════════════════════════════════
#  GUI
# ══════════════════════════════════════════════════════════════════════════════

def crear_ventana(modo):
    global client_dashboard
    global altShowLbl, headingShowLbl, stateShowLbl
    global speedShowLbl, battShowLbl, gpsShowLbl
    global connectBtn, arm_takeOffBtn, landBtn, RTLBtn
    global speedSldr, gradesSldr, previousBtn

    if modo == "global":
        # ── Arrancar servicios integrados ─────────────────────────────────────
        start_autopilot_service()    # AutopilotService en su hilo
        start_camera_service_global() # CameraService en su hilo

        # ── Cliente MQTT del dashboard ────────────────────────────────────────
        client_dashboard = mqtt.Client(client_id="DashboardGlobal", transport="websockets")
        client_dashboard.ws_set_options(path="/mqtt")
        client_dashboard.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
        client_dashboard.username_pw_set(USER_DASHBOARD, PASS_DASHBOARD)
        client_dashboard.on_message = on_mqtt_message_dashboard
        client_dashboard.on_connect = lambda c,u,f,rc: print("[MQTT] Dashboard conectado" if rc==0 else f"[MQTT] Error {rc}")
        client_dashboard.connect(BROKER_DASHBOARD, PORT)
        client_dashboard.subscribe('autopilotServiceDemo/interfazGlobal/#')
        client_dashboard.subscribe(T_OFFER)
        client_dashboard.loop_start()

        _connect = connect_global;  _takeoff = takeoff_global
        _land    = land_global;     _RTL     = RTL_global
        _go      = go_global;       _video   = start_webrtc_dashboard
        _startT  = startTelem_global; _stopT = stopTelem_global
        _heading = changeHeading_global; _speed = changeNavSpeed_global
        titulo   = "Dashboard Dron — Modo Global 🌐"

    else:  # local
        start_camera_service_local()  # CameraService local en su hilo

        _connect = connect_local;   _takeoff = takeoff_local
        _land    = land_local;      _RTL     = RTL_local
        _go      = go_local;        _video   = start_webrtc_dashboard
        _startT  = startTelem_local; _stopT  = stopTelem_local
        _heading = changeHeading_local; _speed = changeNavSpeed_local
        titulo   = "Dashboard Dron — Modo Local 🔌"

    # ── Ventana principal: dos paneles side-by-side ──────────────────────────
    # Columna 0: controles del dron (ancho fijo ~300px)
    # Columna 1: mapa tkintermapview (se expande con la ventana)
    v = tk.Tk()
    v.title(titulo)
    v.columnconfigure(0, weight=0, minsize=310)  # panel controles
    v.columnconfigure(1, weight=1)               # panel mapa — se expande
    v.rowconfigure(0, weight=1)

    # ── Panel izquierdo: controles ────────────────────────────────────────────
    ctrl = tk.Frame(v)
    ctrl.grid(row=0, column=0, sticky="nsew", padx=(4,2), pady=4)
    for i in range(13): ctrl.rowconfigure(i, weight=1)
    ctrl.columnconfigure(0, weight=1); ctrl.columnconfigure(1, weight=1)

    def btn(text, cmd, row, col=0, cs=2, bg="dark orange", parent=None):
        p = parent or ctrl
        b = tk.Button(p, text=text, bg=bg, command=cmd)
        b.grid(row=row, column=col, columnspan=cs, padx=5, pady=3, sticky="nsew")
        return b

    connectBtn     = btn("Conectar",  _connect, 0)
    arm_takeOffBtn = btn("Despegar",  _takeoff, 1)
    landBtn        = btn("Aterrizar", _land,    5, col=0, cs=1)
    RTLBtn         = btn("RTL",       _RTL,     5, col=1, cs=1)

    gradesSldr = tk.Scale(ctrl, label="Grados:", resolution=5, from_=0, to=360,
                          tickinterval=45, orient=tk.HORIZONTAL)
    gradesSldr.grid(row=4, column=0, columnspan=2, padx=5, pady=3, sticky="nsew")
    gradesSldr.bind("<ButtonRelease-1>", _heading)

    nf = tk.LabelFrame(ctrl, text="Navegación")
    nf.grid(row=6, column=0, columnspan=2, padx=8, pady=3, sticky="nsew")
    for i in range(3): nf.rowconfigure(i, weight=1); nf.columnconfigure(i, weight=1)
    dirs = [("NW","NorthWest",0,0),("N","North",0,1),("NE","NorthEast",0,2),
            ("W","West",1,0),("Stop","Stop",1,1),("E","East",1,2),
            ("SW","SouthWest",2,0),("S","South",2,1),("SE","SouthEast",2,2)]
    for label, direction, r, c in dirs:
        b = tk.Button(nf, text=label, bg="dark orange")
        b.configure(command=lambda d=direction, x=b: _go(d, x))
        b.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")

    speedSldr = tk.Scale(ctrl, label="Velocidad (m/s):", resolution=1, from_=0, to=20,
                         tickinterval=5, orient=tk.HORIZONTAL)
    speedSldr.grid(row=7, column=0, columnspan=2, padx=5, pady=3, sticky="nsew")
    speedSldr.bind("<ButtonRelease-1>", _speed)

    btn("Empezar telemetría", _startT, 8, col=0, cs=1)
    btn("Parar telemetría",   _stopT,  8, col=1, cs=1)

    tf = tk.LabelFrame(ctrl, text="Telemetría")
    tf.grid(row=9, column=0, columnspan=2, padx=5, pady=3, sticky="nsew")
    for i in range(6): tf.columnconfigure(i, weight=1)
    for txt, col in [("Altitud",0),("Heading",1),("Estado",2),("Vel.",3),("Batería",4),("GPS",5)]:
        tk.Label(tf, text=txt, font=("Arial",7,"bold")).grid(row=0, column=col, padx=2, pady=1)
    altShowLbl     = tk.Label(tf, text=''); altShowLbl.grid(row=1, column=0, padx=2)
    headingShowLbl = tk.Label(tf, text=''); headingShowLbl.grid(row=1, column=1, padx=2)
    stateShowLbl   = tk.Label(tf, text=''); stateShowLbl.grid(row=1, column=2, padx=2)
    speedShowLbl   = tk.Label(tf, text=''); speedShowLbl.grid(row=1, column=3, padx=2)
    battShowLbl    = tk.Label(tf, text=''); battShowLbl.grid(row=1, column=4, padx=2)
    gpsShowLbl     = tk.Label(tf, text=''); gpsShowLbl.grid(row=1, column=5, padx=2)

    btn("▶ Ver video del dron", _video, 10)

    df = tk.LabelFrame(ctrl, text="Detección de objetos")
    df.grid(row=11, column=0, columnspan=2, padx=5, pady=3, sticky="nsew")
    for i in range(4): df.columnconfigure(i, weight=1)
    for col, (name, oid) in enumerate([("Banana",46),("Reloj",74),("Pizza",53),("Bicicleta",1)]):
        tk.Button(df, text=name, bg="dark orange",
                  command=lambda o=oid: set_detect(o)).grid(
            row=0, column=col, padx=5, pady=5, sticky="nsew")

    # ── Panel derecho: mapa ───────────────────────────────────────────────────
    global map_widget, _goto_callback

    map_frame = tk.LabelFrame(v, text="Mapa — clic para enviar el dron al punto")
    map_frame.grid(row=0, column=1, sticky="nsew", padx=(2,4), pady=4)
    map_frame.rowconfigure(0, weight=1)
    map_frame.columnconfigure(0, weight=1)

    map_widget = tkintermapview.TkinterMapView(
        map_frame, width=600, height=700, corner_radius=4)
    map_widget.grid(row=0, column=0, sticky="nsew")

    # Posición inicial — Barcelona por defecto, se recentrará al llegar GPS
    map_widget.set_position(DEFAULT_LAT, DEFAULT_LON)
    map_widget.set_zoom(15)

    # Registrar el callback de clic al mapa
    map_widget.add_left_click_map_command(on_map_click)

    # Asignar la función go_to_gps correcta según el modo
    _goto_callback = goto_gps_global if modo == "global" else goto_gps_local

    # Botones de control del mapa (zoom + centrar en dron)
    map_ctrl = tk.Frame(map_frame)
    map_ctrl.grid(row=1, column=0, sticky="ew", pady=2)
    map_ctrl.columnconfigure(0, weight=1)
    map_ctrl.columnconfigure(1, weight=1)
    map_ctrl.columnconfigure(2, weight=1)

    def center_on_drone():
        if drone_lat and drone_lon:
            map_widget.set_position(drone_lat, drone_lon)
            map_widget.set_zoom(17)

    def clear_path():
        global drone_path, drone_path_line
        drone_path = []
        if drone_path_line:
            drone_path_line.delete()
            drone_path_line = None

    tk.Button(map_ctrl, text="🎯 Centrar en dron",  bg="dark orange",
              command=center_on_drone).grid(row=0, column=0, padx=3, pady=3, sticky="ew")
    tk.Button(map_ctrl, text="🗑 Borrar ruta",       bg="dark orange",
              command=clear_path).grid(row=0, column=1, padx=3, pady=3, sticky="ew")
    tk.Button(map_ctrl, text="🗺 OpenStreetMap",     bg="dark orange",
              command=lambda: map_widget.set_tile_server(
                  "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png")
              ).grid(row=0, column=2, padx=3, pady=3, sticky="ew")

    # Tamaño inicial de la ventana
    v.geometry("950x750")

    return v


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    modo = selector_modo()
    MODE = modo   # asignar variable global antes de crear la ventana
    print(f"[MAIN] Modo: {modo}")
    crear_ventana(modo).mainloop()