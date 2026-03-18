# ui/splash_screen.py
# ============================================================
#  LogiCheck — Splash Screen con carga condicional de YOLO
# ============================================================

import sys
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QApplication, QGraphicsOpacityEffect
)
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    QThread, Signal, QSequentialAnimationGroup,
    QRect
)
from PySide6.QtGui import (
    QFont, QColor, QPainter, QLinearGradient,
    QPainterPath, QRadialGradient
)

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)


# ══════════════════════════════════════════════════════════════
#  Hilo de inicialización (DB + recursos + YOLO opcional)
# ══════════════════════════════════════════════════════════════
class InitWorker(QThread):
    """Inicializa la BD, recursos y opcionalmente el modelo YOLO."""
    progress = Signal(int, str)   # (porcentaje, mensaje)
    finished = Signal(object, object)  # (model_or_None, device_or_None)

    def __init__(self, load_yolo: bool = False, user_data: dict = None):
        super().__init__()
        self.load_yolo = load_yolo
        self.user_data = user_data or {}

    def run(self):
        import time
        preloaded_model  = None
        preloaded_device = None

        try:
            from core.auth   import init_db
            from core.logger import init_logs_table

            self.progress.emit(10, "Iniciando motor de base de datos...")
            time.sleep(0.25)

            self.progress.emit(25, "Verificando tablas de usuarios...")
            init_db()
            time.sleep(0.2)

            self.progress.emit(45, "Cargando módulo de auditoría...")
            init_logs_table()
            time.sleep(0.2)

            self.progress.emit(60, "Aplicando configuración de roles...")
            time.sleep(0.15)

            if self.load_yolo:
                self.progress.emit(70, "Preparando motor de visión artificial...")
                time.sleep(0.1)
                preloaded_model, preloaded_device = self._load_yolo_model()
            else:
                self.progress.emit(70, "Preparando interfaz de usuario...")
                time.sleep(0.2)

            self.progress.emit(90, "Preparando interfaz de usuario...")
            time.sleep(0.2)

            self.progress.emit(100, "¡Listo!")
            time.sleep(0.25)

        except Exception as e:
            self.progress.emit(100, f"Error de inicialización: {e}")

        self.finished.emit(preloaded_model, preloaded_device)

    def _load_yolo_model(self):
        """Carga el modelo YOLO en CUDA. Retorna (model, device) o (None, None) si falla."""
        import time
        try:
            from ultralytics import YOLO
            import torch

            # Determinar ruta del modelo
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
                internal = os.path.join(base_dir, "_internal")
                if os.path.exists(internal):
                    base_dir = internal
            else:
                base_dir = _BASE

            model_path = os.path.join(
                base_dir, "training", "runs", "bultos_cemento2", "weights", "best.pt"
            )
            # Fallback a entrenamiento anterior
            if not os.path.exists(model_path):
                model_path = os.path.join(
                    base_dir, "training", "runs", "bultos_cemento", "weights", "best.pt"
                )
            # Fallback relativo
            if not os.path.exists(model_path):
                model_path = "training/runs/bultos_cemento2/weights/best.pt"

            device = "cuda" if torch.cuda.is_available() else "cpu"

            self.progress.emit(75, f"Cargando modelo IA en {device.upper()}...")
            time.sleep(0.1)

            model = YOLO(model_path)
            model.to(device)

            # Warm-up: ejecutar una inferencia dummy para que CUDA inicialice kernels
            self.progress.emit(85, "Calentando motor de inferencia...")
            import numpy as np
            dummy = np.zeros((480, 640, 3), dtype=np.uint8)
            model.predict(dummy, verbose=False, conf=0.5)

            print(f"[YOLO] Modelo precargado en {device}. Clases: {model.names}")
            return model, device

        except Exception as e:
            # Registrar en log sin bloquear la app
            try:
                from core import logger as app_logger
                app_logger.log_action(
                    self.user_data,
                    "ERROR_CARGA_MODELO",
                    f"No se pudo precargar el modelo YOLO: {e}"
                )
            except Exception:
                pass
            print(f"[YOLO] Advertencia: no se pudo precargar el modelo — {e}")
            return None, None


# ══════════════════════════════════════════════════════════════
#  Barra de progreso con gradiente animado
# ══════════════════════════════════════════════════════════════
class GradientProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value   = 0
        self._maximum = 100
        self.setFixedHeight(6)

    def setValue(self, v: int):
        self._value = max(0, min(v, self._maximum))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r     = h / 2

        # Fondo
        painter.setBrush(QColor("#313244"))
        painter.setPen(Qt.NoPen)
        bg_path = QPainterPath()
        bg_path.addRoundedRect(0, 0, w, h, r, r)
        painter.drawPath(bg_path)

        # Progreso con gradiente
        fill_w = int(w * self._value / self._maximum)
        if fill_w > 0:
            grad = QLinearGradient(0, 0, fill_w, 0)
            grad.setColorAt(0.0, QColor("#89b4fa"))
            grad.setColorAt(0.5, QColor("#cba6f7"))
            grad.setColorAt(1.0, QColor("#74c7ec"))
            painter.setBrush(grad)
            fg_path = QPainterPath()
            fg_path.addRoundedRect(0, 0, fill_w, h, r, r)
            painter.drawPath(fg_path)


# ══════════════════════════════════════════════════════════════
#  Partícula decorativa (círculo flotante)
# ══════════════════════════════════════════════════════════════
class FloatingParticle(QWidget):
    def __init__(self, parent, color="#89b4fa", size=8, x=0, y=0):
        super().__init__(parent)
        self._color = QColor(color)
        self._color.setAlpha(60)
        self.resize(size, size)
        self.move(x, y)
        self._animate()

    def _animate(self):
        import random
        dur  = random.randint(3000, 6000)
        dy   = random.choice([-1, 1]) * random.randint(15, 35)

        self._op = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._op)

        self._fade_in = QPropertyAnimation(self._op, b"opacity", self)
        self._fade_in.setDuration(dur // 2)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(0.6)

        self._fade_out = QPropertyAnimation(self._op, b"opacity", self)
        self._fade_out.setDuration(dur // 2)
        self._fade_out.setStartValue(0.6)
        self._fade_out.setEndValue(0.0)

        self._move = QPropertyAnimation(self, b"pos", self)
        self._move.setDuration(dur)
        self._move.setStartValue(self.pos())
        end = self.pos()
        self._move.setEndValue(type(end)(end.x(), end.y() + dy))
        self._move.setEasingCurve(QEasingCurve.SineCurve)

        self._group = QSequentialAnimationGroup(self)
        self._group.addAnimation(self._fade_in)
        self._group.addAnimation(self._fade_out)
        self._group.setLoopCount(-1)
        self._move.setLoopCount(-1)

        self._group.start()
        self._move.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(self._color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, self.width(), self.height())


# ══════════════════════════════════════════════════════════════
#  Splash Screen Principal
# ══════════════════════════════════════════════════════════════
class SplashScreen(QWidget):
    """
    Splash screen con carga condicional del modelo YOLO.
    - load_yolo=True  → precarga el modelo en CUDA y lo expone en _preloaded_model
    - load_yolo=False → solo inicializa DB (para usuarios sin permiso de video)
    """
    ready = Signal()   # emitido cuando la inicialización termina

    def __init__(self, user_data: dict = None, load_yolo: bool = False):
        super().__init__()
        self._load_yolo      = load_yolo
        self._user_data      = user_data or {}
        self._preloaded_model  = None   # Expuesto a main.py
        self._preloaded_device = None

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.SplashScreen
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(520, 340)

        # Centrar en pantalla
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width()  - self.width())  // 2,
            (screen.height() - self.height()) // 2,
        )

        self._build_ui()
        self._add_particles()
        self._fade_in()
        self._start_worker()

    # ── UI ───────────────────────────────────────────────────

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)

        # Card principal con sombra pintada
        self.card = QFrame(self)
        self.card.setObjectName("splashCard")
        self.card.setGeometry(20, 20, self.width() - 40, self.height() - 40)

        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(50, 40, 50, 35)
        layout.setSpacing(0)

        # ── Logo / Brand ──────────────────────────────────
        logo_row = QHBoxLayout()
        logo_row.setSpacing(12)

        icon_lbl = QLabel("🔍")
        icon_lbl.setStyleSheet("font-size: 40px; background: transparent;")
        logo_row.addWidget(icon_lbl)

        brand_col = QVBoxLayout()
        brand_col.setSpacing(0)

        brand = QLabel("LogiCheck")
        brand.setStyleSheet("""
            font-size: 32px;
            font-weight: 900;
            color: #89b4fa;
            letter-spacing: 2px;
            background: transparent;
        """)
        brand_col.addWidget(brand)

        slogan = QLabel("Sistema de Auditoría Logística")
        slogan.setStyleSheet("""
            font-size: 12px;
            color: #6c7086;
            letter-spacing: 0.5px;
            background: transparent;
        """)
        brand_col.addWidget(slogan)

        logo_row.addLayout(brand_col)
        logo_row.addStretch()

        # Badge de modo IA (solo si se carga YOLO)
        if self._load_yolo:
            self._ai_badge = QLabel("🧠 CUDA")
            self._ai_badge.setStyleSheet("""
                font-size: 10px;
                font-weight: 700;
                color: #a6e3a1;
                background: rgba(166,227,161,0.12);
                border: 1px solid rgba(166,227,161,0.35);
                border-radius: 8px;
                padding: 3px 8px;
            """)
            logo_row.addWidget(self._ai_badge, alignment=Qt.AlignTop)

        layout.addLayout(logo_row)
        layout.addSpacing(30)

        # ── Separador ─────────────────────────────────────
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #313244; border: none;")
        layout.addWidget(sep)

        layout.addSpacing(28)

        # ── Info versión ──────────────────────────────────
        ver_row = QHBoxLayout()
        ver_lbl = QLabel("v1.0.0  ·  Ferretería Durán")
        ver_lbl.setStyleSheet("font-size: 11px; color: #45475a; background: transparent;")
        ver_row.addWidget(ver_lbl)
        ver_row.addStretch()

        self.lbl_pct = QLabel("0%")
        self.lbl_pct.setStyleSheet("""
            font-size: 12px;
            font-weight: 700;
            color: #89b4fa;
            background: transparent;
        """)
        ver_row.addWidget(self.lbl_pct)
        layout.addLayout(ver_row)

        layout.addSpacing(8)

        # ── Barra de progreso ─────────────────────────────
        self.progress = GradientProgressBar()
        layout.addWidget(self.progress)

        layout.addSpacing(12)

        # ── Mensaje de estado ─────────────────────────────
        self.lbl_status = QLabel("Inicializando...")
        self.lbl_status.setStyleSheet("""
            font-size: 12px;
            color: #6c7086;
            background: transparent;
        """)
        layout.addWidget(self.lbl_status)

        layout.addStretch()

        # ── Footer con puntos animados ────────────────────
        footer_row = QHBoxLayout()
        copy_lbl = QLabel("© 2025 · Apulo, Cundinamarca")
        copy_lbl.setStyleSheet("font-size: 10px; color: #313244; background: transparent;")
        footer_row.addWidget(copy_lbl)
        footer_row.addStretch()

        self.lbl_dots = QLabel("●  ○  ○")
        self.lbl_dots.setStyleSheet("font-size: 10px; color: #45475a; background: transparent;")
        footer_row.addWidget(self.lbl_dots)
        layout.addLayout(footer_row)

        # ── Dots animation ────────────────────────────────
        self._dots_states = ["●  ○  ○", "○  ●  ○", "○  ○  ●", "○  ●  ○"]
        self._dots_idx    = 0
        self._dots_timer  = QTimer(self)
        self._dots_timer.timeout.connect(self._tick_dots)
        self._dots_timer.start(420)

        # ── Estilos ───────────────────────────────────────
        self.setStyleSheet("""
            #splashCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e1e2e, stop:1 #181825);
                border: 1px solid #313244;
                border-radius: 18px;
            }
        """)

    def _add_particles(self):
        """Agrega círculos decorativos flotantes."""
        import random
        palette = ["#89b4fa", "#cba6f7", "#74c7ec", "#a6e3a1", "#f9e2af"]
        random.seed(42)
        for _ in range(12):
            color = random.choice(palette)
            size  = random.randint(5, 14)
            x     = random.randint(0, self.width()  - size)
            y     = random.randint(0, self.height() - size)
            FloatingParticle(self, color=color, size=size, x=x, y=y)

    # ── Animaciones ──────────────────────────────────────────

    def _fade_in(self):
        self._op_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._op_effect)
        self._anim_in = QPropertyAnimation(self._op_effect, b"opacity", self)
        self._anim_in.setDuration(500)
        self._anim_in.setStartValue(0.0)
        self._anim_in.setEndValue(1.0)
        self._anim_in.setEasingCurve(QEasingCurve.InOutQuad)
        self._anim_in.start()

    def fade_out_and_close(self):
        self._dots_timer.stop()
        self._anim_out = QPropertyAnimation(self._op_effect, b"opacity", self)
        self._anim_out.setDuration(450)
        self._anim_out.setStartValue(1.0)
        self._anim_out.setEndValue(0.0)
        self._anim_out.setEasingCurve(QEasingCurve.InOutQuad)
        self._anim_out.finished.connect(self.close)
        self._anim_out.start()

    # ── Dots animation ───────────────────────────────────────

    def _tick_dots(self):
        self._dots_idx = (self._dots_idx + 1) % len(self._dots_states)
        self.lbl_dots.setText(self._dots_states[self._dots_idx])

    # ── Worker de inicialización ─────────────────────────────

    def _start_worker(self):
        self._worker = InitWorker(load_yolo=self._load_yolo, user_data=self._user_data)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_progress(self, value: int, message: str):
        # Animar la barra suavemente
        self._bar_anim = QPropertyAnimation(duration=180, parent=self)
        self._bar_anim.setStartValue(self.progress._value)
        self._bar_anim.setEndValue(value)
        self._bar_anim.valueChanged.connect(
            lambda v: (self.progress.setValue(int(v)),
                       self.lbl_pct.setText(f"{int(v)}%"))
        )
        self._bar_anim.start()
        self.lbl_status.setText(message)

    def _on_finished(self, model, device):
        """Recibe el modelo precargado (o None si falló/no aplica)."""
        self._preloaded_model  = model
        self._preloaded_device = device

        # Si se cargó correctamente, actualizar badge
        if model is not None and hasattr(self, "_ai_badge"):
            self._ai_badge.setText(f"🧠 {(device or 'cpu').upper()} ✓")
            self._ai_badge.setStyleSheet("""
                font-size: 10px;
                font-weight: 700;
                color: #a6e3a1;
                background: rgba(166,227,161,0.20);
                border: 1px solid #a6e3a1;
                border-radius: 8px;
                padding: 3px 8px;
            """)
        elif self._load_yolo and model is None and hasattr(self, "_ai_badge"):
            self._ai_badge.setText("⚠️ IA no disponible")
            self._ai_badge.setStyleSheet("""
                font-size: 10px;
                font-weight: 700;
                color: #f9e2af;
                background: rgba(249,226,175,0.12);
                border: 1px solid rgba(249,226,175,0.35);
                border-radius: 8px;
                padding: 3px 8px;
            """)

        QTimer.singleShot(400, lambda: (self.fade_out_and_close(), self.ready.emit()))

    # ── Pintado del fondo (sombra suave) ─────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Sombra difusa (radial sobre fondo transparente)
        grad = QRadialGradient(
            self.width() / 2, self.height() / 2,
            max(self.width(), self.height()) / 1.5
        )
        grad.setColorAt(0.0, QColor(0, 0, 0, 80))
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(grad)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(
            -20, -20,
            self.width() + 40, self.height() + 40
        )
