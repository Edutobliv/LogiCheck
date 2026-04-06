from PySide6.QtWidgets import QWidget, QToolTip
from PySide6.QtGui import (QPainter, QPainterPath, QLinearGradient, QPen, QColor,
                            QFont, QFontMetrics, QRadialGradient)
from PySide6.QtCore import Qt, QPoint, QPointF, QRectF, QTimer, QPropertyAnimation, QEasingCurve, Property


class ModernTrendChart(QWidget):
    """Widget de gráfica de tendencia premium usando QPainter.
    Espera una lista de dicts con claves 'total' y 'discrepancies'.
    Incluye hover interactivo, ejes con etiquetas, puntos animados y gradientes mejorados.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(250)
        self.data = []
        self._max_val = 10
        self._hover_index = -1
        self._points_total = []
        self._points_disc = []
        self.setMouseTracking(True)

        # Animation progress for entrance
        self._anim_progress = 0.0
        self._entrance_anim = QPropertyAnimation(self, b"anim_progress")
        self._entrance_anim.setDuration(800)
        self._entrance_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._entrance_anim.setStartValue(0.0)
        self._entrance_anim.setEndValue(1.0)

    def get_anim_progress(self):
        return self._anim_progress

    def set_anim_progress(self, val):
        self._anim_progress = val
        self.update()

    anim_progress = Property(float, get_anim_progress, set_anim_progress)

    def set_data(self, data):
        """Recibe datos como [{'total': int, 'discrepancies': int}, ...]"""
        self.data = data
        if data:
            self._max_val = max(
                max(d.get('total', 0) for d in data),
                max(d.get('discrepancies', 0) for d in data),
                10
            )
        # Animate entrance
        self._anim_progress = 0.0
        self._entrance_anim.stop()
        self._entrance_anim.start()

    def _compute_points(self, w, h, padding_l, padding_r, padding_t, padding_b):
        """Compute chart point positions."""
        chart_w = w - padding_l - padding_r
        chart_h = h - padding_t - padding_b
        step_x = chart_w / max(len(self.data) - 1, 1)

        points_total = []
        points_disc = []
        for i, d in enumerate(self.data):
            px = padding_l + i * step_x
            # Total
            val_t = d.get('total', 0)
            py_t = padding_t + chart_h - (val_t / self._max_val * chart_h)
            points_total.append(QPointF(px, py_t))
            # Discrepancies
            val_d = d.get('discrepancies', 0)
            py_d = padding_t + chart_h - (val_d / self._max_val * chart_h)
            points_disc.append(QPointF(px, py_d))

        return points_total, points_disc, chart_w, chart_h, step_x

    def mouseMoveEvent(self, event):
        if not self.data or len(self._points_total) == 0:
            self._hover_index = -1
            self.update()
            return

        mx = event.position().x() if hasattr(event, 'position') else event.x()
        closest = -1
        min_dist = float('inf')
        for i, p in enumerate(self._points_total):
            dist = abs(p.x() - mx)
            if dist < min_dist:
                min_dist = dist
                closest = i

        # Only snap if within 30px
        if min_dist <= 30:
            self._hover_index = closest
        else:
            self._hover_index = -1
        self.update()

    def leaveEvent(self, event):
        self._hover_index = -1
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height()

        # Paddings
        padding_l = 52   # left (for Y labels)
        padding_r = 20   # right
        padding_t = 20   # top
        padding_b = 36   # bottom (for X labels)

        chart_w = w - padding_l - padding_r
        chart_h = h - padding_t - padding_b

        if not self.data:
            painter.setPen(QPen(QColor('#585b70'), 1))
            font = QFont('Segoe UI', 11)
            font.setWeight(QFont.DemiBold)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, 'Sin datos históricos')
            painter.end()
            return

        # Detect theme
        is_dark = True
        if hasattr(self.window(), '_is_dark'):
            is_dark = self.window()._is_dark

        grid_color = QColor('#313244') if is_dark else QColor('#dce0e8')
        label_color = QColor('#6c7086') if is_dark else QColor('#4c4f69')
        total_color = QColor('#89b4fa') if is_dark else QColor('#1e66f5')
        disc_color = QColor('#f38ba8') if is_dark else QColor('#d20f39')

        small_font = QFont('Segoe UI', 9)
        small_font.setWeight(QFont.DemiBold)
        painter.setFont(small_font)

        # ── Y-Axis gridlines + labels ──
        num_lines = 5
        for i in range(num_lines + 1):
            y = padding_t + chart_h - (chart_h / num_lines * i)
            val = int(self._max_val / num_lines * i)

            # Gridline
            pen = QPen(grid_color, 1, Qt.DotLine)
            pen.setDashPattern([2, 6])
            painter.setPen(pen)
            painter.drawLine(int(padding_l), int(y), int(w - padding_r), int(y))

            # Label
            painter.setPen(label_color)
            painter.drawText(
                QRectF(0, y - 10, padding_l - 8, 20),
                Qt.AlignRight | Qt.AlignVCenter,
                str(val)
            )

        # Compute points
        pts_total, pts_disc, _, _, step_x = self._compute_points(
            w, h, padding_l, padding_r, padding_t, padding_b
        )
        self._points_total = pts_total
        self._points_disc = pts_disc

        # Apply animation progress: only draw up to anim_progress
        anim_count = max(1, int(len(pts_total) * self._anim_progress))
        pts_total_draw = pts_total[:anim_count]
        pts_disc_draw = pts_disc[:anim_count]

        if len(pts_total_draw) > 1:
            # ── Filled Area under Total ──
            area_path = QPainterPath()
            area_path.moveTo(pts_total_draw[0].x(), padding_t + chart_h)
            for p in pts_total_draw:
                area_path.lineTo(p)
            area_path.lineTo(pts_total_draw[-1].x(), padding_t + chart_h)
            area_path.closeSubpath()

            grad = QLinearGradient(0, padding_t, 0, padding_t + chart_h)
            c1 = QColor(total_color)
            c1.setAlpha(65)
            c2 = QColor(total_color)
            c2.setAlpha(0)
            grad.setColorAt(0, c1)
            grad.setColorAt(1, c2)
            painter.setBrush(grad)
            painter.setPen(Qt.NoPen)
            painter.drawPath(area_path)

            # ── Filled Area under Discrepancies ──
            disc_area = QPainterPath()
            disc_area.moveTo(pts_disc_draw[0].x(), padding_t + chart_h)
            for p in pts_disc_draw:
                disc_area.lineTo(p)
            disc_area.lineTo(pts_disc_draw[-1].x(), padding_t + chart_h)
            disc_area.closeSubpath()

            grad_d = QLinearGradient(0, padding_t, 0, padding_t + chart_h)
            cd1 = QColor(disc_color)
            cd1.setAlpha(35)
            cd2 = QColor(disc_color)
            cd2.setAlpha(0)
            grad_d.setColorAt(0, cd1)
            grad_d.setColorAt(1, cd2)
            painter.setBrush(grad_d)
            painter.setPen(Qt.NoPen)
            painter.drawPath(disc_area)

            # ── Total Line (smooth bezier) ──
            painter.setPen(QPen(total_color, 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            total_path = QPainterPath()
            total_path.moveTo(pts_total_draw[0])
            for i in range(len(pts_total_draw) - 1):
                p1 = pts_total_draw[i]
                p2 = pts_total_draw[i + 1]
                cp1 = QPointF(p1.x() + (p2.x() - p1.x()) / 2, p1.y())
                cp2 = QPointF(p1.x() + (p2.x() - p1.x()) / 2, p2.y())
                total_path.cubicTo(cp1, cp2, p2)
            painter.drawPath(total_path)

            # ── Discrepancies Line (smooth bezier, slightly transparent) ──
            dc = QColor(disc_color)
            dc.setAlpha(200)
            painter.setPen(QPen(dc, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            disc_path = QPainterPath()
            disc_path.moveTo(pts_disc_draw[0])
            for i in range(len(pts_disc_draw) - 1):
                p1 = pts_disc_draw[i]
                p2 = pts_disc_draw[i + 1]
                cp1 = QPointF(p1.x() + (p2.x() - p1.x()) / 2, p1.y())
                cp2 = QPointF(p1.x() + (p2.x() - p1.x()) / 2, p2.y())
                disc_path.cubicTo(cp1, cp2, p2)
            painter.drawPath(disc_path)

            # ── Data Points (dots) ──
            for i, p in enumerate(pts_total_draw):
                is_hovered = (i == self._hover_index)
                radius = 5 if is_hovered else 3
                painter.setPen(Qt.NoPen)
                if is_hovered:
                    # Glow
                    glow = QRadialGradient(p, 12)
                    gc = QColor(total_color)
                    gc.setAlpha(80)
                    glow.setColorAt(0, gc)
                    gc2 = QColor(total_color)
                    gc2.setAlpha(0)
                    glow.setColorAt(1, gc2)
                    painter.setBrush(glow)
                    painter.drawEllipse(p, 12, 12)

                painter.setBrush(total_color)
                painter.drawEllipse(p, radius, radius)

            for i, p in enumerate(pts_disc_draw):
                is_hovered = (i == self._hover_index)
                radius = 5 if is_hovered else 2.5
                painter.setPen(Qt.NoPen)
                painter.setBrush(disc_color)
                painter.drawEllipse(p, radius, radius)

        # ── X-Axis labels ──
        painter.setFont(small_font)
        painter.setPen(label_color)
        n = len(self.data)
        # Show every Nth label to avoid overlap
        skip = max(1, n // 8)
        for i in range(0, n, skip):
            if i < len(pts_total):
                x = pts_total[i].x()
                label = self.data[i].get('label', f'D{i+1}')
                painter.drawText(
                    QRectF(x - 20, h - padding_b + 6, 40, 20),
                    Qt.AlignCenter, str(label)
                )

        # ── Hover tooltip ──
        if 0 <= self._hover_index < len(self.data) and self._hover_index < len(pts_total):
            d = self.data[self._hover_index]
            p = pts_total[self._hover_index]

            total_val = d.get('total', 0)
            disc_val = d.get('discrepancies', 0)
            label = d.get('label', f'Día {self._hover_index + 1}')

            # Vertical guide line
            guide_pen = QPen(QColor(total_color))
            guide_pen.setWidth(1)
            guide_pen.setStyle(Qt.DashLine)
            guide_pen.setDashPattern([3, 5])
            painter.setPen(guide_pen)
            painter.drawLine(
                int(p.x()), int(padding_t),
                int(p.x()), int(padding_t + chart_h)
            )

            # Tooltip background
            tt_w, tt_h = 140, 60
            tt_x = p.x() - tt_w / 2
            tt_y = p.y() - tt_h - 16
            # Keep within bounds
            tt_x = max(padding_l, min(tt_x, w - padding_r - tt_w))
            tt_y = max(padding_t, tt_y)

            tt_rect = QRectF(tt_x, tt_y, tt_w, tt_h)
            bg_color = QColor('#1e1e2e' if is_dark else '#ffffff')
            bg_color.setAlpha(235)
            border_color = QColor('#45475a' if is_dark else '#dce0e8')

            painter.setPen(QPen(border_color, 1))
            painter.setBrush(bg_color)
            painter.drawRoundedRect(tt_rect, 8, 8)

            # Tooltip text
            tt_font = QFont('Segoe UI', 9)
            tt_font.setWeight(QFont.Bold)
            painter.setFont(tt_font)

            text_color = QColor('#cdd6f4' if is_dark else '#0c0c0d')
            painter.setPen(text_color)
            painter.drawText(
                QRectF(tt_x + 10, tt_y + 6, tt_w - 20, 16),
                Qt.AlignLeft | Qt.AlignVCenter, str(label)
            )

            # Total
            painter.setPen(total_color)
            painter.drawText(
                QRectF(tt_x + 10, tt_y + 22, tt_w - 20, 16),
                Qt.AlignLeft | Qt.AlignVCenter, f"● Total: {total_val}"
            )

            # Discrepancies
            painter.setPen(disc_color)
            painter.drawText(
                QRectF(tt_x + 10, tt_y + 38, tt_w - 20, 16),
                Qt.AlignLeft | Qt.AlignVCenter, f"● Disc: {disc_val}"
            )

        painter.end()
