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

# ── Broker HiveMQ ─────────────────────────────────────────────────────────────
BROKER_DASHBOARD = "554f19f1f4944c978dd30b509d24afc0.s1.eu.hivemq.cloud"
PORT             = 8884

METERED_API = "https://testconection1.metered.live/api/v1/turn/credentials?apiKey=57312a00508de97f6ca0758cce3935fe7670"

# ── Pool de usuarios HiveMQ (dashboard + camera) ──────────────────────────────
# HiveMQ requiere credenciales fijas por usuario.
# Cada instancia del dashboard ocupa el primer slot libre al arrancar.
# Rellena nombre y contraseña con los usuarios que hayas creado en HiveMQ.
# Deja vacío ("") cualquier slot que no hayas creado todavía.
HIVEMQ_USERS = [
    {"user": "InterfazGlobal",  "password": "Kb2avDJmV2aj!Jz"},   # slot 1
    {"user": "Client1",  "password": "GhJpQCxh_ktB4J9"},   # slot 2
    {"user": "",  "password": ""},   # slot 3
    {"user": "",  "password": ""},   # slot 4
]

# ── AutopilotService / MQTT ───────────────────────────────────────────────────
# Usuario dedicado al AutopilotService — solo lo usa la Estación de Tierra.
USER_AUTOPILOT = ""   # rellena con el usuario HiveMQ del AutopilotService
PASS_AUTOPILOT = ""   # rellena con su contraseña

# ── Topics fijos ──────────────────────────────────────────────────────────────
T_OFFER  = "webrtc/offer"
T_ANSWER = "webrtc/answer"

# Topic retain para negociar quién es la Estación de Tierra
T_AUTOPILOT_CLAIM = "autopilot/claim"

# Topic retain por slot: cada slot marca si está ocupado
# Formato: "slot/ocupado/1", "slot/ocupado/2", ...
T_SLOT_PREFIX = "slot/ocupado/"

# ── TCP (Modo Local) ──────────────────────────────────────────────────────────
TCP_HOST = "localhost"
TCP_PORT = 9999

# ══════════════════════════════════════════════════════════════════════════════
#  SELECCIÓN AUTOMÁTICA DE SLOT HIVEMQ
# ══════════════════════════════════════════════════════════════════════════════

# Credenciales activas de esta instancia — se asignan en seleccionar_slot()
USER_DASHBOARD = None
PASS_DASHBOARD = None
SLOT_INDEX     = None   # índice 0-3 del slot ocupado por esta instancia


def seleccionar_slot():
    """Prueba los slots en orden y ocupa el primero que esté libre.

    Un slot está libre si:
      · Tiene usuario/contraseña rellenos en HIVEMQ_USERS, Y
      · No hay ningún mensaje retain en "slot/ocupado/<n>" en el broker.

    Al ocupar un slot publica su índice con retain=True en ese topic,
    de modo que los demás arranques sepan que ya está en uso.

    Retorna el índice del slot ocupado, o termina el proceso si no hay ninguno.
    """
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
            # Slot libre → ocuparlo
            USER_DASHBOARD = creds["user"]
            PASS_DASHBOARD = creds["password"]
            SLOT_INDEX     = idx
            _marcar_slot_ocupado(idx, creds)
            print(f"[SLOT] Slot {idx+1} ocupado (usuario: {creds['user']})")
            return idx

        print(f"[SLOT] Slot {idx+1} ocupado — probando siguiente...")

    # Todos los slots ocupados
    _mostrar_error_slots_llenos()
    import sys; sys.exit(0)


def _marcar_slot_ocupado(idx, creds):
    """Publica retain en el topic del slot para marcarlo como en uso."""
    import uuid as _uuid_inner
    c = mqtt.Client(
        client_id=f"mark_{idx}_{_uuid_inner.uuid4().hex[:4]}",
        transport="websockets"
    )
    c.ws_set_options(path="/mqtt")
    c.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
    c.username_pw_set(creds["user"], creds["password"])
    c.connect(BROKER_DASHBOARD, PORT)
    c.loop_start()
    time.sleep(0.3)
    c.publish(f"{T_SLOT_PREFIX}{idx + 1}", creds["user"], retain=True, qos=1)
    time.sleep(0.3)
    # No desconectar — el retain persiste aunque el cliente se desconecte


def liberar_slot():
    """Borra el retain del slot al cerrar la aplicación."""
    if SLOT_INDEX is None or USER_DASHBOARD is None:
        return
    try:
        import uuid as _uuid_inner
        c = mqtt.Client(
            client_id=f"free_{SLOT_INDEX}_{_uuid_inner.uuid4().hex[:4]}",
            transport="websockets"
        )
        c.ws_set_options(path="/mqtt")
        c.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
        c.username_pw_set(USER_DASHBOARD, PASS_DASHBOARD)
        c.connect(BROKER_DASHBOARD, PORT)
        c.loop_start()
        time.sleep(0.3)
        c.publish(f"{T_SLOT_PREFIX}{SLOT_INDEX + 1}", "", retain=True, qos=1)
        time.sleep(0.3)
        c.loop_stop()
        c.disconnect()
        print(f"[SLOT] Slot {SLOT_INDEX + 1} liberado")
    except Exception as e:
        print(f"[SLOT] Error liberando slot: {e}")


def _mostrar_error_slots_llenos():
    """Ventana de error cuando todos los slots están en uso."""
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


# ── ID único por instancia ────────────────────────────────────────────────────
# Se usa como sufijo en client_id MQTT y en los topics de esta instancia.
#   · client_id único → el broker no expulsa a otras instancias conectadas
#   · MY_ORIGIN único → cada instancia tiene su propio "buzón" de respuestas
#     Ej: "interfazGlobal_a3f7/autopilotServiceDemo/arm_takeOff"
#         "autopilotServiceDemo/interfazGlobal_a3f7/flying"
import uuid as _uuid
_INST_SUFFIX = _uuid.uuid4().hex[:6]            # 6 chars hex, ej. "a3f7c2"
MY_ORIGIN    = f"interfazGlobal_{_INST_SUFFIX}" # origen único de esta instancia

# ══════════════════════════════════════════════════════════════════════════════
#  ESTADO GLOBAL
# ══════════════════════════════════════════════════════════════════════════════

pc            = None
loop_dashboard = None
client_dashboard = None
pending_offer = None
previousBtn   = None
MODE          = None   # "global" o "local"
REAL_DRONE    = False
IS_GROUND_STATION = False   # True si esta instancia es la Estación de Tierra

dron          = Dron()

altShowLbl = headingShowLbl = stateShowLbl = None
speedShowLbl = battShowLbl = gpsShowLbl = None
connectBtn = arm_takeOffBtn = landBtn = RTLBtn = None
speedSldr  = gradesSldr = None

# ── Mapa ──────────────────────────────────────────────────────────────────────
map_widget      = None
drone_marker    = None
target_marker   = None
drone_path      = []
drone_path_line = None
drone_lat       = None
drone_lon       = None
_goto_callback  = None

# YOLOv5
detect_object_id = None
yolo_model       = None


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
#  NEGOCIACIÓN DE ROL — Estación de Tierra vs Cliente
#  Solo aplica en modo Global + Dron Real.
#
#  Protocolo:
#    1. Se abre un cliente MQTT temporal y se suscribe a T_AUTOPILOT_CLAIM.
#    2. Se espera 1.5 s para recibir el mensaje retain (si lo hay).
#    3. Si llega un claim de otro → ya hay una Estación de Tierra → soy Cliente.
#    4. Si no llega nada → soy el primero → me proclamo Estación de Tierra
#       publicando mi client_id con retain=True.
#    5. Si yo mismo publiqué el claim anterior (mismo client_id) lo ignoro —
#       reinicio del proceso con la misma instancia.
# ══════════════════════════════════════════════════════════════════════════════

# MY_ORIGIN ya declarado arriba — se reutiliza como client_id base de negociación
MY_CLIENT_ID = MY_ORIGIN   # alias para compatibilidad con negociar_rol_ground_station

def negociar_rol_ground_station():
    """Determina si esta instancia debe actuar como Estación de Tierra.

    Retorna True  → soy Estación de Tierra (arranco AutopilotService).
    Retorna False → soy Cliente (no arranco AutopilotService).

    Solo se llama cuando MODE=="global" y REAL_DRONE==True.
    """
    resultado = {"claim_recibido": None, "evento": threading.Event()}

    def _on_message(cli, userdata, msg):
        if msg.topic == T_AUTOPILOT_CLAIM:
            payload = msg.payload.decode("utf-8").strip()
            # Ignorar claim propio (reinicio de la misma instancia)
            if payload and payload != MY_CLIENT_ID:
                resultado["claim_recibido"] = payload
            resultado["evento"].set()

    # Cliente temporal solo para negociación
    tmp = mqtt.Client(client_id=MY_CLIENT_ID + "_probe", transport="websockets")
    tmp.ws_set_options(path="/mqtt")
    tmp.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
    tmp.username_pw_set(USER_DASHBOARD, PASS_DASHBOARD)
    tmp.on_message = _on_message
    tmp.connect(BROKER_DASHBOARD, PORT)
    tmp.subscribe(T_AUTOPILOT_CLAIM)
    tmp.loop_start()

    # Esperar hasta 1.5 s por un retain existente
    resultado["evento"].wait(timeout=1.5)
    tmp.loop_stop()
    tmp.disconnect()

    if resultado["claim_recibido"]:
        # Ya hay otra Estación de Tierra activa
        print(f"[ROL] Estación de Tierra detectada: {resultado['claim_recibido']}")
        return False
    else:
        # Soy el primero — publicar claim con retain=True para que los demás me vean
        _publicar_claim()
        print(f"[ROL] Me proclamo Estación de Tierra ({MY_CLIENT_ID})")
        return True


def _publicar_claim():
    """Publica el claim de Estación de Tierra con retain=True.
    Lo hace un cliente independiente para no interferir con el dashboard."""
    claim_client = mqtt.Client(client_id=MY_CLIENT_ID + "_claim", transport="websockets")
    claim_client.ws_set_options(path="/mqtt")
    claim_client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
    claim_client.username_pw_set(USER_DASHBOARD, PASS_DASHBOARD)
    claim_client.connect(BROKER_DASHBOARD, PORT)
    claim_client.loop_start()
    time.sleep(0.3)  # esperar conexión
    claim_client.publish(T_AUTOPILOT_CLAIM, MY_CLIENT_ID, retain=True, qos=1)
    time.sleep(0.3)  # esperar que el broker confirme
    # No desconectar — el retain persiste en el broker aunque el cliente se vaya


def limpiar_claim_ground_station():
    """Borra el claim retain al cerrar la Estación de Tierra.
    Publica payload vacío en el topic retain — el broker elimina el retain."""
    try:
        c = mqtt.Client(client_id=MY_CLIENT_ID + "_cleanup", transport="websockets")
        c.ws_set_options(path="/mqtt")
        c.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
        c.username_pw_set(USER_DASHBOARD, PASS_DASHBOARD)
        c.connect(BROKER_DASHBOARD, PORT)
        c.loop_start()
        time.sleep(0.3)
        c.publish(T_AUTOPILOT_CLAIM, "", retain=True, qos=1)  # vacío = borrar retain
        time.sleep(0.3)
        c.loop_stop()
        c.disconnect()
        print("[ROL] Claim liberado — el próximo en arrancar será Estación de Tierra")
    except Exception as e:
        print(f"[ROL] Error limpiando claim: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  DIÁLOGO DE ROL — informa al usuario qué rol tiene esta instancia
# ══════════════════════════════════════════════════════════════════════════════

def mostrar_dialogo_rol(es_estacion):
    """Muestra una ventana modal que informa del rol asignado.

    Estación de Tierra → verde oscuro, icono 📡
    Cliente            → azul oscuro, icono 📺
    """
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

    # Franja superior con color de acento
    franja = tk.Frame(d, bg=accent, height=5)
    franja.pack(fill="x")

    # Icono grande
    tk.Label(d, text=icono, font=("Arial", 42), bg=bg_color, fg=accent
             ).pack(pady=(18, 4))

    # Título del rol
    tk.Label(d, text=titulo_rol, font=("Arial", 16, "bold"), bg=bg_color, fg=accent
             ).pack(pady=(0, 8))

    # Descripción
    tk.Label(d, text=desc, font=("Arial", 9), bg=bg_color, fg="#cccccc",
             justify="center", wraplength=420).pack(pady=(0, 20))

    # Botón continuar
    tk.Button(d, text="Continuar →",
              font=("Arial", 11, "bold"), bg=accent, fg="white",
              activebackground=bg_color, relief="flat", cursor="hand2",
              padx=24, pady=8, command=d.destroy).pack()

    # Cerrar automáticamente tras 6 s si el usuario no pulsa
    d.after(6000, lambda: d.destroy() if d.winfo_exists() else None)

    d.protocol("WM_DELETE_WINDOW", d.destroy)
    d.mainloop()


# ══════════════════════════════════════════════════════════════════════════════
#  AUTOPILOT SERVICE (integrado)
# ══════════════════════════════════════════════════════════════════════════════

autopilot_sending_topic = None
client_autopilot        = None


def autopilot_publish_event(event):
    client_autopilot.publish(autopilot_sending_topic + '/' + event)
    print(f"[AUTOPILOT] → {autopilot_sending_topic}/{event}")


def autopilot_publish_telemetry(telemetry_info):
    client_autopilot.publish(autopilot_sending_topic + '/telemetryInfo',
                              json.dumps(telemetry_info))


def autopilot_on_message(cli, userdata, message):
    global autopilot_sending_topic

    parts   = message.topic.split("/")
    origin  = parts[0]
    command = parts[2]

    autopilot_sending_topic = "autopilotServiceDemo/" + origin
    print(f"[AUTOPILOT] {origin} → {command}")

    if command == 'connect':
        payload = message.payload.decode("utf-8").strip()
        if payload == 'REAL':
            connection_string = 'COM3'
            baud = 57600
        else:
            connection_string = 'tcp:127.0.0.1:5763'
            baud = 115200
        dron.connect(connection_string, baud, freq=10)
        print(f'Conectado al dron ({connection_string} @ {baud})')
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
        coords = json.loads(message.payload.decode("utf-8"))
        dron.goto(coords["lat"], coords["lon"], coords.get("alt", 5.0),
                  blocking=False)
        print(f"[AUTOPILOT] goto → {coords['lat']:.6f}, {coords['lon']:.6f}, {coords.get('alt',5)}m")


def autopilot_on_connect(cli, userdata, flags, rc):
    print("[AUTOPILOT] Conectado" if rc == 0 else f"[AUTOPILOT] Error MQTT {rc}")


def start_autopilot_service():
    """Arranca el AutopilotService en su propio hilo.
    Solo se llama si IS_GROUND_STATION == True.
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
        client_autopilot.subscribe('+/autopilotServiceDemo/#')
        print("[AUTOPILOT] Servicio listo — esperando comandos")
        client_autopilot.loop_forever()

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


async def run_camera_global(mqtt_cam_client):
    pc_cam = RTCPeerConnection(configuration=get_ice_config())
    pc_cam.addTrack(CameraTrack())

    @pc_cam.on("connectionstatechange")
    async def _(): print(f"[CAM] WebRTC {pc_cam.connectionState}")

    answer_event = asyncio.Event()
    answer_data  = {}
    cam_loop = asyncio.get_event_loop()

    def on_answer(cli, userdata, msg):
        if msg.topic == T_ANSWER:
            answer_data["sdp"] = json.loads(msg.payload)
            asyncio.run_coroutine_threadsafe(
                _apply_answer(pc_cam, answer_data["sdp"], answer_event),
                cam_loop
            )

    mqtt_cam_client.on_message = on_answer
    mqtt_cam_client.subscribe(T_ANSWER)

    await pc_cam.setLocalDescription(await pc_cam.createOffer())
    print("[CAM] Esperando ICE gathering...")
    while pc_cam.iceGatheringState != "complete":
        await asyncio.sleep(0.2)

    candidates = [l for l in pc_cam.localDescription.sdp.splitlines()
                  if l.startswith("a=candidate")]
    has_relay = any("relay" in c for c in candidates)
    print(f"[CAM] {len(candidates)} candidates — {'✓ relay presente' if has_relay else '⚠ sin relay'}")

    mqtt_cam_client.publish(T_OFFER, json.dumps({
        "sdp":  pc_cam.localDescription.sdp,
        "type": pc_cam.localDescription.type,
    }), retain=True)
    print("[CAM] Offer publicada — esperando answer del dashboard...")

    await answer_event.wait()
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
    def _run():
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

    threading.Thread(target=_run, daemon=True).start()
    print("[CAM] CameraService iniciado (modo global)")


async def run_camera_local():
    import fractions
    from aiortc.contrib.signaling import TcpSocketSignaling

    signaling = TcpSocketSignaling("0.0.0.0", TCP_PORT)
    pc_cam    = RTCPeerConnection()
    pc_cam.addTrack(CameraTrack())

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

        while pc_cam.connectionState not in ("failed", "closed"):
            await asyncio.sleep(1)

    except Exception as e:
        print(f"[CAM] Error local: {e}")
    finally:
        await pc_cam.close()


def start_camera_service_local():
    def _run():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_camera_local())

    threading.Thread(target=_run, daemon=True).start()
    print("[CAM] CameraService iniciado (modo local)")


# ══════════════════════════════════════════════════════════════════════════════
#  DETECCIÓN YOLO
# ══════════════════════════════════════════════════════════════════════════════

def load_yolo():
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
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(webrtc_receive_local())
    except Exception as e:
        print(f"[VIDEO] Hilo local terminó: {e}")


async def handle_offer_dashboard(data):
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

    if topic == f'autopilotServiceDemo/{MY_ORIGIN}/telemetryInfo':
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
    elif topic == f'autopilotServiceDemo/{MY_ORIGIN}/connected':
        connectBtn.configure(text='Conectado', fg='white', bg='green')
    elif topic == f'autopilotServiceDemo/{MY_ORIGIN}/flying':
        arm_takeOffBtn.configure(text='En el aire', fg='white', bg='green')
    elif topic == f'autopilotServiceDemo/{MY_ORIGIN}/landed':
        landBtn.configure(text='En tierra', fg='white', bg='green')
        threading.Thread(target=lambda: (time.sleep(5), _reset_btns()), daemon=True).start()
    elif topic == f'autopilotServiceDemo/{MY_ORIGIN}/atHome':
        RTLBtn.configure(text='En tierra', fg='white', bg='green')
        threading.Thread(target=lambda: (time.sleep(5), _reset_btns()), daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
#  MAPA
# ══════════════════════════════════════════════════════════════════════════════

DEFAULT_LAT = 41.3851
DEFAULT_LON =  2.1734

def update_map(lat, lon):
    global drone_marker, drone_path, drone_path_line, drone_lat, drone_lon

    drone_lat, drone_lon = lat, lon
    drone_path.append((lat, lon))

    def _update():
        global drone_marker, drone_path_line
        if map_widget is None:
            return
        if drone_marker is None:
            drone_marker = map_widget.set_marker(
                lat, lon, text="🚁 Dron",
                marker_color_circle="red",
                marker_color_outside="darkred"
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
            lat, lon, text="📍 Destino",
            marker_color_circle="green",
            marker_color_outside="darkgreen"
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
#  CONTROL DEL DRON
# ══════════════════════════════════════════════════════════════════════════════

def _reset_btns():
    for b, t in [(arm_takeOffBtn,'Armar'),(landBtn,'Aterrizar'),(RTLBtn,'RTL')]:
        b.configure(text=t, fg='black', bg='dark orange')

def connect_global():
    if REAL_DRONE == False:
        client_dashboard.publish(f'{MY_ORIGIN}/autopilotServiceDemo/connect')
    else:
        client_dashboard.publish(f'{MY_ORIGIN}/autopilotServiceDemo/connect', 'REAL')
    connectBtn.configure(text='Conectado', fg='white', bg='green')
    speedSldr.set(1)

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

def connect_local():
    if REAL_DRONE == False:
        dron.connect('tcp:127.0.0.1:5763', 115200)
    else:
        dron.connect('COM3', 57600)
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
    global client_dashboard, IS_GROUND_STATION
    global altShowLbl, headingShowLbl, stateShowLbl
    global speedShowLbl, battShowLbl, gpsShowLbl
    global connectBtn, arm_takeOffBtn, landBtn, RTLBtn
    global speedSldr, gradesSldr, previousBtn

    if modo == "global":
        # ── Negociación de rol (solo en modo global + dron real) ──────────────
        if REAL_DRONE:
            print("[ROL] Negociando rol Estación de Tierra vs Cliente...")
            IS_GROUND_STATION = negociar_rol_ground_station()
        else:
            # En simulación siempre arranca el AutopilotService localmente
            IS_GROUND_STATION = True

        # ── Mostrar diálogo de rol (solo en dron real) ─────────────────────
        if REAL_DRONE:
            mostrar_dialogo_rol(IS_GROUND_STATION)

        # ── Arrancar AutopilotService solo si soy Estación de Tierra ─────────
        if IS_GROUND_STATION:
            start_autopilot_service()
            print("[MAIN] AutopilotService iniciado (Estación de Tierra)")
        else:
            print("[MAIN] AutopilotService omitido (Cliente)")

        # ── Arrancar CameraService siempre (cada consola ve su propia cámara) ─
        start_camera_service_global()

        # ── Cliente MQTT del dashboard ────────────────────────────────────────
        # client_id único por instancia → el broker no expulsa al cliente anterior
        client_dashboard = mqtt.Client(client_id=f"Dashboard_{_INST_SUFFIX}", transport="websockets")
        client_dashboard.ws_set_options(path="/mqtt")
        client_dashboard.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
        client_dashboard.username_pw_set(USER_DASHBOARD, PASS_DASHBOARD)
        client_dashboard.on_message = on_mqtt_message_dashboard
        client_dashboard.on_connect = lambda c,u,f,rc: print("[MQTT] Dashboard conectado" if rc==0 else f"[MQTT] Error {rc}")
        client_dashboard.connect(BROKER_DASHBOARD, PORT)
        # Suscribirse al buzón propio de esta instancia (topic dinámico con MY_ORIGIN)
        client_dashboard.subscribe(f'autopilotServiceDemo/{MY_ORIGIN}/#')
        client_dashboard.subscribe(T_OFFER)
        client_dashboard.loop_start()

        _connect = connect_global;  _takeoff = takeoff_global
        _land    = land_global;     _RTL     = RTL_global
        _go      = go_global;       _video   = start_webrtc_dashboard
        _startT  = startTelem_global; _stopT = stopTelem_global
        _heading = changeHeading_global; _speed = changeNavSpeed_global

        # Título indica el rol
        if REAL_DRONE:
            rol_tag = "📡 Estación de Tierra" if IS_GROUND_STATION else "📺 Cliente"
            titulo  = f"Dashboard Dron — Modo Global 🌐  |  {rol_tag}"
        else:
            titulo  = "Dashboard Dron — Modo Global 🌐 (Simulación)"

    else:  # local
        IS_GROUND_STATION = True   # en local siempre es la única instancia
        start_camera_service_local()

        _connect = connect_local;   _takeoff = takeoff_local
        _land    = land_local;      _RTL     = RTL_local
        _go      = go_local;        _video   = start_webrtc_dashboard
        _startT  = startTelem_local; _stopT  = stopTelem_local
        _heading = changeHeading_local; _speed = changeNavSpeed_local
        titulo   = "Dashboard Dron — Modo Local 🔌"

    # ── Ventana principal ─────────────────────────────────────────────────────
    v = tk.Tk()
    v.title(titulo)
    v.columnconfigure(0, weight=0, minsize=310)
    v.columnconfigure(1, weight=1)
    v.rowconfigure(0, weight=1)

    # ── Indicador de rol (visible en barra superior, solo global + real) ──────
    if modo == "global" and REAL_DRONE:
        rol_bg     = "#1b4d2e" if IS_GROUND_STATION else "#1a2a4a"
        rol_fg     = "#2ecc71" if IS_GROUND_STATION else "#3498db"
        rol_texto  = "📡  ESTACIÓN DE TIERRA  — AutopilotService activo" \
                     if IS_GROUND_STATION else \
                     "📺  CLIENTE  — AutopilotService gestionado por otra consola"
        banner = tk.Frame(v, bg=rol_bg, height=28)
        banner.grid(row=0, column=0, columnspan=2, sticky="ew")
        tk.Label(banner, text=rol_texto, font=("Arial", 9, "bold"),
                 bg=rol_bg, fg=rol_fg).pack(pady=4)
        # Desplazar controles y mapa a la fila 1
        v.rowconfigure(0, weight=0)
        v.rowconfigure(1, weight=1)
        ctrl_row = 1; map_row = 1
    else:
        ctrl_row = 0; map_row = 0

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

    v.geometry("950x750")

    # ── Liberar recursos al cerrar ────────────────────────────────────────────
    if modo == "global" and REAL_DRONE and IS_GROUND_STATION:
        # Estación de Tierra: libera claim Y slot
        v.protocol("WM_DELETE_WINDOW",
                   lambda: (limpiar_claim_ground_station(), liberar_slot(), v.destroy()))
    elif modo == "global":
        # Cliente (o simulación global): solo libera el slot
        v.protocol("WM_DELETE_WINDOW",
                   lambda: (liberar_slot(), v.destroy()))

    return v


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    REAL_DRONE = selector_simulacion()
    modo = selector_modo()
    MODE = modo

    # En modo global hay que ocupar un slot HiveMQ antes de continuar
    if modo == "global":
        seleccionar_slot()   # asigna USER_DASHBOARD, PASS_DASHBOARD, SLOT_INDEX

    print(f"[MAIN] Simulación={'sí' if not REAL_DRONE else 'no'}, Modo: {modo}")
    crear_ventana(modo).mainloop()