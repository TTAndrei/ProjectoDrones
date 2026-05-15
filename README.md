# ProjectoDrones
Repositorio integral para control de drones con **dashboards locales y globales**, **servicios MQTT**, **streaming WebRTC**, **deteccion YOLO** y **seguimiento inteligente de objetos**.

Incluye la libreria DronLink importada desde [dronsEETAC/DronLink](https://github.com/dronsEETAC/DronLink) y extensiones propias para control remoto, deteccion de imagen y seguimiento autonomo.

## 📋 Tabla de contenidos
- [Instalacion](#instalacion)
- [Arquitectura](#arquitectura)
- [Componentes principales](#componentes-principales)
- [DashboardTOTAL (nuevo)](#dashboardtotal-integrado)
- [Inicio rapido](#inicio-rapido)
- [Modos de operacion](#modos-de-operacion)
- [Deteccion y seguimiento](#deteccion-y-seguimiento)
- [API MQTT](#api-mqtt)
- [Configuracion avanzada](#configuracion-avanzada)
- [Troubleshooting](#troubleshooting)

---

## Instalacion

### Requisitos previos
- Python 3.8+
- ArduPilot SITL (para simulacion) o drone fisico con telemetria MAVLink
- Broker MQTT (HiveMQ cloud o local)

### Dependencias principales
```bash
pip install pymavlink paho-mqtt aiortc av opencv-python requests torch
```

**Detalles por componente:**

| Componente | Dependencia | Uso |
|-----------|-------------|-----|
| DronLink | pymavlink | Comunicacion MAVLink con el dron |
| MQTT (global) | paho-mqtt | Broker de mensajes para control remoto |
| WebRTC (video) | aiortc, av | Streaming de video P2P |
| Deteccion (YOLO) | torch, opencv-python | Red neuronal de deteccion de objetos |
| API balizas V16 | requests | Descarga de datos de balizas DGT |
| UI Dashboard | tkinter (incluido) | Interfaz grafica local |

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    ProjectoDrones                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────  MODO LOCAL  ──────────────────┐  │
│  │  DashboardTOTAL / Dashboard Local (Python/C#)        │  │
│  │  ↓                                                   │  │
│  │  dronLink.Dron (TCP/Serial) ↔ MAVLink ↔ Simulador  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────  MODO GLOBAL  ────────────────┐   │
│  │  Dashboard / WebApp (HTTP/MQTT)                      │   │
│  │                ↓                                     │   │
│  │  HiveMQ Cloud (MQTT Broker)                          │   │
│  │  │                    │                              │   │
│  │  ├─→ AutopilotService → dronLink.Dron              │   │
│  │  └─→ CameraService → WebRTC (video P2P)            │   │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────  SERVICIOS INTEGRADOS  ───────────┐   │
│  │  • Deteccion YOLO (multi-clase, COCO 80 objetos)   │   │
│  │  • DistanceFollowController (seguimiento PD)        │   │
│  │  • API V16 (balizas DGT en mapa)                    │   │
│  │  • Telemetria bidireccional                         │   │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## DronLink Library

DronLink es la capa base de abstracccion para control del dron, ofreciendo una API simplificada para:
- Conexion (MAVLink TCP/Serial)
- Control de vuelo (arm, takeoff, land, RTL)
- Navegacion (goto, movimientos relativos)
- Telemetria (altitud, velocidad, bateria, GPS)
- RC override (control manual de servos)

### Uso basico
```python
from dronLink.Dron import Dron

# Crear instancia del dron
dron = Dron()

# Conectar al simulador
dron.connect('tcp:127.0.0.1:5763', 115200)
print('Conectado')

# Armar el dron
dron.arm()

# Despegar a 8 metros
dron.takeOff(8)
print('En el aire a 8 metros de altura')

# Navegar forward a 2 m/s
dron.go('Forward')
dron.changeNavSpeed(2)

# Cambiar altitud
dron.change_altitude(10)

# Aterrizar
dron.Land()
```

Para mas informacion, consulta [dronLink/docs](dronLink/docs) o el [repositorio original](https://github.com/dronsEETAC/DronLink).

## Componentes principales

### 🎮 Dashboards

| Componente | Ubicacion | Descripcion | Modo |
|-----------|----------|-------------|------|
| **DashboardTOTAL** | [DashboardTOTAL.py](DashboardTOTAL.py) | Dashboard integrado (TODO en uno) con UI Tkinter, video WebRTC, deteccion YOLO, seguimiento y mapa interactivo | Local + Global |
| Dashboard Local Python | [Dashboards Antiguas/DashboardLocalPython.py](Dashboards%20Antiguas/DashboardLocalPython.py) | Control via TCP/Serial directo con dronLink | Local |
| Dashboard Local C# | [DashboardLocalCsharp](DashboardLocalCsharp) | Interfaz Windows Forms (legacy) | Local |
| Dashboard Global | [Dashboards Antiguas/DashboardGlobalPython.py](Dashboards%20Antiguas/DashboardGlobalPython.py) | Control remoto via MQTT | Global |

### 🔌 Servicios

| Servicio | Archivo | Descripcion |
|---------|---------|------------|
| **AutopilotService** | [AutopilotService.py](AutopilotService.py) | Interprete de comandos MQTT → dronLink. Gestiona arm, takeoff, movimiento, telemetria y seguimiento a distancia |
| **CameraService** | [CameraService.py](CameraService.py) | Captura video de camara y transmite via WebRTC P2P con servidor TURN |
| MQTT Local | [serverMQTT.py](serverMQTT.py) | Broker MQTT basico para pruebas en local (alternativa a HiveMQ cloud) |
| HTTP Server | [serverHTTP.py](serverHTTP.py) | Servidor HTTP que envia comandos al broker MQTT. UI web minimalista |

### 🎥 Vision y Deteccion

| Componente | Archivo | Descripcion |
|-----------|---------|------------|
| **DistanceFollowController** | [distance_follow_controller.py](distance_follow_controller.py) | Controlador PD para seguimiento autonomo de objetos. Usa RC override (PWM) para control longitudinal y lateral |
| YOLO Multi-clase | [yolov5s.pt](yolov5s.pt) | Pesos entrenados YOLOv5 small. Detecta 80 objetos (COCO): personas, coches, animales, etc. |
| Dashboard con video | [Dashboards Antiguas/DashboardLocalConVideoStream.py](Dashboards%20Antiguas/DashboardLocalConVideoStream.py) | Dashboard clasico + video streaming desde camara local |
| Dashboard con deteccion | [Dashboards Antiguas/DashboardLocalConDeteccion.py](Dashboards%20Antiguas/DashboardLocalConDeteccion.py) | Dashboard clasico + deteccion YOLO con overlay en vivo |

### 📡 Comunicacion

| Tipo | Protocolo | Uso |
|-----|----------|-----|
| Local | TCP MAVLink (Serial opcional) | Control directo dron ↔ Dashboard |
| Global | MQTT + HiveMQ Cloud | Control remoto, telemetria, comandos, video signaling |
| Video | WebRTC P2P | Streaming H.264 en tiempo real (bajo latencia) |
| Web | HTTP REST | WebApp con formulario de comandos

---

## 🚀 DashboardTOTAL (integrado)

El archivo [DashboardTOTAL.py](DashboardTOTAL.py) es la **aplicacion principal recomendada**. Incluye todo integrado en un solo proceso:

- ✅ Dashboard UI (Tkinter) con controles de vuelo, slider de velocidad y heading
- ✅ Autopilot Service integrado (interprete MQTT → dronLink)
- ✅ Camera Service integrado (captura y WebRTC P2P)
- ✅ Deteccion YOLO multi-clase en tiempo real
- ✅ Seguimiento inteligente de objetos (Distance Follow con RC override)
- ✅ Mapa interactivo con marcadores GPS y balizas V16 (DGT)
- ✅ Seleccion de modo (local vs global, simulador vs drone real)
- ✅ Negociacion automatica de rol (ground station en MQTT)
- ✅ Terminal integrada para logs y debug

### Seleccion de modo en inicio
Al ejecutar `DashboardTOTAL.py`, aparecen dos dialogos:

1. **Simulacion vs Real**: elige conectar a simulador SITL o drone fisico
2. **Modo de operacion**: elige modo LOCAL (TCP directo) o GLOBAL (MQTT)

### Configuracion centralizada (dentro del archivo)

```python
# MQTT (HiveMQ cloud)
BROKER_DASHBOARD = "554f19f1f4944c978dd30b509d24afc0.s1.eu.hivemq.cloud"
PORT = 8884

# Vision y seguimiento
FLIGHT_TAKEOFF_HEIGHT = 2  # metros
VISION_OBJECT_SIZE_M = 0.18  # calibracion distancia
FOLLOW_TARGET_DISTANCE = 2.0  # metros
FOLLOW_KP_DISTANCE = 40  # PWM/m — ganancias PD
FOLLOW_KD_DISTANCE = 8

# Deteccion YOLO
VISION_CONFIDENCE_MIN = 0.35  # confianza minima
```

### Uso
```bash
# Asegura tener instaladas las dependencias
pip install pymavlink paho-mqtt aiortc av opencv-python requests torch

# Ejecuta el dashboard integrado
python DashboardTOTAL.py
```

---

## Inicio rapido

### Opcion 1: DashboardTOTAL (recomendado - todo en uno)
```bash
python DashboardTOTAL.py
# → Selecciona modo LOCAL o GLOBAL
# → Selecciona SIMULADOR o DRONE REAL
# → Usa interfaz Tkinter integrada
```

### Opcion 2: Flujo MQTT descentralizado
Terminal 1 (Broker MQTT):
```bash
python serverMQTT.py
```

Terminal 2 (Autopilot Service):
```bash
python AutopilotService.py
```

Terminal 3 (Dashboard):
```bash
python "Dashboards Antiguas/DashboardGlobalPython.py"
```

### Opcion 3: WebApp (interfaz web)
```bash
python serverHTTP.py
# Abre http://localhost:5000 en navegador
```

---

## Modos de operacion

### Modo LOCAL
- **Conexion**: TCP/Serial MAVLink directo (dronLink) o simulador SITL
- **Control**: Comandos de vuelo inmediatos (sin latencia de red)
- **Dashboard**: UI Tkinter integrada
- **Ideal para**: Testing, desarrollo, simulacion
- **Ejemplo**:
  ```python
  dron.connect('tcp:127.0.0.1:5763', 115200)  # SITL
  dron.arm()
  dron.takeOff(5)
  ```

### Modo GLOBAL (MQTT)
- **Conexion**: HiveMQ Cloud (MQTT broker externo)
- **Control**: Comandos via topics MQTT (remoto desde cualquier lugar)
- **Arquitectura**: 
  - Dashboard publica comandos → AutopilotService escucha → ejecuta en dron
  - Dron responde telemetria → Dashboard recibe
- **Ideal para**: Control remoto, operacion multiple, multiples GCS
- **Ventajas**: control desde cualquier ubicacion, multiples usuarios, escalable
- **Ejemplo flow**:
  ```
  Dashboard (origen: "interfazGlobal_xxx")
    → publica "interfazGlobal_xxx/autopilotServiceDemo/arm_takeOff" payload="5"
    → AutopilotService escucha "+/autopilotServiceDemo/#"
    → ejecuta dron.arm() + dron.takeOff(5)
    → publica "autopilotServiceDemo/interfazGlobal_xxx/status" respuesta
    → Dashboard recibe status
  ```

---

## Deteccion y seguimiento

### Deteccion YOLO
El modelo YOLOv5 small detecta 80 clases del dataset COCO:

**Categorias principales:**
- 🧑 Personas (clase 0)
- 🚗 Vehiculos (clases 1-7): coches, motos, aviones, autobuses, trenes, camiones
- 🦁 Animales (clases 14-19): pajaros, gatos, perros, caballos, vacas
- 🎒 Objetos (clases 24-74): mochilas, sillas, sofas, laptops, telefonos, etc.

**Configuracion en DashboardTOTAL:**
```python
# Panel de deteccion UI permite seleccionar clases activas
# Parámetros de vision
VISION_CONFIDENCE_MIN = 0.35  # Confianza minima para aceptar
VISION_OBJECT_SIZE_M = 0.18  # Tamaño real del objeto (calibracion)
VISION_CAMERA_VFOV_DEG = 49.5  # Campo de vision vertical
VISION_DISTANCE_K = 1.2  # Factor de calibracion distancia
```

### DistanceFollowController
Controlador de seguimiento autonomo que mantiene distancia y centra el objeto:

**Mecanismo:**
- Lee detecciones (distancia, offset lateral)
- Calcula errores: distancia vs target, posicion vs centro
- Aplica control PD → genera demandas PWM (RC override)
- Envia Ch1 (roll) y Ch2 (pitch) al dron
- Dron ajusta posicion manteniendo altitud y heading

**Parametros de tuning (en distance_follow_controller.py):**
```python
# Ganancia proporcional
KP_DISTANCE = 40  # PWM/m — respuesta a distancia
KP_LATERAL = 180  # PWM/norm — respuesta a offset

# Ganancia derivativa (antioscilacion)
KD_DISTANCE = 8  # PWM/(m/s)
KD_LATERAL = 30  # PWM/(norm/s)

# Zonas muertas
DEADBAND_DIST_M = 0.30  # Si error < 0.3m, no actua
DEADBAND_LAT = 0.12  # Si offset < 0.12, no actua

# Robustez
LOST_TIMEOUT_S = 1.5  # Timeout sin deteccion
RC_MAX_OFFSET = 200  # PWM max (rango efectivo 1300-1700)
```

**Guia de tuning rapido:**
1. Empezar con KP bajos (10-20), KD=0
2. Aumentar KP hasta que oscile ligeramente
3. Aumentar KD para amortiguar oscilacion
4. Ajustar deadbands para tolerancia deseada
5. Ver ejemplos completos en bloque `§SIMULADOR` del archivo

### Deteccion automatica de balizas V16 (DGT)
El Dashboard carga balizas de trafico activas desde API DGT y las dibuja en el mapa:
```python
def get_v16_activas():
    # Descarga JSON desde https://baliza.app/api/dgt
    # Extrae: id, posicion (lat/lon), tipo, velocidad limite
    # Dibuja como marcadores en mapa interactivo
```

---

## 📡 API MQTT

### Estructura de topics
```
<origin>/autopilotServiceDemo/<command>    ← Dashboard publica comandos
autopilotServiceDemo/<origin>/<response>   ← AutopilotService responde
```

Ejemplo: `interfazGlobal_abc123/autopilotServiceDemo/arm_takeOff`

### Comandos de vuelo

**Conexion:**
```bash
# Conectar al dron (SIMULADOR o REAL)
Topic: <origin>/autopilotServiceDemo/connect
Payload: "SIMULADOR"  o "REAL"
```

**Control básico:**
```bash
# Armar y despegar
Topic: <origin>/autopilotServiceDemo/arm_takeOff
Payload: "5"  (altura en metros)

# Movimiento relativo
Topic: <origin>/autopilotServiceDemo/go
Payload: "Forward" | "Back" | "Left" | "Right"

# Cambiar velocidad
Topic: <origin>/autopilotServiceDemo/changeNavSpeed
Payload: "2.5"  (m/s, 0.1-5.0)

# Cambiar heading (yaw)
Topic: <origin>/autopilotServiceDemo/changeHeading
Payload: "90"  (grados, 0-360)

# Cambiar altitud en vuelo
Topic: <origin>/autopilotServiceDemo/changeAltitude
Payload: "10"  (metros)

# Ir a coordenada GPS
Topic: <origin>/autopilotServiceDemo/goto
Payload: {"lat": 41.3851, "lon": 2.1734, "alt": 10}

# Aterrizar
Topic: <origin>/autopilotServiceDemo/Land

# Retorno a base (RTL)
Topic: <origin>/autopilotServiceDemo/RTL
```

**Telemetria:**
```bash
# Solicitar telemetria continua
Topic: <origin>/autopilotServiceDemo/startTelemetry
Respuesta: telemetryInfo cada ~100ms

# Detener telemetria
Topic: <origin>/autopilotServiceDemo/stopTelemetry
```

### Comandos de seguimiento por distancia

**Iniciar seguimiento:**
```bash
Topic: <origin>/autopilotServiceDemo/startDistanceFollow
Payload JSON (opcional, usa valores por defecto si omitido):
{
  "target_distance": 2.0,      # metros — distancia objetivo
  "distance_deadband": 0.30,   # metros — zona muerta
  "lateral_deadband": 0.12,    # normalizado — zona muerta lateral
  "kp_distance": 40,           # PWM/m — ganancia distancia
  "kd_distance": 8,            # PWM/(m/s) — derivada
  "kp_lateral": 180,           # PWM/norm — ganancia lateral
  "kd_lateral": 30,            # PWM/(norm/s) — derivada
  "rc_max_offset": 200,        # PWM max
  "lost_timeout": 1.5          # segundos — timeout perdida
}
```

**Actualizar observacion (cada frame de deteccion):**
```bash
Topic: <origin>/autopilotServiceDemo/updateDistanceFollow
Payload JSON:
{
  "distance_m": 1.8,        # distancia estimada (metros)
  "offset_x": 0.05,         # posicion lateral: -1.0 (izq) a +1.0 (dcha)
  "valid": true,            # confianza de deteccion
  "confidence": 0.92,       # (opcional) confianza YOLO
  "target_id": "car-1"      # (opcional) ID del objeto
}
```

**Detener seguimiento:**
```bash
Topic: <origin>/autopilotServiceDemo/stopDistanceFollow
Payload JSON (opcional):
{
  "reason": "manual"  # motivo de parada
}
```

### Respuestas y eventos

**Status (exito/warning):**
```bash
Topic: autopilotServiceDemo/<origin>/status
Payload:
{
  "timestamp": 1234567890,
  "level": "info|warning",
  "message": "Despegue iniciado",
  "drone_state": "flying|connected|landed",
  ...parametros adicionales...
}
```

**Error:**
```bash
Topic: autopilotServiceDemo/<origin>/error
Payload:
{
  "timestamp": 1234567890,
  "message": "Error detallado",
  "drone_state": "...",
  ...
}
```

**Eventos:**
```bash
Topic: autopilotServiceDemo/<origin>/[connected|flying|landed|...]
Payload: (vacio)
```

**Telemetria periodica:**
```bash
Topic: autopilotServiceDemo/<origin>/telemetryInfo
Payload:
{
  "lat": 41.3851,
  "lon": 2.1734,
  "alt": 8.5,
  "heading": 180,
  "vx": 1.2,
  "vy": -0.3,
  "vz": 0.1,
  "bateria": 85,
  "satellites": 12,
  ...
}
```

---

## ⚙️ Configuracion avanzada

### HiveMQ Cloud (modo GLOBAL)
1. Crea cuenta en https://www.hivemq.com/cloud/
2. Crear cluster (free tier: 100 conexiones, 5GB/mes)
3. Anadir usuarios en "Access Management"
4. Actualiza [DashboardTOTAL.py](DashboardTOTAL.py):
   ```python
   BROKER_DASHBOARD = "tu_broker.hivemq.cloud"
   HIVEMQ_USERS = [
       {"user": "InterfazGlobal", "password": "tu_password"}
   ]
   ```

### SITL (Software In The Loop)
```bash
# Instala ArduPilot
git clone https://github.com/ArduPilot/ardupilot.git
cd ardupilot
Tools/environment_install/install-prereqs-ubuntu.sh

# Lanza simulador SITL
sim_vehicle.py -v ArduCopter --console --map

# Ejecuta dashboard (selecciona SIMULADOR + LOCAL)
python DashboardTOTAL.py
```

### Calibracion de vision (distancia)
Los parametros principales para estimar distancia desde bounding box:

```python
VISION_OBJECT_SIZE_M = 0.18      # Tamaño real objeto (ej: 0.18m = coche pequeno)
VISION_CAMERA_VFOV_DEG = 49.5    # Campo vision vertical (tipico 45-60°)
VISION_DISTANCE_K = 1.2          # Factor calibracion (ajuste empírico 0.8-1.5)

# Protocolo de calibracion:
# 1. Coloca objeto a 5m
# 2. Observa BBox en video overlay
# 3. Si distancia estimada != 5m, ajusta VISION_DISTANCE_K
# 4. Si BBox muy grande/pequeno, ajusta VISION_OBJECT_SIZE_M
```

### Tuning de control PD (distance follow)
Ver archivo [distance_follow_controller.py](distance_follow_controller.py) bloque `§SIMULADOR`.

Resumen rapido:
- **Undershooting** (lento) → aumentar KP
- **Oscilacion** (vibra) → reducir KP o aumentar KD
- **Overshoot** (se pasa) → aumentar KD
- **Rough** (movimientos bruscos) → reducir RC_MAX_OFFSET

Valores iniciales seguros: KP_DIST=20, KD_DIST=4, KP_LAT=100, KD_LAT=15

---

## 🔧 Troubleshooting

### Problema: No se conecta a MQTT
**Soluciones:**
- Verifica credenciales en HiveMQ console
- Comprueba firewall (puerto 8884 abierto)
- Intenta con broker local: `python serverMQTT.py`

### Problema: dronLink no conecta
**Soluciones:**
- Verifica puerto TCP 5763 (SITL debe estar listening)
- Lanza SITL: `sim_vehicle.py -v ArduCopter`
- Reinicia dron si es fisico

### Problema: Video WebRTC no funciona
**Soluciones:**
- Firewall UDP bloqueado (para TURN)
- Usa navegador moderno (Chrome, Firefox, Edge)
- Intenta primero en red local

### Problema: Deteccion YOLO muy lenta
**Soluciones:**
- Reduce resolucion frame: `cap.set(cv2.CAP_PROP_FRAME_WIDTH, 416)`
- Reduce frequency: `DETECTION_CONTROL_HZ = 5` Hz
- Usa GPU si disponible: `torch.cuda.is_available()`

### Problema: Dron oscila en seguimiento
**Soluciones:**
- Reduce KP_DISTANCE (40 → 30)
- Aumenta KD_DISTANCE (8 → 15)
- Aumenta DEADBAND_DIST_M (0.3 → 0.5)

### Problema: Telemetria cortada
**Soluciones:**
- Reduce frequency: `dron.connect(..., freq=5)`
- Publica en batches: `autopilot_publish_telemetry()`
- Comprueba latencia MQTT

---

## 📚 Referencias

- [DronLink Docs](dronLink/docs/)
- [ArduPilot Docs](https://ardupilot.org/)
- [YOLOv5](https://github.com/ultralytics/yolov5)
- [HiveMQ Cloud](https://www.hivemq.com/cloud/)
- [WebRTC Spec](https://webrtc.org/)

---

## 🤝 Contribuciones

Para bugs, sugerencias o mejoras, contacta con el equipo de desarrollo.

## 📄 Licencia

Usa DronLink bajo su licencia original. Consulta [dronLink](dronLink/) para detalles.
