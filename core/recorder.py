"""
Grabador de video.

Guarda los videos en carpetas ordenadas, que es justo como la pestana
de Grabaciones los busca:

    storage/grabaciones/<id_camara>/<AAAA-MM-DD>/<HHMMSS>.mp4

La grabacion se corta en pedazos de 10 minutos. Asi ningun archivo se
hace gigante y, si algo falla, solo se pierde el pedazo que se estaba grabando.
"""
import os
import time
from datetime import datetime

import cv2

from utils.logger import obtener_logger

log = obtener_logger("recorder")

RUTA_GRABACIONES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "storage",
    "grabaciones",
)


class Recorder:
    def __init__(self, id_camara: str, fps: float = 15.0,
                 duracion_segmento_s: int = 600,
                 carpeta_base: str = RUTA_GRABACIONES):
        self.id_camara = id_camara
        self.fps = fps
        self.duracion_segmento_s = duracion_segmento_s
        self.carpeta_base = carpeta_base

        self._writer = None
        self._tamano = None          # ancho y alto del video, segun la primera imagen
        self._inicio_segmento = 0.0

    @property
    def activo(self) -> bool:
        return self._writer is not None

    def iniciar(self, frame) -> bool:
        """Empieza a grabar. Devuelve False si no se pudo crear el archivo."""
        alto, ancho = frame.shape[:2]
        self._tamano = (ancho, alto)
        return self._abrir_segmento()

    def escribir(self, frame) -> None:
        if not self.activo:
            return

        # Si ya paso el tiempo del pedazo actual, se empieza uno nuevo
        if time.monotonic() - self._inicio_segmento >= self.duracion_segmento_s:
            self._cerrar_segmento()
            if not self._abrir_segmento():
                return

        # Todas las imagenes de un video deben medir lo mismo
        alto, ancho = frame.shape[:2]
        if (ancho, alto) != self._tamano:
            frame = cv2.resize(frame, self._tamano)
        self._writer.write(frame)

    def detener(self) -> None:
        self._cerrar_segmento()

    # ---------- Uso interno ----------
    def _abrir_segmento(self) -> bool:
        ahora = datetime.now()
        carpeta = os.path.join(
            self.carpeta_base, self.id_camara, ahora.strftime("%Y-%m-%d")
        )
        os.makedirs(carpeta, exist_ok=True)
        ruta = os.path.join(carpeta, ahora.strftime("%H%M%S") + ".mp4")

        escritor = cv2.VideoWriter(
            ruta, cv2.VideoWriter_fourcc(*"mp4v"), self.fps, self._tamano
        )
        if not escritor.isOpened():
            log.error("No se pudo crear el archivo de grabacion: %s", ruta)
            self._writer = None
            return False

        self._writer = escritor
        self._inicio_segmento = time.monotonic()
        log.info("[%s] Grabando en %s", self.id_camara, ruta)
        return True

    def _cerrar_segmento(self) -> None:
        if self._writer is not None:
            # Es importante cerrar bien el archivo: si no, el video queda danado
            # y no se puede reproducir.
            self._writer.release()
            self._writer = None
