# Hermano OJO

Sistema de monitoreo con camaras IP hecho en Python (PyQt5 + OpenCV + YOLOv8). Todavia esta en desarrollo, asi que hay cosas a medias (mas abajo dejo la lista).

## Que hace

- Muestra varias camaras a la vez en una cuadricula (RTSP, y tambien webcam, un video o una app de celular)
- Detecta movimiento
- Detecta personas con YOLOv8 y les dibuja un cuadro con el porcentaje de seguridad
- Graba video, con el boton o de forma automatica cuando detecta algo
- Toma una foto cuando aparece una persona
- Login con dos roles: administrador y operador
- Pestana de grabaciones para buscar por camara y fecha, y reproducir el video ahi mismo

## Requisitos

- Python 3.10 o mas nuevo
- Una camara IP (o un celular con una app que transmita, o una webcam para probar)
- En Linux a lo mejor hay que instalar esto para que el reproductor funcione:
  `sudo apt install libpulse-mainloop-glib0`


| Campo | Para que sirve |
|---|---|
| `id` | Nombre interno, unico y sin espacios. Tambien es el nombre de la carpeta de sus grabaciones |
| `ip`, `puerto`, `usuario`, `contrasena` | Los datos de la camara (no los del login de la app) |
| `ruta_rtsp` | Cambia segun la marca (`/stream1`, `/h264`, `/Streaming/Channels/101`...). Si no conecta, probar la URL completa en VLC primero |
| `deteccion_movimiento` | Muestra el aviso de movimiento |
| `deteccion_personas` | Activa YOLOv8: cuadros sobre personas, contador y foto |
| `grabacion_automatica` | Graba solo cuando hay algo. Si la IA esta activa graba cuando ve una persona, si no, con cualquier movimiento |
| `fuente` | Opcional, para pruebas. Si existe, se usa en vez de la IP |

Ejemplos de `fuente`:

```json
"fuente": 0                                  // webcam de la laptop
"fuente": "C:/videos/prueba.mp4"             // un video como si fuera camara
"fuente": "http://192.168.1.50:8080/video"   // app de celular que transmite por HTTP
```

(Los comentarios con // de arriba son solo para explicar, el JSON de verdad no los acepta, hay que quitarlos.)

## Usuarios de prueba

| Usuario | Contrasena | Rol |
|---|---|---|
| `admin` | `admin123` | Administrador (puede todo) |
| `operador1` | `operador123` | Operador (solo ver, no borra grabaciones ni gestiona camaras) |

Cambienlas si van a usar esto en serio. Estan en `config/users.json` (guardadas con hash + salt, no en texto plano).

## Correr

```bash
QT_QPA_PLATFORM=wayland python main.py
```

## Como se usa

1. Iniciar sesion
2. En **Monitoreo en vivo** se ven las camaras. El boton **Grabar** de cada una graba a mano (sale "REC")
3. En **Grabaciones** se filtra por camara y fecha, y se hace clic en un video para verlo

Donde se guarda todo:

- Videos: `storage/grabaciones/<camara>/<fecha>/<hora>.mp4` (se cortan en pedazos de 10 minutos)
- Fotos: `storage/capturas/<camara>/<fecha>/<hora>.jpg` (maximo una cada 10 segundos por camara)
- Registro de eventos: `logs/monitoreo.log`

## Estructura

```
Hermano-OJO/
├── main.py
├── config/        # cameras.json y users.json
├── core/          # la logica: camaras, movimiento, YOLO, grabacion, login
├── ui/            # las ventanas
├── utils/         # leer config y logger
├── modelos/       # yolov8n.pt
└── storage/       # videos y fotos (se llena solo)
```

`ultralytics` (YOLOv8) usa licencia AGPL-3.0, ojo con eso si se va a distribuir.

Autor: (tu nombre)
