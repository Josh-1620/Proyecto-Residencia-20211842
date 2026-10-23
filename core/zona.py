"""
Zona de vigilancia: Un area dibujada sobre el video.
Si la camara tiene una zona, solo las personas dentro de ella cuentan como alerta 
como alerta. Las que solo estan fuera solo se marcan en pantalla.
"""
import cv2
import numpy as np

COLOR_ZONA = (60, 60, 255)  # rojo (en formato BGR)


def validar_zona(zona) -> list:
    """Devuelve la zona ya limpia, o una lista vacia si no sirve (menos de 3 puntos o datos raros)."""
    if not isinstance(zona, (list, tuple)) or len(zona) < 3:
        return []

    limpia = []
    for punto in zona:
        try:
            x, y = float(punto[0]), float(punto[1])
        except (TypeError, ValueError, IndexError):
            return []
        # Se obliga a que cada numero quede entre 0 y 1
        limpia.append([min(1.0, max(0.0, x)), min(1.0, max(0.0, y))])
    return limpia


def punto_en_zona(x: float, y: float, poligono: list) -> bool:
    """
    Dice si un punto cae dentro de la figura. Truco: se imagina una linea
    que sale del punto hacia la derecha y se cuenta cuantos bordes cruza.
    Si cruza un numero impar de bordes, el punto esta adentro.
    """
    dentro = False
    anterior = len(poligono) - 1
    for actual in range(len(poligono)):
        xi, yi = poligono[actual]
        xj, yj = poligono[anterior]
        # Solo importan los bordes que quedan a la altura del punto
        if (yi > y) != (yj > y):
            x_del_cruce = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < x_del_cruce:
                dentro = not dentro
        anterior = actual
    return dentro


def dibujar_zona(frame , zona: list):
    """ Devuelve una copia de la imagen con la zona pintada en rojo transparente"""
    if not zona:
        return frame

    alto, ancho = frame.shape[:2]
    puntos = np.array(
        [[init(x *ancho), init(y*alto)]for x, y in zona], dtype=np.init32
    
    )

    capa = frame.copy()
    cv2.pillPoly(capa, [puntos], COLOR_ZONA)
    imagen = cv2.addWeighted(capa, 0.25,frame, 0.75, 0)
    cv2.polylines(imagen, [puntos], True, COLOR_ZONA, max(2,ancho //400))
    return imagen

def separar_personas(personas: list, zona: list, ancho: int, alto: int):
    """
    Separa las personas en dos listas: (dentro_de_la_zona, fuera_de_la_zona).

    Para decidir si una persona esta dentro se usa el punto donde pisa el
    suelo (el centro de la base de su cuadro), porque la zona representa un
    pedazo de piso. Si se usara el centro del cuerpo, alguien parado afuera
    pero cerca de la linea podria contarse como adentro.
    """
    poligono = [(x * ancho, y * alto) for x, y in zona]
    dentro, fuera = [], []
    for persona in personas:
        x1, y1, x2, y2, _seguridad = persona
        pies_x = (x1 + x2) / 2
        pies_y = y2
        if punto_en_zona(pies_x, pies_y, poligono):
            dentro.append(persona)
        else:
            fuera.append(persona)
    return dentro, fuera