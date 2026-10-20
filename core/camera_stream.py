"""
CameraStream: se encarga de UNA camara.

Cada camara trabaja por su cuenta, en su propio "carril", para que si una
se traba las demas (y la ventana) sigan funcionando. En cada carril se hace:
    conectar -> leer imagenes -> buscar movimiento y personas -> grabar
y se le va avisando a la ventana lo que pasa (mediante "senales").
"""
import os
import time

import cv2
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage

from core.capturas import guardar_captura
from core.motion_detector import MotionDetector
from core.person_detector import (
    COLOR_AMARILLO,
    COLOR_ROJO,
    COLOR_VERDE,
    HiloDeteccion,
    detector_listo,
    dibujar_personas,
    iniciar_carga_ia,
)
from core.recorder import Recorder
from core.zona import dibujar_zona, separar_personas, validar_zona
from utils.config_loader import obtener_fuente
from utils.logger import obtener_logger

log = obtener_logger("camera_stream")


class CameraStream(QThread):
    # Avisos que esta camara le manda a la ventana
    frame_listo = pyqtSignal(QImage)        # llego una imagen nueva
    conexion_cambiada = pyqtSignal(bool)    # se conecto o se desconecto
    movimiento_cambiado = pyqtSignal(bool)  # empezo o termino un movimiento
    personas_cambiadas = pyqtSignal(int)    # cuantas personas se ven ahora
    grabando_cambiado = pyqtSignal(bool)    # empezo o termino una grabacion

    SEGUNDOS_ENTRE_REINTENTOS = 3
    SEGUNDOS_POST_EVENTO = 10             # sigue grabando 10 s despues del ultimo evento
    SEGUNDOS_INDICADOR_MOVIMIENTO = 2     # el aviso de movimiento dura 2 s
    SEGUNDOS_ENTRE_ANALISIS_IA = 0.3      # cada cuanto se le manda una imagen a la IA
    SEGUNDOS_RESULTADO_VALIDO = 3         # si la IA no responde en 3 s, se ignora su ultimo resultado
    SEGUNDOS_ENTRE_CAPTURAS = 10          # como maximo una foto cada 10 s por camara
    FPS_PANTALLA = 20                     # imagenes por segundo que se muestran en pantalla
    ANCHO_MAXIMO_PANTALLA = 960
    FALLOS_MAXIMOS_LECTURA = 30           # lecturas fallidas seguidas antes de reconectar

    def __init__(self, camara: dict, parent=None):
        super().__init__(parent)
        self.camara = camara
        self.id_camara = camara["id"]
        self.nombre = camara.get("nombre", self.id_camara)

        self._fuente = obtener_fuente(camara)
        self._es_archivo = isinstance(self._fuente, str) and os.path.isfile(self._fuente)

        self._grabacion_automatica = camara.get("grabacion_automatica", False)
        self._usar_personas = camara.get("deteccion_personas", False)

        # Si se detectan personas, ellas son quienes activan la grabacion
        # automatica. Si no, la activa cualquier movimiento.
        self._usar_movimiento = camara.get("deteccion_movimiento", False) or (
            self._grabacion_automatica and not self._usar_personas
        )

        self._ejecutando = True
        self._grabar_manual = False
        self._hilo_ia = None

    # ---------- Cosas que la ventana puede pedirle a la camara ----------
    def establecer_grabacion_manual(self, activo: bool) -> None:
        self._grabar_manual = activo

    def establecer_zona(self, puntos) -> None:
        """Cambia la zona mientras la camara sigue funcionando (lista vacia = sin Zona)"""
        self._zona = validar_zona(puntos)

    def solicitar_detencion(self) -> None:
        self._ejecutando = False

    def detener(self) -> None:
        self._ejecutando = False
        self.wait(8000)  # espera a que termine (como maximo 8 segundos)

    # ---------- Trabajo principal ----------
    def run(self):
        if self._usar_personas:
            iniciar_carga_ia() # empieza a cargar el modelo, pero no se espera
        try:
            while self._ejecutando:
                captura = self._abrir_captura()
                if captura is None:
                    log.warning("[%s] No se pudo conectar. Reintentando...", self.nombre)
                    self.conexion_cambiada.emit(False)
                    self._esperar(self.SEGUNDOS_ENTRE_REINTENTOS)
                    continue

                log.info("[%s] Conectada", self.nombre)
                self.conexion_cambiada.emit(True)
                try:
                    self._procesar(captura)
                finally:
                    captura.release()
                self.conexion_cambiada.emit(False)

                if self._ejecutando:
                    log.warning("[%s] Conexion perdida. Reintentando...", self.nombre)
                    self._esperar(self.SEGUNDOS_ENTRE_REINTENTOS)
        finally:
            if self._hilo_ia is not None:
                self._hilo_ia.detener()

    def _revisar_ia(self):
        """
        Mira si el modelo de personas ya termino de cargar. Mientras carga, la
        camara sigue mostrando video normal; cuando esta listo, empieza a analizar.
        """

        detector, error = detector_listo()
        if detector is not None:
            self._hilo_ia = HiloDeteccion(detector, self.nombre)
            self._hilo_ia.start()
            log.info("[%s] Deteccion de personas activa", self.nombre)
        elif error is not None:
            # Si falla, la camara sigue funcionando, solo que sin detectar personas.
            # La grabacion automatica pasa a usar el movimiento en su lugar.
            log.error(
                "[%s] No se pudo activar la deteccion de personas: %s",
                self.nombre, error,
            )
            self._usar_personas = False
            if self._grabacion_automatica:
                self._usar_movimiento = True
                log.warning("[%s] Se usara el movimiento para grabar", self.nombre)



    def _abrir_captura(self):
        try:
            if isinstance(self._fuente, str):
                # Se limita la espera a 5 segundos. Sin esto, una camara
                # apagada puede dejar la aplicacion esperando mucho tiempo.
                captura = cv2.VideoCapture(
                    self._fuente, cv2.CAP_FFMPEG,
                    [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000,
                     cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000],
                )
            else:
                captura = cv2.VideoCapture(self._fuente)  # webcam (numero)
        except (TypeError, cv2.error):
            captura = cv2.VideoCapture(self._fuente)  # version vieja de OpenCV

        if not captura.isOpened():
            captura.release()
            return None

        captura.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # para que el video no se atrase
        return captura

    def _procesar(self, captura):
        fps = captura.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 0 or fps > 120:
            fps = 15.0  # muchas camaras no informan sus FPS, se usa un valor normal

        grabador = Recorder(self.id_camara, fps)
        detector_movimiento = MotionDetector() if self._usar_movimiento else None

        intervalo_pantalla = 1.0 / self.FPS_PANTALLA
        # Un archivo de video se lee muy rapido; se frena para que se vea a
        # velocidad normal, como si fuera una camara de verdad.
        intervalo_archivo = (1.0 / fps) if self._es_archivo else 0.0

        fallos = 0
        ultimo_envio_pantalla = 0.0
        ultimo_envio_ia = 0.0
        ultima_captura = 0.0
        ultimo_movimiento = None
        ultima_persona = None
        indicador_movimiento = False
        personas_actuales = 0

        try:
            while self._ejecutando:
                inicio_ciclo = time.monotonic()
                ok, frame = captura.read()

                if not ok:
                    fallos += 1
                    if self._es_archivo or fallos >= self.FALLOS_MAXIMOS_LECTURA:
                        break  # se acabo el video o la camara se cayo: reconectar
                    self.msleep(50)
                    continue
                fallos = 0

                ahora = time.monotonic()

                # --- Movimiento ---
                if detector_movimiento is not None:
                    if detector_movimiento.detectar(frame):
                        ultimo_movimiento = ahora

                    mostrar = (
                        ultimo_movimiento is not None
                        and ahora - ultimo_movimiento < self.SEGUNDOS_INDICADOR_MOVIMIENTO
                    )
                    if mostrar != indicador_movimiento:
                        indicador_movimiento = mostrar
                        self.movimiento_cambiado.emit(mostrar)
                        if mostrar:
                            log.info("[%s] Movimiento detectado", self.nombre)

                # --- Personas (con YOLOv8) ---
                personas = []
                if self._hilo_ia is not None:
                    # Cada cierto tiempo se le manda una imagen a la IA...
                    if ahora - ultimo_envio_ia >= self.SEGUNDOS_ENTRE_ANALISIS_IA:
                        ultimo_envio_ia = ahora
                        self._hilo_ia.enviar(frame)

                    # ...y se usa lo ultimo que haya respondido.
                    personas, momento = self._hilo_ia.ultimo_resultado()
                    if ahora - momento > self.SEGUNDOS_RESULTADO_VALIDO:
                        personas = []

                    if len(personas) > 0:
                        ultima_persona = ahora

                    if len(personas) != personas_actuales:
                        # Si antes no habia nadie y ahora si, se avisa y se toma una foto
                        if personas_actuales == 0:
                            log.info("[%s] Persona detectada", self.nombre)
                            if ahora - ultima_captura >= self.SEGUNDOS_ENTRE_CAPTURAS:
                                ultima_captura = ahora
                                guardar_captura(dibujar_personas(frame, personas), self.id_camara)
                        personas_actuales = len(personas)
                        self.personas_cambiadas.emit(personas_actuales)

                # --- Grabacion (con el boton o automatica) ---
                evento = ultima_persona if self._usar_personas else ultimo_movimiento
                evento_reciente = (
                    evento is not None and ahora - evento < self.SEGUNDOS_POST_EVENTO
                )
                debe_grabar = self._grabar_manual or (
                    self._grabacion_automatica and evento_reciente
                )

                if debe_grabar and not grabador.activo:
                    if grabador.iniciar(frame):
                        self.grabando_cambiado.emit(True)
                elif not debe_grabar and grabador.activo:
                    grabador.detener()
                    self.grabando_cambiado.emit(False)

                if grabador.activo:
                    grabador.escribir(frame)  # el video se guarda limpio, sin cuadros

                # --- Mandar la imagen a la pantalla (con los cuadros de personas) ---
                if ahora - ultimo_envio_pantalla >= intervalo_pantalla:
                    ultimo_envio_pantalla = ahora
                    self.frame_listo.emit(self._a_qimage(frame, personas))

                if intervalo_archivo:
                    restante = intervalo_archivo - (time.monotonic() - inicio_ciclo)
                    if restante > 0:
                        self.msleep(int(restante * 1000))
        finally:
            # Al terminar, se cierra todo lo que haya quedado abierto
            if grabador.activo:
                grabador.detener()
                self.grabando_cambiado.emit(False)
            if indicador_movimiento:
                self.movimiento_cambiado.emit(False)
            if personas_actuales > 0:
                self.personas_cambiadas.emit(0)

    # ---------- Ayudas ----------
    def _esperar(self, segundos: float) -> None:
        """Espera en pausas cortas, para poder cancelar rapido al cerrar la aplicacion."""
        fin = time.monotonic() + segundos
        while self._ejecutando and time.monotonic() < fin:
            self.msleep(100)

    def _a_qimage(self, frame, personas) -> QImage:
        """Convierte la imagen de OpenCV a una imagen que la ventana pueda mostrar."""
        frame = dibujar_personas(frame, personas)

        alto, ancho = frame.shape[:2]
        if ancho > self.ANCHO_MAXIMO_PANTALLA:
            escala = self.ANCHO_MAXIMO_PANTALLA / ancho
            frame = cv2.resize(
                frame,
                (self.ANCHO_MAXIMO_PANTALLA, int(alto * escala)),
                interpolation=cv2.INTER_AREA,
            )
        # OpenCV maneja los colores como azul-verde-rojo y la ventana como
        # rojo-verde-azul, por eso hay que invertirlos.
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        alto, ancho, canales = rgb.shape
        imagen = QImage(rgb.data, ancho, alto, canales * ancho, QImage.Format_RGB888)
        return imagen.copy()  # se hace una copia porque 'rgb' desaparece al salir de aqui
