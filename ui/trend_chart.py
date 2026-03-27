from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPainterPath, QLinearGradient, QPen, QColor
from PySide6.QtCore import Qt, QPoint

class ModernTrendChart(QWidget):
    """Widget de gráfica de tendencia premium usando QPainter.
    Espera una lista de dicts con claves 'total' y 'discrepancies'.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.data = []
        self._max_val = 10

    def set_data(self, data):
        """Recibe datos como [{'total': int, 'discrepancies': int}, ...]"""
        self.data = data
        if data:
            self._max_val = max([d['total'] for d in data] + [10])
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        padding = 40
        chart_w = w - padding * 2
        chart_h = h - padding * 2
        if not self.data:
            painter.setPen(QPen(QColor('#6c7086'), 1))
            painter.drawText(self.rect(), Qt.AlignCenter, 'Sin datos históricos')
            return
        # Ejes
        painter.setPen(QPen(QColor('#313244'), 1, Qt.DashLine))
        for i in range(5):
            y = padding + chart_h - (chart_h / 4 * i)
            painter.drawLine(int(padding), int(y), int(w - padding), int(y))
        # Puntos
        points = []
        step_x = chart_w / (len(self.data) - 1) if len(self.data) > 1 else chart_w
        for i, d in enumerate(self.data):
            px = padding + i * step_x
            py = padding + chart_h - (d['total'] / self._max_val * chart_h)
            points.append(QPoint(int(px), int(py)))
        if len(points) > 1:
            # Área degradada
            path_area = QPainterPath()
            path_area.moveTo(points[0].x(), padding + chart_h)
            for p in points:
                path_area.lineTo(p)
            path_area.lineTo(points[-1].x(), padding + chart_h)
            path_area.closeSubpath()
            grad = QLinearGradient(0, padding, 0, padding + chart_h)
            grad.setColorAt(0, QColor(137, 180, 250, 100))
            grad.setColorAt(1, QColor(137, 180, 250, 0))
            painter.setBrush(grad)
            painter.setPen(Qt.NoPen)
            painter.drawPath(path_area)
            # Línea principal
            painter.setPen(QPen(QColor('#89b4fa'), 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            path_line = QPainterPath()
            path_line.moveTo(points[0])
            for i in range(len(points) - 1):
                p1 = points[i]
                p2 = points[i + 1]
                cp1 = QPoint(int(p1.x() + (p2.x() - p1.x()) / 2), p1.y())
                cp2 = QPoint(int(p1.x() + (p2.x() - p1.x()) / 2), p2.y())
                path_line.cubicTo(cp1, cp2, p2)
            painter.drawPath(path_line)
            # Discrepancias (línea roja punteada)
            painter.setPen(QPen(QColor('#f38ba8'), 2, Qt.DotLine))
            path_disc = QPainterPath()
            path_disc.moveTo(padding, padding + chart_h - (self.data[0]['discrepancies'] / self._max_val * chart_h))
            for i, d in enumerate(self.data):
                px = padding + i * step_x
                py = padding + chart_h - (d['discrepancies'] / self._max_val * chart_h)
                path_disc.lineTo(int(px), int(py))
            painter.drawPath(path_disc)
        painter.end()
