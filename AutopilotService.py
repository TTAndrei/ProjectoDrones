############  INSTALAR ##############
# paho-mqtt, version 1.6.1
#####################################

import json
import os
import threading
import time

import paho.mqtt.client as mqtt

from dronLink.Dron import Dron


BROKER_ADDRESS = "554f19f1f4944c978dd30b509d24afc0.s1.eu.hivemq.cloud"
BROKER_PORT = 8884
USERNAME = "autopilotServiceDemo"
PASSWORD = "qkdb!LasqvHfy9V"
SUBSCRIPTION = "+/autopilotServiceDemo/#"
CLIENT_ID_PREFIX = "autopilotServiceDemo"
SERVICE_INSTANCE_ID = f"AutopilotService_py_{os.getpid()}_{int(time.time())}"


dron = Dron()
client = None
current_origin = None
mqtt_connected = False
_last_publish_error_key = None
_last_publish_error_ts = 0.0
_telem_subscribers = set()
_telem_lock = threading.Lock()
_telem_active = False


def _log_publish_error_throttled(topic, error_text, interval_seconds=5.0):
    global _last_publish_error_key, _last_publish_error_ts
    now = time.time()
    error_key = (topic, error_text)
    if error_key != _last_publish_error_key or (now - _last_publish_error_ts) >= interval_seconds:
        print(f"[MQTT] Error publicando en {topic}: {error_text}")
        _last_publish_error_key = error_key
        _last_publish_error_ts = now


def _topic_for_origin(origin):
    return f"autopilotServiceDemo/{origin}"


def safe_publish(topic, payload=""):
    global client
    try:
        if client is None:
            return False
        if not mqtt_connected:
            # Evita excepciones TLS en cascada mientras la conexion se recupera.
            return False
        info = client.publish(topic, payload)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            _log_publish_error_throttled(topic, mqtt.error_string(info.rc))
        return info.rc == mqtt.MQTT_ERR_SUCCESS
    except Exception as e:
        _log_publish_error_throttled(topic, str(e))
        return False


def publish_event(event, origin=None):
    target_origin = origin or current_origin
    if not target_origin:
        return
    safe_publish(f"{_topic_for_origin(target_origin)}/{event}")


def publish_status(message, origin=None, level="info", **extra):
    target_origin = origin or current_origin
    if not target_origin:
        return
    data = {
        "timestamp": int(time.time()),
        "level": level,
        "message": message,
        "drone_state": getattr(dron, "state", "unknown"),
    }
    data.update(extra)
    safe_publish(f"{_topic_for_origin(target_origin)}/status", json.dumps(data))


def publish_error(message, origin=None, **extra):
    target_origin = origin or current_origin
    if not target_origin:
        return
    data = {
        "timestamp": int(time.time()),
        "message": message,
        "drone_state": getattr(dron, "state", "unknown"),
    }
    data.update(extra)
    safe_publish(f"{_topic_for_origin(target_origin)}/error", json.dumps(data))


def publish_telemetry_info(telemetry_info):
    # Publica telemetría a todos los orígenes suscritos con startTelemetry.
    if not isinstance(telemetry_info, dict):
        return
    with _telem_lock:
        origins = list(_telem_subscribers)
    if not origins:
        return

    payload = dict(telemetry_info)
    payload["_source"] = SERVICE_INSTANCE_ID
    payload["_ts"] = time.time()
    payload_json = json.dumps(payload)
    for origin in origins:
        safe_publish(f"{_topic_for_origin(origin)}/telemetryInfo", payload_json)


def _start_telemetry_if_needed():
    global _telem_active
    with _telem_lock:
        should_start = (not _telem_active) and bool(_telem_subscribers)
    if should_start:
        dron.send_telemetry_info(publish_telemetry_info)
        _telem_active = True
        print("[AUTOPILOT] Telemetria iniciada")


def _stop_telemetry_if_empty():
    global _telem_active
    with _telem_lock:
        should_stop = _telem_active and (not _telem_subscribers)
    if should_stop:
        dron.stop_sending_telemetry_info()
        _telem_active = False
        print("[AUTOPILOT] Telemetria detenida (sin suscriptores)")


def _require_state(expected_state, command_name, origin):
    if dron.state != expected_state:
        msg = f"No se puede ejecutar '{command_name}' en estado '{dron.state}', se esperaba '{expected_state}'"
        publish_error(msg, origin=origin, command=command_name)
        publish_status(msg, origin=origin, level="warning", command=command_name)
        return False
    return True


def handle_command(origin, command, payload_text):
    global current_origin
    current_origin = origin

    if command == "connect":
        if payload_text == "REAL":
            connection_string = "COM3"
            baud = 57600
        else:
            # por defecto conectarse al simulador TCP
            connection_string = 'COM3' #'tcp:127.0.0.1:5763'
            baud = 57600 #115200
        dron.connect(connection_string, baud, freq=10)
        print(f'Conectado al dron ({connection_string} @ {baud})')
        publish_event('connected')

    if command == 'arm_takeOff':
        if dron.state == 'connected':
            print ('vamos a armar')
            dron.arm()
            print ('vamos a despegar')
            altura = int(message.payload.decode("utf-8"))
            dron.takeOff(altura, blocking=False, callback=publish_event, params='flying')

    if command == "go":
        if not _require_state("flying", command, origin):
            return
        direction = payload_text
        dron.go(direction)
        publish_status("Comando de movimiento enviado", origin=origin, direction=direction)
        return

    if command == "Land":
        if not _require_state("flying", command, origin):
            return
        dron.Land(blocking=False, callback=publish_event, params="landed")
        publish_status("Aterrizaje iniciado", origin=origin)
        return

    if command == 'RTL':
        if dron.state == 'flying':
            # operación no bloqueante. Cuando acabe publicará el evento correspondiente
            dron.RTL(blocking=False, callback=publish_event, params='atHome')

    if command == 'startTelemetry':
        # indico qué función va a procesar los datos de telemetría cuando se reciban
        dron.send_telemetry_info(publish_telemetry_info)

    if command == 'stopTelemetry':
        dron.stop_sending_telemetry_info()

    if command == 'changeHeading':
        heading = float(message.payload.decode("utf-8"))
        dron.changeHeading(heading)
        publish_status("Heading actualizado", origin=origin, heading=heading)
        return

    if command == "changeNavSpeed":
        speed = float(payload_text)
        dron.changeNavSpeed(speed)


def on_connect(client, userdata, flags, rc):
    global connected
    if rc==0:
        print("connected OK Returned code=",rc)
        connected = True
    else:
        mqtt_connected = False
        print("[MQTT] Bad connection Returned code=", rc)


def on_disconnect(mqtt_client, userdata, rc):
    global mqtt_connected
    mqtt_connected = False
    if rc != 0:
        print(f"[MQTT] Desconexion inesperada (rc={rc}). Reconectando...")
    else:
        print("[MQTT] Desconexion limpia")


def build_client():
    client_id = f"{CLIENT_ID_PREFIX}_{os.getpid()}_{int(time.time())}"
    print(f"[MQTT] Usando client_id: {client_id}")
    c = mqtt.Client(client_id=client_id, transport="websockets")
    c.ws_set_options(path="/mqtt")
    c.tls_set(
        ca_certs=None,
        certfile=None,
        keyfile=None,
        cert_reqs=mqtt.ssl.CERT_REQUIRED,
        tls_version=mqtt.ssl.PROTOCOL_TLSv1_2,
        ciphers=None,
    )
    c.tls_insecure_set(False)
    c.username_pw_set(USERNAME, PASSWORD)
    c.on_message = on_message
    c.on_connect = on_connect
    c.on_disconnect = on_disconnect
    c.reconnect_delay_set(min_delay=1, max_delay=20)
    return c


def main():
    global client
    backoff = 3
    while True:
        try:
            client = build_client()
            print("[AUTOPILOT] Conectando MQTT...")
            client.connect(BROKER_ADDRESS, BROKER_PORT)
            print("AutopilotServiceDemo esperando peticiones")
            client.loop_forever()
        except KeyboardInterrupt:
            print("[AUTOPILOT] Detenido por usuario")
            break
        except Exception as e:
            print(f"[AUTOPILOT] Error en bucle principal: {e}")
            print(f"[AUTOPILOT] Reintentando en {backoff}s...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)


if __name__ == "__main__":
    main()

