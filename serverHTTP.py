"""
Gateway HTTPS → MQTT + señalización WebRTC para cámara del dron.

Instalación:
    pip install flask paho-mqtt

Genera el certificado TLS autofirmado (una sola vez):
    openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem \
        -days 365 -nodes \
        -subj "/CN=localhost" \
        -addext "subjectAltName=IP:0.0.0.0,IP:127.0.0.1,IP:TU_IP_LOCAL"

    Sustituye TU_IP_LOCAL por la IP de tu máquina en la red local,
    por ejemplo: -addext "subjectAltName=IP:0.0.0.0,IP:127.0.0.1,IP:192.168.1.50"
    Coloca cert.pem y key.pem en la misma carpeta que este script.

Uso:
    python serverHTTP.py
    Abre https://TU_IP_LOCAL:5000 en el móvil/navegador.
    La primera vez Chrome pedirá aceptar el certificado autofirmado:
    pulsa "Avanzado" → "Continuar hacia...".

Arquitectura:
    - El gateway se conecta a HiveMQ como cliente "mobileFlask".
    - Reenvía comandos HTTPS → MQTT al AutopilotService.
    - Para la cámara actúa de intermediario de señalización:
        1. Publica su origen en webrtc/request para pedir stream al CameraService.
        2. Recibe la oferta SDP en webrtc/offer/mobileFlask_<id>.
        3. La expone en GET /webrtc/offer para que el navegador la recoja.
        4. El navegador devuelve su answer vía POST /webrtc/answer.
        5. El gateway la reenvía a webrtc/answer/mobileFlask_<id>.
        6. El vídeo fluye P2P entre CameraService y el navegador.
"""

import json
import os
import threading
import time
import uuid
import ssl
from flask import Flask, request, jsonify, send_from_directory
import paho.mqtt.client as mqtt
from threading import Lock, Event

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════

MQTT_BROKER    = "554f19f1f4944c978dd30b509d24afc0.s1.eu.hivemq.cloud"
MQTT_PORT      = 8884
MQTT_KEEPALIVE = 30

MQTT_USER = "mobileFlask"
MQTT_PASS = "U8BM!Pv4D4R!isq"

# Identificador único de esta instancia del gateway
_INST = uuid.uuid4().hex[:6]
MY_ORIGIN = f"mobileFlask_{_INST}"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Topics de comando (gateway → AutopilotService)
# El AutopilotService escucha: +/autopilotServiceDemo/#
TOPIC_CMD_PREFIX = f"{MY_ORIGIN}/autopilotServiceDemo"

# Topics de telemetría / eventos (AutopilotService → gateway)
TOPIC_TELEM_SUB  = f"autopilotServiceDemo/{MY_ORIGIN}/telemetryInfo"
TOPIC_EVENTS_SUB = f"autopilotServiceDemo/{MY_ORIGIN}/#"

# Topics WebRTC de señalización (igual que el dashboard Python)
T_CAM_REQUEST = "webrtc/request"
T_CAM_OFFER   = f"webrtc/offer/{MY_ORIGIN}"
T_CAM_ANSWER  = f"webrtc/answer/{MY_ORIGIN}"

# ══════════════════════════════════════════════════════════════════════════════
#  ESTADO COMPARTIDO
# ══════════════════════════════════════════════════════════════════════════════

telemetry: dict = {
    "alt":                   0.0,
    "state":                 "disconnected",
    "lat":                   None,
    "lon":                   None,
    "heading":               0.0,
    "groundSpeed":           0.0,
    "flightMode":            "",
    "battery_remaining":     None,
    "gateway_mqtt_connected": False,
    "service_connected":     False,
    "last_event":            "",
    "last_status":           "",
    "last_error":            "",
    "last_update_ts":        0,
}
telemetry_lock = Lock()
mqtt_control_lock = Lock()
mqtt_enabled = True

# Señalización WebRTC: la oferta SDP que llega del CameraService
_pending_offer: dict | None = None   # {"sdp": "...", "type": "offer"}
_offer_event   = Event()             # se dispara cuando llega la oferta
_offer_lock    = Lock()

# ══════════════════════════════════════════════════════════════════════════════
#  MQTT
# ══════════════════════════════════════════════════════════════════════════════

mqtt_client = mqtt.Client(
    client_id=f"gateway_{_INST}",
    transport="websockets"
)
mqtt_client.ws_set_options(path="/mqtt")
mqtt_client.tls_set(
    ca_certs=None, certfile=None, keyfile=None,
    cert_reqs=ssl.CERT_REQUIRED,
    tls_version=ssl.PROTOCOL_TLSv1_2,
)
mqtt_client.tls_insecure_set(False)
mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)


def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Conectado rc={rc}  origen={MY_ORIGIN}")
    with telemetry_lock:
        telemetry["gateway_mqtt_connected"] = (rc == 0)
        telemetry["last_update_ts"] = int(time.time())
    if rc == 0:
        # Telemetría + eventos del AutopilotService
        client.subscribe(TOPIC_TELEM_SUB)
        client.subscribe(TOPIC_EVENTS_SUB)
        # Oferta WebRTC del CameraService (retain=True → llega aunque tardemos)
        client.subscribe(T_CAM_OFFER)
        print(f"[MQTT] Suscrito a {TOPIC_EVENTS_SUB}")
        print(f"[MQTT] Suscrito a {T_CAM_OFFER}")


def on_disconnect(client, userdata, rc):
    with telemetry_lock:
        telemetry["gateway_mqtt_connected"] = False
        telemetry["last_update_ts"] = int(time.time())
    print(f"[MQTT] Desconectado rc={rc}")


def on_message(client, userdata, msg):
    global _pending_offer
    try:
        payload = msg.payload.decode("utf-8")
        topic   = msg.topic

        # ── Señalización WebRTC ────────────────────────────────────────────
        if topic == T_CAM_OFFER:
            if not payload:
                return   # mensaje retain vacío (limpieza)
            data = json.loads(payload)
            with _offer_lock:
                _pending_offer = data
            _offer_event.set()
            print(f"[WebRTC] Oferta recibida del CameraService ({len(payload)} bytes)")
            return

        # ── Telemetría y eventos del AutopilotService ─────────────────────
        with telemetry_lock:
            telemetry["last_update_ts"] = int(time.time())

            if topic.endswith("/telemetryInfo"):
                data = json.loads(payload)
                telemetry.update(data)

            elif topic.endswith("/status"):
                data = json.loads(payload)
                telemetry["last_status"] = data.get("message", "")
                telemetry["last_event"]  = "status"

            elif topic.endswith("/error"):
                data = json.loads(payload)
                telemetry["last_error"] = data.get("message", "error desconocido")
                telemetry["last_event"] = "error"

            elif topic.endswith("/connected"):
                telemetry["service_connected"] = True
                telemetry["state"]      = "connected"
                telemetry["last_event"] = "connected"

            elif topic.endswith("/connectError"):
                telemetry["service_connected"] = False
                telemetry["last_event"] = "connectError"
                telemetry["last_error"] = "Error al conectar con el dron"

            elif topic.endswith("/flying"):
                telemetry["state"]      = "flying"
                telemetry["last_event"] = "flying"

            elif topic.endswith("/landed"):
                telemetry["state"]      = "landed"
                telemetry["last_event"] = "landed"

            elif topic.endswith("/atHome"):
                telemetry["state"]      = "atHome"
                telemetry["last_event"] = "atHome"

            # Normalizar tipos
            for k, t in [("alt", float), ("heading", float), ("groundSpeed", float)]:
                if telemetry.get(k) is not None:
                    try:
                        telemetry[k] = t(telemetry[k])
                    except Exception:
                        pass
            for k in ("lat", "lon"):
                if telemetry.get(k) not in (None, ""):
                    try:
                        telemetry[k] = float(telemetry[k])
                    except Exception:
                        pass

    except Exception as e:
        print(f"[MQTT] Error procesando mensaje: {e}  topic={msg.topic}")
        with telemetry_lock:
            telemetry["last_error"]      = f"Error procesando MQTT: {e}"
            telemetry["last_event"]      = "gatewayParseError"
            telemetry["last_update_ts"]  = int(time.time())


mqtt_client.on_connect    = on_connect
mqtt_client.on_message    = on_message
mqtt_client.on_disconnect = on_disconnect


def _publish(topic: str, payload: str = "") -> tuple[bool, str]:
    """Publica en MQTT. Devuelve (ok, error_msg)."""
    try:
        if not mqtt_client.is_connected():
            raise RuntimeError("Gateway MQTT desconectado")
        info = mqtt_client.publish(topic, payload)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"publish rc={info.rc}")
        return True, ""
    except Exception as e:
        msg = str(e)
        with telemetry_lock:
            telemetry["last_error"]     = f"No se pudo publicar: {msg}"
            telemetry["last_event"]     = "gatewayPublishError"
            telemetry["last_update_ts"] = int(time.time())
        return False, msg


def _mqtt_loop():
    """Hilo MQTT con reconexión automática."""
    backoff = 1
    while True:
        with mqtt_control_lock:
            enabled = mqtt_enabled
        if not enabled:
            time.sleep(1)
            continue
        try:
            print(f"[MQTT] Conectando a {MQTT_BROKER}:{MQTT_PORT}…")
            mqtt_client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
            mqtt_client.loop_forever()
            backoff = 1
        except Exception as e:
            print(f"[MQTT] Error: {e} — reintentando en {backoff}s")
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)


threading.Thread(target=_mqtt_loop, daemon=True).start()

# ══════════════════════════════════════════════════════════════════════════════
#  FLASK APP
# ══════════════════════════════════════════════════════════════════════════════

app = Flask(__name__, static_folder="static", static_url_path="/static")


def _err(msg: str, code: int = 503):
    return jsonify({"error": msg}), code


# ── Página principal ──────────────────────────────────────────────────────────

@app.route("/")
def index():
    try:
        return send_from_directory("templates", "index.html")
    except Exception:
        return (
            "<h3>Gateway HTTPS → MQTT</h3>"
            "<p>Coloca tu cliente en <code>templates/index.html</code></p>"
        )


@app.route("/drone-logo.png")
def drone_logo():
    return send_from_directory(BASE_DIR, "drone-logo.png")


# ── Telemetría ────────────────────────────────────────────────────────────────

@app.route("/telemetry")
def http_telemetry():
    with telemetry_lock:
        return jsonify(dict(telemetry))


@app.route("/gateway/disconnect", methods=["POST"])
def http_gateway_disconnect():
    """Desconecta MQTT del gateway y libera la sesión en el broker."""
    global mqtt_enabled

    # Intento de parada limpia de telemetría antes de desconectar MQTT.
    _publish(f"{TOPIC_CMD_PREFIX}/stopTelemetry")

    with mqtt_control_lock:
        mqtt_enabled = False

    try:
        mqtt_client.disconnect()
    except Exception:
        pass

    with telemetry_lock:
        telemetry["gateway_mqtt_connected"] = False
        telemetry["last_event"] = "gatewayManualDisconnect"
        telemetry["last_status"] = "Gateway MQTT desconectado manualmente"
        telemetry["last_update_ts"] = int(time.time())

    print("[MQTT] Desconexion manual solicitada")
    return ("", 204)


@app.route("/gateway/connect", methods=["POST"])
def http_gateway_connect():
    """Rehabilita la conexión MQTT del gateway tras desconexión manual."""
    global mqtt_enabled
    with mqtt_control_lock:
        mqtt_enabled = True

    with telemetry_lock:
        telemetry["last_event"] = "gatewayManualConnect"
        telemetry["last_status"] = "Gateway MQTT habilitado; reconectando"
        telemetry["last_update_ts"] = int(time.time())

    print("[MQTT] Reconexion manual solicitada")
    return ("", 204)


# ── Comandos de vuelo ─────────────────────────────────────────────────────────

@app.route("/connect", methods=["POST"])
def http_connect():
    """
    Body JSON opcional: {"real": true}
    Sin body o real=false → simulación (tcp:127.0.0.1:5763).
    """
    data = request.get_json(silent=True) or {}
    payload = "REAL" if data.get("real") else ""
    ok, err = _publish(f"{TOPIC_CMD_PREFIX}/connect", payload)
    return ("", 204) if ok else _err(f"connect: {err}")


@app.route("/startTelemetry", methods=["POST"])
def http_start_telemetry():
    ok, err = _publish(f"{TOPIC_CMD_PREFIX}/startTelemetry")
    return ("", 204) if ok else _err(f"startTelemetry: {err}")


@app.route("/stopTelemetry", methods=["POST"])
def http_stop_telemetry():
    ok, err = _publish(f"{TOPIC_CMD_PREFIX}/stopTelemetry")
    return ("", 204) if ok else _err(f"stopTelemetry: {err}")


@app.route("/takeoff", methods=["POST"])
def http_takeoff():
    data   = request.get_json(silent=True) or {}
    altura = data.get("altura") or data.get("alt") or data.get("height") or 5
    ok, err = _publish(f"{TOPIC_CMD_PREFIX}/arm_takeOff", str(altura))
    return ("", 204) if ok else _err(f"takeoff: {err}")


@app.route("/land", methods=["POST"])
def http_land():
    ok, err = _publish(f"{TOPIC_CMD_PREFIX}/Land")
    return ("", 204) if ok else _err(f"land: {err}")


@app.route("/rtl", methods=["POST"])
def http_rtl():
    ok, err = _publish(f"{TOPIC_CMD_PREFIX}/RTL")
    return ("", 204) if ok else _err(f"rtl: {err}")


@app.route("/move", methods=["POST"])
def http_move():
    data      = request.get_json(silent=True) or {}
    direction = data.get("direction") or data.get("dir")
    if not direction:
        return _err("faltó campo 'direction'", 400)
    ok, err = _publish(f"{TOPIC_CMD_PREFIX}/go", str(direction))
    return ("", 204) if ok else _err(f"move: {err}")


@app.route("/changeHeading", methods=["POST"])
def http_change_heading():
    data    = request.get_json(silent=True) or {}
    heading = data.get("heading")
    if heading is None:
        return _err("faltó campo 'heading'", 400)
    ok, err = _publish(f"{TOPIC_CMD_PREFIX}/changeHeading", str(heading))
    return ("", 204) if ok else _err(f"changeHeading: {err}")


@app.route("/changeNavSpeed", methods=["POST"])
def http_change_nav_speed():
    data  = request.get_json(silent=True) or {}
    speed = data.get("speed")
    if speed is None:
        return _err("faltó campo 'speed'", 400)
    ok, err = _publish(f"{TOPIC_CMD_PREFIX}/changeNavSpeed", str(speed))
    return ("", 204) if ok else _err(f"changeNavSpeed: {err}")


@app.route("/changeAltitude", methods=["POST"])
def http_change_altitude():
    data = request.get_json(silent=True) or {}
    alt  = data.get("alt") or data.get("altura")
    if alt is None:
        return _err("faltó campo 'alt'", 400)
    ok, err = _publish(f"{TOPIC_CMD_PREFIX}/changeAltitude", str(alt))
    return ("", 204) if ok else _err(f"changeAltitude: {err}")


@app.route("/goto", methods=["POST"])
def http_goto():
    """
    Body JSON: {"lat": 41.38, "lon": 2.17, "alt": 10}
    Envía el dron a coordenadas GPS.
    """
    data = request.get_json(silent=True) or {}
    lat  = data.get("lat")
    lon  = data.get("lon")
    if lat is None or lon is None:
        return _err("faltan campos 'lat' y/o 'lon'", 400)
    alt     = data.get("alt", 5.0)
    payload = json.dumps({"lat": float(lat), "lon": float(lon), "alt": float(alt)})
    ok, err = _publish(f"{TOPIC_CMD_PREFIX}/goto", payload)
    return ("", 204) if ok else _err(f"goto: {err}")


# ── WebRTC — señalización de cámara ──────────────────────────────────────────

@app.route("/webrtc/request", methods=["POST"])
def webrtc_request():
    """
    El navegador llama aquí para pedir el stream de cámara.
    El gateway publica MY_ORIGIN en webrtc/request con retain=True
    para que el CameraService lo reciba aunque no esté suscrito aún.
    """
    global _pending_offer
    with _offer_lock:
        _pending_offer = None
    _offer_event.clear()

    ok, err = _publish(T_CAM_REQUEST, MY_ORIGIN)
    if not ok:
        return _err(f"No se pudo enviar solicitud WebRTC: {err}")

    print(f"[WebRTC] Solicitud enviada → {T_CAM_REQUEST}  payload={MY_ORIGIN}")
    return jsonify({"status": "requested", "origin": MY_ORIGIN})


@app.route("/webrtc/offer")
def webrtc_get_offer():
    """
    El navegador hace polling aquí hasta recibir la oferta SDP
    que el CameraService publicó en webrtc/offer/<MY_ORIGIN>.
    Espera hasta 15 s antes de devolver 202 (sin oferta aún).
    """
    arrived = _offer_event.wait(timeout=15.0)
    if not arrived:
        return jsonify({"status": "waiting"}), 202

    with _offer_lock:
        offer = dict(_pending_offer) if _pending_offer else None

    if offer is None:
        return jsonify({"status": "waiting"}), 202

    print("[WebRTC] Oferta enviada al navegador")
    return jsonify({"status": "ok", "offer": offer})


@app.route("/webrtc/answer", methods=["POST"])
def webrtc_post_answer():
    """
    El navegador envía aquí su answer SDP después de procesar la oferta.
    El gateway la reenvía al CameraService vía webrtc/answer/<MY_ORIGIN>.
    """
    data = request.get_json(silent=True)
    if not data or "sdp" not in data or "type" not in data:
        return _err("body debe ser {sdp, type}", 400)

    payload = json.dumps({"sdp": data["sdp"], "type": data["type"]})
    ok, err = _publish(T_CAM_ANSWER, payload)
    if not ok:
        return _err(f"No se pudo enviar answer: {err}")

    print(f"[WebRTC] Answer reenviada → {T_CAM_ANSWER}")
    return jsonify({"status": "ok"})


# ══════════════════════════════════════════════════════════════════════════════
#  TELEMETRÍA WATCHDOG  — reenvía startTelemetry si se silencia
# ══════════════════════════════════════════════════════════════════════════════

def _telem_watchdog():
    """Si no llega telemetría en 6 s, vuelve a pedirla."""
    while True:
        time.sleep(3)
        with telemetry_lock:
            last = telemetry["last_update_ts"]
            connected = telemetry.get("service_connected", False)
        if connected and (time.time() - last) > 6:
            _publish(f"{TOPIC_CMD_PREFIX}/startTelemetry")
            print("[WATCHDOG] Re-solicitando telemetría")


threading.Thread(target=_telem_watchdog, daemon=True).start()

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # ── Certificados TLS ──────────────────────────────────────────────────────
    # Busca cert.pem y key.pem en la misma carpeta que este script.
    # Genera el certificado autofirmado con el comando del encabezado de este archivo.
    cert_file = os.path.join(BASE_DIR, "cert.pem")
    key_file  = os.path.join(BASE_DIR, "key.pem")

    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        print("=" * 70)
        print("[ERROR] No se encontraron cert.pem / key.pem.")
        print("Genera el certificado con:")
        print("  openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem \\")
        print('    -days 365 -nodes -subj "/CN=localhost" \\')
        print('    -addext "subjectAltName=IP:0.0.0.0,IP:127.0.0.1,IP:TU_IP_LOCAL"')
        print("=" * 70)
        raise SystemExit(1)

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(cert_file, key_file)

    print(f"[MAIN] Gateway arrancando — origen MQTT: {MY_ORIGIN}")
    print("[MAIN] Flask en https://0.0.0.0:5000")
    print("[MAIN] Abre https://TU_IP_LOCAL:5000 en el navegador.")
    print("[MAIN] La primera vez acepta el certificado autofirmado en Chrome:")
    print('       "Avanzado" → "Continuar hacia..."')

    # use_reloader=False para no lanzar el hilo MQTT dos veces
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False,
            ssl_context=ssl_context)