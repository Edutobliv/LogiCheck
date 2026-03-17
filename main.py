import sys
import os
import subprocess
from PySide6.QtWidgets import QApplication
from PySide6.QtCore    import QEventLoop, Qt
from ui.login_dialog   import LoginDialog
from ui.main_window    import MainWindow
from ui.splash_screen  import SplashScreen
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

    # ── Splash Screen ──────────────────────────────────────
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    # Esperar a que el splash termine (hilo de init + fade-out)
    loop = QEventLoop()
    splash.ready.connect(loop.quit)       # Sale del loop cuando la init termina
    loop.exec()                           # Bloc hasta que ready se emita

    # Dar tiempo al fade-out antes de mostrar el login
    from PySide6.QtCore import QTimer
    _finish_loop = QEventLoop()
    QTimer.singleShot(550, _finish_loop.quit)
    _finish_loop.exec()

    # ── Pantalla de Login ──────────────────────────────────
    login = LoginDialog()
    
    # Forzar al SO a mostrarla en el frente (sin anclarla como siempre visible)
    login.setWindowFlags(login.windowFlags() | Qt.WindowStaysOnTopHint)
    login.show()
    login.setWindowFlags(login.windowFlags() & ~Qt.WindowStaysOnTopHint)
    login.show()
    login.activateWindow()
    login.raise_()

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
        # Reiniciar la aplicación ejecutando el mismo comando original
        subprocess.Popen([sys.executable] + sys.argv)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
