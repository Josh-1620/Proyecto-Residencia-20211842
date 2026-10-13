"""
Capturas: guarda una foto cuando se detecta una persona, para tener
evidencia rapida de que paso. Se guardan en:

    storage/capturas/<id_camara>/<AAAA-MM-DD>/<HHMMSS>.jpg
"""
import os
from datetime import datetime

import cv2

from utils.logger import obtener_logger

log = obtener_logger("capturas")

RUTA_CAPTURAS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "storage",
    "capturas",
)


def guardar_captura(frame, id_camara: str, carpeta_base: str = RUTA_CAPTURAS):
    """Guarda la foto y devuelve su ruta (o None si no se pudo guardar)."""
    ahora = datetime.now()
    carpeta = os.path.join(carpeta_base, id_camara, ahora.strftime("%Y-%m-%d"))
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, ahora.strftime("%H%M%S") + ".jpg")

    ok, datos = cv2.imencode(".jpg", frame)
    if not ok:
        log.error("No se pudo crear la captura de %s", id_camara)
        return None

    # Se guarda con tofile() porque funciona aunque la ruta tenga acentos
    # o caracteres raros (cv2.imwrite falla en esos casos en Windows).
    datos.tofile(ruta)
    return ruta
