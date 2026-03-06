import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton
from PySide6.QtCore import Qt, QEventLoop, Signal

class MainWindow(QMainWindow):
    logout_requested = Signal()

    def __init__(self, title):
        super().__init__()
        self.setWindowTitle(title)
        btn = QPushButton("Logout from " + title, self)
        btn.clicked.connect(self.logout)
        
    def logout(self):
        self.logout_requested.emit()
        self.close()

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    for i in range(2):
        window = MainWindow(f"Window {i}")
        window.setAttribute(Qt.WA_DeleteOnClose)
        
        loop = QEventLoop()
        window.logout_requested.connect(loop.quit)
        window.destroyed.connect(loop.quit)
        
        window.show()
        print(f"Looping {i}")
        loop.exec()
        print(f"Done {i}")
        
    print("exit")
    sys.exit(0)

if __name__ == "__main__":
    main()
