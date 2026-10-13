"""
LoginWindow: la ventana donde se escribe usuario y contrasena.

Se muestra ANTES de la ventana principal. Si los datos son correctos,
se guarda quien entro (usuario, nombre y rol) y la ventana se cierra
dando paso a la aplicacion.
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QFormLayout,
)

from core.auth import verificar_credenciales


class LoginWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Iniciar sesión — Sistema de Monitoreo IP")
        self.setMinimumSize(480, 340)
        self.resize(480, 340)

        self.usuario_autenticado = None  # se llena solo si el inicio de sesion es correcto

        self._construir_ui()

    def _construir_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(16)

        titulo = QLabel("Sistema de Monitoreo IP")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 6px;")
        layout.addWidget(titulo)

        layout.addStretch()

        formulario = QFormLayout()
        formulario.setVerticalSpacing(14)
        formulario.setLabelAlignment(Qt.AlignRight)

        self.campo_usuario = QLineEdit()
        self.campo_usuario.setPlaceholderText("admin")
        self.campo_usuario.setMinimumHeight(32)

        self.campo_contrasena = QLineEdit()
        self.campo_contrasena.setEchoMode(QLineEdit.Password)
        self.campo_contrasena.setPlaceholderText("••••••••")
        self.campo_contrasena.setMinimumHeight(32)
        # Presionar Enter en la contrasena tambien inicia sesion
        self.campo_contrasena.returnPressed.connect(self._intentar_login)

        formulario.addRow("Usuario:", self.campo_usuario)
        formulario.addRow("Contraseña:", self.campo_contrasena)
        layout.addLayout(formulario)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #ff6b6b;")
        self.lbl_error.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_error)

        boton_entrar = QPushButton("Iniciar sesión")
        boton_entrar.setMinimumHeight(36)
        boton_entrar.clicked.connect(self._intentar_login)
        layout.addWidget(boton_entrar)

        layout.addStretch()

    def _intentar_login(self):
        usuario = self.campo_usuario.text().strip()
        contrasena = self.campo_contrasena.text()

        if not usuario or not contrasena:
            self.lbl_error.setText("Ingresa usuario y contraseña.")
            return

        resultado = verificar_credenciales(usuario, contrasena)

        if resultado is None:
            self.lbl_error.setText("Usuario o contraseña incorrectos.")
            self.campo_contrasena.clear()
            return

        self.usuario_autenticado = resultado
        self.accept()  # cierra la ventana indicando que todo salio bien
