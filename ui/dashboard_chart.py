"""
dashboard_chart.py
==================
Widget de gráfica dinámica de tendencias para el Dashboard de LogiCheck.
Muestra los últimos 7 días de despachos vs. discrepancias en tiempo real.
Usa Matplotlib embebido en PySide6 via FigureCanvasQTAgg.
"""

import datetime
from typing import List, Dict

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QSizePolicy
from PySide6.QtGui import QColor

try:
    import matplotlib
    matplotlib.use("Agg")  # Backend sin ventana propia
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.ticker as ticker
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# Paleta de colores consistente con el resto de la UI de LogiCheck
PALETTE = {
    "bg":          "#1a1f2e",       # Fondo oscuro principal
    "panel":       "#222840",       # Fondo del panel de gráfica
    "grid":        "#2e3555",       # Líneas de grid
    "conformes":   "#3dd68c",       # Verde — despachos conformes
    "disc":        "#ff6b6b",       # Rojo — discrepancias
    "total":       "#4d9de0",       # Azul — total despachos
    "text":        "#F8FAFC",       # Texto claro
    "accent":      "#3B82F6",       # Azul acento
}

REFRESH_INTERVAL_MS = 60_000   # Actualizar cada 1 minuto


class TrendChartWidget(QWidget):
    """
    Widget que muestra la tendencia de despachos de los últimos N días.
    Se auto-refresca cada minuto y expone un método manual refresh().
    """

    refreshed = Signal()   # Emitido después de cada actualización

    def __init__(self, parent=None, days: int = 7):
        super().__init__(parent)
        self.days = days
        self._setup_ui()

        # Timer de auto-refresco
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(REFRESH_INTERVAL_MS)

        # Carga inicial
        self.refresh()

    # ──────────────────────────────────────────────────────────
    #  UI Setup
    # ──────────────────────────────────────────────────────────
    def _setup_ui(self):
        self.setMinimumHeight(240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header
        header = QHBoxLayout()
        title = QLabel(f"Tendencia — Últimos {self.days} Días")
        title.setStyleSheet(f"color: {PALETTE['accent']}; font-weight: 700; font-size: 13px;")
        self._lbl_refresh = QLabel()
        self._lbl_refresh.setStyleSheet(f"color: {PALETTE['text']}; font-size: 10px;")
        self._lbl_refresh.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self._lbl_refresh)
        layout.addLayout(header)

        if MATPLOTLIB_AVAILABLE:
            self._fig = Figure(figsize=(6, 2.8), dpi=96, facecolor=PALETTE["panel"])
            self._ax  = self._fig.add_subplot(111)
            self._canvas = FigureCanvas(self._fig)
            self._canvas.setStyleSheet(f"background-color: {PALETTE['panel']}; border-radius: 8px;")
            layout.addWidget(self._canvas)
        else:
            fallback = QLabel("⚠ Instala matplotlib para ver la gráfica:\npip install matplotlib")
            fallback.setAlignment(Qt.AlignCenter)
            fallback.setStyleSheet(f"color: {PALETTE['text']}; font-size: 12px;")
            layout.addWidget(fallback)

    # ──────────────────────────────────────────────────────────
    #  Refresco de datos
    # ──────────────────────────────────────────────────────────
    def refresh(self):
        """Recarga datos de la BD y actualiza la gráfica."""
        if not MATPLOTLIB_AVAILABLE:
            return

        try:
            from core.audit_store import get_monthly_trends
            raw_data = get_monthly_trends()
        except Exception:
            raw_data = []

        # Completar con los últimos N días (incluyendo días sin datos)
        data = self._fill_missing_days(raw_data, self.days)
        self._render(data)

        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._lbl_refresh.setText(f"Act: {ts}")
        self.refreshed.emit()

    def _fill_missing_days(self, raw: List[Dict], n: int) -> List[Dict]:
        """Garantiza exactamente N días; rellena con ceros los días sin registros."""
        today     = datetime.date.today()
        date_map  = {r["date"]: r for r in raw}
        result    = []
        for i in range(n - 1, -1, -1):
            day = (today - datetime.timedelta(days=i)).isoformat()
            if day in date_map:
                result.append(date_map[day])
            else:
                result.append({"date": day, "total": 0, "discrepancies": 0})
        return result

    # ──────────────────────────────────────────────────────────
    #  Renderizado Matplotlib
    # ──────────────────────────────────────────────────────────
    def _render(self, data: List[Dict]):
        ax  = self._ax
        fig = self._fig
        ax.clear()
        ax.set_facecolor(PALETTE["panel"])
        fig.patch.set_facecolor(PALETTE["panel"])

        if not data:
            ax.text(0.5, 0.5, "Sin datos aún", transform=ax.transAxes,
                    ha="center", va="center", color=PALETTE["text"], fontsize=12)
            self._canvas.draw()
            return

        # Datos
        dates      = [datetime.date.fromisoformat(d["date"]) for d in data]
        totals     = [d["total"] for d in data]
        discs      = [d["discrepancies"] for d in data]
        conformes  = [t - d for t, d in zip(totals, discs)]

        # Plot barras apiladas
        x = range(len(dates))
        bars_conf = ax.bar(x, conformes, color=PALETTE["conformes"],
                           alpha=0.85, label="Conformes", width=0.6, zorder=3)
        bars_disc = ax.bar(x, discs, bottom=conformes, color=PALETTE["disc"],
                           alpha=0.85, label="Discrepancias", width=0.6, zorder=3)

        # Línea de total
        ax.plot(x, totals, color=PALETTE["total"], marker="o",
                markersize=5, linewidth=1.8, label="Total", zorder=4, alpha=0.9)

        # Etiquetas en las barras
        for xi, t in zip(x, totals):
            if t > 0:
                ax.text(xi, t + 0.1, str(t), ha="center", va="bottom",
                        color=PALETTE["text"], fontsize=8, fontweight="bold")

        # Eje X con fechas abreviadas
        ax.set_xticks(list(x))
        date_labels = [d.strftime("%d/%m") for d in dates]
        ax.set_xticklabels(date_labels, color=PALETTE["text"], fontsize=9, rotation=0)
        ax.tick_params(axis="y", colors=PALETTE["text"], labelsize=9)

        # Grid sutil
        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True, nbins=5))
        ax.grid(axis="y", color=PALETTE["grid"], linestyle="--", linewidth=0.7, zorder=0)
        ax.set_axisbelow(True)

        # Bordes
        for spine in ax.spines.values():
            spine.set_color(PALETTE["grid"])

        # Leyenda
        legend = ax.legend(
            loc="upper left", fontsize=9,
            facecolor=PALETTE["bg"], edgecolor=PALETTE["grid"],
            labelcolor=PALETTE["text"],
        )

        # Layout compacto
        fig.tight_layout(pad=0.6)
        self._canvas.draw()


# ──────────────────────────────────────────────────────────────────────────
#  Widget de KPI compacto (número + etiqueta + color)
# ──────────────────────────────────────────────────────────────────────────
class KpiCard(QWidget):
    """Tarjeta de indicador clave (número + label) con color dinámico."""

    def __init__(self, label: str, value: str = "—",
                 color: str = PALETTE["accent"], parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        self._val_label = QLabel(value)
        self._val_label.setAlignment(Qt.AlignCenter)
        self._val_label.setStyleSheet(
            f"color: {color}; font-size: 28px; font-weight: 800;"
        )

        self._text_label = QLabel(label.upper())
        self._text_label.setAlignment(Qt.AlignCenter)
        self._text_label.setStyleSheet(
            f"color: {PALETTE['text']}; font-size: 10px; font-weight: 600; letter-spacing: 1px;"
        )

        layout.addWidget(self._val_label)
        layout.addWidget(self._text_label)

        self.setStyleSheet(
            f"background-color: {PALETTE['panel']}; border-radius: 10px;"
        )

    def set_value(self, value: str, color: str = None):
        self._val_label.setText(str(value))
        if color:
            self._val_label.setStyleSheet(
                f"color: {color}; font-size: 28px; font-weight: 800;"
            )
