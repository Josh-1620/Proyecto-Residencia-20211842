"""
CameraWidget: el recuadro que muestra UNA camara en la ventana.

No sabe como se conecta la camara ni como se analiza el video. Solo
MUESTRA lo que le llega (imagen, si esta conectada, si hay movimiento,
si hay personas, si esta grabando) y AVISA cuando se presiona el boton Grabar.
La ventana principal es quien conecta este recuadro con su camara.
"""
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import QColor, QImage, QPainter, QPen, QPixmap, QPolygonF
from PyQt5.QtWidgets import (
    QFrame,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QWidget,
)

from core.zona import validar_zona

COLOR_ZONA = QColor(255, 77, 77)       # rojo: zona ya guardada
COLOR_EDICION = QColor(79, 209, 197)   # turquesa: zona que se esta dibujando


class EtiquetaVideo(QLabel):
    """
    La zona donde se ve el video. Ademas de mostrar la imagen:
      - pinta la zona de vigilancia encima del video
      - cuando se esta dibujando una zona, avisa en que parte del video
        se hizo clic (con numeros de 0 a 1, no en pixeles)
    """
    punto_agregado = pyqtSignal(float, float)  # clic izquierdo: x, y entre 0 y 1
    punto_quitado = pyqtSignal()               # clic derecho: deshacer el ultimo punto

    def __init__(self, parent=None):
        super().__init__(parent)
        self.zona = []             # zona guardada
        self.puntos_edicion = []   # zona que se esta dibujando ahora
        self.editando = False

    def hay_imagen(self) -> bool:
        pixmap = self.pixmap()
        return pixmap is not None and not pixmap.isNull()

    def rect_imagen(self):
        """
        Devuelve el rectangulo que ocupa la imagen dentro de la etiqueta.
        La imagen se centra y deja franjas negras a los lados (o arriba y
        abajo) cuando su forma no coincide con la de la etiqueta; los clics
        en esas franjas no cuentan, y la zona se mide solo sobre la imagen.
        """
        pixmap = self.pixmap()
        if pixmap is None or pixmap.isNull():
            return None
        caja = self.contentsRect()
        x = caja.x() + (caja.width() - pixmap.width()) / 2
        y = caja.y() + (caja.height() - pixmap.height()) / 2
        return QRectF(x, y, pixmap.width(), pixmap.height())

    def mousePressEvent(self, evento):
        if not self.editando:
            super().mousePressEvent(evento)
            return

        if evento.button() == Qt.RightButton:
            self.punto_quitado.emit()
            return

        if evento.button() == Qt.LeftButton:
            rect = self.rect_imagen()
            if rect is None:
                return
            posicion = QPointF(evento.pos())
            if not rect.contains(posicion):
                return  # clic en la franja negra: se ignora
            self.punto_agregado.emit(
                (posicion.x() - rect.x()) / rect.width(),
                (posicion.y() - rect.y()) / rect.height(),
            )

    def paintEvent(self, evento):
        super().paintEvent(evento)  # primero se pinta la imagen normal

        rect = self.rect_imagen()
        puntos = self.puntos_edicion if self.editando else self.zona
        if rect is None or not puntos:
            return

        color = COLOR_EDICION if self.editando else COLOR_ZONA
        en_pantalla = [
            QPointF(rect.x() + px * rect.width(), rect.y() + py * rect.height())
            for px, py in puntos
        ]

        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)

        if len(en_pantalla) >= 3:
            relleno = QColor(color)
            relleno.setAlpha(55)  # transparente, para ver el video debajo
            pintor.setBrush(relleno)
            pintor.setPen(QPen(color, 2))
            pintor.drawPolygon(QPolygonF(en_pantalla))
        elif len(en_pantalla) == 2:
            pintor.setPen(QPen(color, 2))
            pintor.drawLine(en_pantalla[0], en_pantalla[1])

        if self.editando:
            # Un circulo en cada esquina, para ver donde se hizo clic
            pintor.setPen(QPen(color, 2))
            pintor.setBrush(color)
            for punto in en_pantalla:
                pintor.drawEllipse(punto, 4, 4)

        pintor.end()


class CameraWidget(QFrame):
    # Aviso que se manda cuando el usuario presiona o suelta el boton Grabar
    grabacion_solicitada = pyqtSignal(bool)
     # Aviso con la zona nueva (lista de puntos). Si la lista esta vacia, se borro la zona.
    zona_guardada = pyqtSignal(list)

    def __init__(self, camara: dict, parent=None):
        super().__init__(parent)
        self.camara = camara
        self._zona = []
        self._cantidad_personas = 0
        self._edicion_permitida = False

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


        # --- Barra para dibujar la zona (solo se ve mientras se dibuja) ---
        self.barra_edicion = QWidget()
        self.barra_edicion.setObjectName("BarraEdicion")
        layout_edicion = QVBoxLayout(self.barra_edicion)
        layout_edicion.setContentsMargins(0, 0, 0, 0)
        layout_edicion.setSpacing(2)

        self.lbl_ayuda_zona = QLabel(
            "Haz clic en el video para marcar las esquinas de la zona. "
            "Clic derecho: quitar el último punto."
        )
        self.lbl_ayuda_zona.setObjectName("AyudaZona")
        self.lbl_ayuda_zona.setWordWrap(True)

        fila_botones = QHBoxLayout()
        self.btn_guardar_zona = QPushButton("Guardar zona")
        self.btn_guardar_zona.clicked.connect(self._guardar_edicion)
        self.btn_cancelar_zona = QPushButton("Cancelar")
        self.btn_cancelar_zona.clicked.connect(self._cancelar_edicion)
        fila_botones.addStretch()
        fila_botones.addWidget(self.btn_guardar_zona)
        fila_botones.addWidget(self.btn_cancelar_zona)

        layout_edicion.addWidget(self.lbl_ayuda_zona)
        layout_edicion.addLayout(fila_botones)
        self.barra_edicion.setVisible(False)

        # --- Parte de abajo: estado y boton ---
        pie = QHBoxLayout()

        self.lbl_estado = QLabel("Desconectada")
        self.lbl_estado.setObjectName("EstadoConexion")

        self.btn_zona = QPushButton("zona")
        menu_zona = QMenu(self.btn_zona)
        self.accion_dibujar_zona = menu_zona.addAction("Dibujar zona nueva")
        self.accion_dibujar_zona.triggered.connect(self._iniciar_edicion)
        self.accion_borrar_zona = menu_zona.addAction("Borrar zona")
        self.accion_borrar_zona.triggered.connect(self._borrar_zona)
        menu_zona.aboutToShow.connect(self._actualizar_menu_zona)
        self.btn_zona.setMenu(menu_zona)
        self.btn_zona.setEnabled(False)  # se habilita desde permitir_edicion_zona()


    
        self.btn_grabar = QPushButton("Grabar")
        self.btn_grabar.setCheckable(True)
        self.btn_grabar.clicked.connect(self._alternar_grabacion)

        pie.addWidget(self.lbl_estado)
        pie.addStretch()
        pie.addWidget(self.btn_zona)
        pie.addWidget(self.btn_grabar)

        layout_principal.addLayout(encabezado)
        layout_principal.addWidget(self.lbl_video, stretch=1)
        layout_principal.addWidget(self.barra_edicion)

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
            self._cancelar_edicion()  # sin video no se puede seguir dibujando
            self._mostrar_placeholder("Sin señal\nReintentando conexión...")
            self.marcar_movimiento(False)
            self.marcar_personas(0)

    def marcar_movimiento(self, detectado: bool):
        self.lbl_indicador_movimiento.setVisible(detectado)

    def marcar_personas(self, cantidad: int):
        """
        Muestra cuantas personas cuentan. Si la camara tiene zona, son solo las
        que estan dentro de ella (en rojo, porque es una alerta). Se oculta si no hay ninguna.
        """
        self._cantidad_personas = cantidad
        if self._zona:
            self.lbl_indicador_personas.setText(f"En zona: {cantidad}")
            self.lbl_indicador_personas.setStyleSheet("color: #ff6b6b;")
        else:
            self.lbl_indicador_personas.setText(f"Personas: {cantidad}")
            self.lbl_indicador_personas.setStyleSheet("")  # vuelve al color normal
        self.lbl_indicador_personas.setVisible(cantidad > 0)

    def marcar_grabando(self, grabando: bool):
        """Muestra REC cuando realmente se esta grabando (con el boton o solo)."""
        self.lbl_indicador_rec.setVisible(grabando)

    # ---------- Zona de vigilancia ----------
    def establecer_zona(self, puntos):
        """Pone la zona guardada (lista vacia o None = sin zona)."""
        self._zona = validar_zona(puntos)
        self.lbl_video.zona = self._zona
        self.lbl_video.update()
        self.marcar_personas(self._cantidad_personas)  # actualiza el texto del contador

    def permitir_edicion_zona(self, permitido: bool, motivo: str = ""):
        """Activa o desactiva el boton Zona. Si no se permite, 'motivo' se ve al pasar el mouse."""
        self._edicion_permitida = permitido
        self.btn_zona.setEnabled(permitido)
        self.btn_zona.setToolTip(
            "Dibujar o borrar la zona de vigilancia" if permitido else motivo
        )

    def _actualizar_menu_zona(self):
        # "Borrar zona" solo tiene sentido si ya hay una
        self.accion_borrar_zona.setEnabled(bool(self._zona))

    def _iniciar_edicion(self):
        if not self.lbl_video.hay_imagen():
            QMessageBox.information(
                self,
                "Zona",
                "La cámara debe estar conectada y mostrando video para poder dibujar la zona.",
            )
            return
        self.lbl_video.editando = True
        self.lbl_video.puntos_edicion = []
        self.lbl_video.setCursor(Qt.CrossCursor)
        self.barra_edicion.setVisible(True)
        self.btn_guardar_zona.setEnabled(False)  # hacen falta 3 puntos como minimo
        self.btn_zona.setEnabled(False)
        self.lbl_video.update()

    def _terminar_edicion(self):
        self.lbl_video.editando = False
        self.lbl_video.puntos_edicion = []
        self.lbl_video.unsetCursor()
        self.barra_edicion.setVisible(False)
        self.btn_zona.setEnabled(self._edicion_permitida)
        self.lbl_video.update()

    def _agregar_punto(self, x: float, y: float):
        self.lbl_video.puntos_edicion.append([x, y])
        self.btn_guardar_zona.setEnabled(len(self.lbl_video.puntos_edicion) >= 3)
        self.lbl_video.update()

    def _quitar_punto(self):
        if self.lbl_video.puntos_edicion:
            self.lbl_video.puntos_edicion.pop()
        self.btn_guardar_zona.setEnabled(len(self.lbl_video.puntos_edicion) >= 3)
        self.lbl_video.update()

    def _guardar_edicion(self):
        # Se redondea a 4 decimales para que el archivo de configuracion quede ordenado
        puntos = [[round(x, 4), round(y, 4)] for x, y in self.lbl_video.puntos_edicion]
        if len(puntos) < 3:
            return
        self.establecer_zona(puntos)
        self._terminar_edicion()
        self.zona_guardada.emit(self._zona)

    def _cancelar_edicion(self):
        if self.lbl_video.editando:
            self._terminar_edicion()

    def _borrar_zona(self):
        respuesta = QMessageBox.question(
            self, "Borrar zona",
            "¿Borrar la zona de esta cámara?\nDespués alertará por cualquier persona que aparezca.",
        )
        if respuesta == QMessageBox.Yes:
            self.establecer_zona([])
            self.zona_guardada.emit([])

    # ---------- Lo que hace el usuario ----------
    def _alternar_grabacion(self, activo: bool):
        self.btn_grabar.setText("Detener" if activo else "Grabar")
        self.grabacion_solicitada.emit(activo)
