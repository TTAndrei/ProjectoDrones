# =====================================================
#  UTILIDAD: Limpiar todos los retains de slots y claim
#  Ejecutar una vez para resetear el estado del broker.
#
#  Rellena las credenciales de cada slot y ejecuta:
#    python limpiar_slots.py
# =====================================================

import ssl, time
import paho.mqtt.client as mqtt

BROKER = "554f19f1f4944c978dd30b509d24afc0.s1.eu.hivemq.cloud"
PORT   = 8884

# ── Rellena con los mismos usuarios que en el dashboard ──────────────────────
HIVEMQ_USERS = [
    {"user": "InterfazGlobal",  "password": "Kb2avDJmV2aj!Jz"},   # slot 1
    {"user": "Client1",  "password": "GhJpQCxh_ktB4J9"},   # slot 2
    {"user": "",  "password": ""},   # slot 3
    {"user": "",  "password": ""},   # slot 4
]

T_SLOT_PREFIX     = "slot/ocupado/"
T_AUTOPILOT_CLAIM = "autopilot/claim"
# ─────────────────────────────────────────────────────────────────────────────

def limpiar_con_usuario(user, password, topics):
    """Publica payload vacío (borra retain) en cada topic usando las credenciales dadas."""
    c = mqtt.Client(client_id=f"cleaner_{user}", transport="websockets")
    c.ws_set_options(path="/mqtt")
    c.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2)
    c.username_pw_set(user, password)

    conectado = {"ok": False}
    def on_connect(cli, ud, flags, rc):
        conectado["ok"] = rc == 0

    c.on_connect = on_connect
    try:
        c.connect(BROKER, PORT)
        c.loop_start()
        time.sleep(1.0)
        if not conectado["ok"]:
            print(f"  [!] No se pudo conectar con usuario '{user}'")
            c.loop_stop(); return

        for t in topics:
            c.publish(t, "", retain=True, qos=1)
            print(f"  ✓ Retain borrado: {t}  (via {user})")

        time.sleep(0.5)
        c.loop_stop()
        c.disconnect()
    except Exception as e:
        print(f"  [!] Error con usuario '{user}': {e}")


if __name__ == "__main__":
    print("=== Limpiando retains del broker HiveMQ ===\n")

    slots_validos = [(i, s) for i, s in enumerate(HIVEMQ_USERS)
                     if s["user"].strip() and s["password"].strip()]

    if not slots_validos:
        print("ERROR: no hay usuarios configurados en HIVEMQ_USERS.")
        exit(1)

    for idx, creds in slots_validos:
        slot_topic = f"{T_SLOT_PREFIX}{idx + 1}"
        print(f"Slot {idx+1} ({creds['user']}):")
        limpiar_con_usuario(creds["user"], creds["password"],
                            [slot_topic, T_AUTOPILOT_CLAIM])

    print("\n=== Listo. Todos los slots y el claim han sido liberados. ===")