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
        logo_row.setSpacing(0)

        logo_icon = QLabel("🔍")
        logo_icon.setStyleSheet("font-size: 32px; background: transparent;")
        logo_row.addWidget(logo_icon)

        logo_label = QLabel("LogiCheck")
        logo_label.setObjectName("loginBrand")
        logo_row.addWidget(logo_label)

        logo_row.addStretch()

        # ── Botón cerrar (X) ──
        btn_close = QPushButton("✕")
        btn_close.setObjectName("loginCloseBtn")
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setToolTip("Cerrar")
        btn_close.setAutoDefault(False)
        btn_close.setDefault(False)
        btn_close.setFocusPolicy(Qt.NoFocus)
        btn_close.clicked.connect(self.reject)
        logo_row.addWidget(btn_close)

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
        self.btn_login.setDefault(True)       # Enter siempre activa este botón
        self.btn_login.setAutoDefault(True)
        self.btn_login.clicked.connect(self._try_login)
        card_layout.addWidget(self.btn_login)

        card_layout.addStretch()

        # ── Footer ──
        footer = QLabel("Ferretería Durán, Apulo © 2026")
        footer.setObjectName("loginFooter")
        footer.setFixedHeight(72)
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

            /* Card principal con glassmorphism */
            #loginCard {
                background-color: rgba(15, 23, 42, 247); /* Slate 900 con 97% opacidad */
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 20px;
            }

            /* Brand */
            #loginBrand {
                font-family: 'Segoe UI', Inter, sans-serif;
                font-size: 26px;
                font-weight: 900;
                color: #FFFFFF;
                letter-spacing: 1.5px;
                background: transparent;
            }
            #loginSubtitle {
                font-family: 'Segoe UI', Inter, sans-serif;
                font-size: 13px;
                font-weight: 500;
                color: #94A3B8; /* Slate 400 */
                background: transparent;
            }

            /* Títulos */
            #loginTitle {
                font-family: 'Segoe UI', Inter, sans-serif;
                font-size: 22px;
                font-weight: 800;
                color: #F8FAFC; /* Slate 50 */
                background: transparent;
            }
            #loginHint {
                font-size: 13px;
                color: #94A3B8;
                background: transparent;
                margin-top: -2px;
            }

            /* Labels de campos */
            #loginFieldLabel {
                font-size: 12px;
                font-weight: 700;
                color: #CBD5E1; /* Slate 300 */
                letter-spacing: 0.5px;
                text-transform: uppercase;
                background: transparent;
            }

            /* Inputs - Efecto Inset Glass */
            #loginInput {
                background-color: rgba(0, 0, 0, 80);
                border: 1px solid rgba(255, 255, 255, 25);
                border-radius: 10px;
                padding: 0 16px;
                font-size: 14px;
                color: #F8FAFC;
                font-weight: 500;
            }
            #loginInput:focus {
                border-color: #3B82F6; /* Blue 500 neon */
                background-color: rgba(15, 23, 42, 100);
            }
            #loginInput::placeholder {
                color: #64748B; /* Slate 500 */
            }

            /* Botón mostrar contraseña */
            #showPassBtn {
                background-color: rgba(0, 0, 0, 80);
                border: 1px solid rgba(255, 255, 255, 25);
                border-left: none;
                border-top-right-radius: 10px;
                border-bottom-right-radius: 10px;
                font-size: 16px;
                color: #94A3B8;
            }
            #showPassBtn:hover { background-color: rgba(255, 255, 255, 10); color: #F8FAFC; }
            #showPassBtn:checked { color: #3B82F6; }

            /* Error flotante tipo neón */
            #loginError {
                color: #FDA4AF; /* Rose 300 */
                font-size: 13px;
                font-weight: 600;
                background: rgba(225, 29, 72, 0.15); /* Rose 600 opaco */
                border: 1px solid rgba(225, 29, 72, 0.4);
                border-radius: 8px;
                padding: 8px 12px;
            }

            /* Botón principal (Gradient Glow) */
            #loginBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3B82F6, stop:1 #8B5CF6);
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: 800;
                letter-spacing: 0.8px;
            }
            #loginBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #60A5FA, stop:1 #A78BFA);
            }
            #loginBtn:pressed { background: #2563EB; }
            #loginBtn:disabled {
                background: rgba(255, 255, 255, 10);
                color: #64748B;
                border: 1px solid rgba(255, 255, 255, 20);
            }

            /* Footer */
            #loginFooter {
                font-family: 'Segoe UI', Inter, sans-serif;
                font-size: 11px;
                color: #64748B;
                background: transparent;
                letter-spacing: 0.5px;
            }

            /* Botón cerrar X */
            #loginCloseBtn {
                background: transparent;
                border: none;
                border-radius: 6px;
                color: #64748B;
                font-size: 18px;
                font-weight: bold;
                padding: 0;
            }
            #loginCloseBtn:hover {
                background: rgba(225, 29, 72, 0.2);
                color: #F43F5E;
            }
            #loginCloseBtn:pressed {
                background: rgba(225, 29, 72, 0.4);
                color: #E11D48;
            }
        """)
