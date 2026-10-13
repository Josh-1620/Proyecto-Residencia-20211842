"""
MainWindow: la ventana principal, dividida en pestanas.
  - "Monitoreo en vivo": las camaras en cuadricula.
  - "Grabaciones": para buscar y ver los videos guardados.

Aqui es donde se CONECTA cada camara con su recuadro en pantalla:
lo que la camara avisa (imagen, movimiento, personas, grabacion)
llega directo al recuadro que le corresponde.
"""
import math

from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QGridLayout,
    QTabWidget,
    QToolBar,
    QAction,
    QStatusBar,
    QLabel,
)

from core.auth import tiene_permiso
from core.camera_stream import CameraStream
from ui.camera_widget import CameraWidget
from ui.recordings_tab import RecordingsTab
from utils.config_loader import cargar_camaras


class MainWindow(QMainWindow):
    def __init__(self, usuario_actual: dict):
        super().__init__()
        self.usuario_actual = usuario_actual
        self.widgets_camaras = {}
        self.streams = {}
        self._conectadas = set()

        self.setWindowTitle("Sistema de Monitoreo IP")
        self.resize(1280, 840)

        self._construir_toolbar()
        self._construir_pestanas()
        self._construir_status_bar()
        self._iniciar_streams()

    # ---------- Barra de botones de arriba ----------
    def _construir_toolbar(self):
        toolbar = QToolBar("Principal")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        permite_gestion = tiene_permiso(self.usuario_actual, "gestionar_camaras")

        self.accion_agregar = QAction("+ Agregar cámara", self)
        self.accion_agregar.triggered.connect(self._agregar_camara)
        self.accion_agregar.setEnabled(permite_gestion)

        self.accion_configuracion = QAction("Configuración", self)
        self.accion_configuracion.triggered.connect(self._abrir_configuracion)
        self.accion_configuracion.setEnabled(permite_gestion)

        toolbar.addAction(self.accion_agregar)
        toolbar.addAction(self.accion_configuracion)

    # ---------- Pestanas ----------
    def _construir_pestanas(self):
        self.pestanas = QTabWidget()
        self.setCentralWidget(self.pestanas)

        self.tab_grabaciones = RecordingsTab(self.usuario_actual)
        self.pestanas.addTab(self._construir_tab_monitoreo(), "Monitoreo en vivo")
        self.pestanas.addTab(self.tab_grabaciones, "Grabaciones")

        # Al entrar a "Grabaciones" se actualiza la lista, por si hay videos nuevos
        self.pestanas.currentChanged.connect(self._al_cambiar_pestana)

    def _construir_tab_monitoreo(self) -> QWidget:
        contenedor = QWidget()
        layout_grid = QGridLayout(contenedor)
        layout_grid.setSpacing(8)

        camaras = cargar_camaras()
        columnas = max(1, math.ceil(math.sqrt(len(camaras)))) if camaras else 1

        for indice, camara in enumerate(camaras):
            widget = CameraWidget(camara)
            fila, col = divmod(indice, columnas)
            layout_grid.addWidget(widget, fila, col)
            self.widgets_camaras[camara["id"]] = widget

        return contenedor

    # ---------- Barra de abajo ----------
    def _construir_status_bar(self):
        barra = QStatusBar()
        self.setStatusBar(barra)

        self.lbl_resumen = QLabel()
        lbl_usuario = QLabel(
            f"Sesión: {self.usuario_actual['nombre']} ({self.usuario_actual['rol']})"
        )
        lbl_usuario.setStyleSheet("color: #7fb3ff;")

        barra.addWidget(self.lbl_resumen)
        barra.addPermanentWidget(lbl_usuario)
        self._actualizar_resumen()

    def _actualizar_resumen(self):
        total = len(self.widgets_camaras)
        self.lbl_resumen.setText(f"{len(self._conectadas)} de {total} cámara(s) conectada(s)")

    # ---------- Conexion entre cada camara y su recuadro ----------
    def _iniciar_streams(self):
        for camara in cargar_camaras():
            id_camara = camara["id"]
            widget = self.widgets_camaras[id_camara]
            stream = CameraStream(camara, parent=self)

            # De la camara hacia el recuadro
            stream.frame_listo.connect(widget.actualizar_frame)
            stream.conexion_cambiada.connect(widget.marcar_conectada)
            stream.movimiento_cambiado.connect(widget.marcar_movimiento)
            stream.personas_cambiadas.connect(widget.marcar_personas)
            stream.grabando_cambiado.connect(widget.marcar_grabando)
            # El "i=id_camara" es necesario: sin el, todas las camaras
            # usarian el id de la ultima de la lista.
            stream.conexion_cambiada.connect(
                lambda ok, i=id_camara: self._registrar_conexion(i, ok)
            )

            # Del boton Grabar del recuadro hacia la camara
            widget.grabacion_solicitada.connect(stream.establecer_grabacion_manual)

            self.streams[id_camara] = stream

        for stream in self.streams.values():
            stream.start()

    def _registrar_conexion(self, id_camara: str, conectada: bool):
        if conectada:
            self._conectadas.add(id_camara)
        else:
            self._conectadas.discard(id_camara)
        self._actualizar_resumen()

    def _al_cambiar_pestana(self, indice: int):
        if self.pestanas.widget(indice) is self.tab_grabaciones:
            self.tab_grabaciones.buscar_grabaciones()

    # ---------- Al cerrar la ventana ----------
    def closeEvent(self, evento):
        # Primero se les avisa a todas las camaras que paren y despues se
        # espera a cada una. Asi cierran todas a la vez y no una por una.
        for stream in self.streams.values():
            stream.solicitar_detencion()
        for stream in self.streams.values():
            stream.detener()
        super().closeEvent(evento)

    # ---------- Botones que todavia no hacen nada ----------
    def _agregar_camara(self):
        self.statusBar().showMessage("Abrir diálogo para agregar cámara...", 3000)

    def _abrir_configuracion(self):
        self.statusBar().showMessage("Abrir configuración general...", 3000)
