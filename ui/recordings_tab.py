"""
RecordingsTab: la pestana para buscar y ver los videos grabados.

Espera encontrar los videos guardados asi (de eso se encarga recorder.py):

    storage/grabaciones/<id_camara>/<AAAA-MM-DD>/<HHMMSS>.mp4

Esta pestana solo LEE esas carpetas para mostrar la lista, filtrarla y
reproducir el video elegido.
"""
import os

from PyQt5.QtCore import Qt, QDate, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QDateEdit,
    QCheckBox,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QSlider,
    QSplitter,
    QMessageBox,
)

from core.auth import tiene_permiso
from utils.config_loader import cargar_camaras

RUTA_GRABACIONES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "storage",
    "grabaciones",
)


class RecordingsTab(QWidget):
    def __init__(self, usuario_actual: dict, parent=None):
        super().__init__(parent)
        self.usuario_actual = usuario_actual
        self.reproductor = QMediaPlayer(None, QMediaPlayer.VideoSurface)

        self._construir_ui()
        self._poblar_filtro_camaras()
        self.buscar_grabaciones()

    # ---------- Armado de la pantalla ----------
    def _construir_ui(self):
        layout_principal = QVBoxLayout(self)

        # --- Barra de filtros ---
        barra_filtros = QHBoxLayout()

        barra_filtros.addWidget(QLabel("Cámara:"))
        self.combo_camara = QComboBox()
        self.combo_camara.currentIndexChanged.connect(self.buscar_grabaciones)
        barra_filtros.addWidget(self.combo_camara)

        self.chk_filtrar_fecha = QCheckBox("Filtrar por fecha")
        self.chk_filtrar_fecha.toggled.connect(self.buscar_grabaciones)
        barra_filtros.addWidget(self.chk_filtrar_fecha)

        self.fecha_filtro = QDateEdit(calendarPopup=True)
        self.fecha_filtro.setDate(QDate.currentDate())
        self.fecha_filtro.dateChanged.connect(self.buscar_grabaciones)
        barra_filtros.addWidget(self.fecha_filtro)

        boton_actualizar = QPushButton("Actualizar")
        boton_actualizar.clicked.connect(self.buscar_grabaciones)
        barra_filtros.addWidget(boton_actualizar)

        barra_filtros.addStretch()

        boton_eliminar = QPushButton("Eliminar seleccionado")
        boton_eliminar.clicked.connect(self._eliminar_seleccionado)
        # Solo los administradores pueden borrar grabaciones
        boton_eliminar.setEnabled(tiene_permiso(self.usuario_actual, "eliminar_grabaciones"))
        barra_filtros.addWidget(boton_eliminar)
        self.boton_eliminar = boton_eliminar

        layout_principal.addLayout(barra_filtros)

        # --- Zona dividida: lista a la izquierda, reproductor a la derecha ---
        divisor = QSplitter(Qt.Horizontal)

        self.lista_resultados = QListWidget()
        self.lista_resultados.itemClicked.connect(self._reproducir_seleccionado)
        divisor.addWidget(self.lista_resultados)

        panel_reproductor = QWidget()
        layout_reproductor = QVBoxLayout(panel_reproductor)

        self.video_widget = QVideoWidget()
        self.reproductor.setVideoOutput(self.video_widget)
        layout_reproductor.addWidget(self.video_widget)

        controles = QHBoxLayout()
        self.boton_play_pausa = QPushButton("▶ Reproducir")
        self.boton_play_pausa.clicked.connect(self._alternar_reproduccion)
        self.slider_posicion = QSlider(Qt.Horizontal)
        self.slider_posicion.sliderMoved.connect(self.reproductor.setPosition)

        controles.addWidget(self.boton_play_pausa)
        controles.addWidget(self.slider_posicion)
        layout_reproductor.addLayout(controles)

        # La barra de avance se mueve sola mientras el video se reproduce
        self.reproductor.positionChanged.connect(self.slider_posicion.setValue)
        self.reproductor.durationChanged.connect(self.slider_posicion.setMaximum)

        divisor.addWidget(panel_reproductor)
        divisor.setSizes([320, 680])

        layout_principal.addWidget(divisor)

    # ---------- Filtros ----------
    def _poblar_filtro_camaras(self):
        self.combo_camara.blockSignals(True)
        self.combo_camara.addItem("Todas las cámaras", userData=None)
        for camara in cargar_camaras():
            self.combo_camara.addItem(camara["nombre"], userData=camara["id"])
        self.combo_camara.blockSignals(False)

    # ---------- Busqueda de videos ----------
    def buscar_grabaciones(self):
        self.lista_resultados.clear()

        id_camara_filtro = self.combo_camara.currentData()
        fecha_filtro = (
            self.fecha_filtro.date().toString("yyyy-MM-dd")
            if self.chk_filtrar_fecha.isChecked()
            else None
        )

        if not os.path.isdir(RUTA_GRABACIONES):
            return

        # Se recorren las carpetas: camara -> fecha -> videos
        for id_camara in os.listdir(RUTA_GRABACIONES):
            if id_camara_filtro and id_camara != id_camara_filtro:
                continue

            ruta_camara = os.path.join(RUTA_GRABACIONES, id_camara)
            if not os.path.isdir(ruta_camara):
                continue

            for carpeta_fecha in os.listdir(ruta_camara):
                if fecha_filtro and carpeta_fecha != fecha_filtro:
                    continue

                ruta_fecha = os.path.join(ruta_camara, carpeta_fecha)
                if not os.path.isdir(ruta_fecha):
                    continue

                for archivo in sorted(os.listdir(ruta_fecha)):
                    if not archivo.lower().endswith((".mp4", ".avi")):
                        continue
                    ruta_completa = os.path.join(ruta_fecha, archivo)
                    etiqueta = f"{id_camara}  |  {carpeta_fecha}  |  {archivo}"
                    item = QListWidgetItem(etiqueta)
                    # Se guarda la ruta "escondida" en el elemento para
                    # usarla despues cuando el usuario haga clic.
                    item.setData(Qt.UserRole, ruta_completa)
                    self.lista_resultados.addItem(item)

        if self.lista_resultados.count() == 0:
            item = QListWidgetItem("No se encontraron grabaciones con este filtro.")
            item.setFlags(Qt.NoItemFlags)  # no se puede seleccionar
            self.lista_resultados.addItem(item)

    # ---------- Reproduccion ----------
    def _reproducir_seleccionado(self, item: QListWidgetItem):
        ruta_video = item.data(Qt.UserRole)
        if not ruta_video:
            return
        self.reproductor.setMedia(QMediaContent(QUrl.fromLocalFile(ruta_video)))
        self.reproductor.play()
        self.boton_play_pausa.setText("⏸ Pausar")

    def _alternar_reproduccion(self):
        if self.reproductor.state() == QMediaPlayer.PlayingState:
            self.reproductor.pause()
            self.boton_play_pausa.setText("▶ Reproducir")
        else:
            self.reproductor.play()
            self.boton_play_pausa.setText("⏸ Pausar")

    # ---------- Eliminar ----------
    def _eliminar_seleccionado(self):
        item = self.lista_resultados.currentItem()
        ruta_video = item.data(Qt.UserRole) if item else None
        if not ruta_video:
            QMessageBox.information(self, "Eliminar", "Selecciona primero una grabación.")
            return

        confirmacion = QMessageBox.question(
            self,
            "Confirmar",
            f"¿Eliminar el archivo:\n{os.path.basename(ruta_video)}?",
        )
        if confirmacion == QMessageBox.Yes:
            self.reproductor.stop()
            os.remove(ruta_video)
            self.buscar_grabaciones()
