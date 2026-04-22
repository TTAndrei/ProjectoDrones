# ProjectoDrones
Repositorio para crear la aplicacion de control de drones 

## DronLink Library

Este repositorio incluye la librería DronLink importada desde [dronsEETAC/DronLink](https://github.com/dronsEETAC/DronLink).

### Descripción

DronLink es una librería que facilita el desarrollo de aplicaciones de control del dron. Ofrece una amplia variedad de funcionalidades y está diseñada para las necesidades del Drone Engineering Ecosystem (DEE).

### Instalación de dependencias

Para utilizar la librería DronLink, es necesario instalar pymavlink:

```bash
pip install pymavlink
```

### Uso básico

```python
from dronLink.Dron import Dron

# Crear instancia del dron
dron = Dron()

# Conectar al simulador o dron real
dron.connect('tcp:127.0.0.1:5763', 115200)
print('Conectado')

# Armar el dron
dron.arm()
print('Armado')

# Despegar a 8 metros
dron.takeOff(8)
print('En el aire a 8 metros de altura')
```

Para más información sobre los métodos disponibles y ejemplos de uso, consulte la documentación en el directorio `dronLink/docs/` o visite el [repositorio original](https://github.com/dronsEETAC/DronLink).

## ¿Qué hemos hecho?

Siguiendo la documentacion de guia, hemos implementado diferentes funcionalidades a nuestro proyecto, en un formato de versiones: 

## Version 1 

Esta version consiste en usar la mayoria del codigo que ya se encuentra en el [repositorio original](https://github.com/dronsEETAC/DronLink) para introducirnos a las herramientas que tendremos que usar. 

### 4.1 Dashboard Local
Un panel de control local, para controlar el dron mediante señal de radio. [Dashboard Local](DashboardLocalPython.py)

### 4.1.2 Dashboard local en C# 
Existe tambien una version para c# [CarpetaC#](DashboardLocalCsharp)

## 4.2 Dashboard Global
EL objetivo de este aaprtado es eliminar la localidad del comandamiento, implementado conexion a internet, lo que diversifica y flexibiliza la forma de controlar el dron, el quien puede hacerlo, o desde donde. Esto lo haremos mediante el servicio [AutopilotService](AutopilotService.py), el cual junto a un servidor MQTT (el cual se puede crear en [local](serverMQTT.py) o con un servicio externo), nos ayudará a comunicarnos con el Dron. El funcionamiento es el siguiente, se debe iniciar el codigo de [AutopilotService.py](AutopilotService.py), el cual será el interprete entre el servidor y la consola de comandos. Esta se encuentra en [DashBoardGlobal](DashBoardGlobal.py)      

### 4.2.3 WebApp
Otra forma de controlar el dron es mediante una aplicacion web, la cual combina la forma HTTP y MQTT. La pagina HTTP envia la informacion de los comandos al servidor MQTT. Para crear el servidor HTTP se usa el archivo [serverHTTP.py](serverHTTP.py), y el archivo [indexHTTP](templates/indexHTTP.html).

## 4.3 VideoStreaming
El siguiente paso consiste en implementar la transmision de video de la camara del dron a nuestro ordenador. En esta etapa temprana usaremos simulacion de la conexion streaming, usando la camara local. Para ejecutar, deberemos activar el [cameraService.py](cameraService.py) y usar el [Dashboard con Video](DashboardLocalConVideoStreaming.py), seleccionando el boton de recibir imagen.

## 4.4 Detección de Imagen
Este apartado es muy similar al anterior, [DashboardLocalConDeteccion](DashboardLocalConDeteccion.py) pero se han añadido unos botones extra en la consola para detectar cuando ciertos objetos aparezcan en patalla. Esto se hace mediante la red neuronal YOLO que usa el dataset COCO, lo que permite detectar hasta 80 objetos diferentes (personas no funcionan). 

##NEW
[README_Dashboard.docx](https://github.com/user-attachments/files/25898996/README_Dashboard.docx)

## Seguimiento por distancia (MQTT)

Se ha añadido un control modular de seguimiento para mantener distancia estable con un objeto en movimiento (por ejemplo, un coche), reutilizando las funciones existentes de navegacion (`go`, `changeNavSpeed`, `Stop`).

### Comandos nuevos

Topic base (igual que el resto):

```text
<origin>/autopilotServiceDemo/<command>
```

1. `startDistanceFollow`

Payload JSON opcional (si no se envia, usa valores por defecto):

```json
{
	"target_distance": 8.0,
	"distance_deadband": 0.5,
	"lateral_deadband": 0.08,
	"kp_distance": 0.8,
	"kp_lateral": 0.9,
	"min_speed": 0.4,
	"max_speed": 3.0,
	"lost_timeout": 0.9,
	"max_offset_abs": 1.0
}
```

2. `updateDistanceFollow`

Payload JSON con la observacion del reconocedor/tracker:

```json
{
	"distance_m": 7.6,
	"offset_x": -0.12,
	"confidence": 0.91,
	"valid": true,
	"target_id": "car-1"
}
```

Notas:
- `distance_m` en metros.
- `offset_x` normalizado en rango aproximado `[-1, 1]` (izquierda negativo, derecha positivo).
- si `valid=false` o no llegan updates dentro de `lost_timeout`, el controlador ordena `Stop` automaticamente.

3. `stopDistanceFollow`

Payload JSON opcional:

```json
{
	"reason": "manual"
}
```

### Eventos/status

Se publican mensajes de estado en:

```text
autopilotServiceDemo/<origin>/status
autopilotServiceDemo/<origin>/error
```

Incluyendo eventos como `distance_follow_started`, `distance_follow_target_lost` y `distance_follow_stopped`.
