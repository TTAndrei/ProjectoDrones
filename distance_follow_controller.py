import threading
import time


class DistanceFollowController:
    """Small, thread-based controller to keep a target distance to an object.

    It expects measurements from an external detector/tracker and converts them
    into directional navigation commands plus speed updates.
    """

    def __init__(
        self,
        set_nav_speed,
        set_direction,
        stop_direction,
        is_flying,
        publish_status=None,
        publish_error=None,
        control_hz=8.0,
    ):
        self._set_nav_speed = set_nav_speed
        self._set_direction = set_direction
        self._stop_direction = stop_direction
        self._is_flying = is_flying
        self._publish_status = publish_status
        self._publish_error = publish_error

        self._control_hz = max(1.0, float(control_hz))
        self._lock = threading.Lock()

        self._running = False
        self._thread = None
        self._origin = None
        self._params = {}
        self._observation = None
        self._last_obs_ts = 0.0

        self._last_direction = None
        self._last_speed = None
        self._last_lost_report_ts = 0.0

        self._reset_defaults()

    def _reset_defaults(self):
        self._params = {
            "target_distance": 8.0,
            "distance_deadband": 0.5,
            "lateral_deadband": 0.08,
            "kp_distance": 0.8,
            "kp_lateral": 0.9,
            "min_speed": 0.4,
            "max_speed": 3.0,
            "lost_timeout": 0.9,
            "max_offset_abs": 1.0,
        }

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
            self._last_speed = None
            self._last_lost_report_ts = 0.0
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

        # Wait for the loop thread to finish all in-flight motion commands before
        # issuing the final stop, preventing interleaved drone commands.
        # Skip the join when called from the controller thread itself to avoid
        # a deadlock (e.g. when the loop calls stop() on drone-not-flying).
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=2.0)

        if target_origin:
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
            "target_distance": ("target_distance", float),
            "distance_deadband": ("distance_deadband", float),
            "lateral_deadband": ("lateral_deadband", float),
            "kp_distance": ("kp_distance", float),
            "kp_lateral": ("kp_lateral", float),
            "min_speed": ("min_speed", float),
            "max_speed": ("max_speed", float),
            "lost_timeout": ("lost_timeout", float),
            "max_offset_abs": ("max_offset_abs", float),
        }

        for key, value in config.items():
            if key not in mapping:
                continue
            target_key, cast = mapping[key]
            try:
                self._params[target_key] = cast(value)
            except Exception:
                continue

        if self._params["min_speed"] < 0.0:
            self._params["min_speed"] = 0.0
        if self._params["max_speed"] < self._params["min_speed"]:
            self._params["max_speed"] = self._params["min_speed"]
        if self._params["distance_deadband"] < 0.0:
            self._params["distance_deadband"] = 0.0
        if self._params["lateral_deadband"] < 0.0:
            self._params["lateral_deadband"] = 0.0
        if self._params["lost_timeout"] < 0.1:
            self._params["lost_timeout"] = 0.1
        if self._params["max_offset_abs"] <= 0.0:
            self._params["max_offset_abs"] = 1.0

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

            if not self._is_flying():
                self.stop(reason="drone-not-flying", origin=origin)
                return

            now = time.time()
            is_lost = (obs is None) or ((now - last_ts) > params["lost_timeout"]) or (not obs.get("valid", True))
            if is_lost:
                self._send_motion(origin, direction="Stop", speed=None)
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

            direction, speed = self._compute_command(obs, params)
            self._send_motion(origin, direction=direction, speed=speed)
            time.sleep(period)

    def _compute_command(self, obs, params):
        target_distance = params["target_distance"]
        e_d = float(obs["distance_m"]) - target_distance
        e_x = max(-params["max_offset_abs"], min(params["max_offset_abs"], float(obs.get("offset_x", 0.0))))

        longitudinal = 0.0
        lateral = 0.0

        if abs(e_d) > params["distance_deadband"]:
            longitudinal = params["kp_distance"] * e_d

        if abs(e_x) > params["lateral_deadband"]:
            lateral = params["kp_lateral"] * e_x

        if abs(longitudinal) >= abs(lateral):
            axis = "longitudinal"
            demand = longitudinal
        else:
            axis = "lateral"
            demand = lateral

        if abs(demand) < 1e-6:
            return "Stop", None

        speed = max(params["min_speed"], min(params["max_speed"], abs(demand)))

        if axis == "longitudinal":
            direction = "Forward" if demand > 0 else "Back"
        else:
            direction = "Right" if demand > 0 else "Left"

        return direction, speed

    def _send_motion(self, origin, direction, speed):
        try:
            if speed is not None and (self._last_speed is None or abs(speed - self._last_speed) >= 0.08):
                self._set_nav_speed(speed, origin)
                self._last_speed = speed

            if direction != self._last_direction:
                if direction == "Stop":
                    self._stop_direction(origin)
                else:
                    self._set_direction(direction, origin)
                self._last_direction = direction
        except Exception as e:
            self._emit_error("distance_follow_motion_error", origin, error=str(e))

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
