"""
Deteccion de personas con YOLOv8.

YOLOv8 es un programa de inteligencia artificial que mira una imagen y
dice donde hay personas (y con cuanta seguridad). Este archivo tiene:
  - DetectorPersonas: carga el modelo y analiza una imagen.
  - HiloDeteccion: analiza imagenes "por detras" para que el video
    no se trabe mientras la IA piensa.
  - dibujar_personas: dibuja los cuadros verdes sobre las personas.
"""
import os
import threading
import time

import cv2

from utils.logger import obtener_logger

log = obtener_logger("person_detector")

# Carpeta donde se guarda el archivo del modelo (se descarga solo la primera vez)
RUTA_MODELOS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "modelos"
)

# yolov8n es la version mas pequena y rapida. Si tu computadora es potente,
# puedes cambiarla por "yolov8s.pt" (mas precisa, pero mas lenta).
MODELO_POR_DEFECTO = "yolov8n.pt"

# Solo se aceptan detecciones con al menos 50% de seguridad.
# Si detecta cosas que no son personas, sube este numero. Si no ve personas, bajalo.
CONFIANZA_MINIMA = 0.5

# En el modelo de YOLO, la "persona" es la clase numero 0.
CLASE_PERSONA = 0


class DetectorPersonas:
    def __init__(self, nombre_modelo: str = MODELO_POR_DEFECTO):
        # Se importa aqui adentro para que, si ultralytics no esta instalado,
        # el resto de la aplicacion siga funcionando sin IA.
        from ultralytics import YOLO

        os.makedirs(RUTA_MODELOS, exist_ok=True)
        ruta_modelo = os.path.join(RUTA_MODELOS, nombre_modelo)
        log.info("Cargando modelo YOLOv8 (la primera vez se descarga)...")
        self._modelo = YOLO(ruta_modelo)
        self._candado = threading.Lock()
        log.info("Modelo YOLOv8 listo")

    def detectar(self, frame) -> list:
        """
        Devuelve una lista con una tupla (x1, y1, x2, y2, seguridad)
        por cada persona encontrada. Las cuatro primeras son las esquinas
        del cuadro que rodea a la persona.
        """
        # El candado hace que las camaras se turnen para usar el modelo,
        # porque no puede atender a dos camaras exactamente al mismo tiempo.
        with self._candado:
            resultados = self._modelo.predict(
                frame,
                classes=[CLASE_PERSONA],
                conf=CONFIANZA_MINIMA,
                verbose=False,
            )

        personas = []
        for caja in resultados[0].boxes:
            x1, y1, x2, y2 = (int(v) for v in caja.xyxy[0].tolist())
            personas.append((x1, y1, x2, y2, float(caja.conf[0])))
        return personas


# ---------- Un solo modelo para todas las camaras ----------
# Cargar el modelo gasta memoria y tarda varios segundos (sobre todo la
# primera vez). Por eso se carga UNA sola vez, en segundo plano, y todas
# las camaras lo comparten. Mientras carga, las camaras ya muestran su video.
_detector = None
_error_de_carga = None
_hilo_carga = None
_candado = threading.Lock() #Protege 3 variables de arriba


def _cargar_modelo() -> None:
    global _detector, _error_de_carga
    try:
        detector = DetectorPersonas()
        with _candado:
            _detector = detector
    except Exception as error:
        log.error("No se pudo cargar el modelo IA: %s", error)

def iniciar_carga_ia() -> None:
    """Empieza a cargar el modelo sin hacer esperar a nadie."""
    global _hilo_carga
    with _candado:
        if _hilo_carga is None:
            #daemon=true: si la aplicacion se cierra no se queda esperando
            _hilo_carga = threading.Thread(target=_cargar_modelo, daemon=True, name="carga-ia")
            _hilo_carga.start()



def detector_listo():
    """
    Devuelve (detector, error):
        - (detector, None): el modelo ya esta listo para usarse.
        - (None, "texto"):  la carga fallo.
     - (None, None):     todavia esta cargando.
    
    """
    with _candado:
        return _detector, _error_de_carga

def obtener_detector() -> DetectorPersonas:
    """Version que SI espera hasta que el modelo cargue (util para pruebas y scripts)."""
    iniciar_carga_ia()
    _hilo_carga.join()
    detector, error = detector_listo()
    if error is not None:
        raise RuntimeError(error)
    return detector


class HiloDeteccion(threading.Thread):
    """
    Ayudante de una camara: recibe imagenes, las analiza con la IA y
    guarda el ultimo resultado. Asi la camara sigue mostrando video
    fluido mientras la IA hace su trabajo (que tarda un poco).
    """

    def __init__(self, detector: DetectorPersonas, nombre: str):
        super().__init__(daemon=True, name=f"ia-{nombre}")
        self._detector = detector
        self._imagen_pendiente = None
        self._candado = threading.Lock()
        self._aviso = threading.Event()
        self._activo = True
        self._personas = []
        self._momento = 0.0  # cuando termino el ultimo analisis

    def enviar(self, frame) -> None:
        """Deja una imagen lista para analizar (si habia otra sin analizar, se descarta)."""
        with self._candado:
            self._imagen_pendiente = frame
        self._aviso.set()

    def ultimo_resultado(self):
        """Devuelve (lista_de_personas, momento_del_analisis)."""
        with self._candado:
            return self._personas, self._momento

    def detener(self) -> None:
        """Le pide que pare y ESPERA a que termine su analisis actual."""
        self._activo = False
        self._aviso.set()
        # Esperar es importante: si el programa se cierra mientras la IA
        # sigue trabajando, Python se cierra de golpe con un error.
        if self.is_alive() and threading.current_thread() is not self:
            self.join(timeout=5)

    def run(self):
        while self._activo:
            self._aviso.wait()
            self._aviso.clear()
            if not self._activo:
                break

            with self._candado:
                frame = self._imagen_pendiente
                self._imagen_pendiente = None
            if frame is None:
                continue

            try:
                personas = self._detector.detectar(frame)
            except Exception:
                log.exception("Fallo el analisis de una imagen")
                personas = []

            with self._candado:
                self._personas = personas
                self._momento = time.monotonic()

# Colores de los cuadros (en formato BGR)
COLOR_VERDE = (0, 200, 0)      # persona normal (camara sin zona)
COLOR_ROJO = (40, 40, 230)     # persona dentro de la zona (alerta)
COLOR_AMARILLO = (0, 200, 255)  # persona fuera de la zona (solo informativo)


def dibujar_personas(frame, personas: list):
    """Devuelve una COPIA del frame con un cuadro y un texto sobre cada persona."""
    if not personas:
        return frame

    imagen = frame.copy()
    ancho = imagen.shape[1]
    grosor = max(2, ancho // 300)          # cuadros mas gruesos en imagenes grandes
    tamano_texto = max(0.5, ancho / 1400)

    for x1, y1, x2, y2, seguridad in personas:
        color = (0, 200, 0)  # verde (en formato BGR)
        cv2.rectangle(imagen, (x1, y1), (x2, y2), color, grosor)

        # El texto va sobre un recuadro verde para que se lea bien
        # sin importar los colores que haya detras.
        texto = f"Persona {int(seguridad * 100)}%"
        (ancho_texto, alto_texto), base = cv2.getTextSize(
            texto, cv2.FONT_HERSHEY_SIMPLEX, tamano_texto, max(1, grosor - 1)
        )
        arriba = max(0, y1 - alto_texto - base - 6)
        cv2.rectangle(
            imagen, (x1, arriba), (x1 + ancho_texto + 8, arriba + alto_texto + base + 6),
            color, -1,
        )
        cv2.putText(
            imagen, texto, (x1 + 4, arriba + alto_texto + 2),
            cv2.FONT_HERSHEY_SIMPLEX, tamano_texto, (0, 0, 0), max(1, grosor - 1),
        )
    return imagen
