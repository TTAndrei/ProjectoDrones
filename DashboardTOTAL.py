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

# ══════════════════════════════════════════════════════════════════════════════
#  ÍNDICE — buscar §TAG con Ctrl+F para saltar al bloque
# ══════════════════════════════════════════════════════════════════════════════
#  §CONFIG           Configuración MQTT / red / servidor
#  §PARAMS           Parámetros centralizados (vuelo, visión, seguimiento)
#  §V16_API          Balizas V16 — API DGT
#  §SLOTS            Selección automática de slot HiveMQ
#  §ESTADO           Estado global y variables compartidas
#  §SELECTOR_SIM     Pantalla de selección simulación / dron real
#  §SELECTOR_MODO    Pantalla de selección modo (global / local)
#  §ROL_NEGOC        Negociación de rol ground station
#  §ROL_DIALOGO      Diálogo de rol en pantalla
#  §AUTOPILOT        Autopilot Service — gestión de comandos y telemetría
#  §AUTOPILOT_RC     Callbacks RC y controlador de seguimiento
#  §AUTOPILOT_MQTT   MQTT callbacks del autopilot service
#  §CAMARA           Camera Service — captura y streaming WebRTC
#  §DETECCION        Detección YOLO multi-clase
#  §DETECCION_DIST   Estimación de distancia desde bounding box
#  §DETECCION_FOLLOW Lógica de auto-seguimiento (_auto_follow_from_detections)
#  §DETECCION_DEBUG  Debug overlay (puntos centro imagen / bbox)
#  §WEBRTC           WebRTC Dashboard — receptor de vídeo
#  §WEBRTC_MQTT      MQTT message handler del dashboard
#  §WEBRTC_CRIMEN    Alertas de crimen y popup de clip
#  §MAPA             Mapa interactivo con marcadores
#  §V16_MAPA         Balizas V16 — carga y dibujo en el mapa
#  §CONTROL          Control del dron — botones y comandos
#  §CONTROL_GLOBAL   Comandos modo global (connect/takeoff/follow/...)
#  §CONTROL_FOLLOW   Distance follow global
#  §CONTROL_LOCAL    Comandos modo local (dronLink directo)
#  §PANEL_DETECCION  Panel UI de detección (selector clases, parámetros)
#  §GUI              Ventana principal — crear_ventana()
#  §MAIN             Entry point
# ══════════════════════════════════════════════════════════════════════════════

import asyncio, json, os, ssl, threading, time, requests, sys
import logging, warnings, base64, math
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
from distance_follow_controller import DistanceFollowController

# ══════════════════════════════════════════════════════════════════════════════
#  §CONFIG  CONFIGURACIÓN
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

# Credenciales compartidas para el canal WebRTC (CameraService + todos los clientes).
# Siempre usamos el slot 0 (InterfazGlobal) para que CameraService y clientes
# puedan publicar/suscribirse a los topics webrtc/* con el mismo usuario,
# evitando bloqueos de ACL entre distintos usuarios HiveMQ.
USER_WEBRTC = HIVEMQ_USERS[0]["user"]
PASS_WEBRTC = HIVEMQ_USERS[0]["password"]

T_CAM_REQUEST = "webrtc/request"
T_CAM_OFFER   = "webrtc/offer"
T_CAM_ANSWER  = "webrtc/answer"

T_OFFER  = T_CAM_OFFER
T_ANSWER = T_CAM_ANSWER
T_AUTOPILOT_CLAIM = "autopilot/claim"
T_CRIME_ALERT     = "crime/alert"
T_CRIME_CHUNK     = "crime/clip/chunk"
T_SLOT_PREFIX     = "slot/ocupado/"

TCP_HOST = "localhost"
TCP_PORT = 9999

# ══════════════════════════════════════════════════════════════════════════════
#  §PARAMS  CONFIGURACIÓN CENTRALIZADA DE PARÁMETROS
# ══════════════════════════════════════════════════════════════════════════════

# ─── VUELO ───────────────────────────────────────────────────────────────────
FLIGHT_TAKEOFF_HEIGHT    = 2          # metros — altura de despegue
FLIGHT_DEFAULT_NAV_SPEED = 1          # m/s — velocidad de navegación inicial
FLIGHT_MAX_NAV_SPEED     = 5         # m/s — velocidad máxima del slider

# ─── VISIÓN / DETECCIÓN ──────────────────────────────────────────────────────
VISION_OBJECT_SIZE_M      = 0.18       # metros — medida física del objeto (calibración)
VISION_CAMERA_VFOV_DEG    = 49.5      # grados — campo de visión vertical de la cámara
VISION_CAMERA_PITCH_DEG   = 0.0       # grados — 0 frontal, positivo hacia abajo
VISION_DISTANCE_K         = 1.2       # constante de calibración (profundidad/bbox)
VISION_MIN_DISTANCE       = 0.1       # metros — distancia mínima detectable
VISION_MAX_DISTANCE       = 25.0      # metros — distancia máxima de operación
VISION_CONFIDENCE_MIN     = 0.35      # confianza mínima para aceptar detecciones

# ─── SEGUIMIENTO (DISTANCE FOLLOW) ───────────────────────────────────────────
# Control PD via RC override. Ver distance_follow_controller.py para guía de tuning.
FOLLOW_TARGET_DISTANCE    = 2.0      # metros — distancia objetivo al objeto
FOLLOW_DISTANCE_DEADBAND  = 0.30     # metros — zona muerta de distancia
FOLLOW_LATERAL_DEADBAND   = 0.12     # normalizado — zona muerta lateral
FOLLOW_KP_DISTANCE        = 40       # PWM/m   — ganancia P longitudinal
FOLLOW_KD_DISTANCE        = 8        # PWM/(m/s) — ganancia D longitudinal (antioscilación)
FOLLOW_KP_LATERAL         = 180      # PWM/norm — ganancia P lateral
FOLLOW_KD_LATERAL         = 30       # PWM/(norm/s) — ganancia D lateral (antioscilación)
FOLLOW_RC_MAX_OFFSET      = 200      # PWM offset máximo desde neutro (1300–1700)
FOLLOW_RC_MIN_OFFSET      = 40       # PWM offset mínimo cuando hay error activo
FOLLOW_DERIV_ALPHA        = 0.4      # EMA filtro derivada (0.0=sin derivada, 1.0=cruda)
FOLLOW_LOST_TIMEOUT       = 1.5      # segundos — tiempo para considerar pérdida de objetivo
FOLLOW_MAX_OFFSET_ABS     = 1.0      # normalizado — límite máximo de offset lateral
FOLLOW_STOP_AFTER_S       = 2        # segundos — tiempo para detener seguimiento tras perder objetivo
FOLLOW_ALT_STALE_S        = 3.0      # segundos — max antigüedad de altitud en telemetría

# ── Detección y análisis de frames ────────────────────────────────────────────
DETECTION_CONTROL_HZ      = 10.0       # frecuencia de control del seguimiento

# ══════════════════════════════════════════════════════════════════════════════
#  §V16_API  BALIZAS V16 — API DGT
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
#  §SLOTS  SELECCIÓN AUTOMÁTICA DE SLOT HIVEMQ
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
#  §ESTADO  ESTADO GLOBAL
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
connectBtn = arm_takeOffBtn = landBtn = RTLBtn = followBtn = overlayBtn = None
_mode_buttons = {}
_debug_overlay = False
speedSldr  = gradesSldr = None
followTargetDistVar = followDeadzoneVar = None
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
_auto_follow_enabled = False
_auto_follow_active = False
_auto_follow_lock = threading.Lock()
_auto_follow_last_target_ts = 0.0

# Calibracion simple distancia/bbox (usa parámetros centralizados)
_auto_follow_dist_k = VISION_DISTANCE_K
_auto_follow_object_size_m = VISION_OBJECT_SIZE_M
_auto_follow_camera_vfov_deg = VISION_CAMERA_VFOV_DEG
_auto_follow_camera_pitch_deg = VISION_CAMERA_PITCH_DEG
_auto_follow_min_dist = VISION_MIN_DISTANCE
_auto_follow_max_dist = VISION_MAX_DISTANCE
_auto_follow_conf_min = VISION_CONFIDENCE_MIN
_auto_follow_stop_after_s = FOLLOW_STOP_AFTER_S

_follow_alt_m = None
_follow_alt_ts = 0.0

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
#  §SELECTOR_SIM  PANTALLA DE SELECCIÓN DE SIMULACIÓN / DRON
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
#  §SELECTOR_MODO  PANTALLA DE SELECCIÓN DE MODO
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
#  §ROL_NEGOC  NEGOCIACIÓN DE ROL
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
#  §ROL_DIALOGO  DIÁLOGO DE ROL
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
#  §AUTOPILOT  AUTOPILOT SERVICE (integrado)
# ══════════════════════════════════════════════════════════════════════════════

client_autopilot = None

_telem_subscribers: dict = {}
_telem_lock = threading.Lock()
_telem_active = False
_distance_follow = None


def _autopilot_topic(origin: str) -> str:
    return f"autopilotServiceDemo/{origin}"


def _parse_json_payload(payload_text: str) -> dict:
    if not payload_text:
        return {}
    data = json.loads(payload_text)
    if not isinstance(data, dict):
        raise ValueError("Se esperaba un objeto JSON")
    return data


# §AUTOPILOT_RC ── callbacks RC y controlador de seguimiento ──────────────────
def _follow_set_nav_speed(speed, origin):
    dron.changeNavSpeed(float(speed))


def _follow_set_direction(direction, origin):
    dron.go(direction)


def _follow_stop_direction(origin):
    dron.go("Stop")


def _follow_send_rc(roll_pwm, pitch_pwm):
    dron.send_rc(roll_pwm, pitch_pwm, 1500, 1500)


def _is_drone_flying() -> bool:
    return dron.state == 'flying'


def _autopilot_publish_status(message: str, origin: str = None, level: str = "info", **extra):
    if origin is None:
        with _telem_lock:
            origin = next(iter(_telem_subscribers), None)
    if origin is None:
        return
    payload = {
        "timestamp": int(time.time()),
        "level": level,
        "message": message,
        "drone_state": getattr(dron, "state", "unknown"),
    }
    payload.update(extra)
    try:
        client_autopilot.publish(_autopilot_topic(origin) + '/status', json.dumps(payload))
    except Exception as e:
        print(f"[AUTOPILOT] Error publicando status: {e}")


def _autopilot_publish_error(message: str, origin: str = None, **extra):
    if origin is None:
        with _telem_lock:
            origin = next(iter(_telem_subscribers), None)
    if origin is None:
        return
    payload = {
        "timestamp": int(time.time()),
        "message": message,
        "drone_state": getattr(dron, "state", "unknown"),
    }
    payload.update(extra)
    try:
        client_autopilot.publish(_autopilot_topic(origin) + '/error', json.dumps(payload))
    except Exception as e:
        print(f"[AUTOPILOT] Error publicando error: {e}")


def _ensure_distance_follow_controller():
    global _distance_follow
    if _distance_follow is None:
        _distance_follow = DistanceFollowController(
            set_nav_speed=_follow_set_nav_speed,
            set_direction=_follow_set_direction,
            stop_direction=_follow_stop_direction,
            is_flying=_is_drone_flying,
            send_rc=_follow_send_rc,
            publish_status=_autopilot_publish_status,
            publish_error=_autopilot_publish_error,
            control_hz=DETECTION_CONTROL_HZ,
        )
    return _distance_follow


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


# §AUTOPILOT_MQTT ── MQTT callbacks del autopilot service ─────────────────────
def autopilot_on_message(cli, userdata, message):
    parts   = message.topic.split("/")
    origin  = parts[0]
    command = parts[2]
    sending_topic = _autopilot_topic(origin)
    follow_controller = _ensure_distance_follow_controller()

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
            if follow_controller.is_running():
                follow_controller.stop(reason="manual-go", origin=origin)
            dron.go(message.payload.decode("utf-8"))

    elif command == 'Land':
        if dron.state == 'flying':
            if follow_controller.is_running():
                follow_controller.stop(reason="land", origin=origin)
            dron.Land(blocking=False,
                      callback=lambda ev: autopilot_publish_event(ev, origin),
                      params='landed')

    elif command == 'RTL':
        if dron.state == 'flying':
            if follow_controller.is_running():
                follow_controller.stop(reason="rtl", origin=origin)
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
        if follow_controller.is_running():
            follow_controller.stop(reason="manual-speed-change", origin=origin)
        dron.changeNavSpeed(float(message.payload.decode("utf-8")))

    elif command == 'startDistanceFollow':
        if dron.state != 'flying':
            _autopilot_publish_error(
                "No se puede activar seguimiento por distancia: dron no esta en vuelo",
                origin=origin,
                command=command,
            )
            return
        payload_text = message.payload.decode("utf-8").strip() if message.payload else ""
        try:
            cfg = _parse_json_payload(payload_text)
        except Exception as e:
            _autopilot_publish_error(
                f"Payload startDistanceFollow invalido: {e}",
                origin=origin,
                command=command,
                payload=payload_text,
            )
            return
        follow_controller.start(origin=origin, config=cfg)
        _autopilot_publish_status(
            "Seguimiento por distancia activado",
            origin=origin,
            mode="distance-follow",
            config=follow_controller.snapshot_config(),
        )

    elif command == 'updateDistanceFollow':
        if not follow_controller.is_running():
            _autopilot_publish_status(
                "updateDistanceFollow ignorado: seguimiento no activo",
                origin=origin,
                level="warning",
                command=command,
            )
            return
        payload_text = message.payload.decode("utf-8").strip() if message.payload else ""
        try:
            obs = _parse_json_payload(payload_text)
        except Exception as e:
            _autopilot_publish_error(
                f"Payload updateDistanceFollow invalido: {e}",
                origin=origin,
                command=command,
                payload=payload_text,
            )
            return
        if not follow_controller.update_observation(obs):
            _autopilot_publish_error(
                "Observacion de seguimiento invalida",
                origin=origin,
                command=command,
                payload=payload_text,
            )

    elif command == 'stopDistanceFollow':
        payload_text = message.payload.decode("utf-8").strip() if message.payload else ""
        reason = "stop-request"
        try:
            data = _parse_json_payload(payload_text)
            reason = str(data.get("reason", reason))
        except Exception:
            pass
        follow_controller.stop(reason=reason, origin=origin)
        _autopilot_publish_status(
            "Seguimiento por distancia detenido",
            origin=origin,
            reason=reason,
        )

    elif command == 'changeAltitude':
        dron.change_altitude(float(message.payload.decode("utf-8")), blocking=False)

    elif command == 'goto':
        coords = json.loads(message.payload.decode("utf-8"))
        dron.goto(coords["lat"], coords["lon"], coords.get("alt", 5.0),
                  blocking=False)
        print(f"[AUTOPILOT] goto → {coords['lat']:.6f}, {coords['lon']:.6f}, {coords.get('alt',5)}m")

    elif command == 'setFlightMode':
        mode_name = message.payload.decode("utf-8").strip().upper()
        try:
            dron.setFlightMode(mode_name)
            _autopilot_publish_status(f"Modo de vuelo: {mode_name}", origin=origin)
            print(f"[AUTOPILOT] Modo cambiado a {mode_name}")
        except Exception as e:
            _autopilot_publish_error(f"Error cambiando modo a {mode_name}: {e}", origin=origin)


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
        try:
            controller = _ensure_distance_follow_controller()
            if controller.is_running():
                controller.stop(reason="mqtt-disconnect")
        except Exception:
            pass
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
#  §CAMARA  CAMERA SERVICE (integrado)
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

        for box in self._last_boxes:
            x1, y1, x2, y2, label = box[:5]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, label, (x1, max(y1 - 8, 0)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

        _draw_debug_overlay(frame, self._last_boxes)
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

# Servidores TURN públicos de Open Relay (sin cuenta, siempre disponibles).
# Se usan como base garantizada; Metered se añade encima si funciona.
_OPEN_RELAY_SERVERS = [
    RTCIceServer(
        urls=["turn:openrelay.metered.ca:80",
              "turn:openrelay.metered.ca:443",
              "turn:openrelay.metered.ca:443?transport=tcp",
              "turns:openrelay.metered.ca:443"],
        username="openrelayproject",
        credential="openrelayproject",
    ),
    RTCIceServer(urls=["stun:stun.l.google.com:19302",
                       "stun:stun1.l.google.com:19302"]),
]


def get_ice_config():
    print("[ICE] Obteniendo credenciales TURN de Metered...")
    ice_servers = list(_OPEN_RELAY_SERVERS)   # base siempre presente

    try:
        resp = requests.get(METERED_API, timeout=8)
        if resp.status_code != 200:
            print(f"[ICE] Metered API devuelvió {resp.status_code} — usando Open Relay")
        else:
            servers = resp.json()
            metered_servers = []
            for s in servers:
                urls = s.get("urls")
                if isinstance(urls, str):
                    urls = [urls]
                u, c = s.get("username"), s.get("credential")
                if u and c:
                    metered_servers.append(
                        RTCIceServer(urls=urls, username=u, credential=c)
                    )
            if metered_servers:
                ice_servers = metered_servers + ice_servers
                print(f"[ICE] {len(metered_servers)} servidores Metered + Open Relay de respaldo:")
            else:
                print("[ICE] Metered no devolvió servidores con credenciales — usando Open Relay")
            for srv in ice_servers[:3]:
                print(f"  {srv.urls[0]}")
    except Exception as e:
        print(f"[ICE] Error contactando Metered ({e}) — usando Open Relay")

    return RTCConfiguration(iceServers=ice_servers)


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

    # Esperar gathering con evento (no polling) — garantiza candidatos TURN/relay
    print(f"[CAM:{origen}] Esperando ICE gathering (máx 8 s)...")
    cam_gathering_done = asyncio.Event()

    @pc_peer.on("icegatheringstatechange")
    def _on_cam_gathering():
        if pc_peer.iceGatheringState == "complete":
            cam_gathering_done.set()

    if pc_peer.iceGatheringState == "complete":
        cam_gathering_done.set()

    try:
        await asyncio.wait_for(cam_gathering_done.wait(), timeout=8.0)
    except asyncio.TimeoutError:
        print(f"[CAM:{origen}] ICE gathering timeout (8 s) — usando candidatos disponibles")

    candidates = [l for l in pc_peer.localDescription.sdp.splitlines()
                  if l.startswith("a=candidate")]
    has_relay = any("relay" in c for c in candidates)
    print(f"[CAM:{origen}] {len(candidates)} candidatos — "
          f"{'\u2713 relay' if has_relay else '\u26a0 sin relay'}")

    mqtt_cam_client.publish(t_offer_peer, json.dumps({
        "sdp":  pc_peer.localDescription.sdp,
        "type": pc_peer.localDescription.type,
    }), retain=True)
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
            ids = _normalize_detect_ids(json.loads(payload))
            detect_object_ids.clear()
            detect_object_ids.update(ids)
            print(f"[COCO] Clases activas desde C#: {sorted(detect_object_ids)}")
            if ids and yolo_model is None:
                threading.Thread(target=load_yolo, daemon=True).start()
        except Exception as e:
            print(f"[COCO] Error parseando detectClasses: {e}")

    mqtt_cam_client.message_callback_add("webrtc/detectClasses", _on_detect_classes)

    mqtt_cam_client.message_callback_add(T_CAM_REQUEST, _on_request)
    mqtt_cam_client.subscribe(T_CAM_REQUEST)
    print(f"[CAM] Suscrito a solicitudes en {T_CAM_REQUEST}")
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

    if USER_DASHBOARD is None or PASS_DASHBOARD is None:
        print("[CAM] ERROR: credenciales HiveMQ no asignadas — seleccionar_slot() debe ejecutarse primero")
        return

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
            cam_client.username_pw_set(USER_WEBRTC, PASS_WEBRTC)
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
#  §DETECCION  DETECCIÓN YOLO — MULTI-CLASE
# ══════════════════════════════════════════════════════════════════════════════

def load_yolo():
    global yolo_model
    if yolo_model is None:
        print("[DET] Cargando YOLOv5s (modelo base COCO)...")
        import torch
        yolo_model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
        yolo_model.eval()
        print("[DET] Modelo base listo")


_COCHE_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "best.pt")
_COCHE_CLASS_ID   = 2
_yolo_model_coche = None


def load_yolo_coche():
    global _yolo_model_coche
    if _yolo_model_coche is not None:
        return
    import torch
    if os.path.exists(_COCHE_MODEL_PATH):
        print(f"[DET] Cargando modelo entrenado de coches: {_COCHE_MODEL_PATH}")
        try:
            yolov5_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yolov5")
            if os.path.isdir(yolov5_dir):
                _yolo_model_coche = torch.hub.load(
                    yolov5_dir, "custom",
                    path=_COCHE_MODEL_PATH,
                    source="local"
                )
            else:
                _yolo_model_coche = torch.hub.load(
                    "ultralytics/yolov5", "custom",
                    path=_COCHE_MODEL_PATH,
                    force_reload=False
                )
            _yolo_model_coche.names = {0: "Coche"}
            _yolo_model_coche.eval()
            print("[DET] ✓ Modelo de coches entrenado listo")
        except Exception as e:
            print(f"[DET] Error cargando modelo de coches: {e} — usando modelo base")
            _yolo_model_coche = None
    else:
        print(f"[DET] best.pt no encontrado en {_COCHE_MODEL_PATH} — usando modelo base para coches")


def _normalize_detect_ids(raw_ids):
    normalized = set()
    if not isinstance(raw_ids, (list, tuple, set)):
        return normalized
    for raw_id in raw_ids:
        try:
            normalized.add(int(raw_id))
        except Exception:
            continue
    return normalized


def toggle_detect(obj_id: int, active: bool):
    global _auto_follow_active
    if active:
        detect_object_ids.add(obj_id)
        if yolo_model is None:
            threading.Thread(target=load_yolo, daemon=True).start()
        if obj_id == _COCHE_CLASS_ID:
            threading.Thread(target=load_yolo_coche, daemon=True).start()
        print(f"[DET] +clase {obj_id}  activas={sorted(detect_object_ids)}")
    else:
        detect_object_ids.discard(obj_id)
        print(f"[DET] -clase {obj_id}  activas={sorted(detect_object_ids)}")

    if MODE == "global" and not detect_object_ids:
        with _auto_follow_lock:
            if _auto_follow_active:
                try:
                    stopDistanceFollow_global("no-classes-selected")
                except Exception:
                    pass
                _auto_follow_active = False


# §DETECCION_DIST ── estimación de distancia desde bounding box ───────────────
def _estimate_distance_from_bbox(x1, y1, x2, y2, frame_shape, clamp=True):
    img_h = max(1, int(frame_shape[0]))
    box_h = max(1, int(y2 - y1))

    # Modelo pinhole: distance = (focal_px * object_size_m) / bbox_px
    vfov_rad = math.radians(max(5.0, min(170.0, float(_auto_follow_camera_vfov_deg))))
    focal_px = (img_h * 0.5) / max(1e-6, math.tan(vfov_rad * 0.5))
    object_size_m = max(0.01, float(_auto_follow_object_size_m))
    distance = (float(_auto_follow_dist_k) * object_size_m * focal_px) / float(box_h)

    if clamp:
        return max(_auto_follow_min_dist, min(_auto_follow_max_dist, distance))
    return distance


def _update_follow_altitude(alt_value):
    global _follow_alt_m, _follow_alt_ts
    try:
        alt_m = float(alt_value)
    except Exception:
        return
    _follow_alt_m = alt_m
    _follow_alt_ts = time.time()


def _get_follow_altitude():
    if _follow_alt_m is None:
        return None
    if (time.time() - _follow_alt_ts) > FOLLOW_ALT_STALE_S:
        return None
    return _follow_alt_m



def _estimate_horizontal_distance_from_bbox(x1, y1, x2, y2, frame_shape, alt_m=None):
    slant = _estimate_distance_from_bbox(x1, y1, x2, y2, frame_shape, clamp=False)

    # Usa solo el ángulo fijo de montaje de la cámara (no la posición vertical del bbox).
    pitch_rad = math.radians(float(_auto_follow_camera_pitch_deg))
    horizontal = slant * math.cos(pitch_rad)
    if horizontal < 0.0:
        horizontal = 0.0

    return horizontal, slant, pitch_rad


def set_detect_object_physical_size(size_text):
    global _auto_follow_object_size_m
    try:
        raw_text = str(size_text).strip().lower().replace(",", ".")
        if not raw_text:
            raise ValueError("empty value")

        if raw_text.endswith("cm"):
            size_value = float(raw_text[:-2].strip()) / 100.0
        elif raw_text.endswith("m"):
            size_value = float(raw_text[:-1].strip())
        else:
            size_value = float(raw_text)
            # Si se escribe un valor grande sin unidad, se asume cm.
            if size_value > 3.0:
                size_value = size_value / 100.0

        if size_value <= 0.0:
            raise ValueError("size must be positive")
        _auto_follow_object_size_m = size_value
        print(f"[DEPTH] Medida física del objeto: {_auto_follow_object_size_m:.3f} m")
        return True
    except Exception:
        print(f"[DEPTH] Valor inválido '{size_text}'. Usa 'm' o 'cm' (ej: 1.70, 0.17, 17cm)")
        return False


def set_follow_target_altitude(alt_text):
    try:
        raw = str(alt_text).strip().lower().replace(",", ".")
        if raw.endswith("m"):
            raw = raw[:-1].strip()
        alt_m = float(raw)
        if alt_m <= 0.0:
            raise ValueError("altitude must be positive")
        result = dron.change_altitude(alt_m, blocking=False)
        if result:
            print(f"[ALT] Comando altitud enviado: {alt_m:.1f}m")
        else:
            print(f"[ALT] Error: dron no esta volando")
        return result
    except Exception:
        print(f"[ALT] Valor invalido '{alt_text}'. Usa metros (ej: 3, 2.5, 5m)")
        return False


def set_camera_pitch_deg(pitch_text):
    global _auto_follow_camera_pitch_deg
    try:
        raw_text = str(pitch_text).strip().lower().replace(",", ".")
        if raw_text.endswith("deg"):
            raw_text = raw_text[:-3].strip()
        value = float(raw_text)
        if value < -89.0:
            value = -89.0
        if value > 89.0:
            value = 89.0
        _auto_follow_camera_pitch_deg = value
        print(f"[CAM] Pitch camara: {_auto_follow_camera_pitch_deg:.1f} deg")
        return True
    except Exception:
        print(f"[CAM] Valor de pitch invalido '{pitch_text}' (usa grados, ej: 0, 30, 90)")
        return False


def _pick_follow_target(detections):
    if not detections:
        return None

    best = None
    best_score = None
    for d in detections:
        conf = float(d.get("conf", 0.0))
        if conf < _auto_follow_conf_min:
            continue
        area = max(1.0, float(d.get("area", 1.0)))
        score = area * max(conf, 0.01)
        if best is None or score > best_score:
            best = d
            best_score = score
    return best


# §DETECCION_FOLLOW ── lógica de auto-seguimiento ──────────────────────────────
def _auto_follow_from_detections(frame_shape, detections):
    global _auto_follow_active, _auto_follow_last_target_ts

    if not _auto_follow_enabled:
        return

    now = time.time()
    best = _pick_follow_target(detections)
    if best is not None:
        x1, y1, x2, y2 = best["x1"], best["y1"], best["x2"], best["y2"]
        img_h, img_w = int(frame_shape[0]), int(frame_shape[1])
        cx = (x1 + x2) * 0.5
        offset_x = (cx - (img_w * 0.5)) / max(1.0, img_w * 0.5)
        alt_m = _get_follow_altitude()
        horiz_m, slant_m, total_pitch = _estimate_horizontal_distance_from_bbox(
            x1, y1, x2, y2, frame_shape, alt_m=alt_m
        )
        if horiz_m is None:
            distance_m = _auto_follow_max_dist
            valid = False
        else:
            distance_m = max(_auto_follow_min_dist, min(_auto_follow_max_dist, horiz_m))
            valid = True
        confidence = float(best.get("conf", 1.0))
        target_id = f"{best.get('label', 'obj')}:{best.get('cls_id', 'na')}"
        cam_pitch_deg = float(_auto_follow_camera_pitch_deg)
        alt_str = f"{alt_m:.1f}m" if alt_m is not None else "n/a"
        horiz_str = f"{distance_m:.2f}m" if valid else "n/a"
        print(
            f"[FOLLOW] Dist horiz={horiz_str} slant={slant_m:.2f}m "
            f"alt={alt_str} cam_pitch={cam_pitch_deg:.1f}deg "
            f"offset_x={offset_x:+.3f} conf={confidence:.2f} target={target_id}"
        )
    else:
        offset_x = 0.0
        distance_m = None
        confidence = 0.0
        target_id = None
        valid = False

    if MODE == "global":
        if client_dashboard is None:
            return
        with _auto_follow_lock:
            if best is None:
                if _auto_follow_active and (now - _auto_follow_last_target_ts) > _auto_follow_stop_after_s:
                    try:
                        stopDistanceFollow_global("target-lost")
                        print("[FOLLOW] Objetivo perdido: stopDistanceFollow")
                    except Exception as e:
                        print(f"[FOLLOW] Error deteniendo seguimiento: {e}")
                    _auto_follow_active = False
                return

            if not _auto_follow_active:
                if not valid:
                    print("[FOLLOW] Distancia horizontal invalida; esperando alt/pitch")
                    return
                try:
                    startDistanceFollow_global(_follow_config())
                    _auto_follow_active = True
                    print("[FOLLOW] startDistanceFollow")
                except Exception as e:
                    print(f"[FOLLOW] Error arrancando seguimiento: {e}")
                    return

            try:
                updateDistanceFollow_global(
                    distance_m=distance_m,
                    offset_x=offset_x,
                    confidence=confidence,
                    valid=valid,
                    target_id=target_id,
                )
                if valid:
                    _auto_follow_last_target_ts = now
            except Exception as e:
                print(f"[FOLLOW] Error enviando updateDistanceFollow: {e}")
        return

    controller = _ensure_distance_follow_controller()
    with _auto_follow_lock:
        if best is None:
            if _auto_follow_active and (now - _auto_follow_last_target_ts) > _auto_follow_stop_after_s:
                try:
                    controller.update_observation({
                        "distance_m": _auto_follow_max_dist,
                        "offset_x": 0.0,
                        "valid": False,
                        "confidence": 0.0,
                        "target_id": None,
                    })
                    print("[FOLLOW] Objetivo perdido: stop local implícito")
                except Exception as e:
                    print(f"[FOLLOW] Error marcando objetivo perdido: {e}")
                _auto_follow_active = False
            return

        if not _auto_follow_active:
            if not valid:
                print("[FOLLOW] Distancia horizontal invalida; esperando alt/pitch")
                return
            try:
                controller.start(origin="local", config=_follow_config())
                _auto_follow_active = True
                print("[FOLLOW] startDistanceFollow (local)")
            except Exception as e:
                print(f"[FOLLOW] Error arrancando seguimiento local: {e}")
                return

        try:
            controller.update_observation({
                "distance_m": distance_m,
                "offset_x": offset_x,
                "valid": valid,
                "confidence": confidence,
                "target_id": target_id,
            })
            if valid:
                _auto_follow_last_target_ts = now
        except Exception as e:
            print(f"[FOLLOW] Error actualizando seguimiento local: {e}")


# §DETECCION_DEBUG ── overlay de depuración en vídeo ──────────────────────────
def _draw_debug_overlay(frame, boxes):
    if not _debug_overlay:
        return
    h, w = frame.shape[:2]
    cx_img, cy_img = w // 2, h // 2
    # Punto amarillo + anillo en centro de imagen
    cv2.circle(frame, (cx_img, cy_img), 8, (0, 255, 255), -1)
    cv2.circle(frame, (cx_img, cy_img), 14, (0, 255, 255), 2)
    # Punto cian + anillo en centro de cada bbox
    for box in boxes:
        x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
        bx, by = (x1 + x2) // 2, (y1 + y2) // 2
        cv2.circle(frame, (bx, by), 6, (255, 255, 0), -1)
        cv2.circle(frame, (bx, by), 11, (255, 255, 0), 2)


def run_detect(frame):
    if yolo_model is None or not detect_object_ids:
        _auto_follow_from_detections(frame.shape, [])
        return []

    id_to_name = {
        oid: nombre
        for _, clases in COCO_GRUPOS
        for nombre, oid in clases
        if oid in detect_object_ids
    }

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    ids_sin_coche  = detect_object_ids - {_COCHE_CLASS_ID}
    detectar_coche = _COCHE_CLASS_ID in detect_object_ids

    raw_detections = []

    if ids_sin_coche:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            results_base = yolo_model(rgb)
        for *xyxy, conf, cls in results_base.xyxy[0]:
            cls_id = int(cls.item())
            if cls_id in ids_sin_coche:
                raw_detections.append((xyxy, conf, cls_id))

    if detectar_coche:
        modelo_coche = _yolo_model_coche if _yolo_model_coche is not None else yolo_model
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            results_coche = modelo_coche(rgb)
        for *xyxy, conf, cls in results_coche.xyxy[0]:
            cls_interno = int(cls.item())
            if _yolo_model_coche is not None and cls_interno == 0:
                raw_detections.append((xyxy, conf, _COCHE_CLASS_ID))
            elif _yolo_model_coche is None and cls_interno == _COCHE_CLASS_ID:
                raw_detections.append((xyxy, conf, _COCHE_CLASS_ID))

    boxes      = []
    detections = []
    for xyxy, conf, cls_id in raw_detections:
        x1, y1, x2, y2 = map(int, xyxy)
        conf_f = float(conf.item()) if hasattr(conf, "item") else float(conf)
        label  = id_to_name.get(cls_id, str(cls_id))
        boxes.append((x1, y1, x2, y2, label, cls_id, conf_f))
        detections.append({
            "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "label": label, "cls_id": cls_id,
            "conf": conf_f,
            "area": max(1, (x2 - x1) * (y2 - y1)),
        })

    best_depth_target = _pick_follow_target(detections)
    if best_depth_target is not None:
        alt_m = _get_follow_altitude()
        horiz_m, slant_m, total_pitch = _estimate_horizontal_distance_from_bbox(
            best_depth_target["x1"],
            best_depth_target["y1"],
            best_depth_target["x2"],
            best_depth_target["y2"],
            frame.shape,
            alt_m=alt_m,
        )
        dist_str = f"{horiz_m:.2f}m" if horiz_m is not None else "n/a"
        print(
            f"[DEPTH] Dist horiz={dist_str} slant={slant_m:.2f}m "
            f"target={best_depth_target.get('label', 'obj')}:{best_depth_target.get('cls_id', 'na')} "
            f"conf={float(best_depth_target.get('conf', 0.0)):.2f}"
        )

    _auto_follow_from_detections(frame.shape, detections)
    return boxes


# ══════════════════════════════════════════════════════════════════════════════
#  §WEBRTC  WEBRTC DASHBOARD (receptor de vídeo)
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

    # Cliente MQTT dedicado para la señalización WebRTC.
    # Usa USER_WEBRTC (slot 0 / InterfazGlobal) igual que el CameraService,
    # garantizando que ambos extremos comparten el mismo usuario HiveMQ y
    # no hay bloqueos de ACL al publicar/recibir en los topics webrtc/*.
    import uuid as _uuid_webrtc
    webrtc_mqtt = mqtt.Client(
        client_id=f"WebRTCDash_{_uuid_webrtc.uuid4().hex[:6]}",
        transport="websockets"
    )
    webrtc_mqtt.ws_set_options(path="/mqtt")
    webrtc_mqtt.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
    webrtc_mqtt.username_pw_set(USER_WEBRTC, PASS_WEBRTC)
    try:
        webrtc_mqtt.connect(BROKER_DASHBOARD, PORT, keepalive=30)
    except Exception as e:
        print(f"[WebRTC] Error conectando cliente MQTT de señalización: {e}")
        return
    webrtc_mqtt.loop_start()

    def _on_offer(cli, userdata, msg):
        if msg.topic == t_my_offer and msg.payload:
            try:
                data = json.loads(msg.payload)
            except Exception:
                return
            print(f"[SIG] Oferta recibida en {t_my_offer}")
            asyncio.run_coroutine_threadsafe(
                handle_offer_dashboard(data, t_my_answer, webrtc_mqtt), loop_dashboard)

    webrtc_mqtt.message_callback_add(t_my_offer, _on_offer)
    webrtc_mqtt.subscribe(t_my_offer)

    webrtc_mqtt.publish(t_my_request, MY_ORIGIN, retain=True)
    print(f"[WebRTC] Solicitud enviada a {t_my_request} (payload={MY_ORIGIN})")

    async def _retry_request():
        for _ in range(12):
            await asyncio.sleep(5)
            if pc.connectionState in ("connected", "connecting"):
                break
            print(f"[WebRTC] Re-solicitud → {t_my_request}")
            webrtc_mqtt.publish(t_my_request, MY_ORIGIN, retain=True)

    asyncio.run_coroutine_threadsafe(_retry_request(), loop_dashboard)
    loop_dashboard.run_forever()

    # Limpiar cliente WebRTC al salir
    try:
        webrtc_mqtt.loop_stop()
        webrtc_mqtt.disconnect()
    except Exception:
        pass


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
                for box in last_boxes:
                    x1, y1, x2, y2, label = box[:5]
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(img, label, (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                _draw_debug_overlay(img, last_boxes)
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


async def handle_offer_dashboard(data, t_answer: str, webrtc_mqtt=None):
    await pc.setRemoteDescription(
        RTCSessionDescription(sdp=data["sdp"], type=data["type"])
    )
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    # Esperar a que el ICE gathering termine usando un evento en lugar de polling.
    # Esto garantiza que los candidatos TURN/relay tienen tiempo de llegar antes
    # de enviar la answer. Timeout de 8 s para no bloquear indefinidamente.
    print("[WebRTC] Esperando ICE gathering (máx 8 s)...")
    gathering_done = asyncio.Event()

    @pc.on("icegatheringstatechange")
    def _on_gathering():
        if pc.iceGatheringState == "complete":
            gathering_done.set()

    # Por si ya estaba complete antes de registrar el handler
    if pc.iceGatheringState == "complete":
        gathering_done.set()

    try:
        await asyncio.wait_for(gathering_done.wait(), timeout=8.0)
    except asyncio.TimeoutError:
        print("[WebRTC] ICE gathering timeout (8 s) — enviando con candidatos disponibles")

    candidates = [l for l in pc.localDescription.sdp.splitlines()
                  if l.startswith("a=candidate")]
    has_relay = any("relay" in c for c in candidates)
    print(f"[WebRTC] Answer lista — {'✓ relay' if has_relay else '⚠ sin relay'} ({len(candidates)} candidatos)")

    # Usar el cliente WebRTC dedicado si está disponible, sino client_dashboard
    publisher = webrtc_mqtt if webrtc_mqtt is not None else client_dashboard
    publisher.publish(t_answer, json.dumps({
        "sdp":  pc.localDescription.sdp,
        "type": pc.localDescription.type,
    }))
    print(f"[WebRTC] Answer enviada → {t_answer} ✓")


def start_webrtc_dashboard():
    if MODE == "local":
        threading.Thread(target=webrtc_thread_dashboard_local, daemon=True).start()
    else:
        threading.Thread(target=webrtc_thread_dashboard, daemon=True).start()


# §WEBRTC_MQTT ── MQTT message handler del dashboard ──────────────────────────
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

        _update_follow_altitude(data.get("alt"))
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
            _update_mode_btn_ui(data.get('flightMode'))

        _ui_call(_update_telemetry_ui)
    elif topic == T_CRIME_ALERT:
        try:
            data     = json.loads(msg.payload.decode())
            crime_id = str(data.get("crime_id", "?"))
            score    = float(data.get("crime_score", 0))
            if crime_id not in _crime_chunks_buffer:
                _crime_chunks_buffer[crime_id] = {"meta": {}, "chunks": {}, "score": score}
            else:
                _crime_chunks_buffer[crime_id]["score"] = score
            _ui_call(_mostrar_alerta_crimen, data)
        except Exception as e:
            print(f"[CRIME] Error procesando alerta: {e}")

    elif topic == f'{T_CRIME_CHUNK}/start':
        try:
            meta     = json.loads(msg.payload.decode())
            crime_id = str(meta["crime_id"])
            if crime_id not in _crime_chunks_buffer:
                _crime_chunks_buffer[crime_id] = {"meta": meta, "chunks": {}, "score": 0.0}
            else:
                _crime_chunks_buffer[crime_id]["meta"] = meta
            print(f"[CRIME] Recibiendo clip {crime_id[:19]} "
                  f"({meta['total_chunks']} chunks, "
                  f"{meta.get('size_bytes', 0)/1024/1024:.2f} MB)")
        except Exception as e:
            print(f"[CRIME] Error chunk/start: {e}")

    elif topic == T_CRIME_CHUNK:
        try:
            data     = json.loads(msg.payload.decode())
            crime_id = str(data["crime_id"])
            idx      = int(data["chunk_index"])
            total    = int(data["total_chunks"])
            if crime_id not in _crime_chunks_buffer:
                _crime_chunks_buffer[crime_id] = {"meta": {}, "chunks": {}, "score": 0.0}
            _crime_chunks_buffer[crime_id]["chunks"][idx] = data["data"]
            print(f"  [CRIME] Chunk {idx+1}/{total}", end="\r")
        except Exception as e:
            print(f"[CRIME] Error chunk: {e}")

    elif topic == f'{T_CRIME_CHUNK}/end':
        try:
            data     = json.loads(msg.payload.decode())
            crime_id = str(data["crime_id"])
            total    = int(data["total_chunks"])
            buf      = _crime_chunks_buffer.get(crime_id, {})
            chunks   = buf.get("chunks", {})
            score    = buf.get("score", 0.0)
            if len(chunks) == total:
                b64 = "".join(chunks[i] for i in range(total))
                raw = base64.b64decode(b64)
                os.makedirs("clips", exist_ok=True)
                safe_id   = crime_id.replace(":", "-").replace(".", "_")
                clip_path = os.path.join("clips", f"recibido_{safe_id}.mp4")
                with open(clip_path, "wb") as f:
                    f.write(raw)
                print(f"\n[CRIME] ✓ Clip reconstruido: {clip_path} "
                      f"({len(raw)/1024/1024:.2f} MB)")
                _crime_chunks_buffer.pop(crime_id, None)
                _ui_call(_reproducir_clip_en_popup, crime_id, clip_path, score)
            else:
                print(f"\n[CRIME] ✗ Chunks incompletos: {len(chunks)}/{total}")
        except Exception as e:
            print(f"[CRIME] Error chunk/end: {e}")
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


# ── Lista de marcadores de crimen en el mapa ──────────────────────────────────
# §WEBRTC_CRIMEN ── alertas de crimen y popup de clip ─────────────────────────
_crime_markers       = []
_crime_chunks_buffer = {}   # crime_id → {"meta": {}, "chunks": {}}
_crime_popup_refs    = {}   # crime_id → popup de espera

def _mostrar_alerta_crimen(data: dict):
    """Popup de espera + marcador en el mapa. El clip llega después por chunks."""
    global _crime_markers

    crime_id  = str(data.get("crime_id", "?"))
    score     = data.get("crime_score", 0)
    titulo_ts = crime_id[:19].replace("T", " ") if "T" in crime_id else crime_id[:19]

    if map_widget and drone_lat is not None and drone_lon is not None:
        def _add_marker():
            m = map_widget.set_marker(
                drone_lat, drone_lon,
                text=f"🚨 {titulo_ts}",
                marker_color_circle="#e94560",
                marker_color_outside="#8b0000",
                font=("Arial", 8, "bold"),
            )
            _crime_markers.append(m)
        map_widget.after(0, _add_marker)

    popup = tk.Toplevel()
    popup.title(f"🚨 ALERTA DE CRIMEN — {titulo_ts}")
    popup.configure(bg="#212121")
    popup.attributes("-topmost", True)
    popup.resizable(False, False)
    w, h = 500, 200
    popup.geometry(f"{w}x{h}+{(popup.winfo_screenwidth()-w)//2}+"
                   f"{(popup.winfo_screenheight()-h)//2}")

    tk.Label(popup, text="🚨  POSIBLE CRIMEN DETECTADO",
             font=("Arial", 13, "bold"),
             bg="#e94560", fg="white", pady=10).pack(fill="x")
    tk.Label(popup,
             text=f"Score: {score:.1%}   |   {titulo_ts}",
             font=("Arial", 9), bg="#212121", fg="#aaaaaa", pady=6).pack()
    tk.Label(popup, text="⏳ Recibiendo clip del Analizador...",
             font=("Arial", 10), bg="#212121", fg="white").pack(pady=12)

    _crime_popup_refs[crime_id] = popup
    print(f"[CRIME] Alerta {titulo_ts} recibida (score={score:.1%}) — esperando clip...")


def _reproducir_clip_en_popup(crime_id: str, clip_path: str, score: float):
    """Cierra el popup de espera y abre el popup con el vídeo."""
    crime_id  = str(crime_id)
    titulo_ts = crime_id[:19].replace("T", " ") if "T" in crime_id else crime_id[:19]

    popup_espera = _crime_popup_refs.pop(crime_id, None)
    if popup_espera:
        try:
            popup_espera.destroy()
        except Exception:
            pass

    popup = tk.Toplevel()
    popup.title(f"🚨 Crimen {titulo_ts} — Clip recibido")
    popup.configure(bg="#212121")
    popup.attributes("-topmost", True)
    popup.resizable(False, False)
    w, h = 640, 560
    popup.geometry(f"{w}x{h}+{(popup.winfo_screenwidth()-w)//2}+"
                   f"{(popup.winfo_screenheight()-h)//2}")

    tk.Label(popup, text=f"🚨  {titulo_ts}  —  Score: {score:.1%}",
             font=("Arial", 13, "bold"),
             bg="#e94560", fg="white", pady=8).pack(fill="x")

    video_lbl  = tk.Label(popup, bg="#000000", width=620, height=360)
    video_lbl.pack(padx=10, pady=6)

    status_lbl = tk.Label(popup, text="Reproduciendo...",
                           font=("Arial", 9), bg="#212121", fg="#aaaaaa")
    status_lbl.pack()

    btn_f = tk.Frame(popup, bg="#212121")
    btn_f.pack(fill="x", padx=20, pady=8)

    def _confirmar():
        _actualizar_confirmacion(crime_id, 1)
        status_lbl.config(text="✓ Confirmado como crimen", fg="#4caf50")
        cb.config(state="disabled"); db.config(state="disabled")

    def _descartar():
        _actualizar_confirmacion(crime_id, 0)
        status_lbl.config(text="✗ Marcado como falso positivo", fg="#aaaaaa")
        cb.config(state="disabled"); db.config(state="disabled")

    cb = tk.Button(btn_f, text="✓ Confirmar crimen",
                   font=("Arial", 10, "bold"), bg="#e94560", fg="white",
                   relief="flat", padx=16, pady=8, cursor="hand2",
                   command=_confirmar)
    cb.pack(side="left", expand=True, fill="x", padx=4)

    db = tk.Button(btn_f, text="✗ Falso positivo",
                   font=("Arial", 10, "bold"), bg="#424242", fg="white",
                   relief="flat", padx=16, pady=8, cursor="hand2",
                   command=_descartar)
    db.pack(side="right", expand=True, fill="x", padx=4)

    def _play():
        cap = cv2.VideoCapture(clip_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (620, 350))
            try:
                from PIL import Image, ImageTk
                img = ImageTk.PhotoImage(Image.fromarray(frame))
                try:
                    if popup.winfo_exists():
                        popup.after(0, lambda i=img: _upd(i))
                except Exception:
                    break
            except Exception:
                break
            time.sleep(1 / fps)
        cap.release()

    def _upd(img):
        try:
            if popup.winfo_exists():
                video_lbl.config(image=img)
                video_lbl.image = img
                status_lbl.config(
                    text=f"Reproduciendo — Score: {score:.1%}",
                    fg="#4caf50")
        except Exception:
            pass

    threading.Thread(target=_play, daemon=True).start()


def _actualizar_confirmacion(crime_id: str, confirmado: int):
    """Envía veredicto via MQTT al Analizador y actualiza la DB local si existe."""
    crime_id = str(crime_id)
    if client_dashboard:
        try:
            topic   = "crime/true" if confirmado else "crime/false"
            payload = json.dumps({"crime_id": crime_id})
            client_dashboard.publish(topic, payload, qos=1)
            estado  = "confirmado" if confirmado else "falso positivo"
            print(f"[CRIME] {crime_id[:19]} → {estado} (MQTT: {topic})")
        except Exception as e:
            print(f"[CRIME] Error publicando veredicto: {e}")
    import sqlite3 as _sq
    db_path = "crimes.db"
    if os.path.exists(db_path):
        try:
            con = _sq.connect(db_path)
            con.execute("UPDATE crimes SET confirmed=? WHERE id=?",
                        (confirmado, crime_id))
            con.commit()
            con.close()
        except Exception as e:
            print(f"[CRIME] Error actualizando DB: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  §MAPA  MAPA
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
#  §V16_MAPA  BALIZAS V16 — CARGA Y DIBUJO EN EL MAPA
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
#  §CONTROL  CONTROL DEL DRON
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

# §CONTROL_GLOBAL ── comandos modo global ─────────────────────────────────────
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
    _stop_follow_mode("land")
    client_dashboard.publish(f'{MY_ORIGIN}/autopilotServiceDemo/Land')
    landBtn.configure(text='Aterrizando...', fg='black', bg='yellow')

def RTL_global():
    _stop_follow_mode("rtl")
    client_dashboard.publish(f'{MY_ORIGIN}/autopilotServiceDemo/RTL')
    RTLBtn.configure(text='Retornando...', fg='black', bg='yellow')

def _update_mode_btn_ui(flight_mode):
    mode_upper = (flight_mode or "").upper().strip()
    for mode, btn in _mode_buttons.items():
        try:
            btn.configure(bg="#228B22" if mode == mode_upper else "#336699")
        except Exception:
            pass

def setFlightMode_global(mode):
    client_dashboard.publish(f'{MY_ORIGIN}/autopilotServiceDemo/setFlightMode', mode)
    print(f"[UI] setFlightMode → {mode}")

def go_global(direction, btn):
    global previousBtn
    if previousBtn: previousBtn.configure(fg='black', bg='dark orange')
    client_dashboard.publish(f'{MY_ORIGIN}/autopilotServiceDemo/go', direction)
    btn.configure(fg='white', bg='green')
    previousBtn = btn

def startTelem_global(): client_dashboard.publish(f'{MY_ORIGIN}/autopilotServiceDemo/startTelemetry')
def stopTelem_global():  client_dashboard.publish(f'{MY_ORIGIN}/autopilotServiceDemo/stopTelemetry')
def changeHeading_global(e): client_dashboard.publish(f'{MY_ORIGIN}/autopilotServiceDemo/changeHeading', str(gradesSldr.get()))
def changeNavSpeed_global(e):
    _stop_follow_mode("manual-speed-change")
    client_dashboard.publish(f'{MY_ORIGIN}/autopilotServiceDemo/changeNavSpeed', str(speedSldr.get()))


# §CONTROL_FOLLOW ── distance follow global ───────────────────────────────────
def startDistanceFollow_global(config=None):
    payload = json.dumps(config if isinstance(config, dict) else {})
    client_dashboard.publish(f'{MY_ORIGIN}/autopilotServiceDemo/startDistanceFollow', payload)


def updateDistanceFollow_global(distance_m, offset_x=0.0, confidence=1.0, valid=True, target_id=None):
    payload_obj = {
        "distance_m": float(distance_m),
        "offset_x": float(offset_x),
        "confidence": float(confidence),
        "valid": bool(valid),
    }
    if target_id is not None:
        payload_obj["target_id"] = str(target_id)
    client_dashboard.publish(
        f'{MY_ORIGIN}/autopilotServiceDemo/updateDistanceFollow',
        json.dumps(payload_obj),
    )


def stopDistanceFollow_global(reason="manual"):
    client_dashboard.publish(
        f'{MY_ORIGIN}/autopilotServiceDemo/stopDistanceFollow',
        json.dumps({"reason": str(reason)}),
    )


def _follow_config():
    def _read_float(var, fallback):
        try:
            if var is None:
                return float(fallback)
            raw = str(var.get()).strip().lower().replace(",", ".")
            if raw.endswith("m"):
                raw = raw[:-1].strip()
            value = float(raw)
            return value
        except Exception:
            return float(fallback)

    target_distance = max(0.1, _read_float(followTargetDistVar, FOLLOW_TARGET_DISTANCE))
    lateral_deadzone = max(0.0, _read_float(followDeadzoneVar, FOLLOW_LATERAL_DEADBAND))

    return {
        "target_distance":   target_distance,
        "distance_deadband": FOLLOW_DISTANCE_DEADBAND,
        "lateral_deadband":  lateral_deadzone,
        "kp_distance":       FOLLOW_KP_DISTANCE,
        "kd_distance":       FOLLOW_KD_DISTANCE,
        "kp_lateral":        FOLLOW_KP_LATERAL,
        "kd_lateral":        FOLLOW_KD_LATERAL,
        "rc_max_offset":     FOLLOW_RC_MAX_OFFSET,
        "rc_min_offset":     FOLLOW_RC_MIN_OFFSET,
        "lost_timeout":      FOLLOW_LOST_TIMEOUT,
        "max_offset_abs":    FOLLOW_MAX_OFFSET_ABS,
        "deriv_alpha":       FOLLOW_DERIV_ALPHA,
    }


def _set_follow_button_state(enabled: bool):
    if followBtn is None:
        return
    if enabled:
        followBtn.configure(text="Parar seguimiento", fg="white", bg="#2e8b57")
    else:
        followBtn.configure(text="Modo seguimiento", fg="black", bg="dark orange")


def _start_follow_mode():
    global _auto_follow_enabled, _auto_follow_active, _auto_follow_last_target_ts
    if MODE == "local" or IS_GROUND_STATION:
        if not _is_drone_flying():
            print("[FOLLOW] No se puede activar seguimiento: el dron no está en vuelo")
            _ui_call(_set_follow_button_state, False)
            _auto_follow_enabled = False
            return
    _auto_follow_enabled = True
    _auto_follow_active = True
    _auto_follow_last_target_ts = time.time()
    cfg = _follow_config()
    try:
        if MODE == "global":
            startDistanceFollow_global(cfg)
        else:
            _ensure_distance_follow_controller().start(origin="local", config=cfg)
        _ui_call(_set_follow_button_state, True)
        print("[FOLLOW] Modo seguimiento activado")
    except Exception as e:
        _auto_follow_enabled = False
        _ui_call(_set_follow_button_state, False)
        print(f"[FOLLOW] Error activando seguimiento: {e}")


def _stop_follow_mode(reason="manual"):
    global _auto_follow_enabled, _auto_follow_active
    _auto_follow_enabled = False
    with _auto_follow_lock:
        _auto_follow_active = False
    try:
        if MODE == "global":
            stopDistanceFollow_global(reason)
        else:
            controller = _ensure_distance_follow_controller()
            if controller.is_running():
                controller.stop(reason=reason, origin="local")
        print(f"[FOLLOW] Modo seguimiento detenido ({reason})")
    except Exception as e:
        print(f"[FOLLOW] Error deteniendo seguimiento: {e}")
    finally:
        _ui_call(_set_follow_button_state, False)


def toggle_follow_mode():
    if _auto_follow_enabled:
        _stop_follow_mode("toggle-off")
    else:
        _start_follow_mode()


def toggle_debug_overlay():
    global _debug_overlay
    _debug_overlay = not _debug_overlay
    if overlayBtn is not None:
        if _debug_overlay:
            overlayBtn.configure(text="Debug overlay: ON", bg="#2e6b9e")
        else:
            overlayBtn.configure(text="Debug overlay: OFF", bg="#555555")


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

# §CONTROL_LOCAL ── comandos modo local (dronLink directo) ────────────────────
def connect_local():
    connectBtn.configure(text='Conectando...', fg='black', bg='yellow')
    try:
        if REAL_DRONE == False:
            ok = dron.connect('tcp:127.0.0.1:5763', 115200)
        else:
            ok = dron.connect('udp:127.0.0.1:14551', 57600)

        if ok and dron.state == 'connected':
            connectBtn.configure(text='Conectado', fg='white', bg='green')
            speedSldr.set(FLIGHT_DEFAULT_NAV_SPEED)
        else:
            _show_connect_error()
    except Exception as e:
        print(f"[LOCAL] Error conectando: {e}")
        _show_connect_error()

def takeoff_local():
    dron.arm()
    dron.takeOff(FLIGHT_TAKEOFF_HEIGHT, blocking=False,
                 callback=lambda: arm_takeOffBtn.configure(text='En vuelo', fg='white', bg='green'))
    arm_takeOffBtn.configure(text='Despegando...', fg='black', bg='yellow')

def land_local():
    _stop_follow_mode("land")
    dron.Land(blocking=False,
              callback=lambda: (
                  arm_takeOffBtn.configure(text='Despegar', fg='black', bg='dark orange'),
                  landBtn.configure(text='Aterrizar', fg='black', bg='dark orange')
              ),
              params=None)
    landBtn.configure(text='Aterrizando...', fg='black', bg='yellow')

def RTL_local():
    _stop_follow_mode("rtl")
    dron.RTL()
    RTLBtn.configure(text='Retornando...', fg='black', bg='yellow')

def setFlightMode_local(mode):
    try:
        dron.setFlightMode(mode)
        print(f"[UI] setFlightMode → {mode}")
    except Exception as e:
        print(f"[UI] Error cambiando modo a {mode}: {e}")

def go_local(direction, btn):
    global previousBtn
    if previousBtn: previousBtn.configure(fg='black', bg='dark orange')
    _stop_follow_mode("manual-go")
    dron.go(direction)
    btn.configure(fg='white', bg='green')
    previousBtn = btn

def startTelem_local():
    def _update(info):
        _update_follow_altitude(info.get("alt"))
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
        _update_mode_btn_ui(info.get('flightMode'))
    dron.send_telemetry_info(_update)

def stopTelem_local():  dron.stop_sending_telemetry_info()
def changeHeading_local(e):  dron.changeHeading(int(gradesSldr.get()))
def changeNavSpeed_local(e):
    _stop_follow_mode("manual-speed-change")
    dron.changeNavSpeed(float(speedSldr.get()))


# ══════════════════════════════════════════════════════════════════════════════
#  §PANEL_DETECCION  PANEL DE DETECCIÓN MULTI-CLASE
# ══════════════════════════════════════════════════════════════════════════════

def _build_detection_panel(parent):
    df = tk.LabelFrame(parent, text="Detección de objetos (multi-clase COCO)")
    df.grid(row=12, column=0, columnspan=2, padx=5, pady=3, sticky="nsew")

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

    row_idx += 1
    tk.Label(
        inner,
        text="Distancia objetivo de seguimiento (m):",
        font=("Arial", 8, "bold"),
        fg="#333333",
    ).grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=4, pady=(6, 2))

    global followTargetDistVar, followDeadzoneVar
    followTargetDistVar = tk.StringVar(value="5.0")
    target_entry = tk.Entry(inner, textvariable=followTargetDistVar, width=10, font=("Arial", 8))
    target_entry.grid(row=row_idx, column=2, sticky="w", padx=(0, 4), pady=(6, 2))

    row_idx += 1
    tk.Label(
        inner,
        text="Deadzone lateral (normalizada, 0-1):",
        font=("Arial", 8, "bold"),
        fg="#333333",
    ).grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=4, pady=(2, 2))

    followDeadzoneVar = tk.StringVar(value="0.15")
    deadzone_entry = tk.Entry(inner, textvariable=followDeadzoneVar, width=10, font=("Arial", 8))
    deadzone_entry.grid(row=row_idx, column=2, sticky="w", padx=(0, 4), pady=(2, 2))

    row_idx += 1
    tk.Label(
        inner,
        text="Medida física del objeto (m):",
        font=("Arial", 8, "bold"),
        fg="#333333",
    ).grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=4, pady=(6, 2))

    size_var = tk.StringVar(value=f"{_auto_follow_object_size_m:.2f}")
    size_entry = tk.Entry(inner, textvariable=size_var, width=10, font=("Arial", 8))
    size_entry.grid(row=row_idx, column=2, sticky="w", padx=(0, 4), pady=(6, 2))

    def _apply_object_size(*_):
        ok = set_detect_object_physical_size(size_var.get())
        if ok:
            size_var.set(f"{_auto_follow_object_size_m:.2f}")

    tk.Button(
        inner,
        text="Aplicar",
        font=("Arial", 8),
        bg="#3b7ddd",
        fg="white",
        relief="flat",
        padx=6,
        pady=1,
        command=_apply_object_size,
    ).grid(row=row_idx, column=3, sticky="w", padx=2, pady=(6, 2))

    size_entry.bind("<Return>", _apply_object_size)

    row_idx += 1
    tk.Label(
        inner,
        text="Pitch camara (deg, 0 frontal, 90 zenital):",
        font=("Arial", 8, "bold"),
        fg="#333333",
    ).grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=4, pady=(6, 2))

    pitch_var = tk.StringVar(value=f"{_auto_follow_camera_pitch_deg:.1f}")
    pitch_entry = tk.Entry(inner, textvariable=pitch_var, width=10, font=("Arial", 8))
    pitch_entry.grid(row=row_idx, column=2, sticky="w", padx=(0, 4), pady=(6, 2))

    def _apply_pitch(*_):
        ok = set_camera_pitch_deg(pitch_var.get())
        if ok:
            pitch_var.set(f"{_auto_follow_camera_pitch_deg:.1f}")

    tk.Button(
        inner,
        text="Aplicar",
        font=("Arial", 8),
        bg="#3b7ddd",
        fg="white",
        relief="flat",
        padx=6,
        pady=1,
        command=_apply_pitch,
    ).grid(row=row_idx, column=3, sticky="w", padx=2, pady=(6, 2))

    pitch_entry.bind("<Return>", _apply_pitch)

    row_idx += 1
    tk.Label(
        inner,
        text="Altitud objetivo (m):",
        font=("Arial", 8, "bold"),
        fg="#333333",
    ).grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=4, pady=(6, 2))

    alt_target_var = tk.StringVar(value="3.0")
    alt_target_entry = tk.Entry(inner, textvariable=alt_target_var, width=10, font=("Arial", 8))
    alt_target_entry.grid(row=row_idx, column=2, sticky="w", padx=(0, 4), pady=(6, 2))

    def _apply_alt_target(*_):
        set_follow_target_altitude(alt_target_var.get())

    tk.Button(
        inner,
        text="Ir",
        font=("Arial", 8),
        bg="#3b7ddd",
        fg="white",
        relief="flat",
        padx=6,
        pady=1,
        command=_apply_alt_target,
    ).grid(row=row_idx, column=3, sticky="w", padx=2, pady=(6, 2))

    alt_target_entry.bind("<Return>", _apply_alt_target)

    row_idx += 1
    tk.Label(
        inner,
        text="Ejemplo: persona ≈ 1.70m, móvil ≈ 17cm",
        font=("Arial", 7),
        fg="#666666",
    ).grid(row=row_idx, column=0, columnspan=COLS, sticky="w", padx=4, pady=(0, 4))

    return df


# ══════════════════════════════════════════════════════════════════════════════
#  §GUI  GUI
# ══════════════════════════════════════════════════════════════════════════════

def crear_ventana(modo):
    global client_dashboard, IS_GROUND_STATION, root_window
    global altShowLbl, headingShowLbl, stateShowLbl
    global speedShowLbl, battShowLbl, gpsShowLbl
    global connectBtn, arm_takeOffBtn, landBtn, RTLBtn, followBtn, overlayBtn
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
            c.subscribe(f'autopilotServiceDemo/{MY_ORIGIN}/#') if rc==0 else None,
            c.subscribe(T_CRIME_ALERT) if rc==0 else None,
            c.subscribe(T_CRIME_CHUNK) if rc==0 else None,
            c.subscribe(f'{T_CRIME_CHUNK}/start') if rc==0 else None,
            c.subscribe(f'{T_CRIME_CHUNK}/end') if rc==0 else None
        )
        client_dashboard.on_disconnect = lambda c,u,rc: (
            print(f"[MQTT] Dashboard desconectado (rc={rc}) — paho reconectará automáticamente")
            if rc != 0 else None
        )
        client_dashboard.connect(BROKER_DASHBOARD, PORT, keepalive=30)
        client_dashboard.subscribe(f'autopilotServiceDemo/{MY_ORIGIN}/#')
        client_dashboard.subscribe(T_CRIME_ALERT)
        client_dashboard.subscribe(T_CRIME_CHUNK)
        client_dashboard.subscribe(f'{T_CRIME_CHUNK}/start')
        client_dashboard.subscribe(f'{T_CRIME_CHUNK}/end')
        client_dashboard.reconnect_delay_set(min_delay=1, max_delay=30)
        client_dashboard.loop_start()
        _start_telemetry_watchdog_global()

        _connect = connect_global;  _takeoff = takeoff_global
        _land    = land_global;     _RTL     = RTL_global
        _go      = go_global;       _video   = start_webrtc_dashboard
        _stopCam = stop_camera_service
        _startT  = startTelem_global; _stopT = stopTelem_global
        _heading = changeHeading_global; _speed = changeNavSpeed_global
        _setFlightMode = setFlightMode_global

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
        _setFlightMode = setFlightMode_local
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
    for i in range(14): ctrl.rowconfigure(i, weight=1)
    ctrl.columnconfigure(0, weight=1); ctrl.columnconfigure(1, weight=1)

    def btn(text, cmd, row, col=0, cs=2, bg="dark orange", parent=None):
        p = parent or ctrl
        b = tk.Button(p, text=text, bg=bg, command=cmd)
        b.grid(row=row, column=col, columnspan=cs, padx=5, pady=3, sticky="nsew")
        return b

    connectBtn     = btn("Conectar",  _connect, 0)
    arm_takeOffBtn = btn("Despegar",  _takeoff, 1)
    followBtn      = btn("Modo seguimiento", toggle_follow_mode, 2)
    overlayBtn     = btn("Debug overlay: OFF", toggle_debug_overlay, 3, bg="#555555")
    landBtn        = btn("Aterrizar", _land,    5, col=0, cs=1)
    RTLBtn         = btn("RTL",       _RTL,     5, col=1, cs=1)

    mf = tk.LabelFrame(ctrl, text="Modo de vuelo RC")
    mf.grid(row=6, column=0, columnspan=2, padx=8, pady=3, sticky="nsew")
    for i in range(2): mf.columnconfigure(i, weight=1)
    tk.Label(mf, text="Cambiar modo para usar RC físico:", font=("Arial", 7)).grid(
        row=0, column=0, columnspan=4, padx=2, pady=1)
    for idx, mode in enumerate(["GUIDED", "LOITER", "ALT_HOLD", "STABILIZE"]):
        b = tk.Button(mf, text=mode, bg="#336699", fg="white",
                      command=lambda m=mode: _setFlightMode(m))
        b.grid(row=1, column=idx, padx=2, pady=2, sticky="nsew")
        _mode_buttons[mode] = b
    for i in range(4): mf.columnconfigure(i, weight=1)

    gradesSldr = tk.Scale(ctrl, label="Grados:", resolution=5, from_=0, to=360,
                          tickinterval=45, orient=tk.HORIZONTAL)
    gradesSldr.grid(row=4, column=0, columnspan=2, padx=5, pady=3, sticky="nsew")
    gradesSldr.bind("<ButtonRelease-1>", _heading)

    nf = tk.LabelFrame(ctrl, text="Navegación")
    nf.grid(row=7, column=0, columnspan=2, padx=8, pady=3, sticky="nsew")
    for i in range(3): nf.rowconfigure(i, weight=1); nf.columnconfigure(i, weight=1)
    dirs = [("NW","NorthWest",0,0),("N","North",0,1),("NE","NorthEast",0,2),
            ("W","West",1,0),("Stop","Stop",1,1),("E","East",1,2),
            ("SW","SouthWest",2,0),("S","South",2,1),("SE","SouthEast",2,2)]
    for label, direction, r, c in dirs:
        b = tk.Button(nf, text=label, bg="dark orange")
        b.configure(command=lambda d=direction, x=b: _go(d, x))
        b.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")

    speedSldr = tk.Scale(ctrl, label="Velocidad (m/s):", resolution=1, from_=0, to=FLIGHT_MAX_NAV_SPEED,
                         tickinterval=5, orient=tk.HORIZONTAL)
    speedSldr.grid(row=8, column=0, columnspan=2, padx=5, pady=3, sticky="nsew")
    speedSldr.bind("<ButtonRelease-1>", _speed)

    btn("Empezar telemetría", _startT, 9, col=0, cs=1)
    btn("Parar telemetría",   _stopT,  9, col=1, cs=1)

    tf = tk.LabelFrame(ctrl, text="Telemetría")
    tf.grid(row=10, column=0, columnspan=2, padx=5, pady=3, sticky="nsew")
    for i in range(6): tf.columnconfigure(i, weight=1)
    for txt, col in [("Altitud",0),("Heading",1),("Estado",2),("Vel.",3),("Batería",4),("GPS",5)]:
        tk.Label(tf, text=txt, font=("Arial",7,"bold")).grid(row=0, column=col, padx=2, pady=1)
    altShowLbl     = tk.Label(tf, text=''); altShowLbl.grid(row=1, column=0, padx=2)
    headingShowLbl = tk.Label(tf, text=''); headingShowLbl.grid(row=1, column=1, padx=2)
    stateShowLbl   = tk.Label(tf, text=''); stateShowLbl.grid(row=1, column=2, padx=2)
    speedShowLbl   = tk.Label(tf, text=''); speedShowLbl.grid(row=1, column=3, padx=2)
    battShowLbl    = tk.Label(tf, text=''); battShowLbl.grid(row=1, column=4, padx=2)
    gpsShowLbl     = tk.Label(tf, text=''); gpsShowLbl.grid(row=1, column=5, padx=2)

    btn("▶ Ver video del dron",  _video,   11, col=0, cs=1)
    btn("⏹ Desconectar cámara", _stopCam, 11, col=1, cs=1, bg="#e14d03")

    # ── Panel de detección multi-clase ────────────────────────────────────────
    _build_detection_panel(ctrl)

    # ── Panel derecho: mapa ───────────────────────────────────────────────────
    global map_widget, _goto_callback

    map_frame = tk.LabelFrame(v, text="Mapa — clic para enviar el dron al punto")
    map_frame.grid(row=map_row, column=1, sticky="nsew", padx=(2,4), pady=4)
    map_frame.rowconfigure(0, weight=1)
    map_frame.columnconfigure(0, weight=1)

    map_widget = tkintermapview.TkinterMapView(
        map_frame, width=500, height=500, corner_radius=4)
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
#  §MAIN  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    REAL_DRONE = selector_simulacion()
    modo = selector_modo()
    MODE = modo

    if modo == "global":
        seleccionar_slot()

    print(f"[MAIN] Simulación={'sí' if not REAL_DRONE else 'no'}, Modo: {modo}")
    crear_ventana(modo).mainloop()