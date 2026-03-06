# =====================================================
#  DASHBOARD
#  pip install aiortc paho-mqtt av opencv-python requests
# =====================================================

import asyncio, json, ssl, threading, time, requests
import logging
import warnings

# YOLOv5 usa torch.cuda.amp.autocast() que está deprecado en versiones nuevas
# de PyTorch. El warning sale en cada inferencia y llena la consola — lo
# silenciamos globalmente aquí antes de que se importe torch.
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# aioice es la librería interna que aiortc usa para ICE/STUN/TURN.
# Genera logs propios que no queremos ver en la consola.
# CRITICAL significa que solo mostrará errores absolutamente fatales.
logging.getLogger("aioice").setLevel(logging.CRITICAL)
logging.getLogger("aioice.turn").setLevel(logging.CRITICAL)

import cv2, tkinter as tk
import paho.mqtt.client as mqtt
from aiortc import (RTCPeerConnection, RTCSessionDescription,
                    RTCConfiguration, RTCIceServer)
from av import VideoFrame

# ── Configuración MQTT (HiveMQ Cloud) ────────────────────────────────────────
BROKER  = "554f19f1f4944c978dd30b509d24afc0.s1.eu.hivemq.cloud"
PORT    = 8884
USER    = "InterfazGlobal"
PASS    = "Kb2avDJmV2aj!Jz"

# Topics usados para el intercambio de señalización WebRTC:
#   - T_OFFER:  el camera_service publica aquí su SDP offer al arrancar
#   - T_ANSWER: el dashboard publica aquí su SDP answer como respuesta
T_OFFER  = "webrtc/offer"
T_ANSWER = "webrtc/answer"

# URL de la API de Metered para obtener credenciales TURN dinámicas.
# Metered devuelve una lista de servidores ICE (STUN + TURN) con usuario
# y contraseña temporales — más seguro que hardcodear credenciales fijas.
METERED_API = "https://testconection1.metered.live/api/v1/turn/credentials?apiKey=57312a00508de97f6ca0758cce3935fe7670"

# ── Variables globales de estado ──────────────────────────────────────────────
pc            = None   # RTCPeerConnection — gestiona la conexión WebRTC
loop          = None   # event loop de asyncio del hilo WebRTC
client        = None   # cliente MQTT
pending_offer = None   # si la offer llega antes de pulsar el botón, se guarda aquí
previousBtn   = None   # botón de navegación activo, para resetear su color

altShowLbl = headingShowLbl = stateShowLbl = None
connectBtn = arm_takeOffBtn = landBtn = RTLBtn = None
speedSldr  = gradesSldr = None

# ── Detección de objetos (YOLOv5) ─────────────────────────────────────────────
# detect_object_id: ID de clase COCO del objeto a detectar (None = sin detección)
# yolo_model: modelo cargado en memoria, None hasta que el usuario pulse un botón
detect_object_id = None
yolo_model       = None


def load_yolo():
    """Carga el modelo YOLOv5s en memoria (solo la primera vez).
    Se llama en un hilo separado para no bloquear la GUI mientras descarga/carga."""
    global yolo_model
    if yolo_model is None:
        print("[DET] Cargando YOLOv5...")
        import torch
        yolo_model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
        yolo_model.eval()
        print("[DET] Modelo listo")
    return yolo_model


def set_detect(obj_id):
    """Llamada al pulsar un botón de detección.
    Lanza la carga del modelo en segundo plano y activa la detección."""
    global detect_object_id
    # Cargar YOLO en un hilo daemon para no congelar la interfaz
    threading.Thread(target=load_yolo, daemon=True).start()
    detect_object_id = obj_id
    print(f"[DET] Detectando objeto ID={obj_id}")


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


# ── Hilo WebRTC ───────────────────────────────────────────────────────────────

def webrtc_thread():
    """Corre el event loop de asyncio en un hilo separado.

    Tkinter (la GUI) ya ocupa el hilo principal con su propio loop de eventos.
    WebRTC necesita asyncio para manejar operaciones asíncronas (ICE, SDP...).
    La solución es crear un segundo hilo con su propio event loop de asyncio.
    """
    global pc, loop, pending_offer

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # aioice genera tareas asyncio internas que a veces fallan con error 401
    # al intentar optimizar la conexión TURN con CHANNEL_BIND. Este error
    # no afecta al funcionamiento (el video sigue llegando por relay), pero
    # asyncio lo imprime como "Task exception was never retrieved".
    # set_exception_handler() intercepta esos errores antes de que se impriman.
    def _silence_aioice(loop, context):
        exc = context.get("exception", None)
        msg = context.get("message", "")
        if "TransactionFailed" in str(type(exc).__name__) or "aioice" in str(exc):
            return  # silenciar — es ruido interno de aioice, no un error real
        if "CHANNEL_BIND" in msg or "TransactionFailed" in msg:
            return
        loop.default_exception_handler(context)  # otros errores sí mostrarlos

    loop.set_exception_handler(_silence_aioice)

    ice_config = get_ice_config()
    pc = RTCPeerConnection(configuration=ice_config)

    @pc.on("track")
    def on_track(track):
        # Cuando el camera_service establece la conexión, empieza a enviar
        # el track de vídeo. Lo recibimos aquí y lanzamos la visualización.
        if track.kind == "video":
            print("[WebRTC] ✓ Track recibido")
            asyncio.run_coroutine_threadsafe(show_video(track), loop)

    @pc.on("connectionstatechange")
    async def _(): print(f"[WebRTC] {pc.connectionState}")

    @pc.on("iceconnectionstatechange")
    async def _(): print(f"[ICE] {pc.iceConnectionState}")

    @pc.on("icegatheringstatechange")
    async def _(): print(f"[ICE gathering] {pc.iceGatheringState}")

    print("[WebRTC] Hilo listo")

    # Si la offer llegó por MQTT antes de que el usuario pulsara el botón
    # de vídeo, la procesamos ahora que pc ya está inicializado.
    if pending_offer:
        print("[WebRTC] Procesando offer pendiente...")
        asyncio.run_coroutine_threadsafe(handle_offer(pending_offer), loop)
        pending_offer = None

    loop.run_forever()


def start_webrtc():
    """Lanzado al pulsar '▶ Ver video del dron'.
    Arranca el hilo WebRTC con su propio event loop asyncio."""
    threading.Thread(target=webrtc_thread, daemon=True).start()
    print("[GUI] WebRTC iniciado")


# ── Señalización SDP ──────────────────────────────────────────────────────────

async def handle_offer(data):
    """Procesa la SDP offer del camera_service y responde con una answer.

    Flujo de señalización WebRTC (igual que el codelab de Firebase pero
    usando MQTT en lugar de Firestore):
      1. camera_service crea una offer con su SDP y la publica en MQTT
      2. Dashboard la recibe aquí, la aplica como remoteDescription
      3. Dashboard crea su answer y la publica en MQTT
      4. camera_service aplica la answer como remoteDescription
      5. ICE negotiation completa → conexión establecida → vídeo fluye
    """
    await pc.setRemoteDescription(
        RTCSessionDescription(sdp=data["sdp"], type=data["type"])
    )
    print("[SIG] Offer aplicada")

    # Mostrar qué tipos de candidates trajo la offer para diagnóstico:
    # 'host'  = IP local (solo funciona en misma red)
    # 'srflx' = IP pública via STUN (puede fallar con NAT simétrico)
    # 'relay' = tráfico por servidor TURN (funciona en cualquier red)
    candidates = [l for l in data["sdp"].splitlines() if l.startswith("a=candidate")]
    print(f"[SIG] Candidates en offer ({len(candidates)}):")
    for c in candidates:
        tipo = "✓ RELAY" if "relay" in c else "  host/srflx"
        print(f"  {tipo}: {c[12:80]}")

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    # aiortc no implementa trickle ICE (envío de candidates uno a uno).
    # En su lugar, espera a que el gathering esté completo y embute
    # todos los candidates directamente en el SDP de la answer.
    print("[WebRTC] Esperando ICE gathering (STUN + TURN)...")
    while pc.iceGatheringState != "complete":
        await asyncio.sleep(0.2)

    candidates_ans = [l for l in pc.localDescription.sdp.splitlines() if l.startswith("a=candidate")]
    print(f"[SIG] Candidates en answer ({len(candidates_ans)}):")
    for c in candidates_ans:
        tipo = "✓ RELAY" if "relay" in c else "  host/srflx"
        print(f"  {tipo}: {c[12:80]}")

    if not any("relay" in c for c in candidates_ans):
        print("[WARN] Sin candidates relay en answer.")
    else:
        print("[OK] Candidates relay presentes ✓")

    # Publicar la answer con el SDP completo (candidates incluidos)
    client.publish(T_ANSWER, json.dumps({
        "sdp":  pc.localDescription.sdp,
        "type": pc.localDescription.type,
    }))
    print("[SIG] Answer enviada ✓")


# ── Detección y visualización ─────────────────────────────────────────────────

def run_detect(frame):
    """Ejecuta inferencia YOLOv5 sobre un frame y devuelve bounding boxes.

    Se llama mediante run_in_executor() para correr en un ThreadPoolExecutor,
    evitando que el event loop asyncio se bloquee durante la inferencia
    (que en CPU puede tardar ~0.5-1 segundo por frame).
    """
    if yolo_model is None or detect_object_id is None:
        return []
    # Suprimir warnings de PyTorch dentro de la inferencia — YOLOv5 usa
    # torch.cuda.amp.autocast() que está deprecado, y el warning saldría
    # en cada llamada sin este contexto.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = yolo_model(img_rgb)
    boxes = []
    for *box, conf, cls in results.xyxy[0]:
        if int(cls.item()) == detect_object_id:
            boxes.append(tuple(map(int, box)))
    return boxes


async def show_video(track):
    """Recibe frames WebRTC y los muestra en una ventana OpenCV.

    Diseño clave: separación entre recepción y detección.
    - Los frames llegan continuamente por WebRTC y se muestran en tiempo real.
    - YOLO solo se ejecuta cada `detect_every` frames (en hilo separado).
    - Los bounding boxes del último análisis se redibujan en todos los frames
      intermedios, dando sensación de detección continua sin coste de CPU.
    """
    print("[VIDEO] Mostrando frames...")
    frame_count  = 0
    last_boxes   = []   # bounding boxes del último análisis YOLO
    detect_every = 30   # ejecutar YOLO cada 30 frames (~1 vez/segundo a 30fps)

    while True:
        try:
            frame = await asyncio.wait_for(track.recv(), timeout=5.0)
            if isinstance(frame, VideoFrame):
                img = frame.to_ndarray(format="bgr24")
                frame_count += 1

                # Lanzar detección en executor (hilo del SO) cada N frames.
                # run_in_executor permite que asyncio siga procesando mientras
                # YOLO corre en paralelo — el event loop no se bloquea.
                if frame_count % detect_every == 0 and detect_object_id is not None:
                    img_copy = img.copy()  # copia para no modificar el frame que se muestra
                    last_boxes = await asyncio.get_event_loop().run_in_executor(
                        None, run_detect, img_copy
                    )

                # Dibujar los boxes del último análisis sobre el frame actual
                for (x1, y1, x2, y2) in last_boxes:
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(img, "detected", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                cv2.imshow("Video Dron", img)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        except asyncio.TimeoutError:
            # Si en 5 segundos no llega ningún frame, la conexión ICE
            # probablemente está en checking/failed. Se muestra el estado.
            print(f"[VIDEO] Timeout — ICE={pc.iceConnectionState}")
        except Exception as e:
            print(f"[VIDEO] {e}"); break
    cv2.destroyAllWindows()


# ── MQTT callbacks ────────────────────────────────────────────────────────────

def on_connect(mqtt_client, userdata, flags, rc):
    print("[MQTT] Conectado" if rc == 0 else f"[MQTT] Error {rc}")

def on_message(mqtt_client, userdata, msg):
    global pending_offer
    topic = msg.topic
    try:
        data = json.loads(msg.payload)
    except:
        return

    if topic == T_OFFER:
        print("[SIG] Offer recibida")
        if loop is None or pc is None:
            # El usuario aún no pulsó el botón de vídeo — guardamos la offer
            # para procesarla en cuanto el hilo WebRTC esté listo.
            pending_offer = data
        else:
            # El hilo WebRTC ya está corriendo — procesamos directamente.
            # run_coroutine_threadsafe permite llamar a una corrutina asyncio
            # desde un hilo distinto (el hilo del callback MQTT).
            asyncio.run_coroutine_threadsafe(handle_offer(data), loop)
        return

    # Telemetría y estados del dron
    if topic == 'autopilotServiceDemo/interfazGlobal/telemetryInfo':
        altShowLbl['text']     = round(data.get('alt', 0), 2)
        headingShowLbl['text'] = round(data.get('heading', 0), 2)
        stateShowLbl['text']   = data.get('state', '')
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


# ── Control del dron ──────────────────────────────────────────────────────────

def _reset_btns():
    for b, t in [(arm_takeOffBtn,'Armar'),(landBtn,'Aterrizar'),(RTLBtn,'RTL')]:
        b.configure(text=t, fg='black', bg='dark orange')

def connect():
    client.publish('interfazGlobal/autopilotServiceDemo/connect')
    connectBtn.configure(text='Conectado', fg='white', bg='green')
    speedSldr.set(1)

def takeoff():
    client.publish('interfazGlobal/autopilotServiceDemo/arm_takeOff', '5')
    arm_takeOffBtn.configure(text='Despegando...', fg='black', bg='yellow')

def land():
    client.publish('interfazGlobal/autopilotServiceDemo/Land')
    landBtn.configure(text='Aterrizando...', fg='black', bg='yellow')

def RTL():
    client.publish('interfazGlobal/autopilotServiceDemo/RTL')
    RTLBtn.configure(text='Retornando...', fg='black', bg='yellow')

def go(direction, btn):
    global previousBtn
    if previousBtn: previousBtn.configure(fg='black', bg='dark orange')
    client.publish('interfazGlobal/autopilotServiceDemo/go', direction)
    btn.configure(fg='white', bg='green')
    previousBtn = btn

def startTelem(): client.publish('interfazGlobal/autopilotServiceDemo/startTelemetry')
def stopTelem():  client.publish('interfazGlobal/autopilotServiceDemo/stopTelemetry')
def changeHeading(e):  client.publish('interfazGlobal/autopilotServiceDemo/changeHeading', str(gradesSldr.get()))
def changeNavSpeed(e): client.publish('interfazGlobal/autopilotServiceDemo/changeNavSpeed', str(speedSldr.get()))


# ── GUI (Tkinter) ─────────────────────────────────────────────────────────────

def crear_ventana():
    global client
    global altShowLbl, headingShowLbl, stateShowLbl
    global connectBtn, arm_takeOffBtn, landBtn, RTLBtn
    global speedSldr, gradesSldr, previousBtn

    # Conectar MQTT al arrancar la ventana — así recibimos la offer
    # aunque el usuario no haya pulsado el botón de vídeo todavía
    client = mqtt.Client(client_id="DashboardGlobal", transport="websockets")
    client.ws_set_options(path="/mqtt")
    client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
    client.username_pw_set(USER, PASS)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT)
    client.subscribe('autopilotServiceDemo/interfazGlobal/#')
    client.subscribe(T_OFFER)
    client.loop_start()  # loop_start() corre MQTT en su propio hilo — no bloquea Tkinter

    v = tk.Tk()
    v.title("Dashboard Dron")
    for i in range(13): v.rowconfigure(i, weight=1)
    v.columnconfigure(0, weight=1); v.columnconfigure(1, weight=1)

    def btn(text, cmd, row, col=0, cs=2, bg="dark orange"):
        b = tk.Button(v, text=text, bg=bg, command=cmd)
        b.grid(row=row, column=col, columnspan=cs, padx=5, pady=5, sticky="nsew")
        return b

    connectBtn     = btn("Conectar",  connect,  0)
    arm_takeOffBtn = btn("Despegar",  takeoff,  1)
    landBtn        = btn("Aterrizar", land,     5, col=0, cs=1)
    RTLBtn         = btn("RTL",       RTL,      5, col=1, cs=1)

    gradesSldr = tk.Scale(v, label="Grados:", resolution=5, from_=0, to=360,
                          tickinterval=45, orient=tk.HORIZONTAL)
    gradesSldr.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
    gradesSldr.bind("<ButtonRelease-1>", changeHeading)

    nf = tk.LabelFrame(v, text="Navegación")
    nf.grid(row=6, column=0, columnspan=2, padx=50, pady=5, sticky="nsew")
    for i in range(3): nf.rowconfigure(i, weight=1); nf.columnconfigure(i, weight=1)
    dirs = [("NW","NorthWest",0,0),("N","North",0,1),("NE","NorthEast",0,2),
            ("W","West",1,0),("Stop","Stop",1,1),("E","East",1,2),
            ("SW","SouthWest",2,0),("S","South",2,1),("SE","SouthEast",2,2)]
    for label, direction, r, c in dirs:
        b = tk.Button(nf, text=label, bg="dark orange")
        b.configure(command=lambda d=direction, x=b: go(d, x))
        b.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")

    speedSldr = tk.Scale(v, label="Velocidad (m/s):", resolution=1, from_=0, to=20,
                         tickinterval=5, orient=tk.HORIZONTAL)
    speedSldr.grid(row=7, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
    speedSldr.bind("<ButtonRelease-1>", changeNavSpeed)

    btn("Empezar telemetría", startTelem, 8, col=0, cs=1)
    btn("Parar telemetría",   stopTelem,  8, col=1, cs=1)

    tf = tk.LabelFrame(v, text="Telemetría")
    tf.grid(row=9, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
    for i in range(3): tf.columnconfigure(i, weight=1)
    for txt, col in [("Altitud",0),("Heading",1),("Estado",2)]:
        tk.Label(tf, text=txt).grid(row=0, column=col, padx=5, pady=2)
    altShowLbl     = tk.Label(tf, text=''); altShowLbl.grid(row=1, column=0)
    headingShowLbl = tk.Label(tf, text=''); headingShowLbl.grid(row=1, column=1)
    stateShowLbl   = tk.Label(tf, text=''); stateShowLbl.grid(row=1, column=2)

    btn("▶ Ver video del dron", start_webrtc, 10)

    # Botones de detección — cada uno activa YOLO con un ID de clase COCO distinto.
    # Al pulsar, set_detect() carga el modelo (si aún no está cargado) y
    # activa la detección en show_video() a partir del siguiente ciclo.
    df = tk.LabelFrame(v, text="Detección de objetos")
    df.grid(row=11, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
    for i in range(4): df.columnconfigure(i, weight=1)
    for col, (name, oid) in enumerate([("Banana",46),("Reloj",74),("Pizza",53),("Bicicleta",1)]):
        tk.Button(df, text=name, bg="dark orange",
                  command=lambda o=oid: set_detect(o)).grid(
            row=0, column=col, padx=5, pady=5, sticky="nsew")

    return v


if __name__ == "__main__":
    crear_ventana().mainloop()