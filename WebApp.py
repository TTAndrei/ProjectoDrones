import os
import subprocess
import sys
import time


def _script_path(name):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, name)


def _start_process(label, script_name):
    script = _script_path(script_name)
    if not os.path.exists(script):
        raise FileNotFoundError(f"No existe el script: {script}")

    proc = subprocess.Popen(
        [sys.executable, script],
        cwd=os.path.dirname(script),
    )
    print(f"[WebApp] Iniciado {label}: pid={proc.pid} ({script_name})")
    return proc


def _stop_process(label, proc):
    if proc is None:
        return
    if proc.poll() is not None:
        return

    print(f"[WebApp] Deteniendo {label} (pid={proc.pid})...")
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        print(f"[WebApp] Forzando cierre de {label} (pid={proc.pid})")
        proc.kill()


def main():
    processes = []
    try:
        processes.append(("AutopilotService", _start_process("AutopilotService", "AutopilotService.py")))
        processes.append(("HTTP Server", _start_process("HTTP Server", "serverHTTP.py")))
        processes.append(("CameraService", _start_process("CameraService", "CameraService.py")))

        print("[WebApp] Servicios arrancados. Pulsa Ctrl+C para cerrar todo.")

        while True:
            # Si alguno cae, avisamos y dejamos el launcher vivo.
            for label, proc in processes:
                code = proc.poll()
                if code is not None:
                    print(f"[WebApp] Aviso: {label} finalizo con codigo {code}")
            time.sleep(2)

    except KeyboardInterrupt:
        print("\n[WebApp] Interrupcion recibida. Cerrando servicios...")
    finally:
        for label, proc in reversed(processes):
            _stop_process(label, proc)
        print("[WebApp] Cierre completado")


if __name__ == "__main__":
    main()
