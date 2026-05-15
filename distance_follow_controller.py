"""
DistanceFollowController — Seguimiento de objeto con control PD via RC override.

USO:
    controller = DistanceFollowController(send_rc=my_rc_callback, ...)
    controller.start(origin="local", config={...})

    # Llamar en cada frame con detección:
    controller.update_observation({
        "distance_m": 3.2,    # distancia estimada al objeto (metros)
        "offset_x":   0.12,   # posición horizontal: -1=izq, 0=centro, +1=dcha
        "valid":      True,   # False si la detección es incierta
    })
    controller.stop()

CONTROL:
    Eje longitudinal → Pitch RC (Ch2): mantiene distancia objetivo al objeto
    Eje lateral      → Roll  RC (Ch1): centra el objeto horizontalmente en el frame
    Ambos ejes se envían simultáneamente en cada tick via send_rc(roll_pwm, pitch_pwm).

    Convenio PWM ArduPilot LOITER:
      Ch1 Roll:  1500=neutro, >1500=derecha,  <1500=izquierda
      Ch2 Pitch: 1500=neutro, >1500=adelante, <1500=atrás

ANTIOSCILACIÓN:
    El controlador usa PD con filtro paso bajo (EMA) en la derivada.
    Si el dron oscila (overshoot + retorno + overshoot...):
      1. Reducir KP_* (menos agresivo)
      2. Aumentar KD_* (más amortiguación)
      3. Ampliar DEADBAND_* (zona muerta más grande)
    Regla de arranque: empezar con KD=0, subir KP hasta límite de oscilación,
    luego subir KD hasta que las oscilaciones se amortigüen.

GUÍA DE PRUEBA EN SIMULADOR:
    Ver bloque al final del archivo.
"""

import threading
import time

# ═══════════════════════════════════════════════════════════════════
#  ÍNDICE — buscar §TAG con Ctrl+F para saltar al bloque
# ═══════════════════════════════════════════════════════════════════
#  §PARAMS        Parámetros de control (KP, KD, offsets, deadbands)
#  §CLASE         Constructor y estado interno
#  §CICLO_VIDA    configure / start / stop / update_observation
#  §LOOP          Loop de control principal (_loop)
#  §PD            Cálculo PD de demanda RC (_compute_command)
#  §RC_SEND       Envío de comandos RC al dron (_send_motion)
#  §EMIT          Publicación de status y errores
#  §SIMULADOR     Guía simulador + protocolo de tuning
# ═══════════════════════════════════════════════════════════════════

# §PARAMS
# ═══════════════════════════════════════════════════════════════════
#  PARÁMETROS DE CONTROL — editar aquí antes de cada prueba
# ═══════════════════════════════════════════════════════════════════
#
#  KP y KD están en unidades de PWM por unidad de error:
#    KP_DISTANCE [PWM/m]       → a 5m error → 40*5=200 PWM offset (máximo)
#    KD_DISTANCE [PWM/(m/s)]   → a 1m/s de acercamiento → 8 PWM offset extra
#    KP_LATERAL  [PWM/norm]    → a offset=1.0 → 180 PWM offset
#    KD_LATERAL  [PWM/(norm/s)]→ derivada lateral suave
#
#  Señales de alerta en consola:
#    roll=1700 o pitch=1700    → demanda máxima, posiblemente KP muy alto
#    RC alternando 1700/1300   → oscilación, bajar KP o subir KD
#    [FOLLOW] target_lost      → LOST_TIMEOUT_S muy bajo o detección lenta
# ═══════════════════════════════════════════════════════════════════

RC_NEUTRAL        = 1500   # PWM neutro para todos los canales
RC_MAX_OFFSET     = 200    # PWM offset máximo → rango efectivo 1300–1700
RC_MIN_OFFSET     = 40     # PWM offset mínimo cuando hay error activo

# Eje longitudinal (Pitch RC, Ch2)
KP_DISTANCE       = 40     # PWM/m          — ajustar primero (sin KD)
KD_DISTANCE       = 8      # PWM/(m/s)      — subir si oscila adelante/atrás
DEADBAND_DIST_M   = 0.30   # metros         — zona muerta de distancia
TARGET_DIST_M     = 2.0    # metros         — distancia objetivo por defecto

# Eje lateral (Roll RC, Ch1)
KP_LATERAL        = 180    # PWM/norm       — ajustar primero (sin KD)
KD_LATERAL        = 30     # PWM/(norm/s)   — subir si oscila izquierda/derecha
DEADBAND_LAT      = 0.12   # normalizado    — zona muerta lateral

# Robustez y filtros
MAX_OFFSET_ABS    = 1.0    # límite de offset lateral considerado
LOST_TIMEOUT_S    = 1.5    # s — sin detección válida → Stop
DERIV_ALPHA       = 0.4    # EMA derivada: 0.0=sin derivada, 1.0=sin filtro
CONTROL_HZ        = 10.0   # Hz del loop de control


# §CLASE
class DistanceFollowController:

    def __init__(
        self,
        set_nav_speed=None,
        set_direction=None,
        stop_direction=None,
        is_flying=None,
        publish_status=None,
        publish_error=None,
        control_hz=CONTROL_HZ,
        send_rc=None,
    ):
        self._set_nav_speed = set_nav_speed
        self._set_direction = set_direction
        self._stop_direction = stop_direction
        self._is_flying = is_flying
        self._publish_status = publish_status
        self._publish_error = publish_error
        self._send_rc = send_rc

        self._control_hz = max(1.0, float(control_hz))
        self._lock = threading.Lock()

        self._running = False
        self._thread = None
        self._origin = None
        self._params = {}
        self._observation = None
        self._last_obs_ts = 0.0

        self._last_direction = None
        self._last_lost_report_ts = 0.0

        # Estado derivativo PD
        self._prev_e_d = 0.0
        self._prev_e_x = 0.0
        self._prev_ctrl_ts = 0.0
        self._smooth_deriv_d = 0.0
        self._smooth_deriv_x = 0.0
        self._rc_print_tick = 0

        self._reset_defaults()

    def _reset_defaults(self):
        self._params = {
            "target_distance":    TARGET_DIST_M,
            "distance_deadband":  DEADBAND_DIST_M,
            "lateral_deadband":   DEADBAND_LAT,
            "kp_distance":        KP_DISTANCE,
            "kd_distance":        KD_DISTANCE,
            "kp_lateral":         KP_LATERAL,
            "kd_lateral":         KD_LATERAL,
            "rc_max_offset":      RC_MAX_OFFSET,
            "rc_min_offset":      RC_MIN_OFFSET,
            "lost_timeout":       LOST_TIMEOUT_S,
            "max_offset_abs":     MAX_OFFSET_ABS,
            "deriv_alpha":        DERIV_ALPHA,
        }

    # §CICLO_VIDA
    def configure(self, config):
        if not isinstance(config, dict):
            return
        with self._lock:
            self._apply_config_locked(config)

    def start(self, origin, config=None):
        with self._lock:
            self._origin = origin
            if isinstance(config, dict):
                self._apply_config_locked(config)
            self._running = True
            self._last_direction = None
            self._last_lost_report_ts = 0.0
            self._rc_print_tick = 0
            # Reset derivative state so stale data doesn't corrupt first command
            self._prev_e_d = 0.0
            self._prev_e_x = 0.0
            self._prev_ctrl_ts = 0.0
            self._smooth_deriv_d = 0.0
            self._smooth_deriv_x = 0.0
            # Clear stale observation
            self._observation = None
            self._last_obs_ts = 0.0
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._loop, daemon=True)
                self._thread.start()

        self._emit_status(
            "distance_follow_started",
            origin=origin,
            mode="distance-follow",
            config=self.snapshot_config(),
        )

    def stop(self, reason="stop-request", origin=None):
        with self._lock:
            self._running = False
            target_origin = origin or self._origin

        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=2.0)

        # Neutralizar RC antes de cualquier otra acción de parada
        if self._send_rc:
            try:
                self._send_rc(RC_NEUTRAL, RC_NEUTRAL)
            except Exception:
                pass

        if target_origin:
            if self._stop_direction:
                try:
                    self._stop_direction(target_origin)
                except Exception as e:
                    self._emit_error("distance_follow_stop_failed", target_origin, error=str(e))
            self._emit_status("distance_follow_stopped", origin=target_origin, reason=reason)

    def update_observation(self, observation):
        if not isinstance(observation, dict):
            return False

        try:
            distance_m = float(observation["distance_m"])
            offset_x = float(observation.get("offset_x", 0.0))
            valid = bool(observation.get("valid", True))
        except Exception:
            return False

        confidence = observation.get("confidence", None)
        target_id = observation.get("target_id", None)

        with self._lock:
            self._observation = {
                "distance_m": distance_m,
                "offset_x": offset_x,
                "valid": valid,
                "confidence": confidence,
                "target_id": target_id,
            }
            self._last_obs_ts = time.time()
        return True

    def is_running(self):
        with self._lock:
            return bool(self._running)

    def snapshot_config(self):
        with self._lock:
            return dict(self._params)

    def _apply_config_locked(self, config):
        mapping = {
            "target_distance":   ("target_distance",   float),
            "distance_deadband": ("distance_deadband",  float),
            "lateral_deadband":  ("lateral_deadband",   float),
            "kp_distance":       ("kp_distance",        float),
            "kd_distance":       ("kd_distance",        float),
            "kp_lateral":        ("kp_lateral",         float),
            "kd_lateral":        ("kd_lateral",         float),
            "rc_max_offset":     ("rc_max_offset",      float),
            "rc_min_offset":     ("rc_min_offset",      float),
            "lost_timeout":      ("lost_timeout",       float),
            "max_offset_abs":    ("max_offset_abs",     float),
            "deriv_alpha":       ("deriv_alpha",        float),
        }

        for key, value in config.items():
            if key not in mapping:
                continue
            target_key, cast = mapping[key]
            try:
                self._params[target_key] = cast(value)
            except Exception:
                continue

        p = self._params
        if p["distance_deadband"] < 0.0:
            p["distance_deadband"] = 0.0
        if p["lateral_deadband"] < 0.0:
            p["lateral_deadband"] = 0.0
        if p["lost_timeout"] < 0.1:
            p["lost_timeout"] = 0.1
        if p["max_offset_abs"] <= 0.0:
            p["max_offset_abs"] = 1.0
        if p["rc_max_offset"] < 0.0:
            p["rc_max_offset"] = 0.0
        if p["rc_min_offset"] < 0.0:
            p["rc_min_offset"] = 0.0
        p["deriv_alpha"] = max(0.0, min(1.0, p["deriv_alpha"]))

    # §LOOP
    def _loop(self):
        period = 1.0 / self._control_hz

        while True:
            with self._lock:
                running = self._running
                origin = self._origin
                params = dict(self._params)
                obs = dict(self._observation) if isinstance(self._observation, dict) else None
                last_ts = self._last_obs_ts

            if not running:
                return

            if not origin:
                time.sleep(period)
                continue

            if self._is_flying and not self._is_flying():
                self.stop(reason="drone-not-flying", origin=origin)
                return

            now = time.time()
            is_lost = (
                (obs is None)
                or ((now - last_ts) > params["lost_timeout"])
                or (not obs.get("valid", True))
            )

            if is_lost:
                self._send_motion(origin, RC_NEUTRAL, RC_NEUTRAL)
                if (now - self._last_lost_report_ts) > 1.0:
                    self._emit_status(
                        "distance_follow_target_lost",
                        origin=origin,
                        mode="distance-follow",
                        age=round(now - last_ts, 3) if last_ts else None,
                    )
                    self._last_lost_report_ts = now
                time.sleep(period)
                continue

            roll_pwm, pitch_pwm = self._compute_command(obs, params, now)
            self._rc_print_tick += 1
            if self._rc_print_tick >= max(1, int(self._control_hz)):
                self._rc_print_tick = 0
                e_d = obs['distance_m'] - params['target_distance']
                print(
                    f"[FOLLOW-RC] dist={obs['distance_m']:.2f}m (err={e_d:+.2f}m)  "
                    f"offset_x={obs.get('offset_x', 0.0):.3f}  "
                    f"→  ch1(roll)={roll_pwm}  ch2(pitch)={pitch_pwm}  "
                    f"ch3(throttle)=1500  ch4(yaw)=1500"
                )
            self._send_motion(origin, roll_pwm, pitch_pwm)
            time.sleep(period)

    # §PD
    def _compute_command(self, obs, params, now):
        e_d = float(obs["distance_m"]) - params["target_distance"]
        e_x = max(
            -params["max_offset_abs"],
            min(params["max_offset_abs"], float(obs.get("offset_x", 0.0))),
        )

        # Derivada EMA-filtrada
        alpha = params["deriv_alpha"]
        dt = now - self._prev_ctrl_ts if self._prev_ctrl_ts > 0.0 else 0.0
        if dt > 0.01:
            raw_dd = (e_d - self._prev_e_d) / dt
            raw_dx = (e_x - self._prev_e_x) / dt
            self._smooth_deriv_d = alpha * raw_dd + (1.0 - alpha) * self._smooth_deriv_d
            self._smooth_deriv_x = alpha * raw_dx + (1.0 - alpha) * self._smooth_deriv_x

        self._prev_e_d = e_d
        self._prev_e_x = e_x
        self._prev_ctrl_ts = now

        # Demanda PD (en unidades PWM)
        pitch_demand = params["kp_distance"] * e_d + params["kd_distance"] * self._smooth_deriv_d
        roll_demand  = params["kp_lateral"]  * e_x + params["kd_lateral"]  * self._smooth_deriv_x

        # Deadband sobre error (no sobre salida) — si el error está en zona muerta, demanda cero
        if abs(e_d) < params["distance_deadband"]:
            pitch_demand = 0.0
        if abs(e_x) < params["lateral_deadband"]:
            roll_demand = 0.0

        max_off = params["rc_max_offset"]
        min_off = params["rc_min_offset"]

        def to_pwm(demand):
            offset = int(max(-max_off, min(max_off, demand)))
            if 0 < abs(offset) < min_off:
                offset = min_off if offset > 0 else -min_off
            return int(RC_NEUTRAL) + offset

        return to_pwm(roll_demand), to_pwm(pitch_demand)

    # §RC_SEND
    def _send_motion(self, origin, roll_pwm, pitch_pwm):
        try:
            if self._send_rc:
                self._send_rc(roll_pwm, pitch_pwm)
            else:
                # Fallback a comandos de velocidad MAVLink (sin RC callback)
                direction = "Stop"
                if pitch_pwm > RC_NEUTRAL + 20:
                    direction = "Forward"
                elif pitch_pwm < RC_NEUTRAL - 20:
                    direction = "Back"
                elif roll_pwm > RC_NEUTRAL + 20:
                    direction = "Right"
                elif roll_pwm < RC_NEUTRAL - 20:
                    direction = "Left"
                if direction != self._last_direction:
                    if direction == "Stop" and self._stop_direction:
                        self._stop_direction(origin)
                    elif self._set_direction:
                        self._set_direction(direction, origin)
                    self._last_direction = direction
        except Exception as e:
            self._emit_error("distance_follow_motion_error", origin, error=str(e))

    # §EMIT
    def _emit_status(self, message, origin=None, **extra):
        if self._publish_status is None:
            return
        try:
            self._publish_status(message, origin=origin, **extra)
        except Exception:
            pass

    def _emit_error(self, message, origin=None, **extra):
        if self._publish_error is None:
            return
        try:
            self._publish_error(message, origin=origin, **extra)
        except Exception:
            pass


# §SIMULADOR
# ═══════════════════════════════════════════════════════════════════
#  GUÍA DE PRUEBA EN SIMULADOR
# ═══════════════════════════════════════════════════════════════════
#
# OPCIÓN A — ArduPilot SITL + Mission Planner (recomendado)
#   1. Instalar SITL: https://ardupilot.org/dev/docs/sitl-simulator-software-in-the-loop.html
#      En WSL/Linux: sim_vehicle.py -v ArduCopter --console --map
#   2. Conectar dashboard: cambiar TCP_HOST=127.0.0.1, TCP_PORT=5763
#   3. En Mission Planner: conectar al mismo TCP → ver telemetría en tiempo real
#   4. Armar + takeoff a 3m en modo LOITER desde MP o DashboardTOTAL
#   5. Activar seguimiento en Dashboard
#   6. Inyectar detecciones sintéticas desde consola Python:
#        controller.update_observation({"distance_m": 4.0, "offset_x": 0.5, "valid": True})
#   7. Observar en Mission Planner: el dron debe centrar suavemente sin oscilar
#   8. Verificar en Servo Output (MP): Ch1 y Ch2 reflejan los PWM enviados
#
# OPCIÓN B — Dry-run sin dron (mock RC)
#   En DashboardTOTAL.py, reemplazar temporalmente _follow_send_rc:
#       def _follow_send_rc(roll_pwm, pitch_pwm):
#           print(f"[DRY] RC roll={roll_pwm} pitch={pitch_pwm}")
#   Ejecutar DashboardTOTAL.py, activar follow, inyectar observaciones.
#
# PROTOCOLO DE TUNING (secuencia recomendada):
#   Paso 1: Poner KD_DISTANCE=0, KD_LATERAL=0.
#           Subir KP_DISTANCE de 10 en 10 hasta que el dron mantenga
#           distancia pero empiece a oscilar levemente.
#   Paso 2: Subir KD_DISTANCE de 2 en 2 hasta que oscilación desaparezca.
#   Paso 3: Repetir Pasos 1-2 para KP_LATERAL / KD_LATERAL.
#   Paso 4: Si los movimientos son muy bruscos, reducir RC_MAX_OFFSET (ej: 150).
#   Paso 5: Ajustar DEADBAND_DIST_M y DEADBAND_LAT para la tolerancia deseada.
#
# VALORES DE PARTIDA SEGUROS (vuelo físico inicial):
#   KP_DISTANCE=20, KD_DISTANCE=4, KP_LATERAL=100, KD_LATERAL=15
#   RC_MAX_OFFSET=150, DEADBAND_DIST_M=0.5, DEADBAND_LAT=0.20
# ═══════════════════════════════════════════════════════════════════
