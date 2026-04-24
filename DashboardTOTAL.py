# =====================================================
#  DASHBOARD INTEGRADO
#  Incluye Dashboard + AutopilotService + CameraService
#  T0do en un solo archivo — no hay que ejecutar nada más
#
#  Modo Global: MQTT (HiveMQ) + WebRTC + TURN (Metered)
#  Modo Local:  dronLink directo + TcpSocketSignaling
#
#  pip install aiortc paho-mqtt av opencv-python requests

#mavproxy --master=com3 --out=udp:127.0.0.1:14550 --out=udp:127.0.0.1:14551
# =====================================================

import asyncio, json, ssl, threading, time, requests, sys
import logging, warnings
from datetime import datetime, timedelta

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

BROKER_DASHBOARD = "554f19f1f4944c978dd30b509d24afc0.s1.eu.hivemq.cloud"
PORT             = 8884

METERED_API = "https://testconection1.metered.live/api/v1/turn/credentials?apiKey=57312a00508de97f6ca0758cce3935fe7670"

HIVEMQ_USERS = [
    {"user": "InterfazGlobal",  "password": "Kb2avDJmV2aj!Jz"},   # slot 1
    {"user": "Client1",  "password": "GhJpQCxh_ktB4J9"},           # slot 2
    {"user": "Client2",  "password": "GhJpQCxh_ktB4J9"},           # slot 3
    {"user": "Client3",  "password": "GhJpQCxh_ktB4J9"},           # slot 4
]

USER_AUTOPILOT = "autopilotServiceDemo"
PASS_AUTOPILOT = "qkdb!LasqvHfy9V"

T_CAM_REQUEST = "webrtc/request"
T_CAM_OFFER   = "webrtc/offer"
T_CAM_ANSWER  = "webrtc/answer"

T_OFFER  = T_CAM_OFFER
T_ANSWER = T_CAM_ANSWER
T_AUTOPILOT_CLAIM = "autopilot/claim"
T_SLOT_PREFIX = "slot/ocupado/"

TCP_HOST = "localhost"
TCP_PORT = 9999

# ══════════════════════════════════════════════════════════════════════════════
#  BALIZAS V16 — API DGT
# ══════════════════════════════════════════════════════════════════════════════

V16_API_URL = "https://baliza.app/api/dgt"
V16_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://baliza.app/",
    "Origin": "https://baliza.app"
}


def _extraer_lista_v16(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return v
    return []


def get_v16_activas():
    """Consulta la API DGT y devuelve lista de balizas V16 con coordenadas."""
    try:
        r = requests.get(V16_API_URL, headers=V16_HEADERS, timeout=10)
        items = _extraer_lista_v16(r.json())
        v16 = []
        for item in items:
            if "v16" not in str(item).lower():
                continue
            lat = (item.get("lat") or item.get("latitude") or item.get("latitud")
                   or (item.get("position") or {}).get("lat"))
            lon = (item.get("lng") or item.get("lon") or item.get("longitude")
                   or (item.get("position") or {}).get("lng"))
            if lat and lon:
                timestamp_str = (item.get("date") or item.get("timestamp")
                                 or item.get("fecha") or item.get("updated_at"))
                dt = None
                if timestamp_str:
                    try:
                        if isinstance(timestamp_str, str):
                            try:
                                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                            except ValueError:
                                dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        elif isinstance(timestamp_str, (int, float)):
                            dt = datetime.fromtimestamp(timestamp_str)
                    except Exception:
                        pass
                if dt and datetime.now() - dt <= timedelta(minutes=10):
                    v16.append({
                        "lat": float(lat),
                        "lon": float(lon),
                        "raw": item,
                        "timestamp": timestamp_str
                    })
        return v16
    except Exception as e:
        print(f"[V16] Error obteniendo balizas: {e}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
#  SELECCIÓN AUTOMÁTICA DE SLOT HIVEMQ
# ══════════════════════════════════════════════════════════════════════════════

USER_DASHBOARD = None
PASS_DASHBOARD = None
SLOT_INDEX     = None


def seleccionar_slot():
    global USER_DASHBOARD, PASS_DASHBOARD, SLOT_INDEX

    import uuid as _uuid_inner

    slots_con_credenciales = [
        (i, s) for i, s in enumerate(HIVEMQ_USERS)
        if s["user"].strip() and s["password"].strip()
    ]

    if not slots_con_credenciales:
        print("[SLOT] ERROR: no hay ningún usuario HiveMQ configurado en HIVEMQ_USERS.")
        import sys; sys.exit(1)

    for idx, creds in slots_con_credenciales:
        topic_slot = f"{T_SLOT_PREFIX}{idx + 1}"
        ocupado    = {"valor": False, "evento": threading.Event()}

        def _on_msg(cli, userdata, msg, _t=topic_slot):
            payload = msg.payload.decode("utf-8").strip()
            if msg.topic == _t and payload:
                ocupado["valor"] = True
            ocupado["evento"].set()

        probe = mqtt.Client(
            client_id=f"probe_{idx}_{_uuid_inner.uuid4().hex[:4]}",
            transport="websockets"
        )
        probe.ws_set_options(path="/mqtt")
        probe.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
        probe.username_pw_set(creds["user"], creds["password"])
        try:
            probe.connect(BROKER_DASHBOARD, PORT)
        except Exception as e:
            print(f"[SLOT] Slot {idx+1} — error de conexión: {e}")
            continue

        probe.on_message = _on_msg
        probe.subscribe(topic_slot)
        probe.loop_start()
        ocupado["evento"].wait(timeout=1.5)
        probe.loop_stop()
        probe.disconnect()

        if not ocupado["valor"]:
            USER_DASHBOARD = creds["user"]
            PASS_DASHBOARD = creds["password"]
            SLOT_INDEX     = idx
            _marcar_slot_ocupado(idx, creds)
            print(f"[SLOT] Slot {idx+1} ocupado (usuario: {creds['user']})")
            return idx

        print(f"[SLOT] Slot {idx+1} ocupado — probando siguiente...")

    _mostrar_error_slots_llenos()
    import sys; sys.exit(0)


def _publicar_retain(user, password, topic, payload):
    import uuid as _uuid_inner
    ack = threading.Event()

    c = mqtt.Client(
        client_id=f"retain_{_uuid_inner.uuid4().hex[:6]}",
        transport="websockets"
    )
    c.ws_set_options(path="/mqtt")
    c.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
    c.username_pw_set(user, password)
    c.on_publish = lambda cli, ud, mid: ack.set()
    try:
        c.connect(BROKER_DASHBOARD, PORT)
        c.loop_start()
        c.publish(topic, payload, retain=True, qos=1)
        ack.wait(timeout=4.0)
        c.loop_stop()
        c.disconnect()
        status = "✓" if ack.is_set() else "⚠ sin ACK"
        print(f"[RETAIN] {status}  topic={topic}  payload={repr(payload)}")
    except Exception as e:
        print(f"[RETAIN] Error publicando retain {topic}: {e}")


def _marcar_slot_ocupado(idx, creds):
    import atexit
    _publicar_retain(creds["user"], creds["password"],
                     f"{T_SLOT_PREFIX}{idx + 1}", creds["user"])
    atexit.register(liberar_slot)


def liberar_slot():
    if SLOT_INDEX is None or USER_DASHBOARD is None:
        return
    print(f"[SLOT] Liberando slot {SLOT_INDEX + 1}...")
    _publicar_retain(USER_DASHBOARD, PASS_DASHBOARD,
                     f"{T_SLOT_PREFIX}{SLOT_INDEX + 1}", "")
    print(f"[SLOT] Slot {SLOT_INDEX + 1} liberado")


def _mostrar_error_slots_llenos():
    err = tk.Tk()
    err.title("Sin slots disponibles")
    err.resizable(False, False)
    err.configure(bg="#212121")
    w, h = 420, 220
    x = (err.winfo_screenwidth()  - w) // 2
    y = (err.winfo_screenheight() - h) // 2
    err.geometry(f"{w}x{h}+{x}+{y}")
    tk.Label(err, text="⚠", font=("Arial", 36), bg="#212121", fg="#e94560").pack(pady=(20, 4))
    tk.Label(err, text="No hay slots disponibles",
             font=("Arial", 13, "bold"), bg="#212121", fg="white").pack()
    tk.Label(err, text="Los 4 usuarios de HiveMQ están en uso.\nCierra otra instancia del dashboard e inténtalo de nuevo.",
             font=("Arial", 9), bg="#212121", fg="#aaaaaa", justify="center").pack(pady=10)
    tk.Button(err, text="Cerrar", font=("Arial", 10, "bold"),
              bg="#e94560", fg="white", relief="flat", padx=20, pady=6,
              command=err.destroy).pack()
    err.protocol("WM_DELETE_WINDOW", err.destroy)
    err.mainloop()


import uuid as _uuid
_INST_SUFFIX = _uuid.uuid4().hex[:6]
MY_ORIGIN    = f"interfazGlobal_{_INST_SUFFIX}"
AUTOPILOT_SOURCE_ID = f"DashboardTOTAL_autopilot_{_INST_SUFFIX}"

# ══════════════════════════════════════════════════════════════════════════════
#  ESTADO GLOBAL
# ══════════════════════════════════════════════════════════════════════════════

pc               = None
loop_dashboard   = None
client_dashboard = None
previousBtn      = None
MODE             = None
REAL_DRONE       = False
IS_GROUND_STATION = False

dron = Dron()

altShowLbl = headingShowLbl = stateShowLbl = None
speedShowLbl = battShowLbl = gpsShowLbl = None
connectBtn = arm_takeOffBtn = landBtn = RTLBtn = None
speedSldr  = gradesSldr = None
root_window = None
_connect_attempt_token = 0
_dashboard_telem_source = None
_dashboard_telem_source_last_ts = 0.0
_dashboard_telem_source_last_log = 0.0
_dashboard_last_telem_rx_ts = 0.0
_dashboard_last_telem_request_ts = 0.0
_dashboard_telem_watchdog_started = False

# ── Terminal integrada ────────────────────────────────────────────────────────
_stdout_redirector = None
_stderr_redirector = None


class StreamToTk:
    def __init__(self, original_stream):
        self.original_stream = original_stream
        self.widget = None

    def set_widget(self, widget):
        self.widget = widget

    def write(self, text):
        if not text:
            return
        try:
            self.original_stream.write(text)
        except Exception:
            pass
        w = self.widget
        if w is None:
            return
        try:
            w.after(0, self._append, text)
        except Exception:
            pass

    def _append(self, text):
        w = self.widget
        if w is None:
            return
        try:
            if not w.winfo_exists():
                return
            w.configure(state="normal")
            w.insert("end", text)
            w.see("end")
            w.configure(state="disabled")
        except Exception:
            pass

    def flush(self):
        try:
            self.original_stream.flush()
        except Exception:
            pass

    @property
    def encoding(self):
        return getattr(self.original_stream, "encoding", "utf-8")


def _ensure_log_redirectors():
    global _stdout_redirector, _stderr_redirector
    if _stdout_redirector is None:
        _stdout_redirector = StreamToTk(sys.stdout)
        sys.stdout = _stdout_redirector
    if _stderr_redirector is None:
        _stderr_redirector = StreamToTk(sys.stderr)
        sys.stderr = _stderr_redirector


def _attach_log_widget(widget):
    _ensure_log_redirectors()
    _stdout_redirector.set_widget(widget)
    _stderr_redirector.set_widget(widget)


def _ui_call(fn, *args, **kwargs):
    """Ejecuta cambios de Tk en el hilo principal cuando sea posible."""
    try:
        if root_window is not None and root_window.winfo_exists():
            root_window.after(0, lambda: fn(*args, **kwargs))
            return
    except Exception:
        pass
    try:
        fn(*args, **kwargs)
    except Exception:
        pass

# ── Mapa ──────────────────────────────────────────────────────────────────────
map_widget      = None
drone_marker    = None
target_marker   = None
drone_path      = []
drone_path_line = None
drone_lat       = None
drone_lon       = None
drone_icon      = None
_goto_callback  = None

# Balizas V16
v16_markers     = []   # lista de marcadores de balizas V16 en el mapa
v16_updating    = True

# ── YOLOv5 — detección multi-clase ───────────────────────────────────────────
detect_object_ids = set()
yolo_model        = None

COCO_GRUPOS = [
    ("Personas",    [("Persona",   0)]),
    ("Vehículos",   [("Bicicleta", 1), ("Coche",    2), ("Moto",     3),
                     ("Avión",     4), ("Autobús",  5), ("Tren",     6),
                     ("Camión",    7)]),
    ("Animales",    [("Pájaro",   14), ("Gato",    15), ("Perro",   16),
                     ("Caballo",  17), ("Vaca",    19)]),
    ("Objetos",     [("Mochila",  24), ("Paraguas",25), ("Maleta",  28),
                     ("Pelota",   32), ("Silla",   56), ("Sofá",    57)]),
    ("Electrónica", [("Portátil", 63), ("Móvil",   67), ("Reloj",   74)]),
    ("Comida",      [("Banana",   46), ("Pizza",   53), ("Pastel",  55)]),
]

# ── Estado del CameraService ──────────────────────────────────────────────────
camera_service_loop    = None
camera_service_client  = None
camera_service_mode    = None
camera_service_running = False
camera_stop_event      = threading.Event()
_cam_peers: dict = {}
_cam_track = None
camera_service_pc = None


# ══════════════════════════════════════════════════════════════════════════════
#  PANTALLA DE SELECCIÓN DE SIMULACIÓN / DRON
# ══════════════════════════════════════════════════════════════════════════════

def selector_simulacion():
    seleccion = {"valor": None}

    sel = tk.Tk()
    sel.title("Dashboard Dron — Simulación o dron real")
    sel.resizable(False, False)
    sel.configure(bg="#212121")

    w, h = 440, 280
    x = (sel.winfo_screenwidth()  - w) // 2
    y = (sel.winfo_screenheight() - h) // 2
    sel.geometry(f"{w}x{h}+{x}+{y}")

    tk.Label(sel, text="Dashboard Dron",
             font=("Arial", 18, "bold"), bg="#212121", fg="white").pack(pady=(28, 4))
    tk.Label(sel, text="¿Usar simulación o dron real?",
             font=("Arial", 10), bg="#212121", fg="#aaaaaa").pack(pady=(0, 24))

    btn_frame = tk.Frame(sel, bg="#212121")
    btn_frame.pack(fill="x", padx=40)

    def elegir(valor):
        seleccion["valor"] = valor
        sel.destroy()

    tk.Button(btn_frame, text="Simulación",
              font=("Arial", 12, "bold"), bg="#2196f3", fg="white",
              activebackground="#1976d2", relief="flat", cursor="hand2", pady=10,
              command=lambda: elegir(False)).pack(fill="x", padx=2, pady=2)
    tk.Button(btn_frame, text="Dron real",
              font=("Arial", 12, "bold"), bg="#e94560", fg="white",
              activebackground="#c73652", relief="flat", cursor="hand2", pady=10,
              command=lambda: elegir(True)).pack(fill="x", padx=2, pady=2)

    sel.protocol("WM_DELETE_WINDOW", sel.destroy)
    sel.mainloop()

    if seleccion["valor"] is None:
        import sys; sys.exit(0)

    return seleccion["valor"]


# ══════════════════════════════════════════════════════════════════════════════
#  PANTALLA DE SELECCIÓN DE MODO
# ══════════════════════════════════════════════════════════════════════════════

def selector_modo():
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

    f_global = tk.Frame(btn_frame, bg="#212121")
    f_global.pack(fill="x", pady=6, ipady=2)
    tk.Button(f_global, text="Modo Global",
              font=("Arial", 12, "bold"), bg="#e94560", fg="white",
              activebackground="#c73652", relief="flat", cursor="hand2", pady=10,
              command=lambda: elegir("global")).pack(fill="x", padx=2, pady=2)
    tk.Label(f_global, text="MQTT + WebRTC + TURN",
             font=("Arial", 8), bg="#212121", fg="#aaaaaa").pack(pady=(0, 4))

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


# ══════════════════════════════════════════════════════════════════════════════
#  NEGOCIACIÓN DE ROL
# ══════════════════════════════════════════════════════════════════════════════

MY_CLIENT_ID = MY_ORIGIN

def negociar_rol_ground_station():
    resultado = {"claim_recibido": None, "evento": threading.Event()}

    def _on_message(cli, userdata, msg):
        if msg.topic == T_AUTOPILOT_CLAIM:
            payload = msg.payload.decode("utf-8").strip()
            if payload and payload != MY_CLIENT_ID:
                resultado["claim_recibido"] = payload
            resultado["evento"].set()

    tmp = mqtt.Client(client_id=MY_CLIENT_ID + "_probe", transport="websockets")
    tmp.ws_set_options(path="/mqtt")
    tmp.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
    tmp.username_pw_set(USER_DASHBOARD, PASS_DASHBOARD)
    tmp.on_message = _on_message
    tmp.connect(BROKER_DASHBOARD, PORT)
    tmp.subscribe(T_AUTOPILOT_CLAIM)
    tmp.loop_start()

    resultado["evento"].wait(timeout=1.5)
    tmp.loop_stop()
    tmp.disconnect()

    if resultado["claim_recibido"]:
        print(f"[ROL] Estación de Tierra detectada: {resultado['claim_recibido']}")
        return False
    else:
        _publicar_claim()
        print(f"[ROL] Me proclamo Estación de Tierra ({MY_CLIENT_ID})")
        return True


def _publicar_claim():
    import atexit
    _publicar_retain(USER_DASHBOARD, PASS_DASHBOARD, T_AUTOPILOT_CLAIM, MY_CLIENT_ID)
    atexit.register(limpiar_claim_ground_station)


def limpiar_claim_ground_station():
    print("[ROL] Liberando claim de Estación de Tierra...")
    _publicar_retain(USER_DASHBOARD, PASS_DASHBOARD, T_AUTOPILOT_CLAIM, "")
    print("[ROL] Claim liberado")


# ══════════════════════════════════════════════════════════════════════════════
#  DIÁLOGO DE ROL
# ══════════════════════════════════════════════════════════════════════════════

def mostrar_dialogo_rol(es_estacion):
    d = tk.Tk()
    d.title("Rol asignado")
    d.resizable(False, False)

    if es_estacion:
        bg_color   = "#1b4d2e"
        accent     = "#2ecc71"
        icono      = "📡"
        titulo_rol = "ESTACIÓN DE TIERRA"
        desc       = ("Esta instancia controla el AutopilotService.\n"
                      "El dron está conectado directamente a este equipo.\n"
                      "Otras consolas en la red actuarán como Clientes.")
    else:
        bg_color   = "#1a2a4a"
        accent     = "#3498db"
        icono      = "📺"
        titulo_rol = "CLIENTE"
        desc       = ("Ya existe una Estación de Tierra activa en la red.\n"
                      "Esta consola solo enviará comandos y recibirá telemetría.\n"
                      "El AutopilotService NO se ha iniciado aquí.")

    d.configure(bg=bg_color)

    w, h = 480, 300
    x = (d.winfo_screenwidth()  - w) // 2
    y = (d.winfo_screenheight() - h) // 2
    d.geometry(f"{w}x{h}+{x}+{y}")

    franja = tk.Frame(d, bg=accent, height=5)
    franja.pack(fill="x")
    tk.Label(d, text=icono, font=("Arial", 42), bg=bg_color, fg=accent).pack(pady=(18, 4))
    tk.Label(d, text=titulo_rol, font=("Arial", 16, "bold"), bg=bg_color, fg=accent).pack(pady=(0, 8))
    tk.Label(d, text=desc, font=("Arial", 9), bg=bg_color, fg="#cccccc",
             justify="center", wraplength=420).pack(pady=(0, 20))
    tk.Button(d, text="Continuar →",
              font=("Arial", 11, "bold"), bg=accent, fg="white",
              activebackground=bg_color, relief="flat", cursor="hand2",
              padx=24, pady=8, command=d.destroy).pack()

    d.after(6000, lambda: d.destroy() if d.winfo_exists() else None)
    d.protocol("WM_DELETE_WINDOW", d.destroy)
    d.mainloop()


# ══════════════════════════════════════════════════════════════════════════════
#  AUTOPILOT SERVICE (integrado)
# ══════════════════════════════════════════════════════════════════════════════

client_autopilot = None

_telem_subscribers: dict = {}
_telem_lock = threading.Lock()
_telem_active = False


def _autopilot_topic(origin: str) -> str:
    return f"autopilotServiceDemo/{origin}"


def autopilot_publish_event(event, origin: str = None):
    if origin is None:
        with _telem_lock:
            origin = next(iter(_telem_subscribers), None)
    if origin is None:
        return
    topic = _autopilot_topic(origin) + '/' + event
    try:
        client_autopilot.publish(topic)
        print(f"[AUTOPILOT] → {topic}")
    except Exception as e:
        print(f"[AUTOPILOT] Error publicando evento: {e}")


def autopilot_publish_telemetry(telemetry_info):
    cli = client_autopilot
    if cli is None:
        return
    if not isinstance(telemetry_info, dict):
        return
    try:
        payload_obj = dict(telemetry_info)
        payload_obj["_source"] = AUTOPILOT_SOURCE_ID
        payload_obj["_ts"] = time.time()
        payload = json.dumps(payload_obj)
    except Exception:
        return
    with _telem_lock:
        topics = list(_telem_subscribers.values())
    for base_topic in topics:
        try:
            cli.publish(base_topic + '/telemetryInfo', payload)
        except Exception as e:
            print(f"[AUTOPILOT] Error telemetría → {base_topic}: {type(e).__name__}")


def _start_telem_if_needed():
    global _telem_active
    if not _telem_active:
        dron.send_telemetry_info(autopilot_publish_telemetry)
        _telem_active = True
        print("[AUTOPILOT] Telemetría iniciada")


def _stop_telem_if_empty():
    global _telem_active
    if _telem_active and not _telem_subscribers:
        dron.stop_sending_telemetry_info()
        _telem_active = False
        print("[AUTOPILOT] Telemetría detenida (sin suscriptores)")


def autopilot_on_message(cli, userdata, message):
    parts   = message.topic.split("/")
    origin  = parts[0]
    command = parts[2]
    sending_topic = _autopilot_topic(origin)

    print(f"[AUTOPILOT] {origin} → {command}")

    if command == 'connect':
        payload = message.payload.decode("utf-8").strip()
        if payload == 'REAL':
            connection_string = 'udp:127.0.0.1:14551'
            baud = 57600
        else:
            connection_string = 'tcp:127.0.0.1:5763'
            baud = 115200
        try:
            ok = dron.connect(connection_string, baud, freq=10)
            if ok and dron.state == 'connected':
                print(f'Conectado al dron ({connection_string} @ {baud})')
                autopilot_publish_event('connected', origin)
            else:
                print(f'[AUTOPILOT] No se pudo conectar ({connection_string} @ {baud})')
                autopilot_publish_event('connectError', origin)
        except Exception as e:
            print(f"[AUTOPILOT] Error conectando: {e}")
            autopilot_publish_event('connectError', origin)

    elif command == 'arm_takeOff':
        if dron.state == 'connected':
            dron.arm()
            altura = int(message.payload.decode("utf-8"))
            dron.takeOff(altura, blocking=False,
                         callback=lambda ev: autopilot_publish_event(ev, origin),
                         params='flying')

    elif command == 'go':
        if dron.state == 'flying':
            dron.go(message.payload.decode("utf-8"))

    elif command == 'Land':
        if dron.state == 'flying':
            dron.Land(blocking=False,
                      callback=lambda ev: autopilot_publish_event(ev, origin),
                      params='landed')

    elif command == 'RTL':
        if dron.state == 'flying':
            dron.RTL(blocking=False,
                     callback=lambda ev: autopilot_publish_event(ev, origin),
                     params='atHome')

    elif command == 'startTelemetry':
        with _telem_lock:
            _telem_subscribers[origin] = sending_topic
        print(f"[AUTOPILOT] Suscriptor telemetría: {origin} "
              f"(total={len(_telem_subscribers)})")
        _start_telem_if_needed()

    elif command == 'stopTelemetry':
        with _telem_lock:
            _telem_subscribers.pop(origin, None)
        print(f"[AUTOPILOT] Baja telemetría: {origin} "
              f"(total={len(_telem_subscribers)})")
        _stop_telem_if_empty()

    elif command == 'changeHeading':
        dron.changeHeading(float(message.payload.decode("utf-8")))

    elif command == 'changeNavSpeed':
        dron.changeNavSpeed(float(message.payload.decode("utf-8")))

    elif command == 'changeAltitude':
        dron.change_altitude(float(message.payload.decode("utf-8")), blocking=False)

    elif command == 'goto':
        coords = json.loads(message.payload.decode("utf-8"))
        dron.goto(coords["lat"], coords["lon"], coords.get("alt", 5.0),
                  blocking=False)
        print(f"[AUTOPILOT] goto → {coords['lat']:.6f}, {coords['lon']:.6f}, {coords.get('alt',5)}m")


def autopilot_on_connect(cli, userdata, flags, rc):
    print("[AUTOPILOT] Conectado" if rc == 0 else f"[AUTOPILOT] Error MQTT {rc}")


def start_autopilot_service():
    global client_autopilot

    def _build_client():
        c = mqtt.Client("autopilotServiceDemo", transport="websockets")
        c.ws_set_options(path="/mqtt")
        c.tls_set(cert_reqs=mqtt.ssl.CERT_REQUIRED,
                  tls_version=mqtt.ssl.PROTOCOL_TLSv1_2)
        c.tls_insecure_set(False)
        c.username_pw_set(USER_AUTOPILOT, PASS_AUTOPILOT)
        c.on_connect = autopilot_on_connect
        c.on_message = autopilot_on_message
        c.on_disconnect = _autopilot_on_disconnect
        return c

    def _autopilot_on_disconnect(cli, userdata, rc):
        if rc != 0:
            print(f"[AUTOPILOT] Desconexión inesperada (rc={rc}) — reconectando...")

    def _run():
        global client_autopilot
        backoff = 1
        while True:
            try:
                client_autopilot = _build_client()
                client_autopilot.connect(BROKER_DASHBOARD, PORT, keepalive=30)
                client_autopilot.subscribe('+/autopilotServiceDemo/#')
                print("[AUTOPILOT] Servicio listo — esperando comandos")
                backoff = 1
                client_autopilot.loop_forever()
            except Exception as e:
                print(f"[AUTOPILOT] Error de conexión: {e} — reintentando en {backoff} s...")
                try:
                    client_autopilot.disconnect()
                except Exception:
                    pass
                time.sleep(backoff)
                backoff = min(backoff * 2, 30)

    threading.Thread(target=_run, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
#  CAMERA SERVICE (integrado)
# ══════════════════════════════════════════════════════════════════════════════

class CameraTrack(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        import fractions
        self._fractions = fractions
        self.cap = cv2.VideoCapture(0)
        self.frame_count = 0
        self._last_boxes = []
        if not self.cap.isOpened():
            raise RuntimeError("No se pudo abrir la cámara")
        print("[CAM] Cámara abierta")

    async def recv(self):
        self.frame_count += 1

        max_retries = 100
        retries = 0
        ret, frame = self.cap.read()
        while not ret:
            retries += 1
            if retries > max_retries:
                raise RuntimeError("[CAM] Cámara no responde tras múltiples intentos")
            await asyncio.sleep(0.033)
            ret, frame = self.cap.read()

        if self.frame_count % 30 == 0 and detect_object_ids:
            self._last_boxes = await asyncio.get_event_loop().run_in_executor(
                None, run_detect, frame.copy()
            )
        elif not detect_object_ids:
            self._last_boxes = []

        for (x1, y1, x2, y2, label) in self._last_boxes:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, max(y1 - 8, 0)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        vf = VideoFrame.from_ndarray(frame_rgb, format="rgb24")
        vf.pts = self.frame_count
        vf.time_base = self._fractions.Fraction(1, 30)
        return vf

    def stop(self):
        try:
            if self.cap and self.cap.isOpened():
                self.cap.release()
        except Exception:
            pass
        super().stop()

def get_ice_config():
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
    exc = context.get("exception", None)
    msg = context.get("message", "")
    if "TransactionFailed" in str(type(exc).__name__) or "aioice" in str(exc):
        return
    if "CHANNEL_BIND" in msg or "TransactionFailed" in msg:
        return
    loop.default_exception_handler(context)


async def _cam_connect_peer(origen: str, mqtt_cam_client):
    global _cam_peers, _cam_track

    print(f"[CAM] Nueva conexión para cliente: {origen}")

    pc_peer = RTCPeerConnection(configuration=get_ice_config())
    _cam_peers[origen] = pc_peer

    pc_peer.addTrack(_cam_track)

    @pc_peer.on("connectionstatechange")
    async def _on_state():
        state = pc_peer.connectionState
        print(f"[CAM:{origen}] WebRTC → {state}")
        if state in ("failed", "closed", "disconnected"):
            _cam_peers.pop(origen, None)

    answer_event = asyncio.Event()
    cam_loop     = asyncio.get_event_loop()
    t_offer_peer  = f"{T_CAM_OFFER}/{origen}"
    t_answer_peer = f"{T_CAM_ANSWER}/{origen}"

    def _on_mqtt(cli, userdata, msg):
        if msg.topic == t_answer_peer:
            try:
                data = json.loads(msg.payload)
            except Exception:
                return
            asyncio.run_coroutine_threadsafe(
                _apply_answer_peer(pc_peer, data, answer_event),
                cam_loop
            )

    mqtt_cam_client.message_callback_add(t_answer_peer, _on_mqtt)
    mqtt_cam_client.subscribe(t_answer_peer)

    await pc_peer.setLocalDescription(await pc_peer.createOffer())
    print(f"[CAM:{origen}] Esperando ICE gathering...")
    while pc_peer.iceGatheringState != "complete":
        await asyncio.sleep(0.2)

    candidates = [l for l in pc_peer.localDescription.sdp.splitlines()
                  if l.startswith("a=candidate")]
    has_relay = any("relay" in c for c in candidates)
    print(f"[CAM:{origen}] {len(candidates)} candidates — "
          f"{'✓ relay' if has_relay else '⚠ sin relay'}")

    mqtt_cam_client.publish(t_offer_peer, json.dumps({
        "sdp":  pc_peer.localDescription.sdp,
        "type": pc_peer.localDescription.type,
    }), retain=False)
    print(f"[CAM:{origen}] Oferta publicada → {t_offer_peer}")

    try:
        await asyncio.wait_for(answer_event.wait(), timeout=30.0)
        print(f"[CAM:{origen}] Conexión establecida ✓")
    except asyncio.TimeoutError:
        print(f"[CAM:{origen}] Timeout esperando answer — descartando peer")
        _cam_peers.pop(origen, None)
        await pc_peer.close()
        return

    while (not camera_stop_event.is_set()
           and pc_peer.connectionState not in ("failed", "closed", "disconnected")):
        await asyncio.sleep(1)

    try:
        await pc_peer.close()
    except Exception:
        pass
    _cam_peers.pop(origen, None)
    print(f"[CAM:{origen}] Peer cerrado")


async def _apply_answer_peer(pc_peer, data, event):
    try:
        if pc_peer.signalingState == "stable":
            print("[CAM] Peer ya estable — ignorando answer duplicada")
            return
        await pc_peer.setRemoteDescription(
            RTCSessionDescription(sdp=data["sdp"], type=data["type"])
        )
        print("[CAM] Answer aplicada ✓")
        event.set()
    except Exception as e:
        print(f"[CAM] Error aplicando answer: {e}")


async def run_camera_global(mqtt_cam_client):
    global camera_service_loop, camera_service_client, camera_service_running
    global _cam_track, _cam_peers

    camera_service_loop   = asyncio.get_event_loop()
    camera_service_client = mqtt_cam_client
    camera_service_running = True
    _cam_peers = {}

    _cam_track = CameraTrack()
    print("[CAM] Cámara abierta — esperando solicitudes de clientes...")

    cam_loop = asyncio.get_event_loop()
    def _on_request(cli, userdata, msg):
        try:
            origen = msg.payload.decode("utf-8").strip()
        except Exception:
            return
        if not origen:
            return
        if origen in _cam_peers:
            print(f"[CAM] Solicitud de {origen} ignorada — peer ya existe")
            return
        print(f"[CAM] Solicitud de stream de: {origen}")
        asyncio.run_coroutine_threadsafe(
            _cam_connect_peer(origen, mqtt_cam_client),
            cam_loop
        )

    def _on_detect_classes(cli, userdata, msg):
        try:
            payload = msg.payload.decode("utf-8").strip()
            if not payload:
                return
            import json as _json
            ids = _json.loads(payload)
            detect_object_ids.clear()
            detect_object_ids.update(ids)
            print(f"[COCO] Clases activas desde C#: {sorted(detect_object_ids)}")
            if ids and yolo_model is None:
                import threading as _threading
                _threading.Thread(target=load_yolo, daemon=True).start()
        except Exception as e:
            print(f"[COCO] Error parseando detectClasses: {e}")

    mqtt_cam_client.message_callback_add("webrtc/detectClasses", _on_detect_classes)

    mqtt_cam_client.message_callback_add(T_CAM_REQUEST, _on_request)
    mqtt_cam_client.subscribe(T_CAM_REQUEST)
    print(f"[CAM] Suscrito a solicitudes en {T_CAM_REQUEST}")

    def _on_detect_classes(cli, userdata, msg):
        try:
            ids = json.loads(msg.payload.decode("utf-8").strip())
            detect_object_ids.clear()
            detect_object_ids.update(ids)
            print(f"[COCO] Clases activas: {sorted(detect_object_ids)}")
            if ids and yolo_model is None:
                threading.Thread(target=load_yolo, daemon=True).start()
        except Exception as e:
            print(f"[COCO] Error: {e}")

    mqtt_cam_client.message_callback_add("webrtc/detectClasses", _on_detect_classes)
    mqtt_cam_client.subscribe("webrtc/detectClasses")
    print("[CAM] Suscrito a webrtc/detectClasses")

    try:
        while not camera_stop_event.is_set():
            await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        pass
    finally:
        print(f"[CAM] Cerrando {len(_cam_peers)} peer(s)...")
        close_tasks = [pc.close() for pc in list(_cam_peers.values())]
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        _cam_peers.clear()
        try:
            _cam_track.stop()
        except Exception:
            pass
        try:
            mqtt_cam_client.loop_stop()
            mqtt_cam_client.disconnect()
        except Exception:
            pass
        camera_service_loop   = None
        camera_service_client = None
        camera_service_running = False
        print("[CAM] CameraService detenido")


def start_camera_service_global():
    global camera_service_mode, camera_service_running

    if camera_service_running:
        print("[CAM] CameraService ya está activo")
        return

    camera_stop_event.clear()
    camera_service_mode = "global"

    def _run():
        try:
            cam_client = mqtt.Client(client_id=f"CameraService_{_INST_SUFFIX}", transport="websockets")
            cam_client.ws_set_options(path="/mqtt")
            cam_client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
            cam_client.username_pw_set(USER_DASHBOARD, PASS_DASHBOARD)
            cam_client.connect(BROKER_DASHBOARD, PORT)
            cam_client.loop_start()

            loop = asyncio.new_event_loop()
            loop.set_exception_handler(_silence_aioice_handler)
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_camera_global(cam_client))
        except Exception as e:
            print(f"[CAM] Error en CameraService global: {e}")
        finally:
            try:
                loop.close()
            except Exception:
                pass

    threading.Thread(target=_run, daemon=True).start()
    print("[CAM] CameraService iniciado (modo global)")


async def run_camera_local():
    global camera_service_pc, camera_service_loop, camera_service_running
    from aiortc.contrib.signaling import TcpSocketSignaling

    signaling = TcpSocketSignaling("0.0.0.0", TCP_PORT)
    pc_cam    = RTCPeerConnection()
    cam_track = CameraTrack()
    pc_cam.addTrack(cam_track)
    camera_service_pc = pc_cam
    camera_service_loop = asyncio.get_event_loop()
    camera_service_running = True

    @pc_cam.on("connectionstatechange")
    async def _(): print(f"[CAM] WebRTC {pc_cam.connectionState}")

    try:
        print(f"[CAM] Esperando cliente en 0.0.0.0:{TCP_PORT}...")
        await signaling.connect()

        offer = await pc_cam.createOffer()
        await pc_cam.setLocalDescription(offer)
        await signaling.send(pc_cam.localDescription)
        print("[CAM] Offer enviada — esperando answer...")

        while True:
            obj = await signaling.receive()
            if isinstance(obj, RTCSessionDescription):
                await pc_cam.setRemoteDescription(obj)
                print("[CAM] Conexión local establecida ✓")
                break
            elif obj is None:
                print("[CAM] Fallo en la coordinación TCP")
                break

        while pc_cam.connectionState not in ("failed", "closed") and not camera_stop_event.is_set():
            await asyncio.sleep(1)

    except Exception as e:
        print(f"[CAM] Error local: {e}")
    finally:
        try:
            await pc_cam.close()
        except Exception:
            pass
        try:
            cam_track.stop()
        except Exception:
            pass
        camera_service_pc = None
        camera_service_loop = None
        camera_service_running = False


def start_camera_service_local():
    global camera_service_mode, camera_service_running

    if camera_service_running:
        print("[CAM] CameraService ya está activo")
        return

    camera_stop_event.clear()
    camera_service_mode = "local"

    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_camera_local())
        except Exception as e:
            print(f"[CAM] Error en CameraService local: {e}")
        finally:
            try:
                loop.close()
            except Exception:
                pass

    threading.Thread(target=_run, daemon=True).start()
    print("[CAM] CameraService iniciado (modo local)")


def stop_camera_service():
    global camera_service_running

    if not camera_service_running and not _cam_peers and _cam_track is None:
        print("[CAM] CameraService ya estaba detenido")
        return

    print(f"[CAM] Solicitud de parada ({len(_cam_peers)} peer(s) activos)...")
    camera_stop_event.set()

    loop = camera_service_loop
    if loop is not None:
        async def _close_all():
            tasks = [pc.close() for pc in list(_cam_peers.values())]
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        try:
            asyncio.run_coroutine_threadsafe(_close_all(), loop)
        except Exception:
            pass

    if camera_service_client is not None:
        try:
            camera_service_client.loop_stop()
            camera_service_client.disconnect()
        except Exception:
            pass

    camera_service_running = False
    print("[CAM] Cámara desconectada")


# ══════════════════════════════════════════════════════════════════════════════
#  DETECCIÓN YOLO — MULTI-CLASE
# ══════════════════════════════════════════════════════════════════════════════

def load_yolo():
    global yolo_model
    if yolo_model is None:
        print("[DET] Cargando YOLOv5s...")
        import torch
        yolo_model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
        yolo_model.eval()
        print("[DET] Modelo listo")


def toggle_detect(obj_id: int, active: bool):
    if active:
        detect_object_ids.add(obj_id)
        if yolo_model is None:
            threading.Thread(target=load_yolo, daemon=True).start()
        print(f"[DET] +clase {obj_id}  activas={sorted(detect_object_ids)}")
    else:
        detect_object_ids.discard(obj_id)
        print(f"[DET] -clase {obj_id}  activas={sorted(detect_object_ids)}")


def run_detect(frame):
    if yolo_model is None or not detect_object_ids:
        return []

    id_to_name = {
        oid: nombre
        for _, clases in COCO_GRUPOS
        for nombre, oid in clases
        if oid in detect_object_ids
    }

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        results = yolo_model(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

    boxes = []
    for *xyxy, conf, cls in results.xyxy[0]:
        cls_id = int(cls.item())
        if cls_id in detect_object_ids:
            x1, y1, x2, y2 = map(int, xyxy)
            boxes.append((x1, y1, x2, y2, id_to_name.get(cls_id, str(cls_id))))
    return boxes


# ══════════════════════════════════════════════════════════════════════════════
#  WEBRTC DASHBOARD (receptor de vídeo)
# ══════════════════════════════════════════════════════════════════════════════

async def show_video(track):
    print("[VIDEO] Mostrando frames (boxes incluidos en stream)...")
    while True:
        try:
            frame = await asyncio.wait_for(track.recv(), timeout=5.0)
            if isinstance(frame, VideoFrame):
                img = frame.to_ndarray(format="bgr24")
                cv2.imshow("Video Dron", img)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        except asyncio.TimeoutError:
            print("[VIDEO] Timeout esperando frame")
        except Exception as e:
            print(f"[VIDEO] {e}")
            break
    cv2.destroyAllWindows()


def webrtc_thread_dashboard():
    global pc, loop_dashboard

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

    t_my_offer   = f"{T_CAM_OFFER}/{MY_ORIGIN}"
    t_my_answer  = f"{T_CAM_ANSWER}/{MY_ORIGIN}"
    t_my_request = T_CAM_REQUEST

    def _on_offer(cli, userdata, msg):
        if msg.topic == t_my_offer and msg.payload:
            if pc.connectionState in ("connecting", "connected"):
                return
            try:
                data = json.loads(msg.payload)
            except Exception:
                return
            print(f"[SIG] Oferta recibida en {t_my_offer}")
            asyncio.run_coroutine_threadsafe(
                handle_offer_dashboard(data, t_my_answer), loop_dashboard)

    client_dashboard.message_callback_add(t_my_offer, _on_offer)
    client_dashboard.subscribe(t_my_offer)

    client_dashboard.publish(t_my_request, MY_ORIGIN, retain=False)
    print(f"[WebRTC] Solicitud enviada a {t_my_request} (payload={MY_ORIGIN})")

    async def _retry_request():
        for _ in range(12):
            await asyncio.sleep(5)
            if pc.connectionState in ("connected", "connecting"):
                break
            print(f"[WebRTC] Re-solicitud → {t_my_request}")
            client_dashboard.publish(t_my_request, MY_ORIGIN, retain=False)

    asyncio.run_coroutine_threadsafe(_retry_request(), loop_dashboard)
    loop_dashboard.run_forever()


async def webrtc_receive_local():
    from aiortc.contrib.signaling import TcpSocketSignaling
    from aiortc import MediaStreamTrack

    await asyncio.sleep(0.8)

    signaling = TcpSocketSignaling(TCP_HOST, TCP_PORT)
    pc_local  = RTCPeerConnection()

    @pc_local.on("track")
    def on_track(track):
        if isinstance(track, MediaStreamTrack) and track.kind == "video":
            print("[VIDEO] ✓ Track recibido (local)")
            asyncio.ensure_future(show_video_local(track))

    @pc_local.on("connectionstatechange")
    async def _():
        print(f"[WebRTC] {pc_local.connectionState}")

    try:
        print(f"[VIDEO] Conectando al CameraService en {TCP_HOST}:{TCP_PORT}...")
        await signaling.connect()

        print("[VIDEO] Esperando offer...")
        offer = await signaling.receive()
        print("[VIDEO] Offer recibida")
        await pc_local.setRemoteDescription(offer)

        answer = await pc_local.createAnswer()
        await pc_local.setLocalDescription(answer)
        await signaling.send(pc_local.localDescription)
        print("[VIDEO] Answer enviada — esperando conexión...")

        while pc_local.connectionState != "connected":
            await asyncio.sleep(0.1)
        print("[VIDEO] Conexión establecida ✓")

        while pc_local.connectionState not in ("failed", "closed"):
            await asyncio.sleep(1)

    except Exception as e:
        print(f"[VIDEO] Error local: {e}")
    finally:
        await pc_local.close()


async def show_video_local(track):
    print("[VIDEO] Mostrando frames (local)...")
    frame_count, last_boxes = 0, []

    while True:
        try:
            frame = await asyncio.wait_for(track.recv(), timeout=5.0)
            if isinstance(frame, VideoFrame):
                img = frame.to_ndarray(format="bgr24")
                frame_count += 1
                if frame_count % 30 == 0 and detect_object_ids:
                    last_boxes = await asyncio.get_event_loop().run_in_executor(
                        None, run_detect, img.copy()
                    )
                for (x1, y1, x2, y2, label) in last_boxes:
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(img, label, (x1, y1 - 10),
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
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(webrtc_receive_local())
    except Exception as e:
        print(f"[VIDEO] Hilo local terminó: {e}")


async def handle_offer_dashboard(data, t_answer: str):
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

    client_dashboard.publish(t_answer, json.dumps({
        "sdp":  pc.localDescription.sdp,
        "type": pc.localDescription.type,
    }))
    print(f"[WebRTC] Answer enviada → {t_answer} ✓")


def start_webrtc_dashboard():
    if MODE == "local":
        threading.Thread(target=webrtc_thread_dashboard_local, daemon=True).start()
    else:
        threading.Thread(target=webrtc_thread_dashboard, daemon=True).start()


def on_mqtt_message_dashboard(cli, userdata, msg):
    global _connect_attempt_token
    global _dashboard_telem_source, _dashboard_telem_source_last_ts, _dashboard_telem_source_last_log
    global _dashboard_last_telem_rx_ts
    topic = msg.topic

    if topic == f'autopilotServiceDemo/{MY_ORIGIN}/telemetryInfo':
        try:
            data = json.loads(msg.payload)
        except Exception:
            return

        now = time.time()
        source = str(data.get("_source", "unknown"))
        can_switch = (_dashboard_telem_source is None or
                      (now - _dashboard_telem_source_last_ts) > 8.0)

        if can_switch and source != _dashboard_telem_source:
            print(f"[TELEM] Fuente activa -> {source}")
            _dashboard_telem_source = source
        elif source != _dashboard_telem_source:
            if (now - _dashboard_telem_source_last_log) > 5.0:
                print(f"[TELEM] Ignorando telemetria de {source}; activa={_dashboard_telem_source}")
                _dashboard_telem_source_last_log = now
            return

        _dashboard_telem_source_last_ts = now
        _dashboard_last_telem_rx_ts = now

        def _update_telemetry_ui():
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

        _ui_call(_update_telemetry_ui)
    elif topic == f'autopilotServiceDemo/{MY_ORIGIN}/connected':
        _connect_attempt_token += 1
        _ui_call(_set_connected_btn)
    elif topic == f'autopilotServiceDemo/{MY_ORIGIN}/connectError':
        _connect_attempt_token += 1
        _ui_call(_show_connect_error)
    elif topic == f'autopilotServiceDemo/{MY_ORIGIN}/flying':
        _ui_call(arm_takeOffBtn.configure, text='En vuelo', fg='white', bg='green')
    elif topic == f'autopilotServiceDemo/{MY_ORIGIN}/landed':
        _ui_call(arm_takeOffBtn.configure, text='Despegar', fg='black', bg='dark orange')
        _ui_call(landBtn.configure, text='Aterrizar', fg='black', bg='dark orange')
    elif topic == f'autopilotServiceDemo/{MY_ORIGIN}/atHome':
        _ui_call(RTLBtn.configure, text='En tierra', fg='white', bg='green')
        _ui_call(arm_takeOffBtn.configure, text='Despegar', fg='black', bg='dark orange')
        _ui_call(landBtn.configure, text='Aterrizar', fg='black', bg='dark orange')


# ══════════════════════════════════════════════════════════════════════════════
#  MAPA
# ══════════════════════════════════════════════════════════════════════════════

DEFAULT_LAT = 41.3851
DEFAULT_LON =  2.1734

def _load_drone_icon():
    try:
        import os, io
        from PIL import Image, ImageTk
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "drone-logo.png")
        img = Image.open(path).convert("RGBA").resize((36, 36), Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

def update_map(lat, lon):
    global drone_marker, drone_path, drone_path_line, drone_lat, drone_lon, drone_icon

    drone_lat, drone_lon = lat, lon
    drone_path.append((lat, lon))

    def _update():
        global drone_marker, drone_path_line, drone_icon
        if map_widget is None:
            return
        if drone_marker is None:
            if drone_icon is None:
                drone_icon = _load_drone_icon()
            if drone_icon:
                drone_marker = map_widget.set_marker(
                    lat, lon, text="",
                    icon=drone_icon,
                    icon_anchor="center"
                )
            else:
                drone_marker = map_widget.set_marker(
                    lat, lon, text="🚁",
                    marker_color_circle="red",
                    marker_color_outside="darkred",
                    font=("Arial", 8),
                    image_zoom_visibility=(0, float("inf")),
                )
        else:
            drone_marker.set_position(lat, lon)

        drone_marker.set_position(lat, lon)

        if len(drone_path) >= 2:
            if drone_path_line:
                drone_path_line.delete()
            drone_path_line = map_widget.set_path(
                drone_path[-200:], color="dodger blue", width=2)

    if map_widget:
        map_widget.after(0, _update)


def on_map_click(coords):
    global target_marker
    lat, lon = coords

    def _mark():
        global target_marker
        if target_marker:
            target_marker.delete()
        target_marker = map_widget.set_marker(
            lat, lon, text="",
            marker_color_circle="green",
            marker_color_outside="darkgreen",
            font=("Arial", 3),
        )

    if map_widget:
        map_widget.after(0, _mark)

    if _goto_callback:
        _goto_callback(lat, lon)
    print(f"[MAP] Ir a → lat={lat:.6f}, lon={lon:.6f}")


def goto_gps_global(lat, lon):
    if client_dashboard:
        try:
            alt_str = altShowLbl['text'].replace(' m', '').strip()
            alt = float(alt_str) if alt_str else 5.0
        except:
            alt = 5.0
        payload = json.dumps({"lat": lat, "lon": lon, "alt": alt})
        client_dashboard.publish(
            f'{MY_ORIGIN}/autopilotServiceDemo/goto', payload)
        print(f"[MAP] MQTT goto → lat={lat:.6f}, lon={lon:.6f}, alt={alt}m")


def goto_gps_local(lat, lon):
    try:
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
#  BALIZAS V16 — CARGA Y DIBUJO EN EL MAPA
# ══════════════════════════════════════════════════════════════════════════════

def load_v16_markers():
    """Obtiene balizas V16 de la API DGT y las pinta en el mapa tkintermapview."""
    global v16_markers, v16_updating

    v16_updating = True

    def _run():
        print("[V16] Consultando API DGT...")
        balizas = get_v16_activas()
        print(f"[V16] {len(balizas)} baliza(s) V16 encontradas")

        def _draw():
            global v16_markers
            # Eliminar marcadores anteriores
            for m in v16_markers:
                try:
                    m.delete()
                except Exception:
                    pass
            v16_markers = []

            for b in balizas:
                # Construir texto de detalle para el tooltip/texto del marcador
                detalles = []
                for k, v in b["raw"].items():
                    if not isinstance(v, dict) and k not in ("lat", "lon", "lng",
                                                              "latitude", "longitude"):
                        detalles.append(f"{k}: {v}")
                detalle_txt = " | ".join(detalles[:4])   # máximo 4 campos en el label

                m = map_widget.set_marker(
                    b["lat"], b["lon"],
                    text=f"⚠ V16",
                    marker_color_circle="#f57c00",
                    marker_color_outside="#e65100",
                    font=("Arial", 7, "bold"),
                )
                v16_markers.append(m)

            print(f"[V16] {len(v16_markers)} marcador(es) dibujados en el mapa")
            if not v16_markers:
                print("[V16] Sin balizas activas en este momento")

        if map_widget:
            map_widget.after(0, _draw)

    threading.Thread(target=_run, daemon=True).start()


def clear_v16_markers():
    """Elimina todos los marcadores V16 del mapa."""
    global v16_markers, v16_updating
    v16_updating = False
    for m in v16_markers:
        try:
            m.delete()
        except Exception:
            pass
    v16_markers = []
    print("[V16] Marcadores eliminados del mapa")


# ══════════════════════════════════════════════════════════════════════════════
#  CONTROL DEL DRON
# ══════════════════════════════════════════════════════════════════════════════

def _reset_btns():
    for b, t in [(arm_takeOffBtn, 'Despegar'), (landBtn, 'Aterrizar'), (RTLBtn, 'RTL')]:
        b.configure(text=t, fg='black', bg='dark orange')

def _reset_connect_btn():
    connectBtn.configure(text='Conectar', fg='black', bg='dark orange')

def _show_connect_error():
    connectBtn.configure(text='Error de conexion', fg='white', bg='#c62828')
    connectBtn.after(2000, lambda: _reset_connect_btn() if connectBtn['text'] == 'Error de conexion' else None)

def _set_connected_btn():
    connectBtn.configure(text='Conectado', fg='white', bg='green')
    speedSldr.set(1)

def connect_global():
    global _connect_attempt_token
    if REAL_DRONE == False:
        client_dashboard.publish(f'{MY_ORIGIN}/autopilotServiceDemo/connect')
    else:
        client_dashboard.publish(f'{MY_ORIGIN}/autopilotServiceDemo/connect', 'REAL')
    connectBtn.configure(text='Conectando...', fg='black', bg='yellow')
    _connect_attempt_token += 1
    my_token = _connect_attempt_token

    def _timeout_reset():
        time.sleep(20)
        try:
            if my_token == _connect_attempt_token and connectBtn['text'] == 'Conectando...':
                _ui_call(_show_connect_error)
        except Exception:
            pass

    threading.Thread(target=_timeout_reset, daemon=True).start()

def takeoff_global():
    client_dashboard.publish(f'{MY_ORIGIN}/autopilotServiceDemo/arm_takeOff', '5')
    arm_takeOffBtn.configure(text='Despegando...', fg='black', bg='yellow')

def land_global():
    client_dashboard.publish(f'{MY_ORIGIN}/autopilotServiceDemo/Land')
    landBtn.configure(text='Aterrizando...', fg='black', bg='yellow')

def RTL_global():
    client_dashboard.publish(f'{MY_ORIGIN}/autopilotServiceDemo/RTL')
    RTLBtn.configure(text='Retornando...', fg='black', bg='yellow')

def go_global(direction, btn):
    global previousBtn
    if previousBtn: previousBtn.configure(fg='black', bg='dark orange')
    client_dashboard.publish(f'{MY_ORIGIN}/autopilotServiceDemo/go', direction)
    btn.configure(fg='white', bg='green')
    previousBtn = btn

def startTelem_global(): client_dashboard.publish(f'{MY_ORIGIN}/autopilotServiceDemo/startTelemetry')
def stopTelem_global():  client_dashboard.publish(f'{MY_ORIGIN}/autopilotServiceDemo/stopTelemetry')
def changeHeading_global(e): client_dashboard.publish(f'{MY_ORIGIN}/autopilotServiceDemo/changeHeading', str(gradesSldr.get()))
def changeNavSpeed_global(e): client_dashboard.publish(f'{MY_ORIGIN}/autopilotServiceDemo/changeNavSpeed', str(speedSldr.get()))


def _start_telemetry_watchdog_global():
    global _dashboard_telem_watchdog_started
    if _dashboard_telem_watchdog_started:
        return
    _dashboard_telem_watchdog_started = True

    def _run():
        global _dashboard_last_telem_request_ts
        while True:
            try:
                now = time.time()
                last_rx = _dashboard_last_telem_rx_ts
                if client_dashboard is not None:
                    stale = (last_rx > 0.0) and ((now - last_rx) > 5.0)
                    can_retry = (now - _dashboard_last_telem_request_ts) > 6.0
                    if stale and can_retry:
                        client_dashboard.publish(f'{MY_ORIGIN}/autopilotServiceDemo/startTelemetry')
                        _dashboard_last_telem_request_ts = now
                        print("[TELEM] Watchdog: solicitando reanudacion de telemetria")
            except Exception:
                pass
            time.sleep(1.0)

    threading.Thread(target=_run, daemon=True).start()

def connect_local():
    connectBtn.configure(text='Conectando...', fg='black', bg='yellow')
    try:
        if REAL_DRONE == False:
            ok = dron.connect('tcp:127.0.0.1:5763', 115200)
        else:
            ok = dron.connect('udp:127.0.0.1:14551', 57600)

        if ok and dron.state == 'connected':
            connectBtn.configure(text='Conectado', fg='white', bg='green')
            speedSldr.set(1)
        else:
            _show_connect_error()
    except Exception as e:
        print(f"[LOCAL] Error conectando: {e}")
        _show_connect_error()

def takeoff_local():
    dron.arm()
    dron.takeOff(5, blocking=False,
                 callback=lambda: arm_takeOffBtn.configure(text='En vuelo', fg='white', bg='green'))
    arm_takeOffBtn.configure(text='Despegando...', fg='black', bg='yellow')

def land_local():
    dron.Land(blocking=False,
              callback=lambda: (
                  arm_takeOffBtn.configure(text='Despegar', fg='black', bg='dark orange'),
                  landBtn.configure(text='Aterrizar', fg='black', bg='dark orange')
              ),
              params=None)
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
#  PANEL DE DETECCIÓN MULTI-CLASE
# ══════════════════════════════════════════════════════════════════════════════

def _build_detection_panel(parent):
    df = tk.LabelFrame(parent, text="Detección de objetos (multi-clase COCO)")
    df.grid(row=11, column=0, columnspan=2, padx=5, pady=3, sticky="nsew")

    canvas = tk.Canvas(df, height=130, highlightthickness=0)
    vsb    = tk.Scrollbar(df, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    inner = tk.Frame(canvas)
    win_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    canvas.bind("<Configure>",
                lambda e: canvas.itemconfig(win_id, width=e.width))
    inner.bind("<Configure>",
               lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<MouseWheel>",
                lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    COLS = 5
    checkbox_vars = {}

    row_idx = 0
    for grupo_nombre, clases in COCO_GRUPOS:
        tk.Label(inner, text=grupo_nombre,
                 font=("Arial", 7, "bold"), fg="#555555"
                 ).grid(row=row_idx, column=0, columnspan=COLS,
                        sticky="w", padx=4, pady=(4, 0))
        row_idx += 1

        for col_idx, (nombre, oid) in enumerate(clases):
            var = tk.BooleanVar(value=False)
            checkbox_vars[oid] = var
            tk.Checkbutton(
                inner,
                text=nombre,
                variable=var,
                font=("Arial", 8),
                onvalue=True, offvalue=False,
                command=lambda o=oid, v=var: toggle_detect(o, v.get()),
                anchor="w", padx=2, pady=1,
            ).grid(row=row_idx + col_idx // COLS,
                   column=col_idx % COLS,
                   sticky="w", padx=3, pady=1)

        row_idx += (len(clases) + COLS - 1) // COLS

    def _clear_all():
        detect_object_ids.clear()
        for v in checkbox_vars.values():
            v.set(False)
        print("[DET] Todas las clases desactivadas")

    tk.Button(inner, text="✕  Desactivar todas",
              font=("Arial", 8), bg="#e94560", fg="white",
              relief="flat", padx=6, pady=2,
              command=_clear_all
              ).grid(row=row_idx, column=0, columnspan=COLS,
                     padx=4, pady=(6, 4), sticky="w")

    return df


# ══════════════════════════════════════════════════════════════════════════════
#  GUI
# ══════════════════════════════════════════════════════════════════════════════

def crear_ventana(modo):
    global client_dashboard, IS_GROUND_STATION, root_window
    global altShowLbl, headingShowLbl, stateShowLbl
    global speedShowLbl, battShowLbl, gpsShowLbl
    global connectBtn, arm_takeOffBtn, landBtn, RTLBtn
    global speedSldr, gradesSldr, previousBtn

    if modo == "global":
        print("[ROL] Negociando rol Estación de Tierra vs Cliente...")
        IS_GROUND_STATION = negociar_rol_ground_station()
        mostrar_dialogo_rol(IS_GROUND_STATION)

        if IS_GROUND_STATION:
            start_autopilot_service()
            print("[MAIN] AutopilotService iniciado (Estación de Tierra)")
        else:
            print("[MAIN] AutopilotService omitido (Cliente)")

        if IS_GROUND_STATION:
            start_camera_service_global()
        else:
            print("[CAM] Cliente — esperando stream de la Estación de Tierra")

        client_dashboard = mqtt.Client(client_id=f"Dashboard_{_INST_SUFFIX}", transport="websockets")
        client_dashboard.ws_set_options(path="/mqtt")
        client_dashboard.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
        client_dashboard.username_pw_set(USER_DASHBOARD, PASS_DASHBOARD)
        client_dashboard.on_message = on_mqtt_message_dashboard
        client_dashboard.on_connect = lambda c,u,f,rc: (
            print("[MQTT] Dashboard conectado" if rc==0 else f"[MQTT] Error {rc}"),
            c.subscribe(f'autopilotServiceDemo/{MY_ORIGIN}/#') if rc==0 else None
        )
        client_dashboard.on_disconnect = lambda c,u,rc: (
            print(f"[MQTT] Dashboard desconectado (rc={rc}) — paho reconectará automáticamente")
            if rc != 0 else None
        )
        client_dashboard.connect(BROKER_DASHBOARD, PORT, keepalive=30)
        client_dashboard.subscribe(f'autopilotServiceDemo/{MY_ORIGIN}/#')
        client_dashboard.reconnect_delay_set(min_delay=1, max_delay=30)
        client_dashboard.loop_start()
        _start_telemetry_watchdog_global()

        _connect = connect_global;  _takeoff = takeoff_global
        _land    = land_global;     _RTL     = RTL_global
        _go      = go_global;       _video   = start_webrtc_dashboard
        _stopCam = stop_camera_service
        _startT  = startTelem_global; _stopT = stopTelem_global
        _heading = changeHeading_global; _speed = changeNavSpeed_global

        sim_tag = " · Sim" if not REAL_DRONE else ""
        rol_tag = "📡 Estación de Tierra" if IS_GROUND_STATION else "📺 Cliente"
        titulo  = f"Dashboard Dron — Modo Global 🌐{sim_tag}  |  {rol_tag}"

    else:  # local
        IS_GROUND_STATION = True
        start_camera_service_local()

        _connect = connect_local;   _takeoff = takeoff_local
        _land    = land_local;      _RTL     = RTL_local
        _go      = go_local;        _video   = start_webrtc_dashboard
        _stopCam = stop_camera_service
        _startT  = startTelem_local; _stopT  = stopTelem_local
        _heading = changeHeading_local; _speed = changeNavSpeed_local
        titulo   = "Dashboard Dron — Modo Local 🔌"

    # ── Ventana principal ─────────────────────────────────────────────────────
    v = tk.Tk()
    root_window = v
    v.title(titulo)
    v.columnconfigure(0, weight=0, minsize=310)
    v.columnconfigure(1, weight=1)
    v.rowconfigure(0, weight=1)

    if modo == "global":
        rol_bg    = "#1b4d2e" if IS_GROUND_STATION else "#1a2a4a"
        rol_fg    = "#2ecc71" if IS_GROUND_STATION else "#3498db"
        sim_tag   = " (Simulación)" if not REAL_DRONE else ""
        rol_texto = f"📡  ESTACIÓN DE TIERRA{sim_tag}  — AutopilotService activo" \
                    if IS_GROUND_STATION else \
                    f"📺  CLIENTE{sim_tag}  — AutopilotService gestionado por otra consola"
        banner = tk.Frame(v, bg=rol_bg, height=28)
        banner.grid(row=0, column=0, columnspan=2, sticky="ew")
        tk.Label(banner, text=rol_texto, font=("Arial", 9, "bold"),
                 bg=rol_bg, fg=rol_fg).pack(pady=4)
        v.rowconfigure(0, weight=0)
        v.rowconfigure(1, weight=1)
        ctrl_row = 1; map_row = 1
    else:
        ctrl_row = 0; map_row = 0

    terminal_row = map_row + 1
    v.rowconfigure(terminal_row, weight=0)

    # ── Panel izquierdo: controles ────────────────────────────────────────────
    ctrl = tk.Frame(v)
    ctrl.grid(row=ctrl_row, column=0, sticky="nsew", padx=(4,2), pady=4)
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

    btn("▶ Ver video del dron",  _video,   10, col=0, cs=1)
    btn("⏹ Desconectar cámara", _stopCam, 10, col=1, cs=1, bg="#e14d03")

    # ── Panel de detección multi-clase ────────────────────────────────────────
    _build_detection_panel(ctrl)

    # ── Panel derecho: mapa ───────────────────────────────────────────────────
    global map_widget, _goto_callback

    map_frame = tk.LabelFrame(v, text="Mapa — clic para enviar el dron al punto")
    map_frame.grid(row=map_row, column=1, sticky="nsew", padx=(2,4), pady=4)
    map_frame.rowconfigure(0, weight=1)
    map_frame.columnconfigure(0, weight=1)

    map_widget = tkintermapview.TkinterMapView(
        map_frame, width=600, height=700, corner_radius=4)
    map_widget.grid(row=0, column=0, sticky="nsew")

    map_widget.set_position(DEFAULT_LAT, DEFAULT_LON)
    map_widget.set_zoom(15)
    map_widget.add_left_click_map_command(on_map_click)

    _goto_callback = goto_gps_global if modo == "global" else goto_gps_local

    # ── Barra de controles del mapa (6 columnas) ──────────────────────────────
    map_ctrl = tk.Frame(map_frame)
    map_ctrl.grid(row=1, column=0, sticky="ew", pady=2)
    for col in range(6):
        map_ctrl.columnconfigure(col, weight=1)

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

    tk.Button(map_ctrl, text="🎯 Centrar en dron", bg="dark orange",
              command=center_on_drone
              ).grid(row=0, column=0, padx=3, pady=3, sticky="ew")

    tk.Button(map_ctrl, text="🗑 Borrar ruta", bg="dark orange",
              command=clear_path
              ).grid(row=0, column=1, padx=3, pady=3, sticky="ew")

    tk.Button(map_ctrl, text="🗺 OpenStreetMap", bg="dark orange",
              command=lambda: map_widget.set_tile_server(
                  "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png")
              ).grid(row=0, column=2, padx=3, pady=3, sticky="ew")

    # ── Botones de balizas V16 ────────────────────────────────────────────────
    tk.Button(map_ctrl, text="⚠ Balizas V16", bg="#f57c00", fg="white",
              font=("Arial", 9, "bold"),
              command=load_v16_markers
              ).grid(row=0, column=3, padx=3, pady=3, sticky="ew")

    tk.Button(map_ctrl, text="✕ Ocultar V16", bg="#b35c00", fg="white",
              font=("Arial", 9),
              command=clear_v16_markers
              ).grid(row=0, column=4, padx=3, pady=3, sticky="ew")

    # ── Terminal integrada (desplegable) ──────────────────────────────────────
    term_frame = tk.LabelFrame(v, text="Terminal (feedback Python)")
    term_frame.grid(row=terminal_row, column=0, columnspan=2,
                    sticky="nsew", padx=4, pady=(0, 4))
    term_frame.columnconfigure(0, weight=1)
    term_frame.rowconfigure(1, weight=1)

    term_header = tk.Frame(term_frame)
    term_header.grid(row=0, column=0, sticky="ew", padx=4, pady=3)
    term_header.columnconfigure(0, weight=0)
    term_header.columnconfigure(1, weight=0)
    term_header.columnconfigure(2, weight=1)

    term_body = tk.Frame(term_frame)
    term_body.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
    term_body.columnconfigure(0, weight=1)
    term_body.rowconfigure(0, weight=1)

    term_text = tk.Text(term_body, height=10, wrap="word",
                        bg="#101010", fg="#d8d8d8", insertbackground="#d8d8d8")
    term_text.grid(row=0, column=0, sticky="nsew")
    term_text.configure(state="disabled")

    term_scroll = tk.Scrollbar(term_body, orient="vertical", command=term_text.yview)
    term_scroll.grid(row=0, column=1, sticky="ns")
    term_text.configure(yscrollcommand=term_scroll.set)

    term_visible = {"value": False}

    def toggle_terminal():
        term_visible["value"] = not term_visible["value"]
        if term_visible["value"]:
            term_body.grid()
            toggle_btn.configure(text="Ocultar terminal")
            toggle_term_map_btn.configure(text="Ocultar terminal")
        else:
            term_body.grid_remove()
            toggle_btn.configure(text="Mostrar terminal")
            toggle_term_map_btn.configure(text="Terminal")

    toggle_btn = tk.Button(term_header, text="Mostrar terminal", bg="dark orange",
                           command=toggle_terminal)
    toggle_btn.grid(row=0, column=0, padx=(0, 5), sticky="w")

    toggle_term_map_btn = tk.Button(map_ctrl, text="Terminal", bg="dark orange",
                                    command=toggle_terminal)
    toggle_term_map_btn.grid(row=0, column=5, padx=3, pady=3, sticky="ew")

    tk.Button(term_header, text="Limpiar", bg="dark orange",
              command=lambda: (
                  term_text.configure(state="normal"),
                  term_text.delete("1.0", "end"),
                  term_text.configure(state="disabled")
              )).grid(row=0, column=1, padx=(0, 5), sticky="w")

    term_body.grid_remove()
    _attach_log_widget(term_text)
    print("[UI] Terminal integrada lista")

    v.geometry("1100x860")

    # ── Auto-refresco de balizas V16 cada 1 minuto ───────────────────────────
    def _auto_refresh_v16():
        global v16_updating
        while True:
            time.sleep(60)
            if v16_updating and map_widget:
                load_v16_markers()

    threading.Thread(target=_auto_refresh_v16, daemon=True).start()
    # Carga inicial al arrancar el dashboard
    v.after(2000, load_v16_markers)

    # ── Liberar recursos al cerrar ────────────────────────────────────────────
    if modo == "global" and IS_GROUND_STATION:
        v.protocol("WM_DELETE_WINDOW",
                   lambda: (stop_camera_service(), limpiar_claim_ground_station(), liberar_slot(), v.destroy()))
    elif modo == "global":
        v.protocol("WM_DELETE_WINDOW",
                   lambda: (stop_camera_service(), liberar_slot(), v.destroy()))
    else:
        v.protocol("WM_DELETE_WINDOW",
                   lambda: (stop_camera_service(), v.destroy()))

    return v


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    REAL_DRONE = selector_simulacion()
    modo = selector_modo()
    MODE = modo

    if modo == "global":
        seleccionar_slot()

    print(f"[MAIN] Simulación={'sí' if not REAL_DRONE else 'no'}, Modo: {modo}")
    crear_ventana(modo).mainloop()