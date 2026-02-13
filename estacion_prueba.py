import tkinter as tk
from dronLink.Dron import Dron

dron = Dron()
ventana = tk.Tk()
ventana.geometry('400x700')
ventana.title("Pequeña estación de tierra")

# Ajuste de filas y columnas
for i in range(12):
    ventana.rowconfigure(i, weight=1)
ventana.columnconfigure(0, weight=1)

# ----- Conectar / Armar -----
connectBtn = tk.Button(ventana, text="Conectar", bg="dark orange",
                       command=lambda: dron.connect('udp:127.0.0.1:14550', 57600)) #dron.connect('udp:127.0.0.1:14550', 57600)dron.connect('tcp:127.0.0.1:5763', 115200)
connectBtn.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

armBtn = tk.Button(ventana, text="Armar", bg="orange",
                   command=lambda: dron.arm())
armBtn.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

# ----- Altura -----
tk.Label(ventana, text="Altura (m):").grid(row=2, column=0)
altura_entry = tk.Entry(ventana)
altura_entry.grid(row=3, column=0)

# Aplicar altura (sin despegar)
aplicarAlturaBtn = tk.Button(ventana, text="Aplicar altura", bg="orange",
                             command=lambda: dron.change_altitude(int(altura_entry.get())))
aplicarAlturaBtn.grid(row=4, column=0, padx=5, pady=5, sticky="nsew")

# ----- Velocidad -----
tk.Label(ventana, text="Velocidad (m/s):").grid(row=5, column=0)
velocidad_entry = tk.Entry(ventana)
velocidad_entry.grid(row=6, column=0)

# Aplicar Velocidad
aplicarVelocidadBtn = tk.Button(ventana, text="Aplicar Velocidad", bg="orange",
                             command=lambda: dron.setMoveSpeed(float(velocidad_entry.get())) )
aplicarVelocidadBtn.grid(row=7, column=0, padx=5, pady=5, sticky="nsew")

# Despegue separado
takeOffBtn = tk.Button(ventana, text="Despegar", bg="orange",
                       command=lambda: dron.takeOff(4))  # Altura por defecto o la que lleve el dron
takeOffBtn.grid(row=8, column=0, padx=5, pady=5, sticky="nsew")

landBtn = tk.Button(ventana, text="Aterrizar", bg="orange",
                    command=lambda: dron.Land())
landBtn.grid(row=9, column=0, padx=5, pady=5, sticky="nsew")

# ----- Navegación -----
nav_frame = tk.LabelFrame(ventana, text="Navegación")
nav_frame.grid(row=10, column=0, rowspan=3, padx=5, pady=5)

nav_frame.rowconfigure((0, 1, 2), weight=1)
nav_frame.columnconfigure((0, 1, 2), weight=1)

botones_nav = {
    "NW": ('NorthWest', 0, 0),
    "No": ('North', 0, 1),
    "NE": ('NorthEast', 0, 2),
    "We": ('West', 1, 0),
    "St": ('Stop', 1, 1),
    "Ea": ('East', 1, 2),
    "SW": ('SouthWest', 2, 0),
    "So": ('South', 2, 1),
    "SE": ('SouthEast', 2, 2)
}

for txt, (cmd, r, c) in botones_nav.items():
    tk.Button(nav_frame, text=txt, bg="orange",
              command=lambda d=cmd: dron.go(d)).grid(
        row=r, column=c, padx=3, pady=3, sticky="nsew"
    )

# RTL
RTLBtn = tk.Button(ventana, text="RTL", bg="orange",
                   command=lambda: dron.RTL())
RTLBtn.grid(row=12, column=0, padx=5, pady=5, sticky="nsew")

# Desconectar
disconnectBtn = tk.Button(ventana, text="Desconectar", bg="orange",
                           command=lambda: dron.disconnect())
disconnectBtn.grid(row=13, column=0, padx=5, pady=5, sticky="nsew")

ventana.mainloop()
