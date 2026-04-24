"""Widgets premium para el dashboard de LogiCheck."""
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Property, QRectF, QPointF
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPen, QFont, QLinearGradient
import datetime


class MiniSparkline(QWidget):
    """Pequeña gráfica de línea (sparkline) para mostrar tendencia en las stat cards."""
    def __init__(self, color="#3B82F6", parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.setMinimumWidth(60)
        self._color = QColor(color)
        self._data = []

    def set_data(self, data: list):
        """Recibe lista de ints/floats."""
        self._data = data or []
        self.update()

    def paintEvent(self, event):
        if len(self._data) < 2:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        pad = 3
        cw = w - pad * 2
        ch = h - pad * 2
        max_val = max(self._data) or 1
        min_val = min(self._data)
        val_range = max(max_val - min_val, 1)

        points = []
        step = cw / max(len(self._data) - 1, 1)
        for i, v in enumerate(self._data):
            px = pad + i * step
            py = pad + ch - ((v - min_val) / val_range * ch)
            points.append(QPointF(px, py))

        # Gradient fill
        area = QPainterPath()
        area.moveTo(points[0].x(), pad + ch)
        for p in points:
            area.lineTo(p)
        area.lineTo(points[-1].x(), pad + ch)
        area.closeSubpath()

        grad = QLinearGradient(0, pad, 0, pad + ch)
        c1 = QColor(self._color)
        c1.setAlpha(50)
        c2 = QColor(self._color)
        c2.setAlpha(0)
        grad.setColorAt(0, c1)
        grad.setColorAt(1, c2)
        painter.setBrush(grad)
        painter.setPen(Qt.NoPen)
        painter.drawPath(area)

        # Line
        path = QPainterPath()
        path.moveTo(points[0])
        for i in range(len(points) - 1):
            p1, p2 = points[i], points[i + 1]
            cp1 = QPointF(p1.x() + (p2.x() - p1.x()) / 2, p1.y())
            cp2 = QPointF(p1.x() + (p2.x() - p1.x()) / 2, p2.y())
            path.cubicTo(cp1, cp2, p2)

        painter.setPen(QPen(self._color, 1.5, Qt.SolidLine, Qt.RoundCap))
        painter.drawPath(path)

        # End dot
        painter.setBrush(self._color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(points[-1], 2.5, 2.5)

        painter.end()


class ChangeBadge(QLabel):
    """Badge que muestra un porcentaje de cambio (positivo/negativo) con color."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(20)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(
            "font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 10px;"
            "background: rgba(166,227,161,0.15); color: #10B981;"
        )
        self.setText("— ")

    def set_change(self, pct: float):
        """Set the percentage change. Positive = green, Negative = red, Zero = neutral."""
        if pct > 0:
            self.setText(f"▲ {pct:+.0f}%")
            self.setStyleSheet(
                "font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 10px;"
                "background: rgba(166,227,161,0.15); color: #10B981;"
            )
        elif pct < 0:
            self.setText(f"▼ {pct:.0f}%")
            self.setStyleSheet(
                "font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 10px;"
                "background: rgba(243,139,168,0.15); color: #EF4444;"
            )
        else:
            self.setText("— 0%")
            self.setStyleSheet(
                "font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 10px;"
                "background: rgba(108,112,134,0.15); color: #64748B;"
            )


class SystemHealthWidget(QWidget):
    """Widget de salud del sistema con barras animadas."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []  # list of (label, value 0-100, color)

    def set_items(self, items: list):
        """items = [(label, value_pct, hex_color), ...]"""
        self._items = items
        self.setMinimumHeight(max(len(items) * 36 + 10, 60))
        self.update()

    def paintEvent(self, event):
        if not self._items:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        w = self.width()
        bar_h = 8
        row_h = 36
        label_w = 90
        val_w = 40
        bar_x = label_w + 8
        bar_w = w - bar_x - val_w - 8

        is_dark = True
        if hasattr(self.window(), '_is_dark'):
            is_dark = self.window()._is_dark

        for i, (label, value, color) in enumerate(self._items):
            y = i * row_h + 10

            # Label
            painter.setPen(QColor('#CBD5E1' if is_dark else '#4c4f69'))
            font = QFont('Segoe UI', 10)
            font.setWeight(QFont.DemiBold)
            painter.setFont(font)
            painter.drawText(QRectF(0, y, label_w, 20), Qt.AlignRight | Qt.AlignVCenter, label)

            # Track
            track_y = y + 22
            track_color = QColor('#1E293B' if is_dark else '#dce0e8')
            painter.setPen(Qt.NoPen)
            painter.setBrush(track_color)
            painter.drawRoundedRect(QRectF(bar_x, track_y, bar_w, bar_h), 4, 4)

            # Fill
            fill_w = max(0, min(value / 100.0 * bar_w, bar_w))
            fill_color = QColor(color)
            grad = QLinearGradient(bar_x, 0, bar_x + fill_w, 0)
            grad.setColorAt(0, fill_color)
            highlight = QColor(fill_color)
            highlight.setAlpha(180)
            grad.setColorAt(1, highlight)
            painter.setBrush(grad)
            painter.drawRoundedRect(QRectF(bar_x, track_y, fill_w, bar_h), 4, 4)

            # Value text
            painter.setPen(QColor(color))
            font2 = QFont('Segoe UI', 9)
            font2.setWeight(QFont.Bold)
            painter.setFont(font2)
            painter.drawText(
                QRectF(bar_x + bar_w + 8, y, val_w, 30),
                Qt.AlignLeft | Qt.AlignVCenter,
                f"{value}%"
            )

        painter.end()


class ActivityTimelineWidget(QWidget):
    """Mini-timeline vertical de actividad reciente."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._events = []  # list of (time_str, description, color_hex)
        self.setMinimumHeight(120)

    def set_events(self, events: list):
        """events = [(time_str, description, color_hex), ...]"""
        self._events = events[:6]  # Max 6 events
        self.setMinimumHeight(max(len(self._events) * 40 + 10, 60))
        self.update()

    def paintEvent(self, event):
        if not self._events:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.TextAntialiasing)
            painter.setPen(QColor('#585b70'))
            font = QFont('Segoe UI', 10)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, "Sin actividad reciente")
            painter.end()
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        is_dark = True
        if hasattr(self.window(), '_is_dark'):
            is_dark = self.window()._is_dark

        dot_r = 5
        line_x = 20
        text_x = 38
        row_h = 40

        for i, (time_str, desc, color_hex) in enumerate(self._events):
            y = i * row_h + 14
            color = QColor(color_hex)

            # Vertical connector line
            if i < len(self._events) - 1:
                lc = QColor('#1E293B' if is_dark else '#dce0e8')
                painter.setPen(QPen(lc, 1.5))
                painter.drawLine(line_x, y + dot_r, line_x, y + row_h)

            # Dot
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(QPointF(line_x, y), dot_r, dot_r)

            # Time
            painter.setPen(QColor('#64748B' if is_dark else '#4c4f69'))
            font_time = QFont('Segoe UI', 9)
            font_time.setWeight(QFont.Bold)
            painter.setFont(font_time)
            painter.drawText(QRectF(text_x, y - 9, 60, 16), Qt.AlignLeft | Qt.AlignVCenter, time_str)

            # Description
            painter.setPen(QColor('#F8FAFC' if is_dark else '#0c0c0d'))
            font_desc = QFont('Segoe UI', 10)
            painter.setFont(font_desc)
            painter.drawText(
                QRectF(text_x + 62, y - 9, self.width() - text_x - 70, 16),
                Qt.AlignLeft | Qt.AlignVCenter, desc
            )

        painter.end()


def get_greeting(user_name: str = "") -> str:
    """Retorna un saludo basado en la hora del día."""
    hour = datetime.datetime.now().hour
    if hour < 6:
        prefix = "🌙 Buenas noches"
    elif hour < 12:
        prefix = "☀️ Buenos días"
    elif hour < 18:
        prefix = "🌤️ Buenas tardes"
    else:
        prefix = "🌙 Buenas noches"

    if user_name:
        first_name = user_name.split()[0]
        return f"{prefix}, {first_name}"
    return prefix
