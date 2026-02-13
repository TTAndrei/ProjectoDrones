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
