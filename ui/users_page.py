# ui/users_page.py
# ============================================================
#  LogiCheck — Página de Gestión de Usuarios (solo Admin)
# ============================================================

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QLineEdit, QComboBox, QFormLayout, QMessageBox,
    QGraphicsDropShadowEffect, QAbstractItemView, QScrollArea,
    QSizePolicy, QSpacerItem, QCheckBox, QDateTimeEdit
)
from PySide6.QtCore import Qt, Signal, QDateTime
from PySide6.QtGui import QColor, QFont
import json
from datetime import datetime, timedelta
import sys, os

_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _base not in sys.path:
    sys.path.insert(0, _base)

from core.auth import (
    get_all_users, create_user, update_user,
    change_password, deactivate_user, reactivate_user,
    update_user_permissions, clone_permissions
)
from core.permissions import (
    ROLES, ROLE_ICONS, SYSTEM_FUNCTIONS, 
    get_role_permissions, _base_page_access, _base_action_access
)
from core import logger as app_logger


# ══════════════════════════════════════════════════════════════
#  Diálogo: Crear / Editar Usuario
# ══════════════════════════════════════════════════════════════
class UserDialog(QDialog):
    """Diálogo para crear un usuario nuevo o editar uno existente."""

    def __init__(self, parent=None, user_data: dict = None, current_admin_id: int = None):
        super().__init__(parent)
        self._edit_mode = user_data is not None
        self._user_data = user_data or {}
        self._current_admin_id = current_admin_id
        self._overrides = {}
        
        if self._edit_mode and self._user_data.get("permissions_override"):
            try:
                self._overrides = json.loads(self._user_data["permissions_override"])
            except: pass

        self.setWindowTitle("Editar Usuario" if self._edit_mode else "Nuevo Usuario")
        self.setMinimumWidth(500)
        self.setModal(True)
        self._build_ui()
        self._apply_styles()

        if self._edit_mode:
            self._fill_fields()

    # ── UI ───────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(18)

        # Header
        icon = "✏️" if self._edit_mode else "👤"
        title_lbl = QLabel(f"{icon}  {'Editar Usuario' if self._edit_mode else 'Nuevo Usuario'}")
        title_lbl.setObjectName("dlgTitle")
        layout.addWidget(title_lbl)

        # Form
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        # Nombre completo
        self.inp_fullname = QLineEdit()
        self.inp_fullname.setObjectName("loginInput")
        self.inp_fullname.setFixedHeight(38)
        self.inp_fullname.setPlaceholderText("Ej: Juan García")
        form.addRow("Nombre completo:", self.inp_fullname)

        # Username (solo en creación)
        if not self._edit_mode:
            self.inp_username = QLineEdit()
            self.inp_username.setObjectName("loginInput")
            self.inp_username.setFixedHeight(38)
            self.inp_username.setPlaceholderText("Ej: juan.garcia")
            form.addRow("Usuario:", self.inp_username)

            self.inp_password = QLineEdit()
            self.inp_password.setObjectName("loginInput")
            self.inp_password.setFixedHeight(38)
            self.inp_password.setPlaceholderText("Contraseña inicial")
            self.inp_password.setEchoMode(QLineEdit.Password)
            form.addRow("Contraseña:", self.inp_password)

        # Rol
        role_row = QHBoxLayout()
        self.cmb_role = QComboBox()
        self.cmb_role.setObjectName("dlgCombo")
        self.cmb_role.setFixedHeight(38)
        self.cmb_role.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        for role_key, role_name in ROLES.items():
            icon = ROLE_ICONS.get(role_key, "")
            self.cmb_role.addItem(f"{icon}  {role_name}", role_key)
            
        self.btn_inspect_role = QPushButton("🔍")
        self.btn_inspect_role.setFixedSize(38, 38)
        self.btn_inspect_role.setCursor(Qt.PointingHandCursor)
        self.btn_inspect_role.setToolTip("Ver permisos de este rol")
        self.btn_inspect_role.setStyleSheet("""
            QPushButton { 
                background: #313244; border-radius: 8px; border: 1px solid #45475a; 
                font-size: 16px; color: #cdd6f4;
            }
            QPushButton:hover { background: #45475a; border-color: #89b4fa; }
        """)
        self.btn_inspect_role.clicked.connect(self._show_role_info)
        
        role_row.addWidget(self.cmb_role)
        role_row.addWidget(self.btn_inspect_role)
        form.addRow("Rol base:", role_row)

        layout.addLayout(form)
        
        # --- Matriz de Privilegios Granulares ---
        layout.addWidget(QLabel("🛡️  Matriz de Privilegios (Herencia y Overrides):"))
        layout.addWidget(QLabel("<i>Configura permisos específicos sin cambiar el rol base del usuario.</i>"))
        
        perm_scroll = QScrollArea()
        perm_scroll.setWidgetResizable(True)
        perm_scroll.setMinimumHeight(250)
        perm_scroll.setObjectName("permScroll")
        
        perm_container = QWidget()
        perm_container.setObjectName("permContainer")
        self.perm_vbox = QVBoxLayout(perm_container)
        self.perm_vbox.setContentsMargins(10, 10, 10, 10)
        self.perm_vbox.setSpacing(15)
        
        self.perm_controls = {} # Key: combo_widget

        for category, functions in SYSTEM_FUNCTIONS.items():
            cat_label = QLabel(f"<b>{category.upper()}</b>")
            cat_label.setStyleSheet("color: #89b4fa; font-size: 11px; margin-top: 5px;")
            self.perm_vbox.addWidget(cat_label)
            
            for key, label in functions.items():
                row = QHBoxLayout()
                lbl_func = QLabel(label)
                lbl_func.setWordWrap(True)
                lbl_func.setObjectName("permLabel")
                
                # Estado heredado (indicador visual)
                self.lbl_inherited = QLabel("(Heredado: ?)")
                self.lbl_inherited.setObjectName("inheritedLabel")
                self.lbl_inherited.setProperty("key", key)
                
                # Selector tri-estatal
                combo = QComboBox()
                combo.setFixedWidth(110)
                combo.addItem("🔗 Heredar", None)   # Nada en override
                combo.addItem("✅ Permitir", True)  # True en override
                combo.addItem("❌ Prohibir", False) # False en override
                
                # Cargar valor actual si existe
                if key in self._overrides:
                    current_val = self._overrides[key]
                    idx = combo.findData(current_val)
                    if idx >= 0: combo.setCurrentIndex(idx)
                
                self.perm_controls[key] = (combo, self.lbl_inherited)
                
                row.addWidget(lbl_func, 1)
                row.addWidget(self.lbl_inherited)
                row.addWidget(combo)
                self.perm_vbox.addLayout(row)

        perm_scroll.setWidget(perm_container)
        layout.addWidget(perm_scroll)
        
        # Actualizar indicadores de herencia iniciales
        self.cmb_role.currentIndexChanged.connect(self._update_inheritance_labels)
        self._update_inheritance_labels()
        
        # --- NUEVO: Expiración (Delegación Temporal) ---
        exp_lay = QHBoxLayout()
        self.chk_expire = QCheckBox("Permisos Temporales (Expira el:)")
        self.chk_expire.setStyleSheet("color: #a6adc8;")
        self.date_expire = QDateTimeEdit(QDateTime.currentDateTime().addDays(7))
        self.date_expire.setCalendarPopup(True)
        self.date_expire.setEnabled(False)
        self.chk_expire.toggled.connect(self.date_expire.setEnabled)
        
        if self._user_data.get("permissions_expire_at"):
            self.chk_expire.setChecked(True)
            self.date_expire.setDateTime(QDateTime.fromString(self._user_data["permissions_expire_at"], Qt.ISODate))
            
        exp_lay.addWidget(self.chk_expire)
        exp_lay.addWidget(self.date_expire)
        layout.addLayout(exp_lay)
        
        layout.addStretch()

        # Botones
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("dlgCancelBtn")
        btn_cancel.setFixedHeight(40)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("Guardar" if self._edit_mode else "Crear Usuario")
        btn_ok.setObjectName("dlgOkBtn")
        btn_ok.setFixedHeight(40)
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.clicked.connect(self._validate_and_accept)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def _update_inheritance_labels(self):
        """Actualiza el texto que indica qué permisos hereda el rol seleccionado."""
        role_key = self.cmb_role.currentData()
        if not role_key: return
        
        for category, functions in SYSTEM_FUNCTIONS.items():
            for key, label in functions.items():
                if key not in self.perm_controls: continue
                combo, lbl_inherit = self.perm_controls[key]
                
                # Determinar acceso base
                if key.startswith("page.view."):
                    pg_name = key.replace("page.view.", "")
                    has_base = _base_page_access(role_key, pg_name)
                else:
                    has_base = _base_action_access(role_key, key)
                
                status_txt = "SÍ" if has_base else "NO"
                lbl_inherit.setText(f"<i>(Rol: {status_txt})</i>")
                
                # Usar propiedades dinámicas para que el CSS maneje el color
                lbl_inherit.setProperty("has_base", has_base)
                lbl_inherit.style().unpolish(lbl_inherit)
                lbl_inherit.style().polish(lbl_inherit)

    def _show_role_info(self):
        """Muestra los permisos detallados del rol seleccionado."""
        role_key = self.cmb_role.currentData()
        role_name = self.cmb_role.currentText().strip()
        perms = get_role_permissions(role_key)
        
        msg = f"<b>{role_name}</b> tiene los siguientes permisos:<br><br>"
        msg += "<b>🏢 Acceso a páginas:</b><br>• " + "<br>• ".join(perms["páginas"]) if perms["páginas"] else "Ninguna"
        msg += "<br><br><b>⚙️ Acciones permitidas:</b><br>• " + "<br>• ".join(perms["acciones"]) if perms["acciones"] else "Ninguna"
        
        # El override del usuario se suma a esto
        msg += "<br><br><i>Nota: Si activas Permisos Especiales abajo, se sumarán a estos permisos base.</i>"
        
        QMessageBox.information(self, "Detalles de Permisos", msg)

    def _fill_fields(self):
        self.inp_fullname.setText(self._user_data.get("full_name", ""))
        role_key = self._user_data.get("role", "op_factura")
        idx = self.cmb_role.findData(role_key)
        if idx >= 0:
            self.cmb_role.setCurrentIndex(idx)

    # ── Validación ───────────────────────────────────────────

    def _validate_and_accept(self):
        full_name = self.inp_fullname.text().strip()
        if not full_name:
            QMessageBox.warning(self, "Campo requerido", "El nombre completo es obligatorio.")
            return

        if not self._edit_mode:
            username = self.inp_username.text().strip()
            password = self.inp_password.text()
            if not username:
                QMessageBox.warning(self, "Campo requerido", "El nombre de usuario es obligatorio.")
                return
            if len(password) < 6:
                QMessageBox.warning(self, "Contraseña débil", "La contraseña debe tener al menos 6 caracteres.")
                return
            self.result_username = username.lower()
            self.result_password = password

        new_role = self.cmb_role.currentData()
        
        # Protección de Auto-Descenso: Un admin no puede quitarse su propio rol de admin
        if self._edit_mode and self._user_data["id"] == self._current_admin_id:
            if self._user_data["role"] == "admin" and new_role != "admin":
                QMessageBox.critical(self, "Protección", "No puedes quitarte el rol de Administrador a ti mismo para evitar bloqueos.")
                return

        # Recoger Overrides (Granularidad Absoluta)
        overrides = {}
        for key, (combo, _) in self.perm_controls.items():
            val = combo.currentData()
            if val is not None:
                overrides[key] = val
        
        self.result_overrides = json.dumps(overrides) if overrides else None
        self.result_expire = self.date_expire.dateTime().toString(Qt.ISODate) if self.chk_expire.isChecked() else None
        
        self.result_fullname = full_name
        self.result_role = new_role
        self.accept()

    # ── Estilos ───────────────────────────────────────────────

    def _apply_styles(self):
        # El tema base se hereda de style.qss, aquí solo detalles específicos del diálogo.
        self.setObjectName("UserDialog")
        self.setStyleSheet("""
            #dlgTitle { font-size: 17px; font-weight: 800; color: #cdd6f4; }
            #dlgOkBtn {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #89b4fa, stop:1 #74c7ec);
                color: #11111b; border: none; border-radius: 8px; font-weight: 700;
            }
            #dlgOkBtn:hover { background: #b4befe; }
        """)


# ══════════════════════════════════════════════════════════════
#  Diálogo: Cambiar Contraseña
# ══════════════════════════════════════════════════════════════
class ChangePasswordDialog(QDialog):
    """Diálogo para cambiar la contraseña de un usuario."""

    def __init__(self, parent=None, username: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Cambiar Contraseña")
        self.setFixedSize(380, 280)
        self.setModal(True)
        self._username = username
        self._build_ui()
        self._apply_styles()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(16)

        title = QLabel(f"🔑  Cambiar contraseña de: {self._username}")
        title.setObjectName("dlgTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)

        self.inp_new = QLineEdit()
        self.inp_new.setObjectName("loginInput")
        self.inp_new.setFixedHeight(38)
        self.inp_new.setEchoMode(QLineEdit.Password)
        self.inp_new.setPlaceholderText("Nueva contraseña")
        form.addRow("Nueva:", self.inp_new)

        self.inp_confirm = QLineEdit()
        self.inp_confirm.setObjectName("loginInput")
        self.inp_confirm.setFixedHeight(38)
        self.inp_confirm.setEchoMode(QLineEdit.Password)
        self.inp_confirm.setPlaceholderText("Confirmar contraseña")
        form.addRow("Confirmar:", self.inp_confirm)

        layout.addLayout(form)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setObjectName("dlgCancelBtn")
        btn_cancel.setFixedHeight(40)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("Cambiar Contraseña")
        btn_ok.setObjectName("dlgOkBtn")
        btn_ok.setFixedHeight(40)
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.clicked.connect(self._validate)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def _validate(self):
        new_pass = self.inp_new.text()
        confirm = self.inp_confirm.text()
        if len(new_pass) < 6:
            QMessageBox.warning(self, "Contraseña débil", "Mínimo 6 caracteres.")
            return
        if new_pass != confirm:
            QMessageBox.warning(self, "No coinciden", "Las contraseñas no coinciden.")
            return
        self.result_password = new_pass
        self.accept()

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog { background-color: #1e1e2e; border: 1px solid #313244; border-radius: 14px; }
            #dlgTitle { font-size: 15px; font-weight: 800; color: #cdd6f4; background: transparent; }
            QLabel { color: #a6adc8; font-size: 13px; background: transparent; }
            #loginInput { background-color: #11111b; border: 1.5px solid #313244; border-radius: 8px; padding: 0 12px; font-size: 13px; color: #cdd6f4; }
            #loginInput:focus { border-color: #89b4fa; }
            #dlgOkBtn { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #89b4fa, stop:1 #74c7ec); color: #11111b; border: none; border-radius: 8px; font-size: 13px; font-weight: 700; }
            #dlgOkBtn:hover { background: #b4befe; }
            #dlgCancelBtn { background: transparent; color: #a6adc8; border: 1.5px solid #45475a; border-radius: 8px; font-size: 13px; font-weight: 600; }
            #dlgCancelBtn:hover { background: rgba(255,255,255,0.05); color: #cdd6f4; }
        """)


# ══════════════════════════════════════════════════════════════
#  Widget principal: Gestión de Usuarios
# ══════════════════════════════════════════════════════════════
class UsersPage(QWidget):
    """Página de gestión de usuarios. Solo visible para el rol 'admin'."""

    def __init__(self, admin_user_data: dict = None, parent=None):
        super().__init__(parent)
        self._admin = admin_user_data or {}
        self._build_ui()
        self.refresh_table()

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

        # ── Header Banner ──
        banner = QFrame()
        banner.setObjectName("welcomeBanner")
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(24, 20, 24, 20)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        lbl_title = QLabel("👥  Gestión de Usuarios")
        lbl_title.setObjectName("welcomeTitle")
        lbl_sub = QLabel("Administra los accesos al sistema. Solo el Administrador puede ver esta sección.")
        lbl_sub.setObjectName("welcomeSub")
        lbl_sub.setWordWrap(True)
        title_col.addWidget(lbl_title)
        title_col.addWidget(lbl_sub)

        banner_layout.addLayout(title_col)
        banner_layout.addStretch()

        self.btn_new_user = QPushButton("➕  Nuevo Usuario")
        self.btn_new_user.setObjectName("primaryBtn")
        self.btn_new_user.setFixedHeight(42)
        self.btn_new_user.setCursor(Qt.PointingHandCursor)
        self.btn_new_user.clicked.connect(self._open_create_dialog)
        banner_layout.addWidget(self.btn_new_user)

        layout.addWidget(banner)

        # ── Stat cards ──
        stats_row = QHBoxLayout()
        stats_row.setSpacing(15)

        self._card_total   = self._make_stat_card("👤", "0", "Usuarios Totales",  "#89b4fa", card_id="total")
        self._card_active  = self._make_stat_card("✅", "0", "Usuarios Activos",  "#a6e3a1", card_id="active")
        self._card_inactive= self._make_stat_card("🚫", "0", "Usuarios Inactivos","#f38ba8", card_id="inactive")
        self._card_roles   = self._make_stat_card("🎭", "5", "Roles Disponibles", "#cba6f7", card_id="roles")

        stats_row.addWidget(self._card_total)
        stats_row.addWidget(self._card_active)
        stats_row.addWidget(self._card_inactive)
        stats_row.addWidget(self._card_roles)
        layout.addLayout(stats_row)

        # ── Tabla de usuarios ──
        table_card = QFrame()
        table_card.setObjectName("glowCard")
        shadow = QGraphicsDropShadowEffect(table_card)
        shadow.setBlurRadius(25); shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 60))
        table_card.setGraphicsEffect(shadow)

        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(20, 18, 20, 18)

        tbl_header_row = QHBoxLayout()
        tbl_title = QLabel("Lista de Usuarios Registrados")
        tbl_title.setObjectName("cardTitle")
        tbl_header_row.addWidget(tbl_title)
        tbl_header_row.addStretch()

        self.btn_refresh = QPushButton("🔄  Actualizar")
        self.btn_refresh.setObjectName("secondaryBtn")
        self.btn_refresh.setFixedHeight(34)
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.refresh_table)
        tbl_header_row.addWidget(self.btn_refresh)
        table_layout.addLayout(tbl_header_row)

        # Tabla
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Usuario", "Nombre Completo", "Rol", "Estado", "Creado", "Acciones"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        # self.table.setColumnWidth(6, 450)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(320)
        self.table.setShowGrid(False)
        table_layout.addWidget(self.table)

        layout.addWidget(table_card)
        layout.addStretch()

        scroll.setWidget(page)
        outer.addWidget(scroll)

    def _make_stat_card(self, icon, value, desc, color, card_id=""):
        """Crea una mini tarjeta de estadística."""
        card = QFrame()
        card.setObjectName("statCard")
        if card_id:
            card.setProperty("card_id", card_id)

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(20); shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 50))
        card.setGraphicsEffect(shadow)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(4)

        top = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setObjectName("statIcon")
        if card_id: icon_lbl.setProperty("card_id", card_id)
        
        if not card_id:
            icon_lbl.setStyleSheet(f"font-size: 20px; color: {color}; background: transparent;")
        else:
            icon_lbl.setStyleSheet("font-size: 20px; background: transparent;")
        top.addWidget(icon_lbl)
        top.addStretch()

        val_lbl = QLabel(value)
        val_lbl.setObjectName("statValue")
        if card_id: val_lbl.setProperty("card_id", card_id)
        
        if not card_id:
            val_lbl.setStyleSheet(f"font-size: 24px; font-weight: 900; color: {color}; background: transparent;")
        else:
            val_lbl.setStyleSheet("font-size: 24px; font-weight: 900; background: transparent;")
            
        top.addWidget(val_lbl)
        lay.addLayout(top)

        desc_lbl = QLabel(desc)
        desc_lbl.setObjectName("statDesc")
        lay.addWidget(desc_lbl)

        # Guardar referencia al value label en el card para actualizarlo
        card._val_label = val_lbl
        return card

    # ── Datos ────────────────────────────────────────────────

    def refresh_table(self):
        """Recarga todos los usuarios desde la BD y actualiza la tabla."""
        users = get_all_users()
        self.table.setRowCount(0)

        active_count   = sum(1 for u in users if u["active"])
        inactive_count = sum(1 for u in users if not u["active"])

        self._card_total._val_label.setText(str(len(users)))
        self._card_active._val_label.setText(str(active_count))
        self._card_inactive._val_label.setText(str(inactive_count))

        for row_idx, user in enumerate(users):
            self.table.insertRow(row_idx)
            self.table.setRowHeight(row_idx, 52)

            # ID
            item_id = QTableWidgetItem(str(user["id"]))
            item_id.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 0, item_id)

            # Username
            uname = QTableWidgetItem(user["username"])
            uname.setTextAlignment(Qt.AlignCenter)
            # Removemos setForeground para permitir que el estilo general maneje el color correctamented
            self.table.setItem(row_idx, 1, uname)

            # Nombre completo
            self.table.setItem(row_idx, 2, QTableWidgetItem(user["full_name"]))

            # Rol con ícono
            role_key = user["role"]
            role_icon = ROLE_ICONS.get(role_key, "")
            role_name = ROLES.get(role_key, role_key)
            role_item = QTableWidgetItem(f"{role_icon}  {role_name}")
            role_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 3, role_item)

            # Estado
            is_active = bool(user["active"])
            estado_item = QTableWidgetItem("✅ Activo" if is_active else "🚫 Inactivo")
            estado_item.setTextAlignment(Qt.AlignCenter)
            estado_item.setForeground(
                QColor("#40a02b") if is_active else QColor("#d20f39")
            )
            self.table.setItem(row_idx, 4, estado_item)

            # Fecha creación (solo fecha, sin hora)
            created = str(user.get("created_at", "—"))[:10]
            created_item = QTableWidgetItem(created)
            created_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 5, created_item)

            # Botones de acción en celda
            action_widget = QWidget()
            action_widget.setStyleSheet("background: transparent;")
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(4, 2, 4, 2)
            action_layout.setSpacing(4)

            btn_edit = QPushButton("✏️ Editar")
            btn_edit.setFixedHeight(30)
            btn_edit.setCursor(Qt.PointingHandCursor)
            btn_edit.setObjectName("btnTableEdit")
            btn_edit.clicked.connect(lambda _, u=user: self._open_edit_dialog(u))

            btn_pass = QPushButton("🔑 Clave")
            btn_pass.setFixedHeight(30)
            btn_pass.setCursor(Qt.PointingHandCursor)
            btn_pass.setObjectName("btnTablePass")
            btn_pass.clicked.connect(lambda _, u=user: self._open_password_dialog(u))

            if is_active:
                btn_toggle = QPushButton("🚫 Desactivar")
                btn_toggle.setFixedHeight(30)
                btn_toggle.setObjectName("btnTableToggleOff")
                btn_toggle.clicked.connect(lambda _, u=user: self._toggle_user(u, deactivate=True))
            else:
                btn_toggle = QPushButton("✅ Activar")
                btn_toggle.setFixedHeight(30)
                btn_toggle.setObjectName("btnTableToggleOn")
                btn_toggle.clicked.connect(lambda _, u=user: self._toggle_user(u, deactivate=False))

            btn_toggle.setFixedHeight(32)
            btn_toggle.setCursor(Qt.PointingHandCursor)

            btn_clone = QPushButton("🛡️  Clonar")
            btn_clone.setFixedHeight(30)
            btn_clone.setCursor(Qt.PointingHandCursor)
            btn_clone.setObjectName("btnTableClone")
            btn_clone.setToolTip("Clonar permisos a otro usuario")
            btn_clone.clicked.connect(lambda _, u=user: self._clone_user_permissions(u))

            action_layout.addWidget(btn_edit)
            action_layout.addWidget(btn_pass)
            action_layout.addWidget(btn_clone)
            action_layout.addWidget(btn_toggle)
            action_layout.addStretch()

            self.table.setCellWidget(row_idx, 6, action_widget)

    # ── Acciones ─────────────────────────────────────────────

    def _open_create_dialog(self):
        dlg = UserDialog(self)
        if dlg.exec() == QDialog.Accepted:
            ok = create_user(
                dlg.result_username,
                dlg.result_password,
                dlg.result_role,
                dlg.result_fullname,
            )
            if ok:
                QMessageBox.information(self, "Éxito", f"Usuario '{dlg.result_username}' creado correctamente.")
                app_logger.log_action(self._admin, app_logger.USUARIO_CREADO,
                                      f"Nuevo usuario: {dlg.result_username} | Rol: {dlg.result_role}")
                self.refresh_table()
            else:
                QMessageBox.critical(self, "Error", f"El nombre de usuario '{dlg.result_username}' ya existe.")

    def _open_edit_dialog(self, user: dict):
        dlg = UserDialog(self, user_data=user, current_admin_id=self._admin.get("id"))
        if dlg.exec() == QDialog.Accepted:
            # 1. Update basic info
            update_user(user["id"], dlg.result_fullname, dlg.result_role)
            
            # 2. Update Overrides (Auditoría incluida)
            update_user_permissions(user["id"], dlg.result_overrides, dlg.result_expire, self._admin.get("id"))
            
            app_logger.log_action(self._admin, app_logger.USUARIO_EDITADO,
                                  f"Usuario: {user['username']} | Permisos modif. por: {self._admin['username']}")
            
            QMessageBox.information(self, "Éxito", "Usuario y permisos actualizados correctamente.")
            self.refresh_table()

    def _clone_user_permissions(self, user: dict):
        """Implementa la opción 5: Clonación de Privilegios."""
        users = [u for u in get_all_users() if u["id"] != user["id"] and u["active"]]
        if not users:
            QMessageBox.warning(self, "Clonación", "No hay otros usuarios activos para recibir estos permisos.")
            return
            
        # Diálogo simple para elegir destino
        dest_dlg = QDialog(self)
        dest_dlg.setObjectName("cloneDialog")
        dest_dlg.setWindowTitle(f"Clonar permisos de {user['username']} a...")
        dest_dlg.setFixedWidth(400)
        dest_dlg.setStyleSheet("background-color: #1e1e2e;") # Forzar fondo para evitar transparencia
        lay = QVBoxLayout(dest_dlg)
        
        combo = QComboBox()
        for u in users:
            combo.addItem(f"{u['username']} ({u['full_name']})", u["id"])
        lay.addWidget(QLabel("Selecciona el usuario destino:"))
        lay.addWidget(combo)
        
        btn_ok = QPushButton("Clonar Ahora")
        btn_ok.clicked.connect(dest_dlg.accept)
        lay.addWidget(btn_ok)
        
        if dest_dlg.exec() == QDialog.Accepted:
            to_id = combo.currentData()
            to_name = combo.currentText()
            if clone_permissions(user["id"], to_id, self._admin.get("id")):
                app_logger.log_action(self._admin, "PERMISOS_CLONADOS", 
                                      f"Clonó permisos de {user['username']} a {to_name}")
                QMessageBox.information(self, "Éxito", f"Se han clonado los privilegios a {to_name}.")
                self.refresh_table()

    def _open_password_dialog(self, user: dict):
        dlg = ChangePasswordDialog(self, username=user["username"])
        if dlg.exec() == QDialog.Accepted:
            change_password(user["id"], dlg.result_password)
            app_logger.log_action(self._admin, app_logger.CONTRASENA_CAMBIADA,
                                  f"Contraseña cambiada de: {user['username']}")
            QMessageBox.information(self, "Éxito", f"Contraseña de '{user['username']}' actualizada.")

    def _toggle_user(self, user: dict, deactivate: bool):
        action = "desactivar" if deactivate else "activar"
        reply = QMessageBox.question(
            self,
            f"Confirmar {action}",
            f"¿Deseas {action} al usuario '{user['username']}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            if deactivate:
                deactivate_user(user["id"])
                app_logger.log_action(self._admin, app_logger.USUARIO_DESACTIVADO,
                                      f"Usuario desactivado: {user['username']}")
            else:
                reactivate_user(user["id"])
                app_logger.log_action(self._admin, app_logger.USUARIO_ACTIVADO,
                                      f"Usuario activado: {user['username']}")
            self.refresh_table()
