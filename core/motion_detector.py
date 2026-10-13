"""
Detector de movimiento.

Funciona asi: el programa aprende como se ve la escena "en reposo" y,
en cada imagen nueva, marca lo que cambio. Si lo que cambio es lo
bastante grande, lo considera movimiento.
"""
import cv2


class MotionDetector:
    ANCHO_ANALISIS = 640  # las imagenes mas anchas se achican para trabajar mas rapido

    def __init__(self, area_minima: int = 1500, frames_calentamiento: int = 30):
        """
        area_minima: que tan grande debe ser lo que se mueve para contarlo.
            Un numero mas alto ignora cosas pequenas (insectos, sombras).
        frames_calentamiento: al empezar, el programa necesita unas imagenes
            para aprender la escena. Durante ese tiempo no avisa nada.
        """
        self.area_minima = area_minima
        self.frames_calentamiento = frames_calentamiento
        self._frames_vistos = 0

        self._sustractor = cv2.createBackgroundSubtractorMOG2(
            history=300, varThreshold=32, detectShadows=False
        )
        self._kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    def detectar(self, frame) -> bool:
        alto, ancho = frame.shape[:2]
        if ancho > self.ANCHO_ANALISIS:
            escala = self.ANCHO_ANALISIS / ancho
            frame = cv2.resize(
                frame,
                (self.ANCHO_ANALISIS, int(alto * escala)),
                interpolation=cv2.INTER_AREA,
            )

        # Se difumina un poco la imagen para que el ruido de la camara
        # no se confunda con movimiento.
        suavizado = cv2.GaussianBlur(frame, (5, 5), 0)

        # La mascara queda en blanco donde algo cambio respecto a la escena.
        mascara = self._sustractor.apply(suavizado)

        self._frames_vistos += 1
        if self._frames_vistos <= self.frames_calentamiento:
            return False

        # Se borran los puntitos sueltos y se unen las manchas cercanas,
        # para que un objeto cuente como una sola mancha.
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, self._kernel)
        mascara = cv2.dilate(mascara, self._kernel, iterations=2)

        contornos, _ = cv2.findContours(
            mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        return any(cv2.contourArea(c) >= self.area_minima for c in contornos)
