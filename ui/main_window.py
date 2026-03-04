from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QFrame, QTableWidget, QTableWidgetItem,
                               QHeaderView, QSizePolicy, QGraphicsDropShadowEffect,
                               QGraphicsOpacityEffect,
                               QScrollArea, QStackedWidget, QToolButton, QSpacerItem,
                               QProgressBar, QStatusBar, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize, Property, QPoint, QVariantAnimation, QSequentialAnimationGroup, QParallelAnimationGroup, QThread, Signal
from PySide6.QtGui import QFont, QColor, QIcon, QPainter, QPainterPath, QLinearGradient, QPen
import datetime
import os
import sys


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
        try:
            start_val = int(self.value_label.text())
        except ValueError:
            start_val = 0
            
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(duration)
        self.anim.setStartValue(start_val)
        self.anim.setEndValue(int(end_val))
        self.anim.valueChanged.connect(lambda v: self.value_label.setText(str(v)))
        self.anim.setEasingCurve(QEasingCurve.OutQuart)
        self.anim.start()


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
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LogiCheck — Auditoría Logística Inteligente")
        self.setMinimumSize(1100, 700)
        self.showMaximized()
        
        self._is_dark = True
        self._current_invoice = None  # Stores last InvoiceData
        
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
        
        version_label = QLabel("v1.0 — Ferretería Durán")
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
        
        # Nav buttons — Flujo del proceso: Factura → Video → Asignación → Reportes
        self.nav_buttons = []
        nav_items = [
            ("📊", "Dashboard"),
            ("📄", "Factura PDF"),
            ("📹", "Análisis de Video"),
            ("🚛", "Asignación Vehicular"),
            ("📋", "Reportes"),
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
        
        # User card
        user_card = QFrame()
        user_card.setObjectName("userCard")
        user_layout = QHBoxLayout(user_card)
        user_layout.setContentsMargins(10, 8, 10, 8)
        avatar = QLabel("👤")
        avatar.setStyleSheet("font-size: 20px; background: transparent;")
        user_layout.addWidget(avatar)
        user_info = QVBoxLayout()
        user_info.setSpacing(0)
        user_name = QLabel("Administrador")
        user_name.setObjectName("userName")
        user_role = QLabel("Ferretería Durán, Apulo")
        user_role.setObjectName("userRole")
        user_info.addWidget(user_name)
        user_info.addWidget(user_role)
        user_layout.addLayout(user_info)
        user_layout.addStretch()
        sidebar_layout.addWidget(user_card)
        
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
        # Page 1: Factura PDF (primero — el flujo comienza aqui)
        self.stacked.addWidget(self._create_invoice_page())
        # Page 2: Análisis de Video
        self.stacked.addWidget(self._create_video_page())
        # Page 3: Asignación Vehicular
        self.stacked.addWidget(self._create_vehicle_page())
        # Page 4: Reportes
        self.stacked.addWidget(self._create_reports_page())
        
        root_layout.addWidget(self.content_area)
        
        # --- Status bar ---
        status = QStatusBar()
        status.setObjectName("statusBar")
        status.showMessage("  ✅ Sistema listo  |  LogiCheck v1.0  |  Modelo YOLO: No cargado")
        self.setStatusBar(status)
    
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
        
        # Recent activity card
        activity_card = GlowCard()
        activity_card.setObjectName("glowCard")
        activity_layout = QVBoxLayout(activity_card)
        activity_layout.setContentsMargins(20, 18, 20, 18)
        activity_header = QLabel("📋  Actividad Reciente")
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
        
        # Placeholder row
        self.table_recent.setRowCount(1)
        self.table_recent.setItem(0, 0, QTableWidgetItem("—"))
        self.table_recent.setItem(0, 1, QTableWidgetItem("Sin auditorías aún"))
        self.table_recent.setItem(0, 2, QTableWidgetItem("—"))
        self.table_recent.setItem(0, 3, QTableWidgetItem("—"))
        
        bottom_row.addWidget(activity_card, 3)
        
        # Model info card
        model_card = GlowCard()
        model_card.setObjectName("glowCard")
        model_layout = QVBoxLayout(model_card)
        model_layout.setContentsMargins(20, 18, 20, 18)
        model_header = QLabel("🤖  Estado del Modelo IA")
        model_header.setObjectName("cardTitle")
        model_layout.addWidget(model_header)
        
        model_items = [
            ("Motor", "YOLOv8 (Ultralytics)"),
            ("Estado", "⏳ Sin entrenar"),
            ("Clases", "Cemento, Tubería Presión, Tubería Sanitaria"),
            ("Precisión", "— (Pendiente entrenamiento)"),
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
        controls_layout.addWidget(self.btn_load_video)
        
        self.btn_start_analysis = QPushButton("▶  Iniciar Análisis YOLO")
        self.btn_start_analysis.setObjectName("successBtn")
        self.btn_start_analysis.setCursor(Qt.PointingHandCursor)
        controls_layout.addWidget(self.btn_start_analysis)
        
        self.btn_stop_analysis = QPushButton("⏹  Detener")
        self.btn_stop_analysis.setObjectName("dangerBtn")
        self.btn_stop_analysis.setCursor(Qt.PointingHandCursor)
        controls_layout.addWidget(self.btn_stop_analysis)
        
        controls_layout.addStretch()
        
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
        
        self.video_frame = QLabel("📹\n\nCargue un video desde la USB\npara visualizar la detección con IA")
        self.video_frame.setObjectName("videoFrame")
        self.video_frame.setAlignment(Qt.AlignCenter)
        self.video_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_frame.setMinimumHeight(400)
        video_container_layout.addWidget(self.video_frame)
        
        # Progress bar for video
        self.video_progress = QProgressBar()
        self.video_progress.setValue(0)
        self.video_progress.setFixedHeight(6)
        self.video_progress.setTextVisible(False)
        self.video_progress.setObjectName("videoProgress")
        video_container_layout.addWidget(self.video_progress)
        
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
        
        results_layout.addSpacing(10)
        
        # Alertas
        alertas_header = QLabel("🔔  Alertas")
        alertas_header.setObjectName("cardTitle")
        results_layout.addWidget(alertas_header)
        
        self.table_alertas = QTableWidget(0, 2)
        self.table_alertas.setHorizontalHeaderLabels(["Hora", "Evento"])
        self.table_alertas.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_alertas.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_alertas.verticalHeader().setVisible(False)
        self.table_alertas.setMinimumHeight(120)
        results_layout.addWidget(self.table_alertas)
        
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
        data_sub.setStyleSheet("font-size: 12px; color: #6c7086; background: transparent; border: none;")
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
        btns_row.addWidget(self.btn_export_pdf)
        
        self.btn_export_excel = QPushButton("📊  Exportar a Excel")
        self.btn_export_excel.setObjectName("successBtn")
        self.btn_export_excel.setCursor(Qt.PointingHandCursor)
        btns_row.addWidget(self.btn_export_excel)
        
        btns_row.addStretch()
        export_layout.addLayout(btns_row)
        
        layout.addWidget(export_card)
        
        # History
        history_card = GlowCard()
        history_layout = QVBoxLayout(history_card)
        history_layout.setContentsMargins(20, 18, 20, 18)
        
        history_header = QLabel("🕐  Historial de Auditorías")
        history_header.setObjectName("cardTitle")
        history_layout.addWidget(history_header)
        
        self.table_history = QTableWidget(0, 6)
        self.table_history.setHorizontalHeaderLabels(["Fecha", "Factura Nro.", "Materiales", "Discrepancias", "Vehículo", "Estado"])
        self.table_history.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_history.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_history.setAlternatingRowColors(True)
        self.table_history.verticalHeader().setVisible(False)
        self.table_history.setMinimumHeight(250)
        history_layout.addWidget(self.table_history)
        
        layout.addWidget(history_card)
        layout.addStretch()
        
        return page
    
    # ----------------------------------------------------------------
    # NAVIGATION
    # ----------------------------------------------------------------
    def _on_nav_click(self, page_name):
        page_map = {
            "Dashboard": 0,
            "Factura PDF": 1,
            "Análisis de Video": 2,
            "Asignación Vehicular": 3,
            "Reportes": 4,
        }
        
        icons = ["📊", "📄", "📹", "🚛", "📋"]
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
    
    def _animate_dashboard_stats(self):
        # Demo data to show the animation effect
        self.stat_despachos.animate_to(142)
        self.stat_discrepancias.animate_to(3)
        self.stat_vehiculos.animate_to(18)
    
    # ----------------------------------------------------------------
    # THEME TOGGLE
    # ----------------------------------------------------------------
    def toggle_theme(self):
        self._is_dark = not self._is_dark
        if self._is_dark:
            self.theme_label.setText("🌙 Modo Oscuro")
            self._apply_dark_theme()
        else:
            self.theme_label.setText("☀️ Modo Claro")
            self._apply_light_theme()
    
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
        self.datetime_label.setText(now.strftime("📅 %d/%m/%Y   🕐 %H:%M:%S"))

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

        except Exception as e:
            QMessageBox.critical(self, "Error al leer PDF", str(e))
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
