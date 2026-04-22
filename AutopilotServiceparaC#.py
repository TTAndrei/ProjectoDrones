############  INSTALAR ##############
# paho-mqtt, version 1.6.1
#####################################

import paho.mqtt.client as mqtt
import json
import time
from dronLink.Dron import Dron
from distance_follow_controller import DistanceFollowController


distance_follow = None

# esta función sirve para publicar los eventos resultantes de las acciones solicitadas
def publish_event (event):
    global sending_topic, client
    client.publish(sending_topic + '/'+event)


def publish_telemetry_info (telemetry_info):
    # cuando reciba datos de telemetría los publico
    global sending_topic, client
    client.publish(sending_topic + '/telemetryInfo', json.dumps(telemetry_info))


def publish_status(message, **extra):
    global sending_topic, client, dron
    payload = {
        "timestamp": int(time.time()),
        "level": "info",
        "message": message,
        "drone_state": getattr(dron, "state", "unknown"),
    }
    payload.update(extra)
    client.publish(sending_topic + '/status', json.dumps(payload))


def publish_error(message, **extra):
    global sending_topic, client, dron
    payload = {
        "timestamp": int(time.time()),
        "message": message,
        "drone_state": getattr(dron, "state", "unknown"),
    }
    payload.update(extra)
    client.publish(sending_topic + '/error', json.dumps(payload))


def _parse_json_payload(payload_text):
    if not payload_text:
        return {}
    data = json.loads(payload_text)
    if not isinstance(data, dict):
        raise ValueError("Se esperaba un objeto JSON")
    return data


def _follow_set_nav_speed(speed, origin):
    dron.changeNavSpeed(float(speed))


def _follow_set_direction(direction, origin):
    dron.go(direction)


def _follow_stop_direction(origin):
    dron.go("Stop")


def _is_drone_flying():
    return dron.state == 'flying'


def _ensure_follow_controller():
    global distance_follow
    if distance_follow is None:
        distance_follow = DistanceFollowController(
            set_nav_speed=_follow_set_nav_speed,
            set_direction=_follow_set_direction,
            stop_direction=_follow_stop_direction,
            is_flying=_is_drone_flying,
            publish_status=lambda msg, origin=None, **extra: publish_status(msg, **extra),
            publish_error=lambda msg, origin=None, **extra: publish_error(msg, **extra),
            control_hz=8.0,
        )
    return distance_follow

def on_message(cli, userdata, message):
    global  sending_topic, client
    global dron
    # el mensaje que se recibe tiene este formato:
    #    "origen"/autopilotServiceDemo/"command"
    # tengo que averiguar el origen y el command
    splited = message.topic.split("/")
    origin = splited[0] # aqui tengo el nombre de la aplicación que origina la petición
    command = splited[2] # aqui tengo el comando

    sending_topic = "autopilotServiceDemo/" + origin # lo necesitaré para enviar las respuestas
    follow_controller = _ensure_follow_controller()

    if command == 'connect':
        # decide between simulator and real drone based on payload
        # el dashboard publica solo el topic o bien incluye "REAL" como payload
        payload = message.payload.decode("utf-8").strip()
        if payload == 'REAL':
            connection_string = 'COM3'
            baud = 57600
        else:
            # por defecto conectarse al simulador TCP
            connection_string = 'tcp:127.0.0.1:5763'
            baud = 115200
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

    if command == 'go':
        if dron.state == 'flying':
            if follow_controller.is_running():
                follow_controller.stop(reason="manual-go", origin=origin)
            direction = message.payload.decode("utf-8")
            dron.go(direction)

    if command == 'Land':
        if dron.state == 'flying':
            if follow_controller.is_running():
                follow_controller.stop(reason="land", origin=origin)
            # operación no bloqueante. Cuando acabe publicará el evento correspondiente
            dron.Land(blocking=False, callback=publish_event, params='landed')

    if command == 'RTL':
        if dron.state == 'flying':
            if follow_controller.is_running():
                follow_controller.stop(reason="rtl", origin=origin)
            # operación no bloqueante. Cuando acabe publicará el evento correspondiente
            dron.RTL(blocking=False, callback=publish_event, params='atHome')

    if command == 'startTelemetry':
        # indico qué función va a procesar los datos de telemetría cuando se reciban
        dron.send_telemetry_info(publish_telemetry_info)
        print ('Empezamos a enviar información de telemetría')

    if command == 'stopTelemetry':
        dron.stop_sending_telemetry_info()

    if command == 'changeHeading':
        heading = float(message.payload.decode("utf-8"))
        dron.changeHeading(heading)
    
    if command == 'changeNavSpeed':
        if follow_controller.is_running():
            follow_controller.stop(reason="manual-speed-change", origin=origin)
        speed = float(message.payload.decode("utf-8"))
        dron.changeNavSpeed(speed)

    if command == 'startDistanceFollow':
        if dron.state != 'flying':
            publish_error("No se puede activar seguimiento: dron no esta en vuelo", command=command)
            return
        payload_text = message.payload.decode("utf-8").strip() if message.payload else ""
        try:
            cfg = _parse_json_payload(payload_text)
        except Exception as e:
            publish_error(f"Payload startDistanceFollow invalido: {e}", command=command, payload=payload_text)
            return
        follow_controller.start(origin=origin, config=cfg)
        publish_status("Seguimiento por distancia activado", mode="distance-follow", config=follow_controller.snapshot_config())

    if command == 'updateDistanceFollow':
        if not follow_controller.is_running():
            publish_status("updateDistanceFollow ignorado: seguimiento no activo", level="warning", command=command)
            return
        payload_text = message.payload.decode("utf-8").strip() if message.payload else ""
        try:
            obs = _parse_json_payload(payload_text)
        except Exception as e:
            publish_error(f"Payload updateDistanceFollow invalido: {e}", command=command, payload=payload_text)
            return
        if not follow_controller.update_observation(obs):
            publish_error("Observacion de seguimiento invalida", command=command, payload=payload_text)

    if command == 'stopDistanceFollow':
        payload_text = message.payload.decode("utf-8").strip() if message.payload else ""
        reason = "stop-request"
        try:
            data = _parse_json_payload(payload_text)
            reason = str(data.get("reason", reason))
        except Exception:
            pass
        follow_controller.stop(reason=reason, origin=origin)
        publish_status("Seguimiento por distancia detenido", reason=reason)
    
    if command == 'changeAltitude':
        altitud = float(message.payload.decode("utf-8"))
        dron.changeAltitud(altitud)
    
    if command == 'goTo':
        # el payload tiene el formato "lat,lon,alt"
        payload = message.payload.decode("utf-8")
        try:
            # Separar por "/"
            partes = payload.split('/')

            # Cambiar coma por punto y convertir a float
            lat, lon, alt = [float(p.replace(',', '.')) for p in partes]
            dron.goto(lat, lon, alt, blocking=False)
        except Exception as e:
            print(f"Error al procesar el comando goTo con payload '{payload}': {e}")


def on_connect(client, userdata, flags, rc):
    global connected
    if rc==0:
        print("connected OK Returned code=",rc)
        connected = True
    else:
        print("Bad connection Returned code=",rc)


dron = Dron()

client = mqtt.Client("autopilotServiceDemo", transport="websockets")

# me conecto al broker publico y gratuito
broker_address = "554f19f1f4944c978dd30b509d24afc0.s1.eu.hivemq.cloud"
broker_port = 8884
username = "autopilotServiceDemo"
password = "qkdb!LasqvHfy9V"

client.ws_set_options(path="/mqtt")

# IMPORTANTE: Configurar TLS/SSL para puerto 8884
client.tls_set(
    ca_certs=None,
    certfile=None,
    keyfile=None,
    cert_reqs=mqtt.ssl.CERT_REQUIRED,
    tls_version=mqtt.ssl.PROTOCOL_TLSv1_2,
    ciphers=None
)
client.tls_insecure_set(False)

client.username_pw_set(username, password)


client.on_message = on_message
client.on_connect = on_connect
client.connect (broker_address,broker_port)

# me subscribo a todos los mensajes cuyo destino sea este servicio
client.subscribe('+/autopilotServiceDemo/#')
print ('AutopilotServiceDemo esperando peticiones')
client.loop_forever()

