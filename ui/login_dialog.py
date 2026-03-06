# ui/login_dialog.py
# ============================================================
#  LogiCheck — Pantalla de Login Premium
# ============================================================

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QGraphicsDropShadowEffect, QSizePolicy
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QPoint
from PySide6.QtGui import QFont, QColor, QLinearGradient, QPainter, QPainterPath, QIcon
import sys
import os

# Asegurar que podamos importar desde core/
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from core.auth import authenticate, init_db
from core import logger as app_logger


class ShakeAnimation:
    """Agita horizontalmente un widget para indicar error."""
    def __init__(self, widget):
        self.widget = widget
        self.anim = QPropertyAnimation(widget, b"pos")
        self.anim.setEasingCurve(QEasingCurve.InOutSine)
        self.anim.setDuration(400)

    def shake(self):
        orig = self.widget.pos()
        offsets = [8, -8, 6, -6, 4, -4, 0]
        self.anim.stop()
        self.anim.setKeyValueAt(0.0,  QPoint(orig.x(), orig.y()))
        self.anim.setKeyValueAt(0.15, QPoint(orig.x() + 8, orig.y()))
        self.anim.setKeyValueAt(0.30, QPoint(orig.x() - 8, orig.y()))
        self.anim.setKeyValueAt(0.50, QPoint(orig.x() + 5, orig.y()))
        self.anim.setKeyValueAt(0.70, QPoint(orig.x() - 5, orig.y()))
        self.anim.setKeyValueAt(0.85, QPoint(orig.x() + 2, orig.y()))
        self.anim.setKeyValueAt(1.0,  QPoint(orig.x(), orig.y()))
        self.anim.start()


class LoginDialog(QDialog):
    """Ventana de login modal. Llama a exec() y revisa self.user_data."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_data = None  # Se llena cuando login es exitoso

        init_db()  # Garantiza que la BD existe

        self.setWindowTitle("LogiCheck — Iniciar Sesión")
        self.setFixedSize(440, 540)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Drag support
        self._drag_pos = None

        self._build_ui()
        self._apply_styles()

    # ── UI Builder ────────────────────────────────────────────

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)

        # Card principal
        self.card = QFrame(self)
        self.card.setObjectName("loginCard")
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(0)

        # ── Logo / Brand ──
        logo_row = QHBoxLayout()
        logo_icon = QLabel("🔍")
        logo_icon.setStyleSheet("font-size: 32px; background: transparent;")
        logo_row.addWidget(logo_icon)
        logo_label = QLabel("LogiCheck")
        logo_label.setObjectName("loginBrand")
        logo_row.addWidget(logo_label)
        logo_row.addStretch()
        card_layout.addLayout(logo_row)

        card_layout.addSpacing(6)

        subtitle = QLabel("Sistema de Auditoría Logística")
        subtitle.setObjectName("loginSubtitle")
        card_layout.addWidget(subtitle)

        card_layout.addSpacing(36)

        # ── Título ──
        title = QLabel("Bienvenido de vuelta")
        title.setObjectName("loginTitle")
        card_layout.addWidget(title)

        card_layout.addSpacing(4)

        hint = QLabel("Ingresa tus credenciales para continuar")
        hint.setObjectName("loginHint")
        card_layout.addWidget(hint)

        card_layout.addSpacing(28)

        # ── Campo usuario ──
        lbl_user = QLabel("Usuario")
        lbl_user.setObjectName("loginFieldLabel")
        card_layout.addWidget(lbl_user)
        card_layout.addSpacing(6)

        self.input_user = QLineEdit()
        self.input_user.setObjectName("loginInput")
        self.input_user.setPlaceholderText("Ej: admin")
        self.input_user.setFixedHeight(42)
        self.input_user.returnPressed.connect(self._try_login)
        card_layout.addWidget(self.input_user)

        card_layout.addSpacing(16)

        # ── Campo contraseña ──
        lbl_pass = QLabel("Contraseña")
        lbl_pass.setObjectName("loginFieldLabel")
        card_layout.addWidget(lbl_pass)
        card_layout.addSpacing(6)

        pass_row = QHBoxLayout()
        pass_row.setSpacing(0)
        self.input_pass = QLineEdit()
        self.input_pass.setObjectName("loginInput")
        self.input_pass.setPlaceholderText("••••••••")
        self.input_pass.setFixedHeight(42)
        self.input_pass.setEchoMode(QLineEdit.Password)
        self.input_pass.returnPressed.connect(self._try_login)
        pass_row.addWidget(self.input_pass)

        self.btn_show_pass = QPushButton("👁")
        self.btn_show_pass.setObjectName("showPassBtn")
        self.btn_show_pass.setFixedSize(42, 42)
        self.btn_show_pass.setCursor(Qt.PointingHandCursor)
        self.btn_show_pass.setCheckable(True)
        self.btn_show_pass.toggled.connect(self._toggle_password_visibility)
        pass_row.addWidget(self.btn_show_pass)
        card_layout.addLayout(pass_row)

        card_layout.addSpacing(10)

        # ── Mensaje de error ──
        self.lbl_error = QLabel("")
        self.lbl_error.setObjectName("loginError")
        self.lbl_error.setAlignment(Qt.AlignCenter)
        self.lbl_error.setWordWrap(True)
        self.lbl_error.hide()
        card_layout.addWidget(self.lbl_error)

        card_layout.addSpacing(24)

        # ── Botón ingresar ──
        self.btn_login = QPushButton("  Ingresar al Sistema")
        self.btn_login.setObjectName("loginBtn")
        self.btn_login.setFixedHeight(46)
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.clicked.connect(self._try_login)
        card_layout.addWidget(self.btn_login)

        card_layout.addStretch()

        # ── Footer ──
        footer = QLabel("Ferretería Durán, Apulo © 2025")
        footer.setObjectName("loginFooter")
        footer.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(footer)

        outer.addWidget(self.card)
        self._shake = ShakeAnimation(self.card)

    # ── Lógica ───────────────────────────────────────────────

    def _try_login(self):
        username = self.input_user.text().strip()
        password = self.input_pass.text()

        if not username or not password:
            self._show_error("Por favor completa todos los campos.")
            return

        self.btn_login.setEnabled(False)
        self.btn_login.setText("  Verificando...")

        # Simula una pequeña pausa visual
        QTimer.singleShot(350, lambda: self._do_auth(username, password))

    def _do_auth(self, username: str, password: str):
        result = authenticate(username, password)
        if result:
            self.user_data = result
            self.accept()  # Cierra el diálogo con Accepted
        else:
            self.btn_login.setEnabled(True)
            self.btn_login.setText("  Ingresar al Sistema")
            self._show_error("Usuario o contraseña incorrectos.")
            self._shake.shake()
            self.input_pass.clear()
            self.input_pass.setFocus()
            # Registrar el intento fallido (usuario dummy sin ID ni rol real)
            _fake = {"id": None, "username": username, "role": "desconocido", "full_name": username}
            app_logger.log_action(_fake, app_logger.LOGIN_FALLIDO,
                                  f"Contraseña incorrecta para el usuario '{username}'")

    def _show_error(self, msg: str):
        self.lbl_error.setText(f"⚠  {msg}")
        self.lbl_error.show()

    def _toggle_password_visibility(self, checked: bool):
        self.input_pass.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)

    # ── Drag to move (window frameless) ──────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    # ── Estilos ───────────────────────────────────────────────

    def _apply_styles(self):
        self.setStyleSheet("""
            /* Diálogo transparente */
            LoginDialog { background: transparent; }

            /* Card principal */
            #loginCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e1e2e, stop:1 #181825);
                border: 1px solid #313244;
                border-radius: 20px;
            }

            /* Brand */
            #loginBrand {
                font-size: 24px;
                font-weight: 900;
                color: #89b4fa;
                letter-spacing: 1px;
                background: transparent;
            }
            #loginSubtitle {
                font-size: 12px;
                color: #6c7086;
                background: transparent;
            }

            /* Títulos */
            #loginTitle {
                font-size: 20px;
                font-weight: 800;
                color: #cdd6f4;
                background: transparent;
            }
            #loginHint {
                font-size: 12px;
                color: #6c7086;
                background: transparent;
            }

            /* Labels de campos */
            #loginFieldLabel {
                font-size: 12px;
                font-weight: 700;
                color: #a6adc8;
                letter-spacing: 0.5px;
                background: transparent;
            }

            /* Inputs */
            #loginInput {
                background-color: #11111b;
                border: 1.5px solid #313244;
                border-radius: 8px;
                padding: 0 14px;
                font-size: 13px;
                color: #cdd6f4;
            }
            #loginInput:focus {
                border-color: #89b4fa;
                background-color: #181825;
            }
            #loginInput::placeholder {
                color: #45475a;
            }

            /* Botón mostrar contraseña */
            #showPassBtn {
                background-color: #11111b;
                border: 1.5px solid #313244;
                border-left: none;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                font-size: 16px;
                color: #6c7086;
            }
            #showPassBtn:hover { background-color: #1e1e2e; color: #cdd6f4; }
            #showPassBtn:checked { color: #89b4fa; }

            /* Error */
            #loginError {
                color: #f38ba8;
                font-size: 12px;
                background: rgba(243, 139, 168, 0.10);
                border: 1px solid rgba(243, 139, 168, 0.25);
                border-radius: 6px;
                padding: 6px 10px;
            }

            /* Botón principal */
            #loginBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #89b4fa, stop:1 #74c7ec);
                color: #11111b;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 800;
                letter-spacing: 0.5px;
            }
            #loginBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #b4befe, stop:1 #89dceb);
            }
            #loginBtn:pressed { background: #74c7ec; }
            #loginBtn:disabled {
                background: #313244;
                color: #6c7086;
            }

            /* Footer */
            #loginFooter {
                font-size: 11px;
                color: #45475a;
                background: transparent;
            }
        """)
