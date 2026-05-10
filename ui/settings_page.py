# ui/settings_page.py
# ============================================================
#  LogiCheck — Asistente de Configuración (Wizard)
# ============================================================

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QLineEdit, QFormLayout, QScrollArea,
    QSizePolicy, QSpacerItem, QGraphicsDropShadowEffect,
    QStackedWidget, QMessageBox, QGraphicsOpacityEffect, QDialog
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup, Property
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QLinearGradient

import sys
import os

_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _base not in sys.path:
    sys.path.insert(0, _base)

from core.config_manager import config
from core.notifier import notifier
from core import logger as app_logger

# ══════════════════════════════════════════════════════════════
#  Componente: Diálogo de Tutorial Animado
# ══════════════════════════════════════════════════════════════
class TutorialDialog(QDialog):
    """Un diálogo premium con animaciones para guiar al usuario."""
    
    def __init__(self, title, steps, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(480, 380)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.steps = steps # Lista de (icono, titulo, desc)
        self.current_step = 0
        
        self._build_ui()
        self._apply_styles()
        self._show_step(0)

    def _build_ui(self):
        # Layout principal del diálogo para dejar espacio a la sombra
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        self.content = QFrame(self)
        self.content.setObjectName("tutorialContainer")
        self.content.setFixedSize(480, 380)
        main_layout.addWidget(self.content)
        
        # Efecto de Sombra (Reemplaza al paintEvent para evitar errores de QPainter)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setXOffset(0)
        shadow.setYOffset(5)
        shadow.setColor(QColor(0, 0, 0, 180))
        self.content.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(self.content)
        layout.setContentsMargins(30, 30, 30, 20)
        layout.setSpacing(15)

        # Header con botón cerrar
        header = QHBoxLayout()
        self.lbl_title = QLabel("Tutorial")
        self.lbl_title.setObjectName("tutMainTitle")
        header.addWidget(self.lbl_title)
        header.addStretch()
        
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(30, 30)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setObjectName("tutCloseBtn")
        btn_close.clicked.connect(self.reject)
        header.addWidget(btn_close)
        layout.addLayout(header)

        # Contenido animado (Stack)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        for icon, step_title, step_desc in self.steps:
            page = QWidget()
            p_lay = QVBoxLayout(page)
            p_lay.addStretch() # Empuja el contenido hacia el centro verticalmente
            
            icon_lbl = QLabel(icon)
            icon_lbl.setAlignment(Qt.AlignCenter)
            icon_lbl.setStyleSheet("font-size: 60px; margin-bottom: 10px;")
            p_lay.addWidget(icon_lbl)
            
            t_lbl = QLabel(step_title)
            t_lbl.setObjectName("tutStepTitle")
            t_lbl.setWordWrap(True)
            t_lbl.setAlignment(Qt.AlignCenter)
            p_lay.addWidget(t_lbl)
            
            d_lbl = QLabel(step_desc)
            d_lbl.setObjectName("tutStepDesc")
            d_lbl.setWordWrap(True)
            d_lbl.setAlignment(Qt.AlignCenter)
            p_lay.addWidget(d_lbl)
            
            p_lay.addStretch()
            self.stack.addWidget(page)

        # Barra de progreso
        self.progress_lay = QHBoxLayout()
        self.progress_lay.setSpacing(8)
        self.progress_lay.setAlignment(Qt.AlignCenter)
        self.dots = []
        for i in range(len(self.steps)):
            dot = QFrame()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet("background: #334155; border-radius: 4px;")
            self.dots.append(dot)
            self.progress_lay.addWidget(dot)
        layout.addLayout(self.progress_lay)

        # Navegación
        nav = QHBoxLayout()
        self.btn_back = QPushButton("Anterior")
        self.btn_back.setObjectName("tutNavBtn")
        self.btn_back.clicked.connect(self._prev)
        
        self.btn_next = QPushButton("Siguiente")
        self.btn_next.setObjectName("tutPrimaryBtn")
        self.btn_next.clicked.connect(self._next)
        
        nav.addWidget(self.btn_back)
        nav.addStretch()
        nav.addWidget(self.btn_next)
        layout.addLayout(nav)

    def _apply_styles(self):
        self.content.setStyleSheet("""
            #tutorialContainer { 
                background: #0F172A; 
                border: 1px solid #1E293B; 
                border-radius: 20px;
            }
            #tutMainTitle { color: #3B82F6; font-size: 14px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }
            #tutCloseBtn { background: transparent; color: #CBD5E1; font-weight: bold; border-radius: 15px; }
            #tutCloseBtn:hover { background: rgba(255,255,255,0.05); color: #EF4444; }
            
            #tutStepTitle { color: #F8FAFC; font-size: 18px; font-weight: 800; }
            #tutStepDesc { color: #CBD5E1; font-size: 14px; line-height: 1.4; }
            
            #tutNavBtn { background: transparent; border: 1px solid #334155; color: #F8FAFC; border-radius: 8px; padding: 6px 15px; }
            #tutNavBtn:hover { background: #1E293B; }
            
            #tutPrimaryBtn { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #818CF8); 
                color: #020617; border: none; border-radius: 8px; padding: 6px 20px; font-weight: bold; 
            }
            #tutPrimaryBtn:hover { background: #8B5CF6; }
        """)

    def _show_step(self, idx):
        self.current_step = idx
        self.stack.setCurrentIndex(idx)
        self.btn_back.setVisible(idx > 0)
        self.btn_next.setText("Siguiente" if idx < len(self.steps)-1 else "Entendido")
        
        # Actualizar puntos
        for i, dot in enumerate(self.dots):
            if i == idx:
                dot.setStyleSheet("background: #3B82F6; border-radius: 4px; border: 1px solid #818CF8;")
                dot.setFixedWidth(20)
            else:
                dot.setStyleSheet("background: #334155; border-radius: 4px;")
                dot.setFixedWidth(8)
                
        # Animación de opacidad
        eff = QGraphicsOpacityEffect(self.stack.currentWidget())
        self.stack.currentWidget().setGraphicsEffect(eff)
        # BUGFIX: Guardar referencia a la animación en la clase para evitar que el Garbage Collector la elimine.
        self._current_anim = QPropertyAnimation(eff, b"opacity")
        self._current_anim.setDuration(300)
        self._current_anim.setStartValue(0)
        self._current_anim.setEndValue(1)
        self._current_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._current_anim.start()

    def _next(self):
        if self.current_step < len(self.steps) - 1:
            self._show_step(self.current_step + 1)
        else:
            self.accept()

    def _prev(self):
        if self.current_step > 0:
            self._show_step(self.current_step - 1)

class SettingsPage(QWidget):
    """Página de configuración refactorizada como Asistente (Wizard)."""
    
    def __init__(self, user_data: dict = None, parent=None):
        super().__init__(parent)
        self._user = user_data or {}
        self._inputs = {}
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Header Fijo ──
        self.header = QFrame()
        self.header.setObjectName("welcomeBanner")
        self.header.setFixedHeight(100)
        h_layout = QHBoxLayout(self.header)
        h_layout.setContentsMargins(30, 0, 30, 0)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_col.setAlignment(Qt.AlignCenter)
        self.lbl_wizard_title = QLabel("⚙️ Asistente de Configuración")
        self.lbl_wizard_title.setObjectName("welcomeTitle")
        self.lbl_wizard_step = QLabel("Paso 1 de 4")
        self.lbl_wizard_step.setObjectName("welcomeSub")
        title_col.addWidget(self.lbl_wizard_title)
        title_col.addWidget(self.lbl_wizard_step)
        
        h_layout.addLayout(title_col)
        main_layout.addWidget(self.header)

        # ── Stacked Widget (Pasos) ──
        self.stack = QStackedWidget()
        
        self.step_telegram = self._create_step_notif("Telegram", "tg", [
            ("Token del Bot", "token", True),
            ("Chat ID", "chat_id", False)
        ], "8684027766:AAEM...", self._test_telegram)
        
        self.step_whatsapp = self._create_step_notif("WhatsApp", "wa", [
            ("Teléfono (57...)", "phone", False),
            ("API Key", "apikey", True)
        ], "57300...", self._test_whatsapp)
        
        self.step_cameras = self._create_step_cameras()
        self.step_finish = self._create_step_finish()

        self.stack.addWidget(self.step_telegram)
        self.stack.addWidget(self.step_whatsapp)
        self.stack.addWidget(self.step_cameras)
        self.stack.addWidget(self.step_finish)
        
        main_layout.addWidget(self.stack)

        # ── Barra de Navegación Inferior (Fija al fondo) ──
        nav_bar = QFrame()
        nav_bar.setObjectName("wizardNav")
        nav_bar.setFixedHeight(72)
        nav_bar_lay = QHBoxLayout(nav_bar)
        nav_bar_lay.setContentsMargins(30, 0, 30, 0)

        self.btn_back = QPushButton("← Anterior")
        self.btn_back.setObjectName("secondaryBtn")
        self.btn_back.setMinimumWidth(120)
        self.btn_back.setFixedHeight(40)
        self.btn_back.setCursor(Qt.PointingHandCursor)
        self.btn_back.clicked.connect(self._prev_step)
        self.btn_back.setEnabled(False)

        self.btn_next = QPushButton("Siguiente →")
        self.btn_next.setObjectName("primaryBtn")
        self.btn_next.setMinimumWidth(120)
        self.btn_next.setFixedHeight(40)
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.clicked.connect(self._next_step)

        nav_bar_lay.addWidget(self.btn_back)
        nav_bar_lay.addStretch()
        nav_bar_lay.addWidget(self.btn_next)
        
        main_layout.addWidget(nav_bar)

    # ── Construcción de Pasos ────────────────────────────────

    def _create_step_notif(self, name, prefix, fields, hint, test_func):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(50, 40, 50, 40)
        lay.setSpacing(20)

        icon_lbl = QLabel("✈️" if name == "Telegram" else "📲")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 48px; margin-bottom: 10px;")
        lay.addWidget(icon_lbl)

        title = QLabel(f"Configurar Notificaciones de {name}")
        title.setObjectName("cardTitle")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        desc = QLabel(f"Proporcione las credenciales para enviar alertas automáticas vía {name}.")
        desc.setObjectName("subtleText")
        desc.setAlignment(Qt.AlignCenter)
        lay.addWidget(desc)

        card = QFrame()
        card.setObjectName("glowCard")
        form_lay = QFormLayout(card)
        form_lay.setContentsMargins(20, 20, 20, 20)
        form_lay.setSpacing(15)

        for label, subkey, is_pass in fields:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(5)

            inp = QLineEdit()
            inp.setObjectName("loginInput")
            inp.setFixedHeight(40)
            inp.setPlaceholderText(hint if subkey in ["token", "phone"] else "")
            
            if is_pass:
                inp.setEchoMode(QLineEdit.EchoMode.Password)
                # Botón de visibilidad (Ojito)
                btn_toggle = QPushButton("Ver")
                btn_toggle.setFixedSize(45, 40)
                btn_toggle.setCursor(Qt.PointingHandCursor)
                btn_toggle.setStyleSheet("""
                    QPushButton { 
                        background: transparent; border: none; font-size: 11px;
                        font-weight: bold;
                    }
                    QPushButton:hover { color: #3B82F6; }
                    QPushButton:pressed { color: #0EA5E9; }
                """)
                btn_toggle.clicked.connect(lambda checked=False, i=inp, b=btn_toggle: self._toggle_visibility(i, b))
                
                row_layout.addWidget(inp, 1)
                row_layout.addWidget(btn_toggle)
                form_lay.addRow(f"{label}:", row_widget)
            else:
                form_lay.addRow(f"{label}:", inp)
                
            self._inputs[f"{prefix}_{subkey}"] = inp

        lay.addWidget(card)

        test_lay = QHBoxLayout()
        test_lay.setSpacing(10)
        test_lay.setAlignment(Qt.AlignCenter)

        btn_test = QPushButton(f"🧪 Probar {name}")
        btn_test.setObjectName("secondaryBtn")
        btn_test.setFixedHeight(35)
        btn_test.setMinimumWidth(150)
        btn_test.setCursor(Qt.PointingHandCursor)
        btn_test.clicked.connect(test_func)
        
        btn_help = QPushButton("?")
        btn_help.setObjectName("secondaryBtn")
        btn_help.setFixedSize(35, 35)
        btn_help.setCursor(Qt.PointingHandCursor)
        btn_help.setStyleSheet("border-radius: 17px; font-weight: bold; font-size: 16px;")
        btn_help.setToolTip(f"¿Cómo obtener el token de {name}?")
        btn_help.clicked.connect(lambda checked=False, n=name: self._show_help(n))
        
        test_lay.addWidget(btn_test)
        test_lay.addWidget(btn_help)
        lay.addLayout(test_lay)

        lay.addStretch()
        return page

    def _create_step_cameras(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(40, 30, 40, 30)
        lay.setSpacing(15)

        icon_lbl = QLabel("📷")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 40px; margin-bottom: 5px;")
        lay.addWidget(icon_lbl)

        title = QLabel("Configuración de Conexión")
        title.setObjectName("cardTitle")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        # ── Card de Credenciales ──
        card = QFrame()
        card.setObjectName("glowCard")
        self.form_lay = QFormLayout(card)
        self.form_lay.setContentsMargins(20, 20, 20, 20)
        self.form_lay.setSpacing(12)

        self.inp_host = QLineEdit()
        self.inp_host.setObjectName("loginInput")
        self.inp_host.setPlaceholderText("ej: ferreteria.viewdns.net")
        self._inputs["cam_host"] = self.inp_host

        self.inp_user = QLineEdit()
        self.inp_user.setPlaceholderText("usuario RTSP")
        self._inputs["cam_user"] = self.inp_user
        
        self.inp_pass = QLineEdit()
        self.inp_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._inputs["cam_pass"] = self.inp_pass

        self.inp_port = QLineEdit()
        self.inp_port.setText("554")
        self._inputs["cam_port"] = self.inp_port

        self.inp_model_path = QLineEdit()
        self.inp_model_path.setObjectName("loginInput")
        self.inp_model_path.setPlaceholderText("models/estacion_bultos_v1.pt")
        self._inputs["ai_model_path"] = self.inp_model_path

        self.form_lay.addRow("Host (IP o Dominio):", self.inp_host)
        self.form_lay.addRow("Usuario:", self.inp_user)
        self.form_lay.addRow("Contraseña:", self.inp_pass)
        self.form_lay.addRow("Puerto RTSP:", self.inp_port)
        self.form_lay.addRow("Modelo IA:", self.inp_model_path)

        # Info de seguridad 
        self.lbl_mode_info = QLabel("💡 Usando el puerto 443 para garantizar conexión en redes restringidas.")
        self.lbl_mode_info.setObjectName("subtleText")
        self.lbl_mode_info.setWordWrap(True)
        self.lbl_mode_info.setAlignment(Qt.AlignCenter)

        lay.addWidget(card)
        lay.addWidget(self.lbl_mode_info)

        lay.addStretch()
        return page

    def _create_step_finish(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(50, 40, 50, 40)
        lay.setSpacing(20)

        icon_lbl = QLabel("✅")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 64px; margin-bottom: 10px;")
        lay.addWidget(icon_lbl)

        title = QLabel("¡Todo Listo!")
        title.setObjectName("cardTitle")
        title.setAlignment(Qt.AlignCenter)
        lay.addWidget(title)

        self.lbl_review = QLabel("Presione 'Finalizar' para guardar todos los cambios y aplicar la configuración.")
        self.lbl_review.setObjectName("subtleText")
        self.lbl_review.setWordWrap(True)
        self.lbl_review.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.lbl_review)

        lay.addStretch()
        return page

    # ── Lógica de Navegación ────────────────────────────────

    def _update_step_label(self):
        curr = self.stack.currentIndex()
        self.lbl_wizard_step.setText(f"Paso {curr + 1} de 4")
        self.btn_back.setEnabled(curr > 0)
        if curr == 3:
            self.btn_next.setText("🏁 Finalizar")
            self.btn_next.setObjectName("successBtn")
        else:
            self.btn_next.setText("Siguiente →")
            self.btn_next.setObjectName("primaryBtn")
        self.btn_next.style().unpolish(self.btn_next)
        self.btn_next.style().polish(self.btn_next)

    def _next_step(self):
        curr = self.stack.currentIndex()
        if curr < 3:
            self.stack.setCurrentIndex(curr + 1)
            self._update_step_label()
        else:
            self._save_settings()

    def _prev_step(self):
        curr = self.stack.currentIndex()
        if curr > 0:
            self.stack.setCurrentIndex(curr - 1)
            self._update_step_label()

    # ── Datos ────────────────────────────────────────────────

    def _load_settings(self):
        self._inputs["tg_token"].setText(config.get("notifications.telegram.token", ""))
        self._inputs["tg_chat_id"].setText(config.get("notifications.telegram.chat_id", ""))
        self._inputs["wa_phone"].setText(config.get("notifications.whatsapp.phone", ""))
        self._inputs["wa_apikey"].setText(config.get("notifications.whatsapp.apikey", ""))
        
        # Carga de cámaras (Simplificado)
        self._inputs["cam_host"].setText(config.get("cameras.host", ""))
        self._inputs["cam_user"].setText(config.get("cameras.default_user", ""))
        self._inputs["cam_pass"].setText(config.get("cameras.default_pass", ""))
        self._inputs["cam_port"].setText(str(config.get("cameras.default_port", 554)))
        self._inputs["ai_model_path"].setText(config.get("ai.model_path", ""))

    def _save_settings(self):
        config.set("notifications.telegram.token", self._inputs["tg_token"].text().strip())
        config.set("notifications.telegram.chat_id", self._inputs["tg_chat_id"].text().strip())
        config.set("notifications.whatsapp.phone", self._inputs["wa_phone"].text().strip())
        config.set("notifications.whatsapp.apikey", self._inputs["wa_apikey"].text().strip())

        # Guardar cámaras
        config.set("cameras.host", self._inputs["cam_host"].text().strip())
        config.set("cameras.default_user", self._inputs["cam_user"].text().strip())
        config.set("cameras.default_pass", self._inputs["cam_pass"].text().strip())
        config.set("cameras.default_port", int(self._inputs["cam_port"].text().strip() or "554"))
        config.set("ai.model_path", self._inputs["ai_model_path"].text().strip())
        config.save()

        app_logger.log_action(self._user, "CONFIG_ACTUALIZADA", "El usuario completó el asistente de configuración")
        QMessageBox.information(self, "Asistente", "Configuración guardada correctamente.")
        
        # Volver al inicio del wizard si se desea, o al Dashboard vía señal personalizada
        self.stack.setCurrentIndex(0)
        self._update_step_label()

    def _test_telegram(self):
        token = self._inputs["tg_token"].text().strip()
        chat_id = self._inputs["tg_chat_id"].text().strip()
        if not token or not chat_id:
            QMessageBox.warning(self, "Error", "Complete los campos de Telegram antes de probar.")
            return
        
        # Guardar temporalmente para prueba
        config.set("notifications.telegram.token", token)
        config.set("notifications.telegram.chat_id", chat_id)
        
        notifier.send_telegram("🔔 <b>LogiCheck Asistente</b>\nPrueba exitosa de configuración.")
        QMessageBox.information(self, "Test", "Mensaje enviado. Revise su app de Telegram.")

    def _test_whatsapp(self):
        phone = self._inputs["wa_phone"].text().strip()
        apikey = self._inputs["wa_apikey"].text().strip()
        if not phone or not apikey:
            QMessageBox.warning(self, "Error", "Complete los campos de WhatsApp antes de probar.")
            return
        
        config.set("notifications.whatsapp.phone", phone)
        config.set("notifications.whatsapp.apikey", apikey)
        
        notifier.send_whatsapp("LogiCheck Asistente: Prueba de WhatsApp activa.")
        QMessageBox.information(self, "Test", "Mensaje de prueba solicitado a WhatsApp.")

    def _toggle_visibility(self, inp, btn):
        if inp.echoMode() == QLineEdit.EchoMode.Password:
            inp.setEchoMode(QLineEdit.EchoMode.Normal)
            btn.setText("Ocultar")
        else:
            inp.setEchoMode(QLineEdit.EchoMode.Password)
            btn.setText("Ver")

    def _show_help(self, name):
        """Muestra un tutorial premium animado."""
        if name == "Telegram":
            steps = [
                ("🤖", "Paso 1: Busca al Padre", "Abre tu aplicación de Telegram y busca al usuario <b>@BotFather</b>."),
                ("✍️", "Paso 2: Comando Mágico", "Envía el mensaje <b>/newbot</b> para iniciar la creación de tu bot."),
                ("🏷️", "Paso 3: Identidad", "Elige un nombre para el bot y luego un 'username' único.<br><br><i>(Debe terminar en 'bot')</i>"),
                ("🔑", "Paso 4: Tu Token", "BotFather te enviará un mensaje con un código largo.<br><b>Ese es tu API Token</b>."),
                ("💡", "Paso 5: Activación", "Entra al chat de tu nuevo bot y pulsa 'Iniciar', o envíale un mensaje antes de probar aquí.")
            ]
            title = "Configurar Bot de Telegram"
        else:
            steps = [
                ("🔗", "Paso 1: Contacto", "Agrega el número oficial que aparece en <b>callmebot.com</b> a tus contactos de WhatsApp."),
                ("💬", "Paso 2: Permiso", "Envía el mensaje: <b>I allow callmebot to send me messages</b> a ese contacto."),
                ("🎁", "Paso 3: API Key", "Recibirás un mensaje automático con tu <b>API Key</b> personalizada."),
                ("📞", "Paso 4: Registro", "Introduce tu número con el código de país (ej. 57...) y la API Key que recibiste.")
            ]
            title = "Sincronizar WhatsApp"

        dlg = TutorialDialog(title, steps, self)
        dlg.exec()
