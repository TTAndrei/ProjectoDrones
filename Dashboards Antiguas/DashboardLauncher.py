import tkinter as tk
import subprocess
import sys
import os

def launch_dashboard(dashboard_name):
    script_path = os.path.join(os.path.dirname(__file__), dashboard_name)
    subprocess.Popen([sys.executable, script_path])

def main():
    ventana = tk.Tk()
    ventana.title("Dashboard Launcher")
    ventana.geometry("400x200")
    
    dashboards = [
        ("Dashboard Local Con Detección", "DashboardLocalConDeteccion.py"),
        ("Dashboard Local Con Video Stream", "DashboardLocalConVideoStream.py"),
        ("Dashboard Local Python", "DashboardLocalPython.py"),
        ("Dashboard Global Python", "DashboardGlobalPython.py"),
        ("Dashboard Global Web", "ServerHTTP.py")
    ]
    
    for i, (label, script) in enumerate(dashboards):
        btn = tk.Button(ventana, text=label, height=3, 
                       command=lambda s=script: launch_dashboard(s))
        btn.grid(row=i, column=0, padx=10, pady=10, sticky="nsew")
        ventana.rowconfigure(i, weight=1)
    
    ventana.columnconfigure(0, weight=1)
    ventana.mainloop()

if __name__ == "__main__":
    subprocess.Popen([sys.executable, "AutopilotService.py"])
    subprocess.Popen([sys.executable, "CameraService.py"])
    main()
