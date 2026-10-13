"""
Inicio de sesion y permisos de cada usuario.

Las contrasenas NUNCA se guardan tal cual. Para cada usuario se guarda:
  - una "sal": un texto al azar, distinto para cada usuario.
  - un "hash": el resultado de revolver la sal con la contrasena.
Al iniciar sesion se repite esa mezcla con lo que escribio la persona y se
compara con lo guardado. Asi, aunque alguien vea el archivo de usuarios,
no puede leer las contrasenas.
"""
import hashlib
import json
import os

RUTA_USUARIOS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config",
    "users.json",
)

# Lo que puede hacer cada tipo de usuario.
PERMISOS_POR_ROL = {
    "administrador": {
        "gestionar_camaras": True,
        "gestionar_usuarios": True,
        "eliminar_grabaciones": True,
    },
    "operador": {
        "gestionar_camaras": False,
        "gestionar_usuarios": False,
        "eliminar_grabaciones": False,
    },
}


def _hashear_contrasena(contrasena: str, salt: str) -> str:
    """Mezcla la sal con la contrasena y devuelve el resultado ya revuelto."""
    return hashlib.sha256((salt + contrasena).encode("utf-8")).hexdigest()


def cargar_usuarios() -> list[dict]:
    with open(RUTA_USUARIOS, "r", encoding="utf-8") as archivo:
        datos = json.load(archivo)
    return datos.get("usuarios", [])


def verificar_credenciales(usuario: str, contrasena: str) -> dict | None:
    """
    Revisa si el usuario y la contrasena son correctos.
    Si lo son, devuelve los datos del usuario (sin la sal ni el hash).
    Si no, devuelve None.
    """
    for registro in cargar_usuarios():
        if registro["usuario"] != usuario:
            continue

        hash_calculado = _hashear_contrasena(contrasena, registro["salt"])
        if hash_calculado == registro["hash"]:
            return {
                "usuario": registro["usuario"],
                "nombre": registro["nombre"],
                "rol": registro["rol"],
            }
        return None  # el usuario existe, pero la contrasena es otra

    return None  # ese usuario no existe


def tiene_permiso(usuario_actual: dict, permiso: str) -> bool:
    """Dice si el usuario puede hacer algo, segun su rol."""
    rol = usuario_actual.get("rol", "")
    return PERMISOS_POR_ROL.get(rol, {}).get(permiso, False)
