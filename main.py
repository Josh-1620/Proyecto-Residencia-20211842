import sys

from PyQt5.QtWidgets import QApplication, QDialog

from ui.login_window import LoginWindow
from ui.main_window import MainWindow

# Colores y estilos de toda la aplicacion (tema oscuro).
# Funciona parecido a CSS, el lenguaje de las paginas web.
HOJA_ESTILOS = """
QMainWindow, QWidget, QDialog {
    background-color: #14161a;
    color: #e6e6e6;
    font-family: "Segoe UI", sans-serif;
}
QLabel {
    background-color: transparent;
}
QWidget#BarraEdicion {
    background-color: transparent;
}
QToolBar {
    background-color: #1b1e23;
    border: none;
    padding: 6px;
    spacing: 8px;
}
QToolBar QToolButton {
    background-color: #262a31;
    padding: 6px 12px;
    border-radius: 4px;
}
QToolBar QToolButton:hover {
    background-color: #33383f;
}
QToolBar QToolButton:disabled {
    color: #555;
}
QTabWidget::pane {
    border-top: 1px solid #2c3038;
}
QTabBar::tab {
    background-color: #1b1e23;
    padding: 8px 16px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #262a31;
    border-bottom: 2px solid #4a90e2;
}
QFrame#CameraWidget {
    background-color: #1b1e23;
    border: 1px solid #2c3038;
    border-radius: 6px;
}
QLabel#NombreCamara {
    font-weight: bold;
    font-size: 13px;
}
QLabel#IndicadorRec {
    color: #ff4d4d;
    font-weight: bold;
}
QLabel#IndicadorMovimiento {
    color: #ffcc00;
    font-weight: bold;
}
QLabel#IndicadorPersonas {
    color: #4fd1c5;
    font-weight: bold;
}
QLabel#EstadoConexion {
    color: #888;
    font-size: 11px;
}
QLabel#AyudaZona {
    color: #4fd1c5;
    font-size: 11px;
}
QMenu {
    background-color: #1f2329;
    border: 1px solid #2c3038;
}
QMenu::item {
    padding: 6px 22px;
}
QMenu::item:selected {
    background-color: #33383f;
}
QMenu::item:disabled {
    color: #555;
}
QLineEdit, QComboBox, QDateEdit {
    background-color: #1f2329;
    border: 1px solid #2c3038;
    border-radius: 4px;
    padding: 4px 6px;
}
QPushButton {
    background-color: #2c3038;
    border: none;
    padding: 5px 14px;
    border-radius: 4px;
}
QPushButton:hover {
    background-color: #3a4048;
}
QPushButton:disabled {
    color: #555;
    background-color: #22252b;
}
QPushButton:checked {
    background-color: #b33939;
}
QListWidget {
    background-color: #1b1e23;
    border: 1px solid #2c3038;
}
QStatusBar {
    background-color: #1b1e23;
    color: #999;
}
"""


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(HOJA_ESTILOS)

    # 1. Primero se muestra el inicio de sesion. El programa se queda
    #    esperando aqui hasta que la persona entre o cierre la ventana.
    login = LoginWindow()
    if login.exec_() != QDialog.Accepted:
        sys.exit(0)  # cerro el inicio de sesion sin entrar: se termina el programa

    # 2. Si entro bien, se abre la ventana principal con los datos de esa
    #    persona (para saber que permisos tiene).
    ventana = MainWindow(login.usuario_autenticado)
    ventana.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
