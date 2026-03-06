import sys
import os
import subprocess
from PySide6.QtWidgets import QApplication
from ui.login_dialog import LoginDialog
from ui.main_window import MainWindow
from core import logger as app_logger


def main():
    app = QApplication(sys.argv)

    # Directorio base siempre desde el script
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Cargar hoja de estilos global
    try:
        with open("resources/style.qss", "r") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("Advertencia: No se encontró style.qss")

    # ── Pantalla de Login ──────────────────────────────────
    login = LoginDialog()
    if login.exec() != LoginDialog.Accepted:
        sys.exit(0)

    user_data = login.user_data

    # Registrar inicio de sesión
    app_logger.log_action(user_data, app_logger.LOGIN,
                          f"Acceso desde {os.environ.get('COMPUTERNAME', 'equipo desconocido')}")

    # ── Ventana Principal ──────────────────────────────────
    window = MainWindow(user_data=user_data)

    _logout_requested = [False]

    def _on_logout():
        _logout_requested[0] = True

    window.logout_requested.connect(_on_logout)
    window.show()

    exit_code = app.exec()

    if _logout_requested[0]:
        subprocess.Popen([sys.executable] + sys.argv[1:])

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

