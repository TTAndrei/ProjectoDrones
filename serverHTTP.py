########  INSTALAR  ##########
# Flask
##############################

import json
import threading
import time
from flask import Flask, request, jsonify, send_from_directory
import paho.mqtt.client as mqtt
from threading import Lock

# CONFIGURACIÓN
MQTT_BROKER = "554f19f1f4944c978dd30b509d24afc0.s1.eu.hivemq.cloud"   # cambia si quieres otro broker
MQTT_PORT = 8884
MQTT_KEEPALIVE = 60

# Topics (ajusta si tus tópicos son distintos)
TOPIC_PREFIX_PUB = "mobileFlask/autopilotServiceDemo"        # donde publicamos comandos
TOPIC_TELEMETRY_SUB = "autopilotServiceDemo/mobileFlask/telemetryInfo"  # donde viene telemetría
TOPIC_EVENTS_SUB = "autopilotServiceDemo/mobileFlask/#"

app = Flask(__name__, static_folder="static", static_url_path="/static")

# Estado compartido de telemetría
telemetry = {
    "alt": 0.0,
    "state": "disconnected",
    "lat": None,
    "lon": None,
    "heading": 0.0,
    "groundSpeed": 0.0,
    "flightMode": "",
    "battery_remaining": None,
    "gateway_mqtt_connected": False,
    "service_connected": False,
    "last_event": "",
    "last_status": "",
    "last_error": "",
    "last_update_ts": 0,
}
telemetry_lock = Lock()

# --- MQTT client setup ---
mqtt_client = mqtt.Client(client_id="http_gateway_" + str(int(time.time())), transport="websockets")
# Si tu broker requiere username/password:
# mqtt_client.username_pw_set("user", "pass")

def on_connect(client, userdata, flags, rc):
    print("MQTT conectado con rc =", rc)
    with telemetry_lock:
        telemetry["gateway_mqtt_connected"] = (rc == 0)
        telemetry["last_update_ts"] = int(time.time())

    # Suscribirse a telemetría + eventos de estado/error
    client.subscribe(TOPIC_TELEMETRY_SUB)
    client.subscribe(TOPIC_EVENTS_SUB)
    print("Subscribed to", TOPIC_TELEMETRY_SUB)
    print("Subscribed to", TOPIC_EVENTS_SUB)


def on_disconnect(client, userdata, rc):
    with telemetry_lock:
        telemetry["gateway_mqtt_connected"] = False
        telemetry["last_update_ts"] = int(time.time())
    print("MQTT desconectado, rc =", rc)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode("utf-8")
        with telemetry_lock:
            telemetry["last_update_ts"] = int(time.time())

            if msg.topic.endswith("/telemetryInfo"):
                data = json.loads(payload)
                telemetry.update(data)

            elif msg.topic.endswith("/status"):
                data = json.loads(payload)
                telemetry["last_status"] = data.get("message", "")
                telemetry["last_event"] = "status"

            elif msg.topic.endswith("/error"):
                data = json.loads(payload)
                telemetry["last_error"] = data.get("message", "error desconocido")
                telemetry["last_event"] = "error"

            elif msg.topic.endswith("/connected"):
                telemetry["service_connected"] = True
                telemetry["state"] = "connected"
                telemetry["last_event"] = "connected"

            elif msg.topic.endswith("/connectError"):
                telemetry["service_connected"] = False
                telemetry["last_event"] = "connectError"
                telemetry["last_error"] = "Error al conectar con el dron"

            elif msg.topic.endswith("/flying"):
                telemetry["state"] = "flying"
                telemetry["last_event"] = "flying"

            elif msg.topic.endswith("/landed"):
                telemetry["state"] = "landed"
                telemetry["last_event"] = "landed"

            elif msg.topic.endswith("/atHome"):
                telemetry["state"] = "atHome"
                telemetry["last_event"] = "atHome"

            # Normalizamos tipos para la UI web
            if telemetry.get("alt") is not None:
                telemetry["alt"] = float(telemetry["alt"])
            if telemetry.get("heading") is not None:
                telemetry["heading"] = float(telemetry["heading"])
            if telemetry.get("groundSpeed") is not None:
                telemetry["groundSpeed"] = float(telemetry["groundSpeed"])
            if telemetry.get("lat") not in (None, ""):
                telemetry["lat"] = float(telemetry["lat"])
            if telemetry.get("lon") not in (None, ""):
                telemetry["lon"] = float(telemetry["lon"])
    except Exception as e:
        print("Error procesando mensaje MQTT:", e, msg.topic, msg.payload)
        with telemetry_lock:
            telemetry["last_error"] = f"Error procesando MQTT: {e}"
            telemetry["last_event"] = "gatewayParseError"
            telemetry["last_update_ts"] = int(time.time())


def _publish_command(topic, payload=""):
    try:
        if not mqtt_client.is_connected():
            raise RuntimeError("Gateway MQTT desconectado")
        info = mqtt_client.publish(topic, payload)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"publish rc={info.rc}")
        return True, ""
    except Exception as e:
        with telemetry_lock:
            telemetry["last_error"] = f"No se pudo publicar comando: {e}"
            telemetry["last_event"] = "gatewayPublishError"
            telemetry["last_update_ts"] = int(time.time())
        return False, str(e)

username = "mobileFlask"
password = "U8BM!Pv4D4R!isq"

mqtt_client.ws_set_options(path="/mqtt")

# IMPORTANTE: Configurar TLS/SSL para puerto 8884
mqtt_client.tls_set(
    ca_certs=None,
    certfile=None,
    keyfile=None,
    cert_reqs=mqtt.ssl.CERT_REQUIRED,
    tls_version=mqtt.ssl.PROTOCOL_TLSv1_2,
    ciphers=None
)
mqtt_client.tls_insecure_set(False)

mqtt_client.username_pw_set(username, password)

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.on_disconnect = on_disconnect

def mqtt_connect_and_loop():
    while True:
        try:
            print("Intentando conectar a MQTT broker:", MQTT_BROKER, MQTT_PORT)
            mqtt_client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
            mqtt_client.loop_forever()  # bloqueará aquí; si desconecta intentará reconectar internamente
        except Exception as e:
            print("Error MQTT:", e)
            time.sleep(5)

# Lanzar hilo MQTT en background antes de arrancar Flask
mqtt_thread = threading.Thread(target=mqtt_connect_and_loop, daemon=True)
mqtt_thread.start()

# ------------------ Endpoints HTTP ------------------

@app.route("/connect", methods=["POST"])
def http_connect():
    # Publicar comando de conexión (payload vacío)
    topic = f"{TOPIC_PREFIX_PUB}/connect"
    ok, err = _publish_command(topic, "")
    if not ok:
        return jsonify({"error": f"No se pudo enviar connect: {err}"}), 503
    return ("", 204)

@app.route("/startTelemetry", methods=["POST"])
def http_start_telemetry():
    topic = f"{TOPIC_PREFIX_PUB}/startTelemetry"
    ok, err = _publish_command(topic, "")
    if not ok:
        return jsonify({"error": f"No se pudo enviar startTelemetry: {err}"}), 503
    return ("", 204)

@app.route("/takeoff", methods=["POST"])
def http_takeoff():
    data = request.get_json() or {}
    altura = data.get("altura") or data.get("alt") or data.get("height")
    if altura is None:
        return jsonify({"error": "faltó campo 'altura' en JSON"}), 400
    topic = f"{TOPIC_PREFIX_PUB}/arm_takeOff"
    # publicar la altura como string (igual que hacía el cliente mqtt directamente)
    ok, err = _publish_command(topic, str(altura))
    if not ok:
        return jsonify({"error": f"No se pudo enviar arm_takeOff: {err}"}), 503
    return ("", 204)

@app.route("/land", methods=["POST"])
def http_land():
    topic = f"{TOPIC_PREFIX_PUB}/Land"
    ok, err = _publish_command(topic, "")
    if not ok:
        return jsonify({"error": f"No se pudo enviar Land: {err}"}), 503
    return ("", 204)

@app.route("/rtl", methods=["POST"])
def http_rtl():
    topic = f"{TOPIC_PREFIX_PUB}/RTL"
    ok, err = _publish_command(topic, "")
    if not ok:
        return jsonify({"error": f"No se pudo enviar RTL: {err}"}), 503
    return ("", 204)

@app.route("/move", methods=["POST"])
def http_move():
    data = request.get_json() or {}
    direction = data.get("direction") or data.get("dir")
    if not direction:
        return jsonify({"error": "faltó campo 'direction' en JSON"}), 400
    topic = f"{TOPIC_PREFIX_PUB}/go"
    ok, err = _publish_command(topic, str(direction))
    if not ok:
        return jsonify({"error": f"No se pudo enviar go: {err}"}), 503
    return ("", 204)

@app.route("/changeHeading", methods=["POST"])
def http_change_heading():
    data = request.get_json() or {}
    heading = data.get("heading")
    if heading is None:
        return jsonify({"error": "faltó campo 'heading' en JSON"}), 400
    topic = f"{TOPIC_PREFIX_PUB}/changeHeading"
    ok, err = _publish_command(topic, str(heading))
    if not ok:
        return jsonify({"error": f"No se pudo enviar changeHeading: {err}"}), 503
    return ("", 204)

@app.route("/changeNavSpeed", methods=["POST"])
def http_change_nav_speed():
    data = request.get_json() or {}
    speed = data.get("speed")
    if speed is None:
        return jsonify({"error": "faltó campo 'speed' en JSON"}), 400
    topic = f"{TOPIC_PREFIX_PUB}/changeNavSpeed"
    ok, err = _publish_command(topic, str(speed))
    if not ok:
        return jsonify({"error": f"No se pudo enviar changeNavSpeed: {err}"}), 503
    return ("", 204)


@app.route("/changeAltitude", methods=["POST"])
def http_change_altitude():
    data = request.get_json() or {}
    alt = data.get("alt")
    if alt is None:
        alt = data.get("altura")
    if alt is None:
        return jsonify({"error": "falto campo 'alt' (o 'altura') en JSON"}), 400
    topic = f"{TOPIC_PREFIX_PUB}/changeAltitude"
    ok, err = _publish_command(topic, str(alt))
    if not ok:
        return jsonify({"error": f"No se pudo enviar changeAltitude: {err}"}), 503
    return ("", 204)

@app.route("/telemetry", methods=["GET"])
def http_telemetry():
    # Devuelve la última telemetría conocida
    with telemetry_lock:
        resp = dict(telemetry)
    return jsonify(resp)

# Opcional: servir un archivo HTML desde / (si pones tu cliente en carpeta static/index.html)
@app.route("/")
def index():
    try:
        return send_from_directory("templates", "indexHTTP.html")
    except Exception:
        return "<h3>Servidor HTTP → MQTT gateway</h3><p>Coloca tu cliente en /templates/indexHTTP.html</p>"

# ----------------------------------------------------

if __name__ == "__main__":
    # Ejecutar Flask (no usar en producción; para pruebas).
    print("Arrancando Flask en http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
