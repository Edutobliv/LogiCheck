from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QFrame, QTableWidget, QTableWidgetItem,
                               QHeaderView, QSizePolicy, QGraphicsDropShadowEffect,
                               QGraphicsOpacityEffect,
                               QScrollArea, QStackedWidget, QToolButton, QSpacerItem,
                               QProgressBar, QStatusBar, QFileDialog, QMessageBox, QListWidget, QListWidgetItem, QSlider,
                               QDialog, QStyle, QStyleOptionSlider)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize, Property, QPoint, QVariantAnimation, QSequentialAnimationGroup, QParallelAnimationGroup, QThread, Signal, QEvent
from PySide6.QtGui import QFont, QColor, QIcon, QPainter, QPainterPath, QLinearGradient, QPen, QPixmap, QGuiApplication
import datetime
import os
import sys

# Permisos por rol
_base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _base_path not in sys.path:
    sys.path.insert(0, _base_path)
from core.permissions import can_access_page, can_do_action, get_role_display, ROLE_ICONS
from core import logger as app_logger
from ui.users_page import UsersPage
from ui.logs_page import LogsPage
from core.yolo_manager import YoloAnalyzerWorker, VideoPlayerWorker
import torch
import winsound
from core.audit_store import (save_audit, get_audits, get_dashboard_stats, 
                             init_audits_table, get_monthly_trends)
from ui.trend_chart import ModernTrendChart
from core.report_exporter import export_excel, export_pdf


class ScrubThumbnailWidget(QFrame):
    """Miniatura que aparece sobre el slider al hacer scrubbing (tipo YouTube)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(160, 90) # Relación 16:9
        self.setObjectName("scrubThumbnail")
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        
        self.lbl_img = QLabel()
        self.lbl_img.setAlignment(Qt.AlignCenter)
        self.lbl_img.setStyleSheet("background-color: #000000; border-radius: 4px;")
        layout.addWidget(self.lbl_img)
        
        self.lbl_time = QLabel("00:00")
        self.lbl_time.setAlignment(Qt.AlignCenter)
        self.lbl_time.setStyleSheet("font-size: 10px; color: white; background: rgba(0,0,0,160); border-radius: 2px;")
        self.lbl_time.setFixedHeight(18)
        layout.addWidget(self.lbl_time)
        
        # Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.setGraphicsEffect(shadow)

    def set_thumbnail(self, pixmap, time_str):
        self.lbl_img.setPixmap(pixmap.scaled(self.lbl_img.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.lbl_time.setText(time_str)


class AuditScrubSlider(QSlider):
    """Slider personalizado que dibuja marcas rojas en momentos de detección."""
    def __init__(self, orientation, parent=None):
        super().__init__(orientation)
        if parent:
            self.setParent(parent)
        self.event_markers = [] # Lista de floats (0.0 a 1.0)
        
    def set_event_markers(self, markers):
        self.event_markers = markers
        self.update()

    def paintEvent(self, event):
        # Primero dibujamos el slider normal
        super().paintEvent(event)
        
        if not self.event_markers:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Obtener el área del "groove" (la pista del slider)
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        gr = self.style().subControlRect(QStyle.CC_Slider, opt, QStyle.SC_SliderGroove, self)
        
        # Dibujar marcas rojas
        painter.setPen(Qt.NoPen)
        # Usamos un rojo vibrante con cierta transparencia
        color = QColor("#f38ba8")
        color.setAlpha(200)
        painter.setBrush(color)
        
        # El slider maneja 0-1000, pero calculamos basado en el ancho del groove
        # Dejamos un pequeño margen para que no tape el handle si está justo ahí
        for pct in self.event_markers:
            x = gr.left() + int(pct * gr.width())
            # Dibujamos un rectángulo vertical que resalte la zona
            painter.drawRoundedRect(x - 2, gr.top() + 1, 4, gr.height() - 2, 2, 2)
        
        painter.end()


class AnimatedToggle(QWidget):
    """Toggle switch animado para cambiar entre modo oscuro y claro."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_on = True  # Empieza en modo oscuro
        self.setFixedSize(56, 28)
        self.setCursor(Qt.PointingHandCursor)
        
        self._circle_position = 30  # posición inicial (derecha = ON)
        self._anim = QPropertyAnimation(self, b"circle_position")
        self._anim.setDuration(250)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)
        
    def get_circle_position(self):
        return self._circle_position
    
    def set_circle_position(self, pos):
        self._circle_position = pos
        self.update()
        
    circle_position = Property(int, get_circle_position, set_circle_position)
    
    def mousePressEvent(self, event):
        self._is_on = not self._is_on
        self._anim.setStartValue(self._circle_position)
        self._anim.setEndValue(30 if self._is_on else 6)
        self._anim.start()
        # Emitimos señal al parent
        main_win = self.window()
        if hasattr(main_win, 'toggle_theme'):
            main_win.toggle_theme()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Track
        if self._is_on:
            track_color = QColor("#89b4fa")
        else:
            track_color = QColor("#b0b0b0")
            
        painter.setBrush(track_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, 56, 28, 14, 14)
        
        # Circle
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(self._circle_position, 4, 20, 20)
        
        # Icons (Sol/Luna)
        painter.setPen(QPen(QColor("#1e1e2e" if self._is_on else "#555555"), 1.5))
        font = QFont("Segoe UI Emoji", 9)
        painter.setFont(font)
        if self._is_on:
            painter.drawText(8, 1, 20, 26, Qt.AlignCenter, "🌙")
        else:
            painter.drawText(30, 1, 20, 26, Qt.AlignCenter, "☀️")
        
        painter.end()


class GlowCard(QFrame):
    """Card con efecto de sombra suave (glow)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("glowCard")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)


class StatCard(GlowCard):
    """Tarjeta de estadística con icono, valor y descripción."""
    def __init__(self, icon_text, value, description, accent_color="#89b4fa", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.accent_color = accent_color
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(4)
        
        # Top row: icon + value
        top_row = QHBoxLayout()
        
        icon_label = QLabel(icon_text)
        icon_label.setObjectName("statIcon")
        icon_label.setStyleSheet(f"font-size: 22px; color: {accent_color}; background: transparent;")
        top_row.addWidget(icon_label)
        
        top_row.addStretch()
        
        self.value_label = QLabel(str(value))
        self.value_label.setObjectName("statValue")
        self.value_label.setStyleSheet(f"font-size: 26px; font-weight: 900; color: {accent_color}; background: transparent;")
        top_row.addWidget(self.value_label)
        
        layout.addLayout(top_row)
        
        desc_label = QLabel(description)
        desc_label.setObjectName("statDesc")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
    
    
    def set_value(self, val):
        self.value_label.setText(str(val))
        
    def animate_to(self, end_val, duration=1000):
        # Manejo de porcentajes (si es string con %) o números
        is_pct = False
        if isinstance(end_val, str) and "%" in end_val:
            is_pct = True
            try: end_val = float(end_val.replace("%", ""))
            except: end_val = 0
            
        try:
            val_text = self.value_label.text().replace("%", "")
            start_val = float(val_text) if val_text not in ["—", "0"] else 0
        except:
            start_val = 0
            
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(duration)
        self.anim.setStartValue(start_val)
        self.anim.setEndValue(float(end_val))
        
        def update_val(v):
            if is_pct: self.value_label.setText(f"{v:.1f}%")
            else: self.value_label.setText(str(int(v)))
            
        self.anim.valueChanged.connect(update_val)
        self.anim.setEasingCurve(QEasingCurve.OutQuart)
        self.anim.start()





class ToastNotification(QFrame):
    """Notificación flotante temporal (Toast) estilo Premium."""
    def __init__(self, message, toast_type="success", parent=None):
        super().__init__(parent)
        self.setFixedWidth(320)
        self.setMinimumHeight(64)
        self.setObjectName("toastNotification")
        self.setProperty("type", toast_type)
        
        # Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20); shadow.setOffset(0, 5)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)
        
        lay = QHBoxLayout(self)
        lay.setContentsMargins(15, 10, 15, 10)
        lay.setSpacing(12)
        
        icon_map = {
            "success": "✅",
            "warning": "⚠️",
            "error":   "🚫",
            "info":    "ℹ️"
        }
        
        self.lbl_icon = QLabel(icon_map.get(toast_type, "info"))
        self.lbl_icon.setStyleSheet("font-size: 20px; background: transparent;")
        lay.addWidget(self.lbl_icon)
        
        self.lbl_msg = QLabel(message)
        self.lbl_msg.setObjectName("toastMsg")
        self.lbl_msg.setWordWrap(True)
        lay.addWidget(self.lbl_msg, 1)
        
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)
        
    def show_toast(self):
        self.show()
        # Slide in animation
        self._anim_pos = QPropertyAnimation(self, b"pos")
        self._anim_pos.setDuration(500)
        self._anim_pos.setEasingCurve(QEasingCurve.OutCubic)
        
        p = self.window() # Use main window as reference
        if p:
            start_x = p.width() - self.width() - 20
            self._anim_pos.setStartValue(QPoint(start_x, -100))
            self._anim_pos.setEndValue(QPoint(start_x, 20))
            self._anim_pos.start()
            
        self._timer.start(3500) # Dura 3.5 seg
        
    def _fade_out(self):
        self._anim_out = QPropertyAnimation(self, b"pos")
        self._anim_out.setDuration(500)
        self._anim_out.setEasingCurve(QEasingCurve.InBack)
        self._anim_out.setEndValue(QPoint(self.x(), -100))
        self._anim_out.finished.connect(self.deleteLater)
        self._anim_out.start()


class NavButton(QPushButton):
    """Botón de navegación lateral con icono y texto."""
    def __init__(self, icon_text, text, parent=None):
        super().__init__(parent)
        self.setText(f"  {icon_text}   {text}")
        self.setObjectName("navButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self.setFixedHeight(44)


class MainWindow(QMainWindow):
    logout_requested = Signal()  # Emitida al cerrar sesión

    def __init__(self, user_data: dict = None,
                 preloaded_model=None, preloaded_device=None):
        super().__init__()
        self.setWindowTitle("LogiCheck — Auditoría Logística Inteligente")
        self.setMinimumSize(1100, 700)
        self.showMaximized()
        
        self._is_dark = True
        self._current_invoice = None  # Stores last InvoiceData

        # Modelo YOLO precargado desde el Splash Screen (puede ser None)
        self._preloaded_model  = preloaded_model
        self._preloaded_device = preloaded_device

        # Sesión activa
        self._user = user_data or {"username": "admin", "role": "admin", "full_name": "Administrador"}
        self._role = self._user.get("role", "admin")
        
        # Try to import the invoice parser
        try:
            core_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if core_path not in sys.path:
                sys.path.insert(0, core_path)
            from core.invoice_parser import InvoiceParser
            self._invoice_parser = InvoiceParser()
        except ImportError as e:
            self._invoice_parser = None
            print(f"[WARN] InvoiceParser no disponible: {e}")
        
        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        
        # ============================================================
        # SIDEBAR (Navegación)
        # ============================================================
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(230)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 20, 12, 20)
        sidebar_layout.setSpacing(6)
        
        # Logo / Brand
        brand_layout = QHBoxLayout()
        brand_icon = QLabel("🔍")
        brand_icon.setStyleSheet("font-size: 24px; background: transparent;")
        brand_layout.addWidget(brand_icon)
        brand_label = QLabel("LogiCheck")
        brand_label.setObjectName("brandLabel")
        brand_layout.addWidget(brand_label)
        brand_layout.addStretch()
        sidebar_layout.addLayout(brand_layout)
        
        version_label = QLabel("v1.2 — Ferretería Durán")
        version_label.setObjectName("versionLabel")
        sidebar_layout.addWidget(version_label)
        
        sidebar_layout.addSpacing(25)
        
        # Separator
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFixedHeight(1)
        sidebar_layout.addWidget(sep)
        sidebar_layout.addSpacing(10)
        
        section_label = QLabel("MENÚ PRINCIPAL")
        section_label.setObjectName("sectionLabel")
        sidebar_layout.addWidget(section_label)
        sidebar_layout.addSpacing(5)
        
        # Nav buttons — orden del flujo lógico
        self.nav_buttons = []
        nav_items = [
            ("📊", "Dashboard"),
            ("📄", "Factura PDF"),
            ("📹", "Análisis de Video"),
            ("🚛", "Asignación Vehicular"),
            ("📋", "Reportes"),
            ("📜", "Actividad"),
            ("👥", "Gestión de Usuarios"),
        ]
        
        for icon, text in nav_items:
            btn = NavButton(icon, text)
            btn.clicked.connect(lambda checked, t=text: self._on_nav_click(t))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)
        
        self.nav_buttons[0].setChecked(True)  # Dashboard activo por defecto
        
        sidebar_layout.addStretch()
        
        # Separator
        sep2 = QFrame()
        sep2.setObjectName("separator")
        sep2.setFixedHeight(1)
        sidebar_layout.addWidget(sep2)
        sidebar_layout.addSpacing(10)
        
        # Theme toggle
        theme_row = QHBoxLayout()
        theme_label = QLabel("🌙 Modo Oscuro")
        theme_label.setObjectName("themeLabel")
        self.theme_label = theme_label
        theme_row.addWidget(theme_label)
        theme_row.addStretch()
        self.toggle = AnimatedToggle()
        theme_row.addWidget(self.toggle)
        sidebar_layout.addLayout(theme_row)
        
        sidebar_layout.addSpacing(10)
        
        # User card — datos dinámicos desde la sesión
        user_card = QFrame()
        user_card.setObjectName("userCard")
        user_layout = QHBoxLayout(user_card)
        user_layout.setContentsMargins(10, 8, 10, 8)
        _role_icon = ROLE_ICONS.get(self._role, "👤")
        avatar = QLabel(_role_icon)
        avatar.setStyleSheet("font-size: 20px; background: transparent;")
        user_layout.addWidget(avatar)
        user_info = QVBoxLayout()
        user_info.setSpacing(0)
        user_name = QLabel(self._user.get("full_name", "Usuario"))
        user_name.setObjectName("userName")
        user_role_lbl = QLabel(get_role_display(self._role))
        user_role_lbl.setObjectName("userRole")
        user_info.addWidget(user_name)
        user_info.addWidget(user_role_lbl)
        user_layout.addLayout(user_info)
        user_layout.addStretch()
        sidebar_layout.addWidget(user_card)

        # Botón cerrar sesión
        self.btn_logout = QPushButton("  🔒  Cerrar Sesión")
        self.btn_logout.setObjectName("logoutBtn")
        self.btn_logout.setFixedHeight(38)
        self.btn_logout.setCursor(Qt.PointingHandCursor)
        self.btn_logout.clicked.connect(self._do_logout)
        sidebar_layout.addSpacing(6)
        sidebar_layout.addWidget(self.btn_logout)

        root_layout.addWidget(self.sidebar)

        # ============================================================
        # MAIN CONTENT AREA
        # ============================================================
        self.content_area = QFrame()
        self.content_area.setObjectName("contentArea")
        content_layout = QVBoxLayout(self.content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # --- Top Bar ---
        self.topbar = QFrame()
        self.topbar.setObjectName("topBar")
        self.topbar.setFixedHeight(56)
        topbar_layout = QHBoxLayout(self.topbar)
        topbar_layout.setContentsMargins(25, 0, 25, 0)
        
        self.page_title = QLabel("📊  Dashboard")
        self.page_title.setObjectName("pageTitle")
        topbar_layout.addWidget(self.page_title)
        
        topbar_layout.addStretch()
        
        # Date/Time
        self.datetime_label = QLabel()
        self.datetime_label.setObjectName("datetimeLabel")
        topbar_layout.addWidget(self.datetime_label)
        self._update_time()
        
        # Timer para reloj
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_time)
        self.clock_timer.start(1000)
        
        content_layout.addWidget(self.topbar)
        
        # --- Stacked Pages ---
        self.stacked = QStackedWidget()
        self.stacked.setObjectName("stackedWidget")
        content_layout.addWidget(self.stacked)
        
        # Fade overlay for smooth transitions (avoids QPainter conflicts)
        self._fade_overlay = QWidget(self.stacked)
        self._fade_overlay.setStyleSheet("background-color: rgba(30, 30, 46, 255);")
        self._fade_overlay.hide()
        self._fade_overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        # Opacity effect on the overlay only (not on the stacked)
        self._overlay_opacity = QGraphicsOpacityEffect(self._fade_overlay)
        self._overlay_opacity.setOpacity(1.0)
        self._fade_overlay.setGraphicsEffect(self._overlay_opacity)
        
        self._overlay_anim = QPropertyAnimation(self._overlay_opacity, b"opacity")
        self._overlay_anim.setEasingCurve(QEasingCurve.InOutCubic)
        
        # Page 0: Dashboard
        self.stacked.addWidget(self._create_dashboard_page())
        # Page 1: Factura PDF
        self.stacked.addWidget(self._create_invoice_page())
        # Page 2: Análisis de Video
        self.stacked.addWidget(self._create_video_page())
        # Page 3: Asignación Vehicular
        self.stacked.addWidget(self._create_vehicle_page())
        # Page 4: Reportes
        self.stacked.addWidget(self._create_reports_page())
        # Page 5: Actividad / Logs (todos los roles, filtrado por rol)
        self._logs_page = LogsPage(user_data=self._user)
        self.stacked.addWidget(self._logs_page)
        # Page 6: Gestión de Usuarios (solo Admin)
        self._users_page = UsersPage(admin_user_data=self._user)
        self.stacked.addWidget(self._users_page)
        
        root_layout.addWidget(self.content_area)
        
        # --- Status bar con indicador GPU ---
        self._status_bar = QStatusBar()
        self._status_bar.setObjectName("statusBar")
        _role_display = get_role_display(self._role)
        self._status_bar.showMessage(f"  ✅ Sistema listo  |  LogiCheck v1.2  |  Usuario: {self._user.get('full_name', '')}  |  Rol: {_role_display}")
        self.setStatusBar(self._status_bar)

        # ── GPU Status widget en la statusbar (derecha) ───────
        self._lbl_gpu = QLabel("🔵 CPU")
        self._lbl_gpu.setStyleSheet("font-size: 11px; color: #6c7086; padding: 0 10px;")
        self._status_bar.addPermanentWidget(self._lbl_gpu)
        self._gpu_timer = QTimer(self)
        self._gpu_timer.timeout.connect(self._update_gpu_status)
        self._gpu_timer.start(2500)
        self._update_gpu_status()

        # Inicializar tabla de auditorías al arrancar
        try:
            init_audits_table()
        except Exception:
            pass

        # ── Aplicar permisos según el rol activo ──────────────
        self._apply_role_permissions()
    
    def _update_gpu_status(self):
        """Actualiza el indicador de GPU en la barra de estado con uso real (tipo Task Manager)."""
        try:
            import torch
            if torch.cuda.is_available():
                # mem_get_info retorna (free_bytes, total_bytes)
                free, total = torch.cuda.mem_get_info(0)
                used_gb = (total - free) / (1024 ** 3)
                total_gb = total / (1024 ** 3)
                # Obtenemos el nombre dinámicamente (p.ej. RTX 3050 Laptop)
                name = torch.cuda.get_device_properties(0).name.replace("NVIDIA ", "")
                
                self._lbl_gpu.setText(f"🟢 {name}  {used_gb:.1f}/{total_gb:.1f} GB")
                self._lbl_gpu.setStyleSheet("font-size: 11px; color: #a6e3a1; font-weight: bold; padding: 0 10px;")
            else:
                self._lbl_gpu.setText("🔵 CPU (Modo Conservador)")
                self._lbl_gpu.setStyleSheet("font-size: 11px; color: #6c7086; padding: 0 10px;")
        except Exception:
            self._lbl_gpu.setText("🔵 CPU")
            self._lbl_gpu.setStyleSheet("font-size: 11px; color: #6c7086; padding: 0 10px;")

    # ----------------------------------------------------------------
    # PAGE BUILDERS
    # ----------------------------------------------------------------
    def _create_dashboard_page(self):
        """Página principal con resumen de estadísticas."""
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(page)
        
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(20)
        
        # Welcome banner
        welcome = GlowCard()
        welcome.setObjectName("welcomeBanner")
        welcome_layout = QHBoxLayout(welcome)
        welcome_layout.setContentsMargins(30, 25, 30, 25)
        welcome_text_layout = QVBoxLayout()
        welcome_title = QLabel("Bienvenido a LogiCheck")
        welcome_title.setObjectName("welcomeTitle")
        welcome_text_layout.addWidget(welcome_title)
        welcome_sub = QLabel("Sistema de auditoría logística con visión artificial para la Ferretería Durán, Apulo.\nOptimiza tus despachos, reduce errores y mejora la trazabilidad de los materiales.")
        welcome_sub.setObjectName("welcomeSub")
        welcome_sub.setWordWrap(True)
        welcome_text_layout.addWidget(welcome_sub)
        
        quick_actions = QHBoxLayout()
        btn_quick_video = QPushButton("📹  Analizar Video")
        btn_quick_video.setObjectName("primaryBtn")
        btn_quick_video.setCursor(Qt.PointingHandCursor)
        btn_quick_video.clicked.connect(lambda: self._on_nav_click("Análisis de Video"))
        quick_actions.addWidget(btn_quick_video)
        btn_quick_invoice = QPushButton("📄  Cargar Factura")
        btn_quick_invoice.setObjectName("secondaryBtn")
        btn_quick_invoice.setCursor(Qt.PointingHandCursor)
        btn_quick_invoice.clicked.connect(lambda: self._on_nav_click("Factura PDF"))
        quick_actions.addWidget(btn_quick_invoice)
        quick_actions.addStretch()
        welcome_text_layout.addLayout(quick_actions)
        welcome_layout.addLayout(welcome_text_layout)
        
        welcome_emoji = QLabel("🔍")
        welcome_emoji.setStyleSheet("font-size: 72px; background: transparent;")
        welcome_layout.addWidget(welcome_emoji, alignment=Qt.AlignRight | Qt.AlignVCenter)
        
        layout.addWidget(welcome)
        
        # Stat cards row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(15)
        
        self.stat_despachos = StatCard("📦", "0", "Despachos Auditados", "#89b4fa")
        self.stat_discrepancias = StatCard("⚠️", "0", "Discrepancias Detectadas", "#f38ba8")
        self.stat_accuracy = StatCard("✅", "—", "Precisión del Conteo", "#a6e3a1")
        self.stat_vehiculos = StatCard("🚛", "0", "Vehículos Asignados", "#fab387")
        
        stats_row.addWidget(self.stat_despachos)
        stats_row.addWidget(self.stat_discrepancias)
        stats_row.addWidget(self.stat_accuracy)
        stats_row.addWidget(self.stat_vehiculos)
        
        layout.addLayout(stats_row)
        
        # Bottom section: Recent activity + Model status
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(15)

        # Recent activity card (datos reales de SQLite)
        activity_card = GlowCard()
        activity_card.setObjectName("glowCard")
        activity_layout = QVBoxLayout(activity_card)
        activity_layout.setContentsMargins(20, 18, 20, 18)
        activity_header = QLabel("📋  Auditorías Recientes")
        activity_header.setObjectName("cardTitle")
        activity_layout.addWidget(activity_header)

        self.table_recent = QTableWidget(0, 4)
        self.table_recent.setHorizontalHeaderLabels(["Fecha", "Factura", "Resultado", "Vehículo"])
        self.table_recent.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_recent.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_recent.setAlternatingRowColors(True)
        self.table_recent.verticalHeader().setVisible(False)
        self.table_recent.setMinimumHeight(180)
        activity_layout.addWidget(self.table_recent)

        bottom_row.addWidget(activity_card, 3)

        # Trend Chart Card
        trend_card = GlowCard()
        trend_card.setObjectName("glowCard")
        trend_layout = QVBoxLayout(trend_card)
        trend_layout.setContentsMargins(20, 18, 20, 18)
        trend_header = QHBoxLayout()
        trend_title = QLabel("📈 Tendencia (Últimos 30 días)")
        trend_title.setObjectName("cardTitle")
        trend_header.addWidget(trend_title)
        trend_header.addStretch()
        legend_ia = QLabel("● Total")
        legend_ia.setStyleSheet("color: #89b4fa; font-size: 10px; font-weight: bold;")
        legend_disc = QLabel("● Discrepancias")
        legend_disc.setStyleSheet("color: #f38ba8; font-size: 10px; font-weight: bold;")
        trend_header.addWidget(legend_ia)
        trend_header.addWidget(legend_disc)
        trend_layout.addLayout(trend_header)

        self.chart_trends = ModernTrendChart()
        trend_layout.addWidget(self.chart_trends)
        
        bottom_row.addWidget(trend_card, 4)

        # Model info card
        model_card = GlowCard()
        model_card.setObjectName("glowCard")
        model_layout = QVBoxLayout(model_card)
        model_layout.setContentsMargins(20, 18, 20, 18)
        model_header = QLabel("🤖  Estado del Modelo IA")
        model_header.setObjectName("cardTitle")
        model_layout.addWidget(model_header)

        _cuda_state = ("✅ Precargado" if self._preloaded_model else "⏳ Carga en frío")
        _device_name = (self._preloaded_device or "CPU").upper()
        model_items = [
            ("Motor",    "YOLO11 (Ultralytics)"),
            ("Estado",   f"{_cuda_state} en {_device_name}"),
            ("Clase",    "Bulto de cemento (0)"),
            ("Modelo",   "bultos_cemento2/best.pt"),
        ]
        for key, val in model_items:
            row = QHBoxLayout()
            k_label = QLabel(key)
            k_label.setObjectName("modelKey")
            row.addWidget(k_label)
            row.addStretch()
            v_label = QLabel(val)
            v_label.setObjectName("modelValue")
            row.addWidget(v_label)
            model_layout.addLayout(row)

        model_layout.addStretch()
        bottom_row.addWidget(model_card, 2)
        layout.addLayout(bottom_row)
        layout.addStretch()
        
        return scroll
    
    def _create_video_page(self):
        """Página de análisis de video con YOLO."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(15)
        
        # Controls bar
        controls = GlowCard()
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(18, 12, 18, 12)
        
        self.btn_load_video = QPushButton("📂  Cargar Video")
        self.btn_load_video.setObjectName("primaryBtn")
        self.btn_load_video.setCursor(Qt.PointingHandCursor)
        self.btn_load_video.clicked.connect(self._on_load_video)
        controls_layout.addWidget(self.btn_load_video)

        # Analysis status: premium progress bar above the action button
        analysis_box = QVBoxLayout()
        analysis_box.setContentsMargins(0, 0, 0, 0)
        analysis_box.setSpacing(6)

        self.analysis_progress = QProgressBar()
        self.analysis_progress.setObjectName("analysisProgress")
        self.analysis_progress.setRange(0, 100)
        self.analysis_progress.setValue(0)
        self.analysis_progress.setTextVisible(False)
        self.analysis_progress.setFixedHeight(8)
        self.analysis_progress.setVisible(False)
        analysis_box.addWidget(self.analysis_progress)

        self.btn_start_analysis = QPushButton("▶  Iniciar Análisis YOLO")
        self.btn_start_analysis.setObjectName("successBtn")
        self.btn_start_analysis.setEnabled(False)
        self.btn_start_analysis.setCursor(Qt.PointingHandCursor)
        self.btn_start_analysis.clicked.connect(self._on_video_start)
        analysis_box.addWidget(self.btn_start_analysis)

        controls_layout.addLayout(analysis_box)
        
        self.btn_stop_analysis = QPushButton("⏹  Detener")
        self.btn_stop_analysis.setObjectName("dangerBtn")
        self.btn_stop_analysis.setCursor(Qt.PointingHandCursor)
        self.btn_stop_analysis.clicked.connect(self._on_video_stop)
        controls_layout.addWidget(self.btn_stop_analysis)
        
        controls_layout.addSpacing(15)
        
        # Line position slider
        line_box = QVBoxLayout()
        line_box.setSpacing(0)
        line_lbl = QLabel("Línea de Conteo")
        line_lbl.setObjectName("subtleText")
        line_lbl.setStyleSheet("font-size: 10px; margin-bottom: 2px;")
        line_box.addWidget(line_lbl)
        self.slider_line = QSlider(Qt.Horizontal)
        self.slider_line.setRange(5, 95)
        self.slider_line.setValue(18)
        self.slider_line.setFixedWidth(120)
        self.slider_line.valueChanged.connect(self._on_line_slider_changed)
        line_box.addWidget(self.slider_line)
        controls_layout.addLayout(line_box)
        
        self.lbl_line_val = QLabel("18%")
        self.lbl_line_val.setObjectName("modelValue")
        self.lbl_line_val.setFixedWidth(35)
        controls_layout.addWidget(self.lbl_line_val)
        
        controls_layout.addStretch()

        # Indicador de estado del motor IA (CUDA precargado o no)
        if can_do_action(self._role, "video.iniciar"):
            if self._preloaded_model is not None:
                _dev = (self._preloaded_device or "cpu").upper()
                self.lbl_model_status = QLabel(f"🧠 Motor IA listo ({_dev})")
                self.lbl_model_status.setStyleSheet(
                    "font-size: 10px; color: #a6e3a1; background: transparent;"
                )
            else:
                self.lbl_model_status = QLabel("⚠️ Motor IA: carga en frío")
                self.lbl_model_status.setStyleSheet(
                    "font-size: 10px; color: #f9e2af; background: transparent;"
                )
            controls_layout.addWidget(self.lbl_model_status)

        self.lbl_video_name = QLabel("Ningún video seleccionado")
        self.lbl_video_name.setObjectName("subtleText")
        controls_layout.addWidget(self.lbl_video_name)
        
        layout.addWidget(controls)
        
        # Video + Sidebar
        video_row = QHBoxLayout()
        video_row.setSpacing(15)
        
        # Video frame
        video_container = GlowCard()
        video_container_layout = QVBoxLayout(video_container)
        video_container_layout.setContentsMargins(5, 5, 5, 5)
        video_container_layout.setSpacing(6)

        # Status pill (premium indicator)
        status_row = QHBoxLayout()
        status_row.setContentsMargins(10, 8, 10, 0)
        self.video_status = QLabel("⏸  Sin video")
        self.video_status.setObjectName("videoStatusPill")
        self.video_status.setProperty("state", "idle")
        status_row.addWidget(self.video_status, alignment=Qt.AlignLeft)
        status_row.addStretch()
        video_container_layout.addLayout(status_row)
        
        self.video_frame = QLabel("📹\n\nCargue un video desde la USB\npara visualizar la detección con IA")
        self.video_frame.setObjectName("videoFrame")
        self.video_frame.setAlignment(Qt.AlignCenter)
        self.video_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_frame.setMinimumHeight(400)
        video_container_layout.addWidget(self.video_frame)
        
        # Video Slider
        self.video_slider = AuditScrubSlider(Qt.Horizontal)
        self.video_slider.setObjectName("videoSlider")
        self.video_slider.setRange(0, 1000)
        self.video_slider.setEnabled(False)
        self._is_scrubbing = False
        self.video_slider.sliderPressed.connect(self._on_video_slider_pressed)
        self.video_slider.sliderReleased.connect(self._on_video_slider_released)
        self.video_slider.sliderMoved.connect(self._on_video_slider_moved)
        self.video_slider.setMouseTracking(True)
        self.video_slider.installEventFilter(self)
        video_container_layout.addWidget(self.video_slider)

        # Scrub thumbnail popup
        self.scrub_thumbnail_popup = ScrubThumbnailWidget(self)
        self.scrub_thumbnail_popup.hide()
        self._thumbnails_cache = {} # {frame_idx: QPixmap}

        # Scrub tooltip (timestamp)
        self.scrub_tooltip = QLabel(video_container)
        self.scrub_tooltip.setObjectName("scrubTooltip")
        self.scrub_tooltip.setVisible(False)
        self.scrub_tooltip.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        # Player Controls Bar
        player_bar = QHBoxLayout()
        player_bar.setContentsMargins(10, 0, 10, 5)
        
        self.btn_play_pause = QPushButton("▶")
        self.btn_play_pause.setObjectName("playerBtn")
        self.btn_play_pause.setFixedSize(36, 36)
        self.btn_play_pause.setEnabled(False)
        self.btn_play_pause.clicked.connect(self._on_video_play_pause)
        player_bar.addWidget(self.btn_play_pause)
        
        self.btn_prev_frame = QPushButton("Step -")
        self.btn_prev_frame.setObjectName("playerBtn_small")
        self.btn_prev_frame.setEnabled(False)
        self.btn_prev_frame.clicked.connect(self._on_video_prev_frame)
        player_bar.addWidget(self.btn_prev_frame)
        
        self.btn_next_frame = QPushButton("Step +")
        self.btn_next_frame.setObjectName("playerBtn_small")
        self.btn_next_frame.setEnabled(False)
        self.btn_next_frame.clicked.connect(self._on_video_next_frame)
        player_bar.addWidget(self.btn_next_frame)
        
        player_bar.addSpacing(10)
        
        self.btn_rewind = QPushButton("⏪ 10s")
        self.btn_rewind.setObjectName("playerBtn_small")
        self.btn_rewind.setEnabled(False)
        self.btn_rewind.clicked.connect(self._on_video_rewind)
        player_bar.addWidget(self.btn_rewind)
        
        self.btn_forward = QPushButton("⏩ 10s")
        self.btn_forward.setObjectName("playerBtn_small")
        self.btn_forward.setEnabled(False)
        self.btn_forward.clicked.connect(self._on_video_forward)
        player_bar.addWidget(self.btn_forward)
        
        player_bar.addStretch()

        # Playback speed selector (YouTube-like menu + custom)
        self._playback_speed = 1.0
        self._speed_presets = [1.0, 1.25, 1.5, 2.0, 3.0]

        self.btn_speed = QToolButton()
        self.btn_speed.setObjectName("speedBtn")
        self.btn_speed.setCursor(Qt.PointingHandCursor)
        self._refresh_speed_button_text()
        self.btn_speed.clicked.connect(self._open_speed_panel)
        player_bar.addWidget(self.btn_speed)
        
        # Snapshot button
        self.btn_snapshot = QPushButton("📸 Captura")
        self.btn_snapshot.setObjectName("playerBtn_accent")
        self.btn_snapshot.setEnabled(False)
        self.btn_snapshot.clicked.connect(self._take_snapshot)
        player_bar.addWidget(self.btn_snapshot)
        
        player_bar.addSpacing(15)
        
        self.lbl_frame_time = QLabel("00:00 / 00:00")
        self.lbl_frame_time.setObjectName("subtleText")
        player_bar.addWidget(self.lbl_frame_time)
        
        video_container_layout.addLayout(player_bar)
        
        video_row.addWidget(video_container, 3)
        
        # Live results sidebar
        results_panel = GlowCard()
        results_panel.setFixedWidth(320)
        results_layout = QVBoxLayout(results_panel)
        results_layout.setContentsMargins(18, 15, 18, 15)
        
        results_header = QLabel("📊  Conteo en Tiempo Real")
        results_header.setObjectName("cardTitle")
        results_layout.addWidget(results_header)
        
        self.table_conteo = QTableWidget(3, 3)
        self.table_conteo.setHorizontalHeaderLabels(["Material", "Conteo IA", "Factura"])
        self.table_conteo.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_conteo.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_conteo.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_conteo.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_conteo.setAlternatingRowColors(True)
        self.table_conteo.verticalHeader().setVisible(False)
        
        default_materials = ["Cemento", "Tubería Presión", "Tubería Sanitaria"]
        for i, mat in enumerate(default_materials):
            self.table_conteo.setItem(i, 0, QTableWidgetItem(mat))
            self.table_conteo.setItem(i, 1, QTableWidgetItem("0"))
            self.table_conteo.setItem(i, 2, QTableWidgetItem("—"))
        
        results_layout.addWidget(self.table_conteo)

        results_layout.addSpacing(8)

        # ── Panel Comparación IA vs Factura ───────────────────
        cmp_header = QLabel("📊  IA vs Factura")
        cmp_header.setObjectName("cardTitle")
        results_layout.addWidget(cmp_header)

        self.lbl_audit_result = QLabel("—  Sin análisis")
        self.lbl_audit_result.setObjectName("auditResultBadge")
        self.lbl_audit_result.setAlignment(Qt.AlignCenter)
        self.lbl_audit_result.setFixedHeight(32)
        results_layout.addWidget(self.lbl_audit_result)

        self.table_comparison = QTableWidget(0, 4)
        self.table_comparison.setHorizontalHeaderLabels(["Material", "Factura", "IA", "Δ"])
        self.table_comparison.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_comparison.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_comparison.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_comparison.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_comparison.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_comparison.setAlternatingRowColors(True)
        self.table_comparison.verticalHeader().setVisible(False)
        self.table_comparison.setMaximumHeight(120)
        results_layout.addWidget(self.table_comparison)

        results_layout.addSpacing(8)

        # Registro de eventos (con salto a frame)
        alertas_header = QLabel("🔔  Registro de Detecciones")
        alertas_header.setObjectName("cardTitle")
        results_layout.addWidget(alertas_header)

        self.list_detections = QListWidget()
        self.list_detections.setObjectName("detectionsList")
        self.list_detections.setMinimumHeight(120)
        self.list_detections.setToolTip("Doble clic para saltar al frame de esa detección")
        self.list_detections.itemDoubleClicked.connect(self._on_detection_jump)
        results_layout.addWidget(self.list_detections)

        video_row.addWidget(results_panel)
        layout.addLayout(video_row)
        return page
    
    def _create_invoice_page(self):
        """Página para cargar y analizar factura PDF."""
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(page)
        
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(20)
        
        # Upload area — Drag/Drop styled zone
        upload_card = GlowCard()
        upload_card.setObjectName("glowCard")
        upload_card.setMinimumHeight(280)  # Increased min height
        upload_main = QVBoxLayout(upload_card)
        upload_main.setContentsMargins(0, 0, 0, 0)
        
        # Inner dashed zone
        drop_zone = QFrame()
        drop_zone.setObjectName("videoFrame")
        drop_zone_layout = QVBoxLayout(drop_zone)
        drop_zone_layout.setContentsMargins(40, 20, 40, 20)
        drop_zone_layout.setSpacing(12)
        
        drop_zone_layout.addStretch()  # Center from top
        
        upload_icon = QLabel("📄")
        upload_icon.setStyleSheet("font-size: 48px; background: transparent; border: none;")
        upload_icon.setAlignment(Qt.AlignCenter)
        drop_zone_layout.addWidget(upload_icon)
        
        upload_title = QLabel("Cargar Factura Electrónica")
        upload_title.setObjectName("welcomeTitle")
        upload_title.setAlignment(Qt.AlignCenter)
        drop_zone_layout.addWidget(upload_title)
        
        upload_desc = QLabel(
            "Suba la factura electrónica en formato PDF expedida por la Ferretería Durán "
            "para extraer automáticamente los materiales, cantidades y datos relevantes."
        )
        upload_desc.setObjectName("subtleText")
        upload_desc.setAlignment(Qt.AlignCenter)
        upload_desc.setStyleSheet("font-size: 14px; background: transparent; border: none; color: #a6adc8;")
        upload_desc.setWordWrap(True)
        upload_desc.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        drop_zone_layout.addWidget(upload_desc)
        
        drop_zone_layout.addSpacing(10)
        
        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignCenter)
        self.btn_load_invoice = QPushButton("📂  Seleccionar Archivo PDF")
        self.btn_load_invoice.setObjectName("primaryBtn")
        self.btn_load_invoice.setCursor(Qt.PointingHandCursor)
        self.btn_load_invoice.setFixedWidth(280)
        self.btn_load_invoice.clicked.connect(self._load_invoice)
        btn_row.addWidget(self.btn_load_invoice)
        drop_zone_layout.addLayout(btn_row)
        
        self.lbl_invoice_status = QLabel("Sin factura cargada")
        self.lbl_invoice_status.setObjectName("subtleText")
        self.lbl_invoice_status.setAlignment(Qt.AlignCenter)
        self.lbl_invoice_status.setStyleSheet("font-size: 13px; background: transparent; border: none; color: #6c7086;")
        drop_zone_layout.addWidget(self.lbl_invoice_status)
        
        drop_zone_layout.addStretch()  # Center from bottom
        
        upload_main.addWidget(drop_zone)
        layout.addWidget(upload_card)
        
        # Invoice metadata card (after loading)
        meta_card = GlowCard()
        meta_card.setObjectName("glowCard")
        meta_layout = QVBoxLayout(meta_card)
        meta_layout.setContentsMargins(20, 18, 20, 18)
        
        meta_header = QLabel("🏢  Información de la Factura")
        meta_header.setObjectName("cardTitle")
        meta_layout.addWidget(meta_header)
        
        # Info grid
        info_grid = QHBoxLayout()
        info_grid.setSpacing(30)
        
        # Column 1: Factura info
        col1 = QVBoxLayout()
        col1.setSpacing(4)
        self.lbl_factura_no = QLabel("Nro. Factura:  —")
        self.lbl_factura_no.setObjectName("modelValue")
        col1.addWidget(self.lbl_factura_no)
        self.lbl_factura_fecha = QLabel("Fecha:  —")
        self.lbl_factura_fecha.setObjectName("modelValue")
        col1.addWidget(self.lbl_factura_fecha)
        info_grid.addLayout(col1)
        
        # Column 2: Client info
        col2 = QVBoxLayout()
        col2.setSpacing(4)
        self.lbl_factura_cliente = QLabel("Cliente:  —")
        self.lbl_factura_cliente.setObjectName("modelValue")
        col2.addWidget(self.lbl_factura_cliente)
        self.lbl_factura_total = QLabel("Total a Pagar:  —")
        self.lbl_factura_total.setObjectName("modelValue")
        col2.addWidget(self.lbl_factura_total)
        info_grid.addLayout(col2)
        
        # Column 3: YOLO items summary
        col3 = QVBoxLayout()
        col3.setSpacing(4)
        self.lbl_factura_items = QLabel("Productos YOLO:  —")
        self.lbl_factura_items.setObjectName("modelValue")
        col3.addWidget(self.lbl_factura_items)
        self.lbl_factura_nit = QLabel("Total Ítems Factura:  —")
        self.lbl_factura_nit.setObjectName("modelValue")
        col3.addWidget(self.lbl_factura_nit)
        info_grid.addLayout(col3)
        
        meta_layout.addLayout(info_grid)
        layout.addWidget(meta_card)
        
        # Extracted data table
        data_card = GlowCard()
        data_card.setObjectName("glowCard")
        data_layout = QVBoxLayout(data_card)
        data_layout.setContentsMargins(20, 18, 20, 18)
        
        data_header = QLabel("🤖  Productos para Detección YOLO")
        data_header.setObjectName("cardTitle")
        data_layout.addWidget(data_header)
        
        # sub-label explaining the filter
        data_sub = QLabel("Solo se muestran los productos detectables por visión artificial: Cemento, Tubería Presión y Tubería Sanitaria.")
        data_sub.setObjectName("subtleText")
        data_sub.setWordWrap(True)
        data_sub.setStyleSheet("font-size: 12px; color: #0c0c0d; background: transparent; border: none;") # Changed color to black as per instruction
        data_layout.addWidget(data_sub)
        
        self.table_invoice_data = QTableWidget(0, 4)
        self.table_invoice_data.setHorizontalHeaderLabels([
            "Categoría YOLO", "Descripción en Factura", "Cantidad Factura", "Valor Bruto"
        ])
        self.table_invoice_data.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_invoice_data.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_invoice_data.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_invoice_data.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_invoice_data.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_invoice_data.setAlternatingRowColors(True)
        self.table_invoice_data.verticalHeader().setVisible(False)
        self.table_invoice_data.setMinimumHeight(250)
        data_layout.addWidget(self.table_invoice_data)
        
        layout.addWidget(data_card)
        layout.addStretch()
        
        return scroll
    
    def _create_vehicle_page(self):
        """Página de asignación vehicular."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(20)
        
        # Summary cards
        summary_row = QHBoxLayout()
        summary_row.setSpacing(15)
        
        self.card_peso = StatCard("⚖️", "0 Kg", "Peso Total del Despacho", "#f9e2af")
        self.card_volumen = StatCard("📐", "0 m³", "Volumen Total del Despacho", "#89dceb")
        self.card_vehiculo = StatCard("🚛", "N/A", "Vehículo Recomendado", "#a6e3a1")
        self.card_capacidad = StatCard("📊", "—", "Uso de Capacidad", "#cba6f7")
        
        summary_row.addWidget(self.card_peso)
        summary_row.addWidget(self.card_volumen)
        summary_row.addWidget(self.card_vehiculo)
        summary_row.addWidget(self.card_capacidad)
        
        layout.addLayout(summary_row)
        
        # Vehicle details
        details_card = GlowCard()
        details_layout = QVBoxLayout(details_card)
        details_layout.setContentsMargins(20, 18, 20, 18)
        
        details_header = QLabel("🚛  Flota Disponible")
        details_header.setObjectName("cardTitle")
        details_layout.addWidget(details_header)
        
        self.table_vehicles = QTableWidget(0, 5)
        self.table_vehicles.setHorizontalHeaderLabels(["Tipo", "Placa", "Cap. Peso (Kg)", "Cap. Volumen (m³)", "Estado"])
        self.table_vehicles.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_vehicles.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_vehicles.setAlternatingRowColors(True)
        self.table_vehicles.verticalHeader().setVisible(False)
        self.table_vehicles.setMinimumHeight(250)
        details_layout.addWidget(self.table_vehicles)
        
        layout.addWidget(details_card)

        # --- Botón de asignación ---
        assign_row = QHBoxLayout()
        self.btn_assign_vehicle = QPushButton("🚛  Confirmar Asignación Vehicular")
        self.btn_assign_vehicle.setObjectName("successBtn")
        self.btn_assign_vehicle.setFixedHeight(44)
        self.btn_assign_vehicle.setCursor(Qt.PointingHandCursor)
        self.btn_assign_vehicle.clicked.connect(self._on_vehicle_assigned)
        assign_row.addStretch()
        assign_row.addWidget(self.btn_assign_vehicle)
        layout.addLayout(assign_row)

        layout.addStretch()
        
        return page
    
    def _create_reports_page(self):
        """Página de reportes y exportación."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(20)
        
        # Export options
        export_card = GlowCard()
        export_layout = QVBoxLayout(export_card)
        export_layout.setContentsMargins(30, 25, 30, 25)
        
        export_header = QLabel("📋  Generar Reporte de Auditoría")
        export_header.setObjectName("cardTitle")
        export_layout.addWidget(export_header)
        
        export_desc = QLabel("Genera un reporte completo con los resultados de la auditoría logística.\nIncluye conteo por IA vs factura, discrepancias, asignación vehicular y recomendaciones.")
        export_desc.setObjectName("welcomeSub")
        export_desc.setWordWrap(True)
        export_layout.addWidget(export_desc)
        
        export_layout.addSpacing(15)
        
        btns_row = QHBoxLayout()
        
        self.btn_export_pdf = QPushButton("📄  Exportar a PDF")
        self.btn_export_pdf.setObjectName("primaryBtn")
        self.btn_export_pdf.setCursor(Qt.PointingHandCursor)
        self.btn_export_pdf.clicked.connect(lambda: self._log_export("PDF"))
        btns_row.addWidget(self.btn_export_pdf)
        
        self.btn_export_excel = QPushButton("📊  Exportar a Excel")
        self.btn_export_excel.setObjectName("successBtn")
        self.btn_export_excel.setCursor(Qt.PointingHandCursor)
        self.btn_export_excel.clicked.connect(lambda: self._log_export("Excel"))
        btns_row.addWidget(self.btn_export_excel)
        
        btns_row.addStretch()
        export_layout.addLayout(btns_row)
        
        layout.addWidget(export_card)
        
        # History
        history_card = GlowCard()
        history_layout = QVBoxLayout(history_card)
        history_layout.setContentsMargins(20, 18, 20, 18)
        
        history_header = QHBoxLayout()
        history_title = QLabel("🕐  Historial de Auditorías")
        history_title.setObjectName("cardTitle")
        history_header.addWidget(history_title)
        
        history_header.addStretch()
        btn_refresh_history = QPushButton("🔄 Actualizar")
        btn_refresh_history.setCursor(Qt.PointingHandCursor)
        btn_refresh_history.setObjectName("secondaryBtn")
        btn_refresh_history.clicked.connect(self._refresh_history_table)
        history_header.addWidget(btn_refresh_history)
        history_layout.addLayout(history_header)
        
        self.table_history = QTableWidget(0, 7)
        self.table_history.setHorizontalHeaderLabels(["Fecha", "Factura", "Materiales", "Discrep.\n(IA - Fac)", "Vehículo", "Estado", "Acción"])
        self.table_history.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_history.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_history.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_history.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_history.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table_history.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table_history.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table_history.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_history.setAlternatingRowColors(True)
        self.table_history.verticalHeader().setVisible(False)
        self.table_history.setShowGrid(False)
        self.table_history.setMinimumHeight(280)
        history_layout.addWidget(self.table_history)
        
        layout.addWidget(history_card)

        # Captures History section
        captures_card = GlowCard()
        captures_layout = QVBoxLayout(captures_card)
        captures_layout.setContentsMargins(20, 18, 20, 18)
        
        captures_header = QLabel("📸  Historial de Capturas (Evidencia Visual)")
        captures_header.setObjectName("cardTitle")
        captures_layout.addWidget(captures_header)
        
        self.list_captures = QListWidget()
        self.list_captures.setObjectName("detectionsList") # Reusar estilo
        self.list_captures.setMinimumHeight(150)
        self.list_captures.setFlow(QListWidget.LeftToRight)
        self.list_captures.setWrapping(True)
        self.list_captures.setResizeMode(QListWidget.Adjust)
        self.list_captures.setSpacing(10)
        self.list_captures.setIconSize(QSize(120, 90))
        captures_layout.addWidget(self.list_captures)
        
        layout.addWidget(captures_card)
        layout.addStretch()
        
        # Cargar datos iniciales
        QTimer.singleShot(100, self._refresh_history_table)
        
        return page
    
    # ----------------------------------------------------------------
    # PERMISOS POR ROL
    # ----------------------------------------------------------------
    def _apply_role_permissions(self):
        """
        Oculta/deshabilita nav buttons y botones de acción
        según el rol del usuario autenticado.
        """
        role = self._role

        # Mapa: nombre de página → índice en nav_buttons (mismo orden)
        page_names = [
            "Dashboard",
            "Factura PDF",
            "Análisis de Video",
            "Asignación Vehicular",
            "Reportes",
            "Actividad",
            "Gestión de Usuarios",
        ]

        for i, (btn, page) in enumerate(zip(self.nav_buttons, page_names)):
            allowed = can_access_page(role, page)
            btn.setVisible(allowed)
            btn.setEnabled(allowed)

        # ── Acciones individuales en páginas ──────────────────

        # Factura PDF: solo Op. Factura y Admin pueden cargar
        if hasattr(self, "btn_load_invoice"):
            self.btn_load_invoice.setVisible(can_do_action(role, "factura.cargar"))

        # Análisis de Video: iniciar/detener solo Op. Video y Admin
        if hasattr(self, "btn_start_analysis"):
            can_video = can_do_action(role, "video.iniciar")
            self.btn_start_analysis.setVisible(can_video)
            self.btn_stop_analysis.setVisible(can_video)
            self.btn_load_video.setVisible(can_video)

        # Si el rol no puede ver la primera página activa, ir al Dashboard
        if not can_access_page(role, "Dashboard"):
            # En principio todos ven el dashboard, pero por seguridad:
            self.stacked.setCurrentIndex(0)

    # ----------------------------------------------------------------
    # NAVIGATION
    # ----------------------------------------------------------------
    def _on_nav_click(self, page_name):
        # Verificar permiso antes de navegar
        if not can_access_page(self._role, page_name):
            app_logger.log_action(self._user, app_logger.ACCESO_DENEGADO,
                                  f"Intentó acceder a '{page_name}' | Rol: {self._role}")
            QMessageBox.warning(
                self,
                "Acceso denegado",
                f"Tu rol ({get_role_display(self._role)}) no tiene acceso a esta sección."
            )
            return

        page_map = {
            "Dashboard": 0,
            "Factura PDF": 1,
            "Análisis de Video": 2,
            "Asignación Vehicular": 3,
            "Reportes": 4,
            "Actividad": 5,
            "Gestión de Usuarios": 6,
        }

        icons = ["📊", "📄", "📹", "🚛", "📋", "📜", "👥"]

        # Refrescar páginas al navegar a ellas
        if page_name == "Gestión de Usuarios" and hasattr(self, "_users_page"):
            self._users_page.refresh_table()
        if page_name == "Actividad" and hasattr(self, "_logs_page"):
            self._logs_page.refresh()

        idx = page_map.get(page_name, 0)

        # Don't animate if clicking the same page
        if self.stacked.currentIndex() == idx:
            return
        
        self._pending_page_idx = idx
        self._pending_page_name = page_name
        self._pending_page_icons = icons
        
        # Update nav buttons immediately for responsiveness
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == idx)
        
        # Show the overlay covering the stacked area and fade it IN (cover old page)
        self._fade_overlay.setGeometry(self.stacked.rect())
        self._fade_overlay.show()
        self._fade_overlay.raise_()
        
        self._overlay_anim.stop()
        self._overlay_opacity.setOpacity(0.0)
        self._overlay_anim.setStartValue(0.0)
        self._overlay_anim.setEndValue(1.0)
        self._overlay_anim.setDuration(120)
        
        try:
            self._overlay_anim.finished.disconnect()
        except RuntimeError:
            pass
        self._overlay_anim.finished.connect(self._on_cover_done)
        self._overlay_anim.start()
    
    def _on_cover_done(self):
        """Called when overlay fully covers old content. Switch page, then fade overlay out."""
        idx = self._pending_page_idx
        icons = self._pending_page_icons
        page_name = self._pending_page_name
        
        self.stacked.setCurrentIndex(idx)
        self.page_title.setText(f"{icons[idx]}  {page_name}")
        
        # Fade overlay OUT to reveal new page
        try:
            self._overlay_anim.finished.disconnect()
        except RuntimeError:
            pass
        
        self._overlay_anim.setStartValue(1.0)
        self._overlay_anim.setEndValue(0.0)
        self._overlay_anim.setDuration(200)
        self._overlay_anim.finished.connect(self._on_reveal_done)
        self._overlay_anim.start()
        
        # Animate stat cards if dashboard
        if idx == 0:
            QTimer.singleShot(250, self._animate_dashboard_stats)
    
    def _on_reveal_done(self):
        """Called when overlay has fully faded out. Hide it."""
        try:
            self._overlay_anim.finished.disconnect()
        except RuntimeError:
            pass
        self._fade_overlay.hide()
    
    def resizeEvent(self, event):
        """Keep overlay sized to stacked widget."""
        super().resizeEvent(event)
        if hasattr(self, '_fade_overlay'):
            self._fade_overlay.setGeometry(self.stacked.rect())
        # Keep scrub tooltip from drifting on resize
        if hasattr(self, "_is_scrubbing") and self._is_scrubbing and hasattr(self, "video_slider"):
            try:
                self._update_scrub_tooltip(self.video_slider.value())
            except Exception:
                pass

    def keyPressEvent(self, event):
        """Atajos de teclado estilo player (solo en Análisis de Video)."""
        try:
            if self.stacked.currentIndex() == 2:  # Video page
                key = event.key()
                if key == Qt.Key_Space:
                    if hasattr(self, "btn_play_pause") and self.btn_play_pause.isEnabled():
                        self._on_video_play_pause()
                        event.accept()
                        return
                if key == Qt.Key_Left:
                    if hasattr(self, "player_worker") and self.player_worker and self.player_worker.isRunning():
                        self._on_video_rewind()
                        event.accept()
                        return
                if key == Qt.Key_Right:
                    if hasattr(self, "player_worker") and self.player_worker and self.player_worker.isRunning():
                        self._on_video_forward()
                        event.accept()
                        return
                if key == Qt.Key_Up:
                    self._set_playback_speed(float(getattr(self, "_playback_speed", 1.0)) + 0.1)
                    event.accept()
                    return
                if key == Qt.Key_Down:
                    self._set_playback_speed(float(getattr(self, "_playback_speed", 1.0)) - 0.1)
                    event.accept()
                    return
        except Exception:
            pass
        super().keyPressEvent(event)
    
    def _animate_dashboard_stats(self):
        """Lee datos REALES de SQLite para animar las tarjetas del Dashboard."""
        try:
            stats = get_dashboard_stats()
            self.stat_despachos.animate_to(stats["despachos_hoy"])
            self.stat_discrepancias.animate_to(stats["discrepancias_hoy"])
            self.stat_vehiculos.animate_to(stats["vehiculos_hoy"])
            acc = stats["accuracy_pct"]
            self.stat_accuracy.set_value(f"{acc:.1f}%")

            # Tabla de auditorías recientes
            recent = stats.get("recent_audits", [])
            self.table_recent.setRowCount(0)
            if recent:
                for row_data in recent:
                    r = self.table_recent.rowCount()
                    self.table_recent.insertRow(r)
                    # Fecha abreviada
                    fecha = str(row_data.get("fecha", ""))[:16]
                    self.table_recent.setItem(r, 0, QTableWidgetItem(fecha))
                    self.table_recent.setItem(r, 1, QTableWidgetItem(str(row_data.get("factura_no", "—"))))
                    result_item = QTableWidgetItem(str(row_data.get("resultado", "—")))
                    result_color = QColor("#a6e3a1") if row_data.get("resultado") == "CONFORME" else QColor("#f38ba8")
                    result_item.setForeground(result_color)
                    self.table_recent.setItem(r, 2, result_item)
                    self.table_recent.setItem(r, 3, QTableWidgetItem(str(row_data.get("vehiculo", "—"))))
            else:
                self.table_recent.setRowCount(1)
                self.table_recent.setItem(0, 0, QTableWidgetItem("—"))
                self.table_recent.setItem(0, 1, QTableWidgetItem("Sin auditorías aún"))
                self.table_recent.setItem(0, 2, QTableWidgetItem("—"))
                self.table_recent.setItem(0, 3, QTableWidgetItem("—"))
        except Exception as e:
            print(f"[DASHBOARD] Error cargando stats reales: {e}")
            self.stat_despachos.animate_to(0)
            self.stat_discrepancias.animate_to(0)
            self.stat_vehiculos.animate_to(0)

        # Cargar Gráfica de Tendencia
        try:
            trends = get_monthly_trends()
            # Si no hay datos, crear unos pocos dummy para visualización inicial (opcional)
            if not trends:
                trends = [{"total": 0, "discrepancies": 0} for _ in range(7)]
            self.chart_trends.set_data(trends)
        except Exception as e:
            print(f"[DASHBOARD] Error cargando tendencias: {e}")
    
    # ----------------------------------------------------------------
    # THEME TOGGLE
    # ----------------------------------------------------------------
    def toggle_theme(self):
        self._is_dark = not self._is_dark
        if self._is_dark:
            self.theme_label.setText("🌙 Modo Oscuro")
            self._apply_dark_theme()
            app_logger.log_action(self._user, app_logger.TEMA_CAMBIADO,
                                  "Cambió a Modo Oscuro")
        else:
            self.theme_label.setText("☀️ Modo Claro")
            self._apply_light_theme()
            app_logger.log_action(self._user, app_logger.TEMA_CAMBIADO,
                                  "Cambió a Modo Claro")
    
    def _apply_dark_theme(self):
        try:
            import os
            from PySide6.QtWidgets import QApplication
            qss_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "style.qss")
            with open(qss_path, "r") as f:
                QApplication.instance().setStyleSheet(f.read())
            self._fade_overlay.setStyleSheet("background-color: rgba(30, 30, 46, 255);")
        except Exception:
            pass
    
    def _apply_light_theme(self):
        try:
            import os
            from PySide6.QtWidgets import QApplication
            qss_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources", "style_light.qss")
            with open(qss_path, "r") as f:
                QApplication.instance().setStyleSheet(f.read())
            self._fade_overlay.setStyleSheet("background-color: rgba(239, 241, 245, 255);")
        except Exception:
            pass
    
    # ----------------------------------------------------------------
    # UTILITIES
    # ----------------------------------------------------------------
    def _update_time(self):
        now = datetime.datetime.now()
        self.datetime_label.setText(f"📅 {now.strftime('%d/%m/%Y')}   🕐 {now.strftime('%H:%M:%S')}")

    def _do_logout(self):
        """Confirma y cierra sesión volviendo al login."""
        reply = QMessageBox.question(
            self,
            "Cerrar Sesión",
            f"¿Deseas cerrar la sesión de '{self._user.get('full_name', '')}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            app_logger.log_action(self._user, app_logger.LOGOUT,
                                  f"Sesión cerrada por el usuario")
            self.logout_requested.emit()
            self.close()


    # ----------------------------------------------------------------
    # PDF INVOICE LOGIC
    # ----------------------------------------------------------------
    def _load_invoice(self):
        """Abre un diálogo para seleccionar el PDF y lo procesa."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Factura Electrónica",
            "",
            "Archivos PDF (*.pdf);;Todos los archivos (*)"
        )
        if not path:
            return

        # Show loading state
        self.lbl_invoice_status.setText("⏳  Leyendo factura...")
        self.btn_load_invoice.setEnabled(False)
        self.btn_load_invoice.setText("   Procesando...")

        # Parse
        if self._invoice_parser is None:
            QMessageBox.critical(
                self,
                "Error",
                "PyMuPDF no está instalado.\n\nEjecuta en la terminal:\n  pip install PyMuPDF"
            )
            self._reset_load_button()
            return

        try:
            invoice = self._invoice_parser.parse(path)
            self._current_invoice = invoice

            if invoice.parse_error:
                QMessageBox.warning(
                    self,
                    "Advertencia al leer PDF",
                    f"El archivo se leyó pero hubo un problema:\n{invoice.parse_error}\n\n"
                    "Se mostrarán los datos encontrados de todas formas."
                )

            self._populate_invoice_ui(invoice)
            # Log de factura cargada
            import os as _os
            app_logger.log_action(self._user, app_logger.FACTURA_CARGADA,
                                  f"Archivo: {_os.path.basename(path)}")

        except Exception as e:
            QMessageBox.critical(self, "Error al leer PDF", str(e))
            app_logger.log_action(self._user, app_logger.FACTURA_CARGADA,
                                  f"ERROR al leer: {os.path.basename(path)} — {e}")
        finally:
            self._reset_load_button()

    def _reset_load_button(self):
        self.btn_load_invoice.setEnabled(True)
        self.btn_load_invoice.setText("📂  Seleccionar Archivo PDF")

    def _populate_invoice_ui(self, invoice):
        """Llena los controles de la página de factura con los datos extraídos."""
        filename = os.path.basename(invoice.pdf_path)

        # Status label
        if invoice.total_yolo_items > 0:
            self.lbl_invoice_status.setText(
                f"✅  {filename}  —  "
                f"{invoice.total_yolo_items} producto(s) YOLO de {invoice.total_items_factura} ítems totales"
            )
            self.lbl_invoice_status.setStyleSheet(
                "font-size: 13px; background: transparent; border: none; color: #a6e3a1;"
            )
        else:
            self.lbl_invoice_status.setText(
                f"⚠️  {filename}  —  No se encontraron productos de cemento ni tubería en la factura"
            )
            self.lbl_invoice_status.setStyleSheet(
                "font-size: 13px; background: transparent; border: none; color: #f9e2af;"
            )
            # Log de factura sin productos detectables
            app_logger.log_action(self._user, app_logger.FACTURA_ADVERTENCIA,
                                  f"⚠️ Sin productos YOLO detectables en '{filename}'")

        # Log de error de parseo (si lo hay)
        if invoice.parse_error:
            app_logger.log_action(self._user, app_logger.FACTURA_ADVERTENCIA,
                                  f"Error al parsear '{filename}': {invoice.parse_error}")

        # Metadata labels
        self.lbl_factura_no.setText(f"Nro. Factura:  {invoice.numero_factura}")
        self.lbl_factura_fecha.setText(f"Fecha:  {invoice.fecha_expedicion}")
        self.lbl_factura_cliente.setText(f"Cliente:  {invoice.cliente}")
        self.lbl_factura_total.setText(f"Total a Pagar:  {invoice.total_pagar}")
        self.lbl_factura_items.setText(f"Productos YOLO:  {invoice.total_yolo_items}")
        self.lbl_factura_nit.setText(f"Total Ítems Factura:  {invoice.total_items_factura}")

        # Fill YOLO items table  [Categoría YOLO | Descripción | Cantidad | Valor Bruto]
        self.table_invoice_data.setRowCount(0)
        
        # Color coding by category
        cat_colors = {
            "Cemento":           "#f9e2af",  # yellow
            "Tubería Presión":  "#89b4fa",  # blue
            "Tubería Sanitaria": "#a6e3a1", # green
        }
        
        for i, item in enumerate(invoice.yolo_items):
            self.table_invoice_data.insertRow(i)
            row_data = item.to_table_row()
            for col, val in enumerate(row_data):
                cell = QTableWidgetItem(str(val))
                # Color for categoria column
                if col == 0:
                    cell.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                    color = cat_colors.get(item.categoria, "#cdd6f4")
                    cell.setForeground(QColor(color))
                elif col == 2:  # Cantidad
                    cell.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
                elif col == 3:  # Valor Bruto
                    cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table_invoice_data.setItem(i, col, cell)

        self.table_invoice_data.resizeRowsToContents()

        # Navigate to Factura PDF
        self._on_nav_click("Factura PDF")

        # Update dashboard counter with yolo items found
        self.stat_despachos.set_value(invoice.total_yolo_items)

    # ----------------------------------------------------------------
    # VIDEO ANALYSIS LOGGING
    # ----------------------------------------------------------------
    def _on_load_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Video de Auditoría", "", "Videos (*.mp4 *.avi *.mkv *.mov)"
        )
        if file_path:
            self._video_path = file_path
            self.lbl_video_name.setText(os.path.basename(file_path))
            can_start = can_do_action(self._user, "video.iniciar")
            self.btn_start_analysis.setEnabled(can_start)
            self.show_toast("Video cargado. Iniciando análisis…", "info")
            self._set_video_status("queued")

            # Auto-start analysis on load (if permitted and not already running)
            if can_start:
                if not (hasattr(self, "analyzer") and self.analyzer and self.analyzer.isRunning()):
                    self._on_video_start()

    def _on_video_start(self):
        """Inicia el análisis offline de YOLO."""
        if not hasattr(self, "_video_path") or not self._video_path:
            return
        if hasattr(self, "analyzer") and self.analyzer and self.analyzer.isRunning():
            return

        self.btn_start_analysis.setEnabled(False)
        self.btn_load_video.setEnabled(False)
        self._set_video_status("analyzing")

        # Reset analysis UI
        if hasattr(self, "analysis_progress"):
            self.analysis_progress.setValue(0)
            self.analysis_progress.setVisible(True)

        # Reset / disable playback controls until analysis completes
        self.btn_play_pause.setEnabled(False)
        self.btn_prev_frame.setEnabled(False)
        self.btn_next_frame.setEnabled(False)
        self.btn_rewind.setEnabled(False)
        self.btn_forward.setEnabled(False)
        self.btn_snapshot.setEnabled(False)
        self.video_slider.setEnabled(False)
        self.video_slider.setValue(0)
        self.lbl_frame_time.setText("00:00 / 00:00")
        
        # Clear previous state
        for i in range(self.table_conteo.rowCount()):
            self.table_conteo.setItem(i, 1, QTableWidgetItem("0"))
        self.list_detections.clear()
        self._thumbnails_cache.clear()
        
        # Worker analysis
        # Determinar base_dir de forma robusta para PyInstaller
        if getattr(sys, 'frozen', False):
            # En el .exe, los datos están en el mismo dir que el exe o en _internal
            base_dir = os.path.dirname(sys.executable)
            # Priorizar _internal si existe (típico de modo COLLECT)
            internal_path = os.path.join(base_dir, "_internal")
            if os.path.exists(internal_path):
                base_dir = internal_path
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Usamos el modelo entrenado con YOLO11
        model_path = os.path.join(base_dir, "training", "runs", "bultos_cemento2", "weights", "best.pt")
        if not os.path.exists(model_path): # Fallback a otro entrenamiento
            model_path = os.path.join(base_dir, "training", "runs", "bultos_cemento", "weights", "best.pt")
        
        # Si sigue sin existir, buscar en el CWD (fallback final)
        if not os.path.exists(model_path):
             model_path = "training/runs/bultos_cemento2/weights/best.pt"

        self.analyzer = YoloAnalyzerWorker(
            self._video_path,
            model_path,
            line_pos=self.slider_line.value() / 100.0,
            preloaded_model=self._preloaded_model,
            preloaded_device=self._preloaded_device,
        )
        self.analyzer.progress_updated.connect(self._on_analysis_progress)
        self.analyzer.thumbnail_ready.connect(self._on_thumbnail_ready)
        self.analyzer.finished_analysis.connect(self._on_analysis_finished)
        self.analyzer.error_occurred.connect(self._on_analysis_error)
        self.analyzer.start()
        
        app_logger.log_action(self._user, app_logger.VIDEO_INICIADO, f"Video: {os.path.basename(self._video_path)}")
        self.show_toast("Iniciando análisis de visión artificial...", "info")

    def _on_thumbnail_ready(self, frame_idx, qimg):
        """Almacena la miniatura en el cache."""
        pixmap = QPixmap.fromImage(qimg)
        self._thumbnails_cache[frame_idx] = pixmap

    def _on_analysis_progress(self, val):
        self.btn_start_analysis.setText(f"Analizando... {val}%")
        if hasattr(self, "analysis_progress"):
            self.analysis_progress.setValue(max(0, min(int(val), 100)))

    def _on_analysis_error(self, err_msg):
        self.btn_start_analysis.setText("⚠️ Error en Análisis")
        self.btn_start_analysis.setEnabled(True)
        self.btn_load_video.setEnabled(True)
        self._set_video_status("idle")
        if hasattr(self, "analysis_progress"):
            self.analysis_progress.setVisible(False)
        self.show_toast(f"Error: {err_msg}", "error")
        app_logger.log_action(self._user, "ERROR_ANALISIS", f"Error YOLO: {err_msg}")

    def _on_analysis_finished(self, final_counts, count_history, tracking_data, fps, crossing_frames):
        self.btn_start_analysis.setText("✅ Análisis Completo")
        if hasattr(self, "analysis_progress"):
            self.analysis_progress.setValue(100)
            self.analysis_progress.setVisible(True)
        self._tracking_data = tracking_data
        self._count_history = count_history
        self._fps = fps
        try:
            self._video_total_frames = int(max(tracking_data.keys())) if tracking_data else 0
        except Exception:
            self._video_total_frames = 0

        # Update event markers on the slider
        if hasattr(self, "video_slider") and self._video_total_frames > 0:
            event_pcts = [f / float(self._video_total_frames) for f in crossing_frames]
            self.video_slider.set_event_markers(event_pcts)
        
        # Enable playback controls
        self.btn_play_pause.setEnabled(True)
        self.btn_prev_frame.setEnabled(True)
        self.btn_next_frame.setEnabled(True)
        self.btn_rewind.setEnabled(True)
        self.btn_forward.setEnabled(True)
        self.btn_snapshot.setEnabled(True)
        self.video_slider.setEnabled(True)

        # Allow new analysis / load again
        self.btn_load_video.setEnabled(True)
        self.btn_start_analysis.setEnabled(True)
        
        self.show_toast("Análisis finalizado. Listo para reproducción.", "success")
        self._set_video_status("ready")
        self._animate_ready_to_play()

    def _animate_ready_to_play(self):
        """Animación premium para indicar que ya se puede reproducir."""
        if not hasattr(self, "btn_play_pause"):
            return

        btn = self.btn_play_pause
        btn.setProperty("ready", True)
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        btn.update()

        # Pulse animation (geometry)
        g0 = btn.geometry()
        grow = 6
        g1 = g0.adjusted(-grow, -grow, grow, grow)

        anim_out = QPropertyAnimation(btn, b"geometry", self)
        anim_out.setDuration(180)
        anim_out.setEasingCurve(QEasingCurve.OutCubic)
        anim_out.setStartValue(g0)
        anim_out.setEndValue(g1)

        anim_in = QPropertyAnimation(btn, b"geometry", self)
        anim_in.setDuration(220)
        anim_in.setEasingCurve(QEasingCurve.InOutCubic)
        anim_in.setStartValue(g1)
        anim_in.setEndValue(g0)

        group = QSequentialAnimationGroup(self)
        group.addAnimation(anim_out)
        group.addAnimation(anim_in)
        group.start()

        # Remove highlight after a moment
        def clear_ready():
            btn.setProperty("ready", False)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

        QTimer.singleShot(1800, clear_ready)
        
    def _on_video_play_pause(self):
        if hasattr(self, "player_worker") and self.player_worker.isRunning():
            is_paused = not self.player_worker._is_paused
            self.player_worker.set_paused(is_paused)
            self.btn_play_pause.setText("▶" if is_paused else "⏸")
        else:
            # Start player
            self.player_worker = VideoPlayerWorker(
                self._video_path, self._count_history, self._tracking_data, self._fps,
                line_pos=self.slider_line.value()/100.0
            )
            # Apply selected playback speed
            try:
                self.player_worker.set_speed(float(getattr(self, "_playback_speed", 1.0)))
            except Exception:
                self.player_worker.set_speed(1.0)
            self.player_worker.frame_ready.connect(self._on_frame_ready)
            self.player_worker.counts_updated.connect(self._on_counts_updated)
            self.player_worker.detection_event.connect(self._on_detection_event)
            self.player_worker.progress_updated.connect(self._on_player_progress)
            self.player_worker.position_updated.connect(self._on_player_position)
            self.player_worker.finished.connect(self._on_playback_finished)
            self.player_worker.start()
            self.btn_play_pause.setText("⏸")

    def _refresh_speed_button_text(self):
        v = float(getattr(self, "_playback_speed", 1.0) or 1.0)
        self.btn_speed.setText(f"⚙ {v:.1f}x")

    def _set_playback_speed(self, v: float):
        try:
            v = float(v)
        except Exception:
            v = 1.0
        v = max(0.5, min(15.0, round(v, 1)))
        self._playback_speed = v
        self._refresh_speed_button_text()
        if hasattr(self, "player_worker") and self.player_worker.isRunning():
            self.player_worker.set_speed(v)

    def _open_speed_panel(self):
        """Panel simple tipo YouTube para velocidad (slider + presets + +/-)."""
        # Close existing panel if open
        if hasattr(self, "_speed_panel") and self._speed_panel and self._speed_panel.isVisible():
            self._speed_panel.close()

        dlg = QDialog(self)
        dlg.setObjectName("speedPanel")
        dlg.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        dlg.setAttribute(Qt.WA_TranslucentBackground, True)

        # Card container
        card = QFrame(dlg)
        card.setObjectName("speedPanelCard")
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 110))
        card.setGraphicsEffect(shadow)
        card.setMinimumWidth(360)

        root = QVBoxLayout(dlg)
        # give room for shadow so it doesn't clip
        root.setContentsMargins(16, 14, 16, 18)
        root.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(12)

        title = QLabel("Velocidad de reproducción")
        title.setObjectName("speedPanelTitle")
        lay.addWidget(title)

        self._speed_value_lbl = QLabel(f"{float(self._playback_speed):.1f}x")
        self._speed_value_lbl.setObjectName("speedPanelValue")
        self._speed_value_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._speed_value_lbl)

        # Slider row with - / +
        row = QHBoxLayout()
        row.setSpacing(12)

        btn_minus = QPushButton("–")
        btn_minus.setObjectName("speedAdjustBtn")
        btn_minus.setFixedSize(36, 36)
        btn_plus = QPushButton("+")
        btn_plus.setObjectName("speedAdjustBtn")
        btn_plus.setFixedSize(36, 36)

        slider = QSlider(Qt.Horizontal)
        slider.setObjectName("speedPanelSlider")
        slider.setRange(5, 150)  # 0.5x..15.0x as tenths
        slider.setSingleStep(1)
        slider.setPageStep(5)
        slider.setValue(int(round(float(self._playback_speed) * 10)))

        def set_from_slider(v_int: int):
            v = max(0.5, min(15.0, round(v_int / 10.0, 1)))
            self._speed_value_lbl.setText(f"{v:.1f}x")
            self._set_playback_speed(v)
            refresh_chip_states(v)

        slider.valueChanged.connect(set_from_slider)
        btn_minus.clicked.connect(lambda: slider.setValue(max(slider.minimum(), slider.value() - 1)))
        btn_plus.clicked.connect(lambda: slider.setValue(min(slider.maximum(), slider.value() + 1)))

        row.addWidget(btn_minus)
        row.addWidget(slider, 1)
        row.addWidget(btn_plus)
        lay.addLayout(row)

        # Preset chips
        chips = QHBoxLayout()
        chips.setSpacing(8)

        chip_buttons = []

        def make_chip(label: str, speed: float):
            b = QPushButton(label)
            b.setObjectName("speedChip")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda: slider.setValue(int(round(speed * 10))))
            chip_buttons.append((b, speed))
            return b

        chips.addWidget(make_chip("Normal", 1.0))
        for v in self._speed_presets:
            if abs(v - 1.0) < 1e-9:
                continue
            chips.addWidget(make_chip(f"{v:.2g}", float(v)))

        chips.addStretch()
        lay.addLayout(chips)

        def refresh_chip_states(v: float):
            v = round(float(v), 1)
            for b, sv in chip_buttons:
                b.setChecked(round(float(sv), 1) == v)

        refresh_chip_states(float(self._playback_speed))

        # Position panel under the speed button, clamped to screen
        anchor = self.btn_speed.mapToGlobal(QPoint(0, self.btn_speed.height()))
        dlg.adjustSize()

        screen = QGuiApplication.screenAt(anchor) or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else None

        x = anchor.x() - max(0, dlg.width() - self.btn_speed.width())
        y = anchor.y() + 10
        if avail is not None:
            x = max(avail.left() + 8, min(x, avail.right() - dlg.width() - 8))
            y = max(avail.top() + 8, min(y, avail.bottom() - dlg.height() - 8))
        dlg.move(x, y)

        self._speed_panel = dlg
        dlg.show()

    def _on_frame_ready(self, qimg):
        pixmap = QPixmap.fromImage(qimg)
        self.video_frame.setPixmap(pixmap.scaled(self.video_frame.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _on_counts_updated(self, counts):
        for i in range(self.table_conteo.rowCount()):
            mat = self.table_conteo.item(i, 0).text()
            if mat in counts:
                self.table_conteo.setItem(i, 1, QTableWidgetItem(str(counts[mat])))

    def _on_detection_event(self, ts, msg):
        item = QListWidgetItem(f"[{ts}] {msg}")
        item.setData(Qt.UserRole, ts)  # Guardar timestamp para jump-to-frame
        self.list_detections.insertItem(0, item)
        if self.list_detections.count() > 50:
            self.list_detections.takeItem(50)

        # Captura automática de evidencia solo cuando se detecta el bulto
        self._take_snapshot()

        # Pulso visual: si la IA detecta más bultos que la factura = advertencia
        try:
            invoice = getattr(self, "_current_invoice", None)
            if invoice and hasattr(self, "table_conteo"):
                # Obtener conteo IA actual
                ia_total = 0
                for i in range(self.table_conteo.rowCount()):
                    item_val = self.table_conteo.item(i, 1)
                    if item_val:
                        try: ia_total += int(item_val.text())
                        except: pass
                # Comparar con total de factura
                fac_total = invoice.total_yolo_items
                if ia_total > fac_total:
                    self._pulse_warning()
        except Exception:
            pass

    def _on_player_progress(self, pct):
        # While scrubbing, don't fight user input
        if not getattr(self, "_is_scrubbing", False):
            self.video_slider.setValue(pct * 10) # range 0-1000
        # time label comes from worker position for accuracy

    def _on_player_position(self, cur_msec: int, total_msec: int):
        # Update time label accurately from playback position
        self._current_msec = int(cur_msec or 0)
        self._total_msec = int(total_msec or 0)
        self.lbl_frame_time.setText(f"{self._fmt_msec(self._current_msec)} / {self._fmt_msec(self._total_msec)}")

    def _fmt_msec(self, msec: int) -> str:
        s = max(0, int(round((msec or 0) / 1000.0)))
        mm = s // 60
        ss = s % 60
        return f"{mm:02d}:{ss:02d}"

    def _on_video_slider_pressed(self):
        self._is_scrubbing = True
        if hasattr(self, "scrub_tooltip"):
            self.scrub_tooltip.setVisible(True)

    def _on_video_slider_moved(self, value: int):
        # Update time label live while dragging (YouTube-like)
        self._update_time_label_from_slider(value=value)
        self._update_scrub_tooltip(value)

    def _on_video_slider_released(self):
        self._is_scrubbing = False
        self._seek_player_to_slider()
        if hasattr(self, "scrub_tooltip"):
            QTimer.singleShot(300, lambda: self.scrub_tooltip.setVisible(False))

    def _update_scrub_tooltip(self, slider_value: int):
        if not hasattr(self, "scrub_tooltip"):
            return
        total_msec = int(getattr(self, "_total_msec", 0) or 0)
        if total_msec <= 0:
            return
        v = int(slider_value)
        pct = max(0.0, min(1.0, v / 1000.0))
        cur_msec = int(round(pct * total_msec))
        self.scrub_tooltip.setText(self._fmt_msec(cur_msec))
        self.scrub_tooltip.adjustSize()

        # Position above the slider handle
        slider = self.video_slider
        x = int(slider.x() + (pct * (slider.width() - 14)))  # 14 ~ handle width
        y = int(slider.y() - self.scrub_tooltip.height() - 10)
        # Center tooltip on handle
        x = x - int(self.scrub_tooltip.width() / 2) + 7
        # Clamp within video container
        x = max(10, min(x, slider.x() + slider.width() - self.scrub_tooltip.width() - 10))
        y = max(10, y)
        self.scrub_tooltip.move(x, y)

    def eventFilter(self, obj, event):
        """Captura hover sobre el slider para mostrar miniatura."""
        if obj == self.video_slider:
            if event.type() == QEvent.MouseMove:
                self._handle_slider_hover(event)
            elif event.type() == QEvent.Leave:
                self.scrub_thumbnail_popup.hide()
        return super().eventFilter(obj, event)

    def _handle_slider_hover(self, event):
        if not hasattr(self, "_video_total_frames") or self._video_total_frames <= 0:
            return
            
        # Calcular posición relativa
        width = self.video_slider.width()
        x = event.position().x()
        pct = max(0.0, min(1.0, x / width))
        
        target_frame = int(round(pct * self._video_total_frames))
        total_msec = int(getattr(self, "_total_msec", 0) or 0)
        cur_msec = int(round(pct * total_msec))
        
        # Buscar miniatura más cercana
        thumb = self._get_nearest_thumbnail(target_frame)
        if thumb:
            self.scrub_thumbnail_popup.set_thumbnail(thumb, self._fmt_msec(cur_msec))
            
            # Posición del popup
            global_pos = self.video_slider.mapToGlobal(QPoint(int(x), 0))
            popup_x = global_pos.x() - self.scrub_thumbnail_popup.width() // 2
            popup_y = global_pos.y() - self.scrub_thumbnail_popup.height() - 20
            
            # Clamping a la pantalla
            screen = QGuiApplication.primaryScreen().availableGeometry()
            popup_x = max(screen.left() + 10, min(popup_x, screen.right() - self.scrub_thumbnail_popup.width() - 10))
            
            self.scrub_thumbnail_popup.move(popup_x, popup_y)
            self.scrub_thumbnail_popup.show()
        else:
            self.scrub_thumbnail_popup.hide()

    def _get_nearest_thumbnail(self, target_frame):
        if not self._thumbnails_cache:
            return None
        
        keys = sorted(self._thumbnails_cache.keys())
        if not keys:
            return None
            
        # Búsqueda binaria para la más cercana
        import bisect
        idx = bisect.bisect_left(keys, target_frame)
        
        if idx == 0:
            best_key = keys[0]
        elif idx == len(keys):
            best_key = keys[-1]
        else:
            before = keys[idx - 1]
            after = keys[idx]
            if target_frame - before < after - target_frame:
                best_key = before
            else:
                best_key = after
                
        # Solo usar si está a una distancia razonable (p.ej. 200 frames) or if we only have 100 thumbnails total
        return self._thumbnails_cache[best_key]

    def _seek_player_to_slider(self):
        if not (hasattr(self, "player_worker") and self.player_worker.isRunning()):
            return
        fps = float(getattr(self, "_fps", 0) or 0)
        total_frames = int(getattr(self, "_video_total_frames", 0) or 0)
        if fps <= 0 or total_frames <= 0:
            return
        pct = float(self.video_slider.value()) / 1000.0
        target_frame = int(round(pct * total_frames))
        target_msec = max(0.0, (target_frame / fps) * 1000.0)
        if hasattr(self.player_worker, "seek_to_msec"):
            self.player_worker.seek_to_msec(target_msec)

    def _update_time_label_from_slider(self, value: int | None = None):
        # Used only for scrubbing preview (not for actual playback time)
        total_msec = int(getattr(self, "_total_msec", 0) or 0)
        if total_msec <= 0:
            return
        v = int(self.video_slider.value() if value is None else value)
        pct = max(0.0, min(1.0, v / 1000.0))
        cur_msec = int(round(pct * total_msec))
        self.lbl_frame_time.setText(f"{self._fmt_msec(cur_msec)} / {self._fmt_msec(total_msec)}")

    def _on_playback_finished(self):
        self.btn_play_pause.setText("▶")
        self._set_video_status("ready")
        # Guardar automáticamente la auditoría (sin diálogo)
        QTimer.singleShot(300, self._auto_save_audit_summary)

    def _auto_save_audit_summary(self):
        """Guarda automáticamente la auditoría al terminar la reproducción visual."""
        try:
            # 1. Recopilar conteo IA final
            final_counts = {}
            for i in range(self.table_conteo.rowCount()):
                mat_item = self.table_conteo.item(i, 0)
                cnt_item = self.table_conteo.item(i, 1)
                if mat_item and cnt_item:
                    try: final_counts[mat_item.text()] = int(cnt_item.text())
                    except: final_counts[mat_item.text()] = 0

            # 2. Recopilar factura
            invoice = getattr(self, "_current_invoice", None)
            factura_counts   = {}
            factura_no       = ""
            cliente          = ""
            if invoice:
                factura_no = getattr(invoice, "numero_factura", "")
                cliente    = getattr(invoice, "cliente", "")
                for item in getattr(invoice, "items", []):
                    desc = str(item.descripcion) if hasattr(item, "descripcion") else str(item)
                    qty  = int(item.cantidad) if hasattr(item, "cantidad") else 0
                    factura_counts[desc] = factura_counts.get(desc, 0) + qty

            if not factura_counts and final_counts:
                factura_counts = dict(final_counts)

            # 3. Calcular discrepancias y resultado
            mats = sorted(set(list(final_counts.keys()) + list(factura_counts.keys())))
            discrepancias = {m: final_counts.get(m, 0) - factura_counts.get(m, 0)
                             for m in mats if final_counts.get(m, 0) != factura_counts.get(m, 0)}
            resultado = "CONFORME" if not discrepancias else "DISCREPANCIA"
            disc_txt = "  |  ".join(f"{m}: {d:+d}" for m, d in discrepancias.items())

            # 4. Actualizar panel lateral
            self._update_comparison_panel(final_counts, factura_counts, resultado)

            # 5. Extraer capturas asociadas
            capturas = []
            for i in range(self.list_captures.count()):
                path = self.list_captures.item(i).data(Qt.UserRole)
                if path and os.path.exists(path):
                    capturas.append(path)

            # 6. Preparar datos y guardar
            audit_data = {
                "factura_no":     factura_no,
                "cliente":        cliente,
                "video_nombre":   os.path.basename(getattr(self, "_video_path", "")),
                "fecha":          datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "conteo_ia":      final_counts,
                "conteo_factura": factura_counts,
                "vehiculo":       "",
                "usuario":        self._user.get("full_name", self._user.get("username", "")),
                "resultado":      resultado,
                "capturas":       capturas,
            }

            audit_id = save_audit(self._user, audit_data)
            if audit_id > 0:
                app_logger.log_action(self._user, "Auditoría Guardada (Auto)",
                                      f"ID #{audit_id} | {resultado} | Vídeo: {audit_data['video_nombre']}")
                if resultado == "DISCREPANCIA":
                    app_logger.log_action(self._user, app_logger.DISCREPANCIA,
                                          f"Auditoría #{audit_id}: {disc_txt if discrepancias else 'Sin datos'}")
                self.show_toast("✅ Análisis finalizado y guardado automáticamente", "success")
                self._refresh_history_table()
            else:
                self.show_toast("⚠️ Error guardando auditoría", "error")

        except Exception as e:
            print(f"[AUDIT] Error en auto-save de resumen: {e}")
            self.show_toast("Reproducción finalizada", "info")

    def _update_comparison_panel(self, conteo_ia: dict, conteo_factura: dict, resultado: str):
        """Actualiza la tabla de comparación IA vs Factura en el panel lateral del video."""
        try:
            if not hasattr(self, "table_comparison"):
                return
            color = "#a6e3a1" if resultado == "CONFORME" else "#f38ba8"
            emoji = "✅" if resultado == "CONFORME" else "⚠️"
            self.lbl_audit_result.setText(f"{emoji}  {resultado}")
            self.lbl_audit_result.setStyleSheet(
                f"font-size: 13px; font-weight: 900; color: {color};"
                "background: transparent; border-radius: 6px;"
            )
            mats = sorted(set(list(conteo_ia.keys()) + list(conteo_factura.keys())))
            self.table_comparison.setRowCount(len(mats))
            for r, mat in enumerate(mats):
                ia_v  = conteo_ia.get(mat, 0)
                fac_v = conteo_factura.get(mat, 0)
                diff  = ia_v - fac_v
                self.table_comparison.setItem(r, 0, QTableWidgetItem(mat))
                self.table_comparison.setItem(r, 1, QTableWidgetItem(str(fac_v)))
                self.table_comparison.setItem(r, 2, QTableWidgetItem(str(ia_v)))
                diff_item = QTableWidgetItem(f"{diff:+d}")
                diff_item.setForeground(QColor("#a6e3a1") if diff == 0
                                        else QColor("#f9e2af") if diff > 0 else QColor("#f38ba8"))
                self.table_comparison.setItem(r, 3, diff_item)
        except Exception as e:
            print(f"[COMPARISON] Error actualizando panel: {e}")

    def _pulse_warning(self):
        """Pulso visual rojo y alerta sonora cuando hay exceso de bultos."""
        try:
            # Alerta sonora sutil en Windows
            try:
                import winsound
                winsound.Beep(880, 150) # Tono de advertencia sutil
            except ImportError:
                pass

            if hasattr(self, "lbl_audit_result"):
                self.lbl_audit_result.setStyleSheet(
                    "font-size: 13px; font-weight: 900; color: #f38ba8;"
                    "background: rgba(243,139,168,0.18); border-radius: 6px;"
                    "border: 2px solid #f38ba8;"
                )
                QTimer.singleShot(600, lambda:
                    self.lbl_audit_result.setStyleSheet(
                        "font-size: 13px; font-weight: 900; color: #f38ba8;"
                        "background: transparent; border-radius: 6px;"
                    ) if hasattr(self, "lbl_audit_result") else None
                )
        except Exception:
            pass

    def _on_detection_jump(self, list_item):
        """Salta al frame/tiempo del evento de detección seleccionado con doble clic."""
        try:
            ts = list_item.data(Qt.UserRole) or list_item.text()
            # El timestamp tiene formato MM:SS
            parts = str(ts).strip().split(":")
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = float(parts[1])
                target_msec = (minutes * 60 + seconds) * 1000.0
                if hasattr(self, "player_worker") and self.player_worker.isRunning():
                    self.player_worker.seek_to_msec(target_msec)
                    self.show_toast(f"➡️  Saltando a {ts}", "info")
        except Exception as e:
            print(f"[JUMP] Error en jump-to-frame: {e}")

    def _on_line_slider_changed(self, val):
        self.lbl_line_val.setText(f"{val}%")
        if hasattr(self, "player_worker") and self.player_worker.isRunning():
            self.player_worker.line_pos = val / 100.0

    def _on_video_prev_frame(self):
        if hasattr(self, "player_worker"):
            self.player_worker.set_paused(True)
            self.player_worker._step_dir = 1  # Swapped to advance as per user feedback
            self.btn_play_pause.setText("▶")

    def _on_video_next_frame(self):
        if hasattr(self, "player_worker"):
            self.player_worker.set_paused(True)
            self.player_worker._step_dir = -1 # Swapped to retreat as per user feedback
            self.btn_play_pause.setText("▶")

    def _on_video_rewind(self):
        if hasattr(self, "player_worker"):
            self.player_worker.seek_backward_10s()

    def _on_video_forward(self):
        if hasattr(self, "player_worker"):
            self.player_worker.seek_forward_10s()

    def _take_snapshot(self):
        """Captura el frame actual y lo guarda en la carpeta 'captures'."""
        if not hasattr(self, "video_frame") or self.video_frame.pixmap() is None:
            return
            
        os.makedirs("captures", exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"captures/snapshot_{timestamp}.png"
        self.video_frame.pixmap().save(filename)
        
        # Add to history list in Reports page
        item = QListWidgetItem(f"Snapshot {timestamp}")
        item.setIcon(QIcon(filename))
        item.setData(Qt.UserRole, os.path.abspath(filename))
        self.list_captures.insertItem(0, item)
        
        self.show_toast(f"Captura guardada: {os.path.basename(filename)}", "success")

    def show_toast(self, message, toast_type="success"):
        toast = ToastNotification(message, toast_type, self)
        toast.show_toast()

    def _on_video_stop(self):
        """
        Detiene análisis/reproducción y limpia el estado para cargar otro video.
        """
        # Stop analyzer if running
        try:
            if hasattr(self, "analyzer") and self.analyzer and self.analyzer.isRunning():
                self.analyzer.stop()
                self.analyzer.wait(1500)
        except Exception:
            pass

        # Stop player if running
        try:
            if hasattr(self, "player_worker") and self.player_worker and self.player_worker.isRunning():
                self.player_worker.stop()
                self.player_worker.wait(1500)
        except Exception:
            pass

        # Close speed panel if open
        try:
            if hasattr(self, "_speed_panel") and self._speed_panel and self._speed_panel.isVisible():
                self._speed_panel.close()
        except Exception:
            pass

        self._thumbnails_cache.clear()
        self.scrub_thumbnail_popup.hide()

        # Clear loaded video
        prev_name = os.path.basename(self._video_path) if hasattr(self, "_video_path") and self._video_path else ""
        self._video_path = None
        self.lbl_video_name.setText("Ningún video seleccionado")
        self._set_video_status("idle")

        # Reset analysis UI
        self.btn_start_analysis.setText("▶  Iniciar Análisis YOLO")
        self.btn_start_analysis.setEnabled(False)
        self.btn_load_video.setEnabled(True)
        if hasattr(self, "analysis_progress"):
            self.analysis_progress.setValue(0)
            self.analysis_progress.setVisible(False)

        # Clear results UI
        for i in range(self.table_conteo.rowCount()):
            self.table_conteo.setItem(i, 1, QTableWidgetItem("0"))
            self.table_conteo.setItem(i, 2, QTableWidgetItem("—"))
        self.list_detections.clear()

        # Reset playback UI
        self.video_frame.setText("📹\n\nCargue un video desde la USB\npara visualizar la detección con IA")
        self.video_frame.setAlignment(Qt.AlignCenter)
        self.video_slider.setValue(0)
        self.video_slider.setEnabled(False)
        self.btn_play_pause.setText("▶")
        self.btn_play_pause.setEnabled(False)
        self.btn_prev_frame.setEnabled(False)
        self.btn_next_frame.setEnabled(False)
        self.btn_rewind.setEnabled(False)
        self.btn_forward.setEnabled(False)
        self.btn_snapshot.setEnabled(False)
        self.lbl_frame_time.setText("00:00 / 00:00")

        self._video_total_frames = 0
        self.video_slider.set_event_markers([])

        app_logger.log_action(
            self._user, app_logger.VIDEO_DETENIDO,
            f"Detuvo y reinició análisis de video{(' — ' + prev_name) if prev_name else ''}"
        )
        self.show_toast("Listo para cargar otro video", "info")

    def _set_video_status(self, state: str):
        if not hasattr(self, "video_status"):
            return
        state = state or "idle"
        self.video_status.setProperty("state", state)
        if state == "idle":
            self.video_status.setText("⏸  Sin video")
        elif state == "queued":
            self.video_status.setText("⏳  Preparando análisis…")
        elif state == "analyzing":
            self.video_status.setText("🧠  Analizando…")
        elif state == "ready":
            self.video_status.setText("✅  Listo para reproducir")
        else:
            self.video_status.setText(state)
        self.video_status.style().unpolish(self.video_status)
        self.video_status.style().polish(self.video_status)
        self.video_status.update()

    # ----------------------------------------------------------------
    # REPORTES — EXPORTACIÓN REAL
    # ----------------------------------------------------------------
    def _log_export(self, formato: str):
        """Genera y guarda un reporte real en Excel o PDF."""
        # Construir datos de la auditoría actual
        final_counts = {}
        for i in range(self.table_conteo.rowCount()):
            mat_item = self.table_conteo.item(i, 0)
            cnt_item = self.table_conteo.item(i, 1)
            if mat_item and cnt_item:
                try: final_counts[mat_item.text()] = int(cnt_item.text())
                except: final_counts[mat_item.text()] = 0

        invoice = getattr(self, "_current_invoice", None)
        factura_counts = {}
        factura_no = ""
        cliente    = ""
        if invoice:
            factura_no = getattr(invoice, "numero_factura", "")
            cliente    = getattr(invoice, "cliente",        "")
            for item in getattr(invoice, "items", []):
                desc = str(item.descripcion) if hasattr(item, "descripcion") else str(item)
                qty  = int(item.cantidad) if hasattr(item, "cantidad") else 0
                factura_counts[desc] = factura_counts.get(desc, 0) + qty

        discrepancias = {m: final_counts.get(m, 0) - factura_counts.get(m, 0)
                         for m in set(list(final_counts.keys()) + list(factura_counts.keys()))
                         if final_counts.get(m, 0) != factura_counts.get(m, 0)}
        resultado = "CONFORME" if not discrepancias else "DISCREPANCIA"

        audit_data = {
            "factura_no":     factura_no or "Sin factura",
            "cliente":        cliente or "Desconocido",
            "video_nombre":   os.path.basename(getattr(self, "_video_path", "") or ""),
            "fecha":          datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
            "usuario":        self._user.get("full_name", self._user.get("username","")),
            "vehiculo":       "",
            "resultado":      resultado,
            "conteo_ia":      final_counts,
            "conteo_factura": factura_counts,
        }

        # Diálogo de guardado
        ext = {"Excel": "xlsx", "PDF": "pdf"}.get(formato, "xlsx")
        timestamp  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_fn = f"logicheck_reporte_{timestamp}.{ext}"
        path, _ = QFileDialog.getSaveFileName(
            self, f"Exportar Reporte {formato}",
            default_fn,
            f"Archivos {formato} (*.{ext})"
        )
        if not path:
            return

        if formato == "Excel":
            ok = export_excel(audit_data, path)
        else:
            ok = export_pdf(audit_data, path)

        if ok:
            app_logger.log_action(
                self._user, app_logger.REPORTE_EXPORTADO,
                f"Formato: {formato} | Archivo: {os.path.basename(path)} | {resultado}"
            )
            self.show_toast(f"✅ Reporte {formato} guardado: {os.path.basename(path)}", "success")
        else:
            self.show_toast(f"⚠️ Error al generar el reporte {formato}", "error")

    # ----------------------------------------------------------------
    # ASIGNACIÓN VEHICULAR
    # ----------------------------------------------------------------
    def _on_vehicle_assigned(self):
        """Registra la confirmación de una asignación vehicular."""
        # Leer datos actuales del despacho desde las stat cards
        peso     = getattr(self.card_peso,     "value_label", None)
        volumen  = getattr(self.card_volumen,  "value_label", None)
        vehiculo = getattr(self.card_vehiculo, "value_label", None)

        peso_txt     = self.card_peso._val_lbl.text()     if hasattr(self.card_peso,     "_val_lbl") else "—"
        volumen_txt  = self.card_volumen._val_lbl.text()  if hasattr(self.card_volumen,  "_val_lbl") else "—"
        vehiculo_txt = self.card_vehiculo._val_lbl.text() if hasattr(self.card_vehiculo, "_val_lbl") else "—"

        factura_info = "Sin factura"
        invoice = getattr(self, "_current_invoice", None)
        if invoice:
            factura_info = f"Factura {invoice.numero_factura}"

        desc = (f"Vehículo: {vehiculo_txt} | Peso: {peso_txt} | "
                f"Volumen: {volumen_txt} | {factura_info}")

        app_logger.log_action(self._user, app_logger.ASIGNACION_CREADA, desc)

        QMessageBox.information(
            self,
            "Asignación Registrada",
            f"✅ La asignación vehicular fue confirmada y registrada en el log de auditoría.\n\n{desc}"
        )

    def _refresh_history_table(self):
        from core.audit_store import get_audits
        try:
            audits = get_audits(limit=50)
            self.table_history.setRowCount(0)
            for r, audit in enumerate(audits):
                self.table_history.insertRow(r)
                self.table_history.setRowHeight(r, 48)
                
                # Fetching fields
                fecha = audit.get("fecha", "")[:16]
                fact = audit.get("factura_no", "") or "Sin factura"
                
                total_ia = sum(int(v) for v in audit.get("conteo_ia", {}).values())
                total_fac = sum(int(v) for v in audit.get("conteo_factura", {}).values())
                diff = total_ia - total_fac
                
                mats = ", ".join(audit.get("conteo_ia", {}).keys()) or "—"
                vehic = audit.get("vehiculo", "") or "—"
                estado = audit.get("resultado", "DESCONOCIDO")

                self.table_history.setItem(r, 0, QTableWidgetItem(fecha))
                self.table_history.setItem(r, 1, QTableWidgetItem(fact))
                self.table_history.setItem(r, 2, QTableWidgetItem(mats))
                
                diff_str = f"{diff:+d}" if diff != 0 else "0"
                diff_item = QTableWidgetItem(diff_str)
                diff_item.setForeground(QColor("#a6e3a1") if diff == 0 else QColor("#f38ba8" if diff < 0 else "#f9e2af"))
                diff_item.setTextAlignment(Qt.AlignCenter)
                self.table_history.setItem(r, 3, diff_item)
                
                self.table_history.setItem(r, 4, QTableWidgetItem(vehic))
                
                estado_item = QTableWidgetItem("✅" if estado == "CONFORME" else "⚠️")
                estado_item.setToolTip(estado)
                estado_item.setTextAlignment(Qt.AlignCenter)
                self.table_history.setItem(r, 5, estado_item)

                # Acciones cell
                w = QWidget()
                l = QHBoxLayout(w)
                l.setContentsMargins(4, 4, 4, 4)
                l.setSpacing(8)
                
                btn_pdf = QPushButton("📄")
                btn_pdf.setToolTip("Exportar a PDF")
                btn_pdf.setFixedSize(32, 32)
                btn_pdf.setCursor(Qt.PointingHandCursor)
                btn_pdf.setObjectName("primaryBtn")
                btn_pdf.clicked.connect(lambda _, a=audit: self._export_past_audit(a, "PDF"))
                
                btn_xls = QPushButton("📊")
                btn_xls.setToolTip("Exportar a Excel")
                btn_xls.setFixedSize(32, 32)
                btn_xls.setCursor(Qt.PointingHandCursor)
                btn_xls.setObjectName("successBtn")
                btn_xls.clicked.connect(lambda _, a=audit: self._export_past_audit(a, "Excel"))

                l.addStretch()
                l.addWidget(btn_pdf)
                l.addWidget(btn_xls)
                l.addStretch()
                self.table_history.setCellWidget(r, 6, w)
        except Exception as e:
            print(f"[HISTORY] Error refrescando tabla: {e}")

    def _export_past_audit(self, audit_data: dict, formato: str):
        from core.report_exporter import export_pdf, export_excel
        
        ext = {"Excel": "xlsx", "PDF": "pdf"}.get(formato, "xlsx")
        timestamp  = audit_data.get("fecha", "").replace(":", "").replace("-", "").replace(" ", "_")
        if not timestamp:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_fn = f"logicheck_reporte_{timestamp}.{ext}"
        path, _ = QFileDialog.getSaveFileName(
            self, f"Exportar Reporte {formato}",
            default_fn,
            f"Archivos {formato} (*.{ext})"
        )
        if not path:
            return

        # Adapt user name if missing
        if not audit_data.get("usuario"):
            audit_data["usuario"] = audit_data.get("username", "—")

        if formato == "Excel":
            ok = export_excel(audit_data, path)
        else:
            ok = export_pdf(audit_data, path)

        if ok:
            app_logger.log_action(
                self._user, app_logger.REPORTE_EXPORTADO,
                f"Formato: {formato} | Archivo: {os.path.basename(path)} | Histórico"
            )
            self.show_toast(f"✅ Reporte {formato} guardado", "success")
        else:
            self.show_toast(f"⚠️ Error al generar el reporte {formato}", "error")

