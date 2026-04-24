# ui/logs_page.py
# ============================================================
#  LogiCheck — Página de Actividad / Logs
#  Admin: ve TODOS los logs + filtros por usuario y acción
#  Otros roles: solo ven SUS propios logs
# ============================================================

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QGraphicsDropShadowEffect, QAbstractItemView,
    QScrollArea, QSizePolicy, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
import sys, os, csv, datetime

_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _base not in sys.path:
    sys.path.insert(0, _base)

from core.logger import (
    get_logs_filtered, get_distinct_usernames, get_distinct_actions,
    get_stats_today
)
from core.permissions import ROLES, ROLE_ICONS

# Colores de acción para la tabla (Equilibrados para ambos temas)
ACTION_COLORS = {
    "Inicio de Sesión":           "#40a02b",   # Verde vibrante
    "Intento de Acceso Fallido":  "#d20f39",   # Rojo profundo
    "Cierre de Sesión":           "#df8e1d",   # Amarillo oscuro/Naranja
    "Acceso Denegado":            "#d20f39",   # Rojo
    "Factura Cargada":            "#1e66f5",   # Azul
    "Factura con Advertencia":    "#fe640b",   # Naranja
    "Factura Procesada":          "#04a5e5",   # Cyan oscuro
    "Video Iniciado":             "#8839ef",   # Púrpura
    "Video Detenido":             "#d20f39",   # Rojo
    "Resultado de Análisis":      "#179299",   # Teal oscuro
    "Discrepancia Detectada":     "#d20f39",   # Rojo — crítico
    "Asignación Vehicular":       "#df8e1d",   # Ocre
    "Reporte Exportado":          "#179299",   # Teal
    "Cambio de Tema":             "#4c4f69",   # Gris oscuro legible
    "Usuario Creado":             "#40a02b",   # Verde
    "Usuario Editado":            "#1e66f5",   # Azul
    "Usuario Desactivado":        "#d20f39",   # Rojo
    "Usuario Activado":           "#40a02b",   # Verde
    "Contraseña Cambiada":        "#8839ef",   # Púrpura
}


class LogsPage(QWidget):
    """Página de actividad con doble comportamiento según el rol del usuario."""

    def __init__(self, user_data: dict, parent=None):
        super().__init__(parent)
        self._user = user_data
        self._role = user_data.get("role", "")
        self._username = user_data.get("username", "")
        self._is_admin = self._role == "admin"
        self._build_ui()
        self.refresh()

    # ── UI ───────────────────────────────────────────────────

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(20)

        # ── Header ──
        header_row = QHBoxLayout()

        col = QVBoxLayout(); col.setSpacing(2)
        icon = "🔍" if self._is_admin else "📋"
        subtitle = ("Registro global de todas las acciones del sistema."
                    if self._is_admin else
                    f"Registros de actividad de '{self._username}'.")
        lbl_title = QLabel(f"{icon}  Registro de Actividad")
        lbl_title.setObjectName("welcomeTitle")
        lbl_sub = QLabel(subtitle)
        lbl_sub.setObjectName("welcomeSub")
        lbl_sub.setWordWrap(True)
        col.addWidget(lbl_title)
        col.addWidget(lbl_sub)
        header_row.addLayout(col)
        header_row.addStretch()

        btn_export = QPushButton("📥  Exportar CSV")
        btn_export.setObjectName("primaryBtn")
        btn_export.setFixedHeight(42)
        btn_export.setCursor(Qt.PointingHandCursor)
        btn_export.clicked.connect(self._export_csv)
        header_row.addWidget(btn_export)
        layout.addLayout(header_row)

        # ── Stat cards ──
        stats_row = QHBoxLayout(); stats_row.setSpacing(15)
        self._card_total   = self._make_stat_card("📋", "0", "Eventos Hoy",      "#3B82F6", card_id="total_events")
        self._card_logins  = self._make_stat_card("🔑", "0", "Inicios Hoy",      "#10B981", card_id="logins_today")
        self._card_users   = self._make_stat_card("👤", "0", "Usuarios Activos",  "#8B5CF6", card_id="users_active")
        stats_row.addWidget(self._card_total)
        stats_row.addWidget(self._card_logins)
        stats_row.addWidget(self._card_users)
        layout.addLayout(stats_row)

        # ── Filtros ──
        filter_card = QFrame(); filter_card.setObjectName("glowCard")
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(16, 12, 16, 12)
        filter_layout.setSpacing(12)

        filter_label = QLabel("Filtrar:")
        filter_label.setObjectName("cardTitle")
        filter_layout.addWidget(filter_label)

        # Filtro por usuario (solo admin)
        if self._is_admin:
            self.cmb_user = QComboBox()
            self.cmb_user.setObjectName("dlgCombo")
            self.cmb_user.setFixedHeight(34)
            self.cmb_user.setMinimumWidth(160)
            self.cmb_user.addItem("Todos los usuarios", "")
            self.cmb_user.currentIndexChanged.connect(self.refresh)
            filter_layout.addWidget(QLabel("Usuario:"))
            filter_layout.addWidget(self.cmb_user)

        # Filtro por acción
        self.cmb_action = QComboBox()
        self.cmb_action.setObjectName("dlgCombo")
        self.cmb_action.setFixedHeight(34)
        self.cmb_action.setMinimumWidth(200)
        self.cmb_action.addItem("Todas las acciones", "")
        for action_name in ACTION_COLORS.keys():
            self.cmb_action.addItem(action_name, action_name)
        self.cmb_action.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(QLabel("Acción:"))
        filter_layout.addWidget(self.cmb_action)

        filter_layout.addStretch()

        btn_refresh = QPushButton("🔄  Actualizar")
        btn_refresh.setObjectName("secondaryBtn")
        btn_refresh.setFixedHeight(34)
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.clicked.connect(self.refresh)
        filter_layout.addWidget(btn_refresh)

        layout.addWidget(filter_card)

        # ── Tabla de logs ──
        table_card = QFrame(); table_card.setObjectName("glowCard")
        shadow = QGraphicsDropShadowEffect(table_card)
        shadow.setBlurRadius(25); shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 60))
        table_card.setGraphicsEffect(shadow)

        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(18, 14, 18, 14)

        self._lbl_count = QLabel("0 registros")
        self._lbl_count.setObjectName("statDesc")
        table_layout.addWidget(self._lbl_count)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Fecha / Hora", "Usuario", "Rol", "Acción", "Descripción"
        ])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.Stretch)

        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setMinimumHeight(380)
        table_layout.addWidget(self.table)

        layout.addWidget(table_card)
        layout.addStretch()

        scroll.setWidget(page)
        outer.addWidget(scroll)

    def _make_stat_card(self, icon, value, desc, color, card_id=""):
        card = QFrame(); card.setObjectName("statCard")
        if card_id: card.setProperty("card_id", card_id)
        
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(20); shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 50))
        card.setGraphicsEffect(shadow)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 14, 18, 14); lay.setSpacing(4)

        top = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setObjectName("statIcon")
        if card_id: icon_lbl.setProperty("card_id", card_id)
        
        if not card_id:
            icon_lbl.setStyleSheet(f"font-size: 20px; color: {color}; background: transparent;")
        else:
            icon_lbl.setStyleSheet("font-size: 20px; background: transparent;")
        
        top.addWidget(icon_lbl); top.addStretch()
        
        val_lbl = QLabel(value)
        val_lbl.setObjectName("statValue")
        if card_id: val_lbl.setProperty("card_id", card_id)
        
        if not card_id:
            val_lbl.setStyleSheet(f"font-size: 24px; font-weight: 900; color: {color}; background: transparent;")
        else:
            val_lbl.setStyleSheet("font-size: 24px; font-weight: 900; background: transparent;")
            
        top.addWidget(val_lbl)
        lay.addLayout(top)

        desc_lbl = QLabel(desc); desc_lbl.setObjectName("statDesc")
        lay.addWidget(desc_lbl)
        card._val = val_lbl
        return card

    # ── Datos ────────────────────────────────────────────────

    def refresh(self):
        """Recarga todos los datos con los filtros actuales."""
        # Actualizar opciones de filtro de usuario (admin)
        if self._is_admin:
            current_user = self.cmb_user.currentData()
            self.cmb_user.blockSignals(True)
            self.cmb_user.clear()
            self.cmb_user.addItem("Todos los usuarios", "")
            for uname in get_distinct_usernames():
                self.cmb_user.addItem(uname, uname)
            idx = self.cmb_user.findData(current_user)
            self.cmb_user.setCurrentIndex(max(idx, 0))
            self.cmb_user.blockSignals(False)
            filter_user = self.cmb_user.currentData() or ""
        else:
            filter_user = ""

        filter_action = self.cmb_action.currentData() or ""

        logs = get_logs_filtered(
            self._role, self._username,
            filter_user=filter_user, filter_action=filter_action
        )

        # Stat cards
        stats = get_stats_today()
        self._card_total._val.setText(str(stats["total_today"]))
        self._card_logins._val.setText(str(stats["logins_today"]))
        self._card_users._val.setText(str(stats["users_active_today"]))

        # Tabla
        self.table.setRowCount(0)
        self._lbl_count.setText(f"{len(logs)} registro{'s' if len(logs) != 1 else ''}")

        for row_idx, log in enumerate(logs):
            self.table.insertRow(row_idx)
            self.table.setRowHeight(row_idx, 44)

            # ID
            id_item = QTableWidgetItem(str(log["id"]))
            id_item.setTextAlignment(Qt.AlignCenter)
            # Removemos color hardcoded para que use el del tema
            self.table.setItem(row_idx, 0, id_item)

            # Timestamp
            ts = str(log.get("timestamp", ""))[:19]
            ts_item = QTableWidgetItem(ts)
            ts_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 1, ts_item)

            # Username
            uname_item = QTableWidgetItem(log.get("username", ""))
            uname_item.setTextAlignment(Qt.AlignCenter)
            # Removemos setForeground para que tome el color del tema
            self.table.setItem(row_idx, 2, uname_item)

            # Rol con ícono
            role_key = log.get("role", "")
            role_icon = ROLE_ICONS.get(role_key, "")
            role_name = ROLES.get(role_key, role_key)
            role_item = QTableWidgetItem(f"{role_icon}  {role_name}")
            role_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 3, role_item)

            # Acción con color
            action = log.get("action", "")
            action_item = QTableWidgetItem(f"  {action}")
            action_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            color = ACTION_COLORS.get(action, "#F8FAFC")
            action_item.setForeground(QColor(color))
            self.table.setItem(row_idx, 4, action_item)

            # Descripción
            desc_item = QTableWidgetItem(log.get("description", ""))
            self.table.setItem(row_idx, 5, desc_item)

    # ── Exportar ─────────────────────────────────────────────

    def _export_csv(self):
        default_name = f"logs_{self._username}_{datetime.date.today()}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Logs a CSV", default_name,
            "CSV Files (*.csv);;All Files (*)"
        )
        if not path:
            return
        try:
            filter_user = (self.cmb_user.currentData() or "") if self._is_admin else ""
            filter_action = self.cmb_action.currentData() or ""
            logs = get_logs_filtered(
                self._role, self._username,
                filter_user=filter_user, filter_action=filter_action
            )
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(
                    f, fieldnames=["id", "timestamp", "username", "role", "action", "description"]
                )
                writer.writeheader()
                writer.writerows(logs)
            QMessageBox.information(self, "Exportado",
                f"Se exportaron {len(logs)} registros a:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar:\n{e}")
