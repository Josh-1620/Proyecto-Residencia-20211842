"""
CameraWidget: el recuadro que muestra UNA camara en la ventana.

No sabe como se conecta la camara ni como se analiza el video. Solo
MUESTRA lo que le llega (imagen, si esta conectada, si hay movimiento,
si hay personas, si esta grabando) y AVISA cuando se presiona el boton Grabar.
La ventana principal es quien conecta este recuadro con su camara.
"""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
)


class CameraWidget(QFrame):
    # Aviso que se manda cuando el usuario presiona o suelta el boton Grabar
    grabacion_solicitada = pyqtSignal(bool)

    def __init__(self, camara: dict, parent=None):
        super().__init__(parent)
        self.camara = camara

        self.setObjectName("CameraWidget")
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumSize(320, 220)

        self._construir_ui()
        self._mostrar_placeholder("Conectando...")

    # ---------- Armado de la pantalla ----------
    def _construir_ui(self):
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(6, 6, 6, 6)
        layout_principal.setSpacing(4)

        # --- Parte de arriba: nombre y avisos ---
        encabezado = QHBoxLayout()

        self.lbl_nombre = QLabel(self.camara.get("nombre", "Cámara"))
        self.lbl_nombre.setObjectName("NombreCamara")

        self.lbl_indicador_rec = QLabel("● REC")
        self.lbl_indicador_rec.setObjectName("IndicadorRec")
        self.lbl_indicador_rec.setVisible(False)

        self.lbl_indicador_movimiento = QLabel("⚠ Movimiento")
        self.lbl_indicador_movimiento.setObjectName("IndicadorMovimiento")
        self.lbl_indicador_movimiento.setVisible(False)

        self.lbl_indicador_personas = QLabel("Personas: 0")
        self.lbl_indicador_personas.setObjectName("IndicadorPersonas")
        self.lbl_indicador_personas.setVisible(False)

        encabezado.addWidget(self.lbl_nombre)
        encabezado.addStretch()
        encabezado.addWidget(self.lbl_indicador_personas)
        encabezado.addWidget(self.lbl_indicador_movimiento)
        encabezado.addWidget(self.lbl_indicador_rec)

        # --- Zona del video ---
        self.lbl_video = QLabel()
        self.lbl_video.setObjectName("VideoFeed")
        self.lbl_video.setAlignment(Qt.AlignCenter)
        # "Ignored" hace que el tamano de la zona no dependa de la imagen.
        # Sin esto, una imagen grande no deja achicar la ventana.
        self.lbl_video.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.lbl_video.setMinimumSize(280, 160)

        # --- Parte de abajo: estado y boton ---
        pie = QHBoxLayout()
        self.btn_grabar = QPushButton("Grabar")
        self.btn_grabar.setCheckable(True)
        self.btn_grabar.clicked.connect(self._alternar_grabacion)

        self.lbl_estado = QLabel("Desconectada")
        self.lbl_estado.setObjectName("EstadoConexion")

        pie.addWidget(self.lbl_estado)
        pie.addStretch()
        pie.addWidget(self.btn_grabar)

        layout_principal.addLayout(encabezado)
        layout_principal.addWidget(self.lbl_video, stretch=1)
        layout_principal.addLayout(pie)

    def _mostrar_placeholder(self, texto: str):
        self.lbl_video.clear()
        self.lbl_video.setStyleSheet(
            "background-color: #1b1e23; color: #666; border-radius: 4px;"
        )
        self.lbl_video.setText(texto)

    # ---------- Lo que la camara le va avisando a este recuadro ----------
    def actualizar_frame(self, imagen_qt: QImage):
        """Recibe una imagen nueva y la muestra ajustada al tamano del recuadro."""
        pixmap = QPixmap.fromImage(imagen_qt).scaled(
            self.lbl_video.size(),
            Qt.KeepAspectRatio,
            Qt.FastTransformation,
        )
        self.lbl_video.setPixmap(pixmap)

    def marcar_conectada(self, conectada: bool):
        self.lbl_estado.setText("Conectada" if conectada else "Desconectada")
        if not conectada:
            self._mostrar_placeholder("Sin señal\nReintentando conexión...")
            self.marcar_movimiento(False)
            self.marcar_personas(0)

    def marcar_movimiento(self, detectado: bool):
        self.lbl_indicador_movimiento.setVisible(detectado)

    def marcar_personas(self, cantidad: int):
        """Muestra cuantas personas se ven (y se oculta si no hay ninguna)."""
        self.lbl_indicador_personas.setText(f"Personas: {cantidad}")
        self.lbl_indicador_personas.setVisible(cantidad > 0)

    def marcar_grabando(self, grabando: bool):
        """Muestra REC cuando realmente se esta grabando (con el boton o solo)."""
        self.lbl_indicador_rec.setVisible(grabando)

    # ---------- Lo que hace el usuario ----------
    def _alternar_grabacion(self, activo: bool):
        self.btn_grabar.setText("Detener" if activo else "Grabar")
        self.grabacion_solicitada.emit(activo)
