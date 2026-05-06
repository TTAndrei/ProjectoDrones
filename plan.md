# Plan de trabajo: centralizar parametros de control

## Objetivo
Crear una seccion unica de configuracion al inicio de `DashboardTOTAL.py` para poder ajustar rapido los parametros importantes del sistema sin buscar literales repartidos por todo el archivo.

## Parametros que deben quedar accesibles
- Altura de despegue
- Velocidad de vuelo
- Distancia de profundidad / distancia objetivo de seguimiento
- Medida fisica del objeto
- Tamano de la deadzone / offset lateral

## Parametros utiles adicionales
- `confidence_min` para aceptar detecciones
- `camera_vfov_deg` para calibracion de profundidad
- `follow_kp_distance` para la reaccion en avance/retroceso
- `follow_kp_lateral` para la reaccion lateral
- `follow_min_speed` y `follow_max_speed` para limitar la respuesta
- `detection_stride` o frecuencia de analisis de frames
- `lost_timeout` para decidir cuando se pierde el objetivo
- `follow_stop_after_s` para detener seguimiento tras perder el objetivo
- Limite maximo de offset normalizado si se quiere proteger la estabilidad

## Archivo principal
- `DashboardTOTAL.py`

## Archivos relacionados
- `distance_follow_controller.py`
- `AutopilotService.py`
- `CameraService.py`

## Plan de implementacion
1. Crear un bloque de configuracion al inicio del script, justo despues de los imports.
2. Agrupar la configuracion por bloques claros:
   - vuelo
   - vision
   - seguimiento
   - red / MQTT / WebRTC
   - interfaz
3. Sustituir los valores hardcodeados por referencias a esa configuracion.
4. Hacer que la UI lea y actualice esos valores desde un unico sitio.
5. Alinear los nombres de la configuracion con el controlador de seguimiento existente.
6. Mantener el flujo actual de deteccion, seguimiento y telemetria, solo cambiando donde se leen los parametros.

## Detalle de integracion sugerido
- La altura de despegue debe usarse en `takeoff_global()` y `takeoff_local()`.
- La velocidad de vuelo debe usarse como valor inicial del slider de velocidad y como referencia de seguimiento.
- La distancia objetivo de seguimiento debe alimentar `target_distance`.
- La deadzone lateral debe alimentar `lateral_deadband`.
- La medida fisica del objeto debe alimentar el calculo de profundidad.
- `kp_distance` y `kp_lateral` deben quedar visibles porque controlan la respuesta del dron.

## Verificacion
1. Revisar que la seccion de parametros quede al principio del archivo y sea facil de editar.
2. Ejecutar validacion de sintaxis sobre `DashboardTOTAL.py`.
3. Comprobar que el modo seguimiento sigue funcionando con correccion lateral.
4. Verificar que la profundidad estimada cambia al acercar o alejar el objeto.
5. Confirmar que la UI usa los nuevos valores sin romper el flujo actual.

## Criterio de exito
- El usuario puede ajustar los parametros clave desde una sola seccion.
- No hace falta buscar valores dispersos por el archivo.
- El seguimiento y la profundidad siguen funcionando igual o mejor, pero con mas control.

## Nota
Si mas adelante se quiere, esta configuracion puede convertirse en un panel editable dentro de la interfaz para no tocar el codigo cada vez.