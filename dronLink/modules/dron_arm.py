import logging
import threading
import time
from os import times_result

from pymavlink import mavutil

def setFlightMode(self, mode):
    mode_mapping = self.vehicle.mode_mapping()
    if mode not in mode_mapping:
        logging.warning("Modo desconocido: %s. Modos disponibles: %s", mode, list(mode_mapping.keys()))
        return False
    mode_id = mode_mapping[mode]
    self.vehicle.mav.command_long_send(
        self.vehicle.target_system,
        self.vehicle.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE,
        0,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
        mode_id,
        0, 0, 0, 0, 0
    )
    msg = self.message_handler.wait_for_message('COMMAND_ACK', timeout=3)
    if msg:
        result = getattr(msg, 'result', -1)
        accepted = (result == mavutil.mavlink.MAV_RESULT_ACCEPTED)
        logging.info("Modo %s → ACK result=%d (%s)", mode, result,
                     "OK" if accepted else "RECHAZADO")
        print(f"[MODE] {mode} → {'OK' if accepted else f'RECHAZADO (result={result})'}")
        return accepted
    else:
        logging.warning("setFlightMode %s: sin ACK (timeout)", mode)
        print(f"[MODE] {mode} → sin ACK (timeout) — puede haberse aplicado igual")
        return False

def _arm2(self, callback=None, params = None):
    self.state = "arming"
    self.setFlightMode ('GUIDED')
    self.vehicle.mav.command_long_send(self.vehicle.target_system, self.vehicle.target_component,
                                         mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 0, 0, 0, 0, 0, 0)

    msg = self.message_handler.wait_for_message('COMMAND_ACK', timeout=3)
    self.vehicle.motors_armed_wait()

    if self.verbose:
        logging.info("Dron armado")

    self.state = "armed"
    if callback != None:
        if self.id == None:
            if params == None:
                callback()
            else:
                callback(params)
        else:
            if params == None:
                callback(self.id)
            else:
                callback(self.id, params)

def _arm(self, callback=None, params = None):
    self.state = "arming"
    self.setFlightMode ('GUIDED')
    self.vehicle.mav.command_long_send(self.vehicle.target_system, self.vehicle.target_component,
                                         mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 0, 0, 0, 0, 0, 0)
    msg = self.message_handler.wait_for_message('COMMAND_ACK', timeout=3)
    timeout = 10
    start_time = time.time()
    armed = False
    while time.time() - start_time < timeout:
        if self.vehicle.motors_armed():
            armed = True
            if self.verbose:
                logging.info("Dron armado")
            break
        time.sleep(0.1)
    if not armed:
        self.state = "connected"

        if self.verbose:
            logging.info("El dron no se ha armado: timeout superado")
        return

    self.state = "armed"
    if callback != None:
        if self.id == None:
            if params == None:
                callback()
            else:
                callback(params)
        else:
            if params == None:
                callback(self.id)
            else:
                callback(self.id, params)


def arm(self, blocking=True, callback=None, params = None):
    if self.state == 'connected':
        if blocking:
            self._arm()
        else:
            armThread = threading.Thread(target=self._arm, args=[callback, params])
            armThread.start()
        return True
    else:
        return False

