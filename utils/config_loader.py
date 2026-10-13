"""
Lectura y escritura de la lista de camaras (config/cameras.json) y
armado de la direccion RTSP de cada una.
"""
import json
import os
from urllib.parse import quote

RUTA_CONFIG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config",
    "cameras.json",
)


def cargar_camaras(ruta_config: str = RUTA_CONFIG) -> list[dict]:
    """Lee el archivo y devuelve la lista de camaras."""
    with open(ruta_config, "r", encoding="utf-8") as archivo:
        datos = json.load(archivo)
    return datos.get("camaras", [])


def construir_url_rtsp(camara: dict) -> str:
    """
    Arma la direccion completa de la camara. Se ve asi:
        rtsp://usuario:contrasena@ip:puerto/ruta
    """
    usuario = camara.get("usuario", "")
    contrasena = camara.get("contrasena", "")
    ip = camara["ip"]
    puerto = camara.get("puerto", 554)
    ruta = camara.get("ruta_rtsp", "")

    # quote() cambia los simbolos especiales (@ : / #) para que no
    # rompan la direccion. Por ejemplo, una contrasena con @ se confundiria
    # con el separador entre la contrasena y la IP.
    credenciales = f"{quote(usuario, safe='')}:{quote(contrasena, safe='')}@" if usuario else ""
    return f"rtsp://{credenciales}{ip}:{puerto}{ruta}"


def obtener_fuente(camara: dict):
    """
    Devuelve de donde se va a leer el video de la camara.

    Normalmente es la direccion RTSP. Pero si la camara trae el campo
    opcional "fuente" en el archivo, se usa ese en su lugar:
        "fuente": 0                                -> la webcam de la laptop
        "fuente": "C:/videos/prueba.mp4"           -> un video guardado
        "fuente": "http://192.168.1.50:8080/video" -> una app de celular
    """
    if "fuente" in camara:
        return camara["fuente"]
    return construir_url_rtsp(camara)


def guardar_camaras(camaras: list[dict], ruta_config: str = RUTA_CONFIG) -> None:
    """Guarda la lista de camaras de vuelta en el archivo."""
    with open(ruta_config, "w", encoding="utf-8") as archivo:
        json.dump({"camaras": camaras}, archivo, indent=2, ensure_ascii=False)
