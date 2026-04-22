############  INSTALAR ##############
# paho-mqtt, version 1.6.1
#####################################

import json
import os
import threading
import time

import paho.mqtt.client as mqtt

from dronLink.Dron import Dron
from distance_follow_controller import DistanceFollowController


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
distance_follow = None


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


def _parse_json_payload(payload_text):
    if not payload_text:
        return {}
    parsed = json.loads(payload_text)
    if not isinstance(parsed, dict):
        raise ValueError("Se esperaba un objeto JSON")
    return parsed


def _follow_set_nav_speed(speed, origin):
    dron.changeNavSpeed(float(speed))


def _follow_set_direction(direction, origin):
    dron.go(direction)


def _follow_stop_direction(origin):
    dron.go("Stop")


def _is_drone_flying():
    return dron.state == "flying"


def _ensure_follow_controller():
    global distance_follow
    if distance_follow is None:
        distance_follow = DistanceFollowController(
            set_nav_speed=_follow_set_nav_speed,
            set_direction=_follow_set_direction,
            stop_direction=_follow_stop_direction,
            is_flying=_is_drone_flying,
            publish_status=publish_status,
            publish_error=publish_error,
            control_hz=8.0,
        )
    return distance_follow


def publish_telemetry_info(telemetry_info):
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
        msg = (
            f"No se puede ejecutar '{command_name}' en estado '{dron.state}', "
            f"se esperaba '{expected_state}'"
        )
        publish_error(msg, origin=origin, command=command_name)
        publish_status(msg, origin=origin, level="warning", command=command_name)
        return False
    return True


def handle_command(origin, command, payload_text):
    global current_origin
    current_origin = origin
    follow_controller = _ensure_follow_controller()

    if command == "connect":
        if payload_text == "REAL":
            connection_string = "COM3"
            baud = 57600
        else:
            connection_string = "tcp:127.0.0.1:5763"
            baud = 115200

        try:
            dron.connect(connection_string, baud, freq=10)
            print(f"Conectado al dron ({connection_string} @ {baud})")
            publish_event("connected", origin=origin)
            publish_status(
                "Conexion con dron establecida",
                origin=origin,
                connection=connection_string,
                baud=baud,
            )
        except Exception as e:
            err = f"Error de conexion con dron: {e}"
            print(err)
            publish_event("connectError", origin=origin)
            publish_error(err, origin=origin, command="connect", connection=connection_string)
        return

    if command == "arm_takeOff":
        if not _require_state("connected", command, origin):
            return
        altura = int(payload_text or "5")
        dron.arm()
        dron.takeOff(altura, blocking=False, callback=publish_event, params="flying")
        publish_status("Despegue iniciado", origin=origin, altitude=altura)
        return

    if command == "go":
        if not _require_state("flying", command, origin):
            return
        if follow_controller.is_running():
            follow_controller.stop(reason="manual-go", origin=origin)
        direction = payload_text
        dron.go(direction)
        publish_status("Comando de movimiento enviado", origin=origin, direction=direction)
        return

    if command == "Land":
        if not _require_state("flying", command, origin):
            return
        if follow_controller.is_running():
            follow_controller.stop(reason="land", origin=origin)
        dron.Land(blocking=False, callback=publish_event, params="landed")
        publish_status("Aterrizaje iniciado", origin=origin)
        return

    if command == "RTL":
        if not _require_state("flying", command, origin):
            return
        if follow_controller.is_running():
            follow_controller.stop(reason="rtl", origin=origin)
        dron.RTL(blocking=False, callback=publish_event, params="atHome")
        publish_status("RTL iniciado", origin=origin)
        return

    if command == "startTelemetry":
        with _telem_lock:
            _telem_subscribers.add(origin)
            total = len(_telem_subscribers)
        print(f"[AUTOPILOT] Suscriptor telemetria: {origin} (total={total})")
        _start_telemetry_if_needed()
        publish_status("Envio de telemetria activado", origin=origin)
        return

    if command == "stopTelemetry":
        with _telem_lock:
            _telem_subscribers.discard(origin)
            total = len(_telem_subscribers)
        print(f"[AUTOPILOT] Baja telemetria: {origin} (total={total})")
        _stop_telemetry_if_empty()
        publish_status("Envio de telemetria detenido", origin=origin)
        return

    if command == "changeHeading":
        heading = float(payload_text)
        dron.changeHeading(heading)
        publish_status("Heading actualizado", origin=origin, heading=heading)
        return

    if command == "changeNavSpeed":
        if follow_controller.is_running():
            follow_controller.stop(reason="manual-speed-change", origin=origin)
        speed = float(payload_text)
        dron.changeNavSpeed(speed)
        publish_status("Velocidad de navegacion actualizada", origin=origin, speed=speed)
        return

    if command == "startDistanceFollow":
        if not _require_state("flying", command, origin):
            return
        try:
            cfg = _parse_json_payload(payload_text)
        except Exception as e:
            publish_error(
                f"Payload startDistanceFollow invalido: {e}",
                origin=origin,
                command=command,
                payload=payload_text,
            )
            return
        follow_controller.start(origin=origin, config=cfg)
        publish_status(
            "Seguimiento por distancia activado",
            origin=origin,
            mode="distance-follow",
            config=follow_controller.snapshot_config(),
        )
        return

    if command == "updateDistanceFollow":
        if not follow_controller.is_running():
            publish_status(
                "updateDistanceFollow ignorado: seguimiento no activo",
                origin=origin,
                level="warning",
                command=command,
            )
            return
        try:
            obs = _parse_json_payload(payload_text)
        except Exception as e:
            publish_error(
                f"Payload updateDistanceFollow invalido: {e}",
                origin=origin,
                command=command,
                payload=payload_text,
            )
            return
        if not follow_controller.update_observation(obs):
            publish_error(
                "Observacion de seguimiento invalida",
                origin=origin,
                command=command,
                payload=payload_text,
            )
        return

    if command == "stopDistanceFollow":
        reason = "stop-request"
        try:
            data = _parse_json_payload(payload_text)
            reason = str(data.get("reason", reason))
        except Exception:
            pass
        follow_controller.stop(reason=reason, origin=origin)
        publish_status("Seguimiento por distancia detenido", origin=origin, reason=reason)
        return

    if command == "changeAltitude":
        if not _require_state("flying", command, origin):
            return
        altitude = float(payload_text)
        ok = dron.change_altitude(altitude, blocking=False)
        if ok:
            publish_status("Altura de vuelo actualizada", origin=origin, altitude=altitude)
        else:
            publish_error(
                "No se pudo cambiar la altura de vuelo",
                origin=origin,
                command=command,
                altitude=altitude,
            )
        return

    if command == "goto":
        if not _require_state("flying", command, origin):
            return
        try:
            coords = json.loads(payload_text or "{}")
            lat = float(coords["lat"])
            lon = float(coords["lon"])
            alt = float(coords.get("alt", 5.0))
        except Exception as e:
            publish_error(
                f"Payload goto invalido: {e}",
                origin=origin,
                command=command,
                payload=payload_text,
            )
            return

        dron.goto(lat, lon, alt, blocking=False)
        publish_status("Navegacion a coordenada iniciada", origin=origin, lat=lat, lon=lon, alt=alt)
        return

    publish_error("Comando no soportado", origin=origin, command=command)


def on_message(cli, userdata, message):
    try:
        parts = message.topic.split("/")
        if len(parts) < 3:
            print(f"[AUTOPILOT] Topic invalido: {message.topic}")
            return

        origin = parts[0]
        command = parts[2]
        payload_text = message.payload.decode("utf-8").strip() if message.payload else ""

        handle_command(origin, command, payload_text)
    except Exception as e:
        print(f"[AUTOPILOT] Error procesando comando: {e}")
        try:
            publish_error(f"Excepcion en on_message: {e}")
        except Exception:
            pass


def on_connect(mqtt_client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        print("[MQTT] connected OK Returned code=", rc)
        mqtt_client.subscribe(SUBSCRIPTION)
        print("[MQTT] Subscribed to", SUBSCRIPTION)
    else:
        mqtt_connected = False
        print("[MQTT] Bad connection Returned code=", rc)


def on_disconnect(mqtt_client, userdata, rc):
    global mqtt_connected
    mqtt_connected = False
    try:
        controller = _ensure_follow_controller()
        if controller.is_running():
            controller.stop(reason="mqtt-disconnect")
    except Exception:
        pass
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
            try:
                controller = _ensure_follow_controller()
                if controller.is_running():
                    controller.stop(reason="service-stop")
            except Exception:
                pass
            break
        except Exception as e:
            print(f"[AUTOPILOT] Error en bucle principal: {e}")
            print(f"[AUTOPILOT] Reintentando en {backoff}s...")
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)


if __name__ == "__main__":
    main()
