"""
Registro de eventos: anota lo que va pasando (conexiones, movimiento,
personas, grabaciones, errores) en la pantalla y en el archivo
logs/monitoreo.log, para poder revisarlo despues.
"""
import logging
import os

RUTA_LOGS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"
)


def obtener_logger(nombre: str) -> logging.Logger:
    logger = logging.getLogger(nombre)
    if logger.handlers:  # si ya esta listo, no se vuelve a configurar
        return logger

    logger.setLevel(logging.INFO)
    formato = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    consola = logging.StreamHandler()
    consola.setFormatter(formato)
    logger.addHandler(consola)

    os.makedirs(RUTA_LOGS, exist_ok=True)
    archivo = logging.FileHandler(
        os.path.join(RUTA_LOGS, "monitoreo.log"), encoding="utf-8"
    )
    archivo.setFormatter(formato)
    logger.addHandler(archivo)

    return logger
