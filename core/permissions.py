# core/permissions.py
# ============================================================
#  LogiCheck — Sistema de Permisos por Rol
# ============================================================

import json
from datetime import datetime

ROLES = {
    "admin":      "Administrador",
    "op_factura": "Operador de Factura",
    "op_video":   "Operador de Video",
    "gerente":    "Gerente",
    "dueno":      "Dueño",
}

ROLE_ICONS = {
    "admin":      "🛡️",
    "op_factura": "📄",
    "op_video":   "📽️",
    "gerente":    "📊",
    "dueno":      "💼",
}

# ── Catálogo Maestro de Funciones ────────────────────────────
# Mapa de keys técnicas → etiquetas amigables
SYSTEM_FUNCTIONS = {
    "Páginas (Sidebar)": {
        "page.view.Dashboard":          "🏠 Ver Dashboard Operativo",
        "page.view.Factura PDF":        "📄 Acciones de Facturación",
        "page.view.Análisis de Video": "📹 Acciones de Análisis de Video",
        "page.view.Asignación Vehicular": "🚛 Realizar Cálculo de Vehículos",
        "page.view.Reportes":           "📊 Consultar Histórico / Reportes",
        "page.view.Actividad":          "📜 Ver Bitácora de Actividad",
        "page.view.Gestión de Usuarios": "👥 Administrar Cuentas y Roles",
    },
    "Acciones Específicas": {
        "factura.cargar":       "📤 Cargar y Procesar PDFs de Facturas",
        "video.iniciar":        "▶️ Iniciar Análisis de IA (YOLO)",
        "video.detener":        "⏹️ Detener Procesamiento de Video",
        "vehiculo.gestionar":   "📝 Modificar Datos de Vehículos",
        "reportes.exportar":    "📥 Descargar Reportes Excel/CSV",
        "admin.usuarios":       "🔑 Cambiar Claves / Editar Usuarios",
        "admin.config":         "⚙️ Configurar Parámetros del Sistema",
    }
}

def can_access_page(user: dict | str, page: str) -> bool:
    """Retorna True si el usuario puede ver la página."""
    role = user if isinstance(user, str) else user.get("role")
    action_key = f"page.view.{page}"
    
    # 1. Verificar fecha de expiración
    if isinstance(user, dict) and user.get("expires_at"):
        try:
            exp_date = datetime.fromisoformat(user["expires_at"])
            if datetime.now() > exp_date:
                return _base_page_access(role, page)
        except: pass

    # 2. Check Overrides Granulares (Permitir / Denegar explícitamente)
    if isinstance(user, dict) and user.get("overrides"):
        try:
            overrides = json.loads(user["overrides"])
            if action_key in overrides:
                # El override puede ser True (permitir) o False (prohibir)
                return bool(overrides[action_key])
        except: pass

    return _base_page_access(role, page)

def can_do_action(user: dict | str, action: str) -> bool:
    """Retorna True si el usuario puede ejecutar la acción."""
    role = user if isinstance(user, str) else user.get("role")

    # 1. Verificar expiración
    if isinstance(user, dict) and user.get("expires_at"):
        try:
            exp_date = datetime.fromisoformat(user["expires_at"])
            if datetime.now() > exp_date:
                return _base_action_access(role, action)
        except: pass

    # 2. Check Overrides Granulares
    if isinstance(user, dict) and user.get("overrides"):
        try:
            overrides = json.loads(user["overrides"])
            if action in overrides:
                return bool(overrides[action])
        except: pass

    return _base_action_access(role, action)

def _base_page_access(role: str, page: str) -> bool:
    """Lógica interna de acceso a páginas por rol."""
    data = {
        "Dashboard":         ["admin", "op_factura", "op_video", "gerente", "dueno"],
        "Factura PDF":       ["admin", "op_factura", "op_video", "gerente"],
        "Análisis de Video": ["admin", "op_factura", "op_video", "gerente"],
        "Asignación Vehicular":["admin", "op_video", "gerente"],
        "Reportes":          ["admin", "op_factura", "op_video", "gerente", "dueno"],
        "Actividad":         ["admin", "op_factura", "op_video", "gerente", "dueno"],
        "Gestión de Usuarios":["admin"],
    }
    return role in data.get(page, [])

def _base_action_access(role: str, action: str) -> bool:
    """Lógica interna de acciones permitidas por rol."""
    data = {
        "factura.cargar":     ["admin", "op_factura"],
        "video.iniciar":      ["admin", "op_video"],
        "video.detener":      ["admin", "op_video"],
        "vehiculo.gestionar": ["admin", "op_video", "gerente"],
        "reportes.exportar":  ["admin", "op_factura", "op_video", "gerente", "dueno"],
        "admin.usuarios":     ["admin"],
        "admin.config":       ["admin"],
    }
    return role in data.get(action, [])

def get_role_permissions(role: str) -> dict:
    """Retorna un dict con los accesos (páginas y acciones) de un rol."""
    perms = {"páginas": [], "acciones": []}
    
    # 1. Páginas
    all_pages = ["Dashboard", "Factura PDF", "Análisis de Video", "Asignación Vehicular", "Reportes", "Actividad", "Gestión de Usuarios"]
    for pg in all_pages:
        if _base_page_access(role, pg):
            perms["páginas"].append(pg)
            
    # 2. Acciones
    all_actions = ["factura.cargar", "video.iniciar", "video.detener", "vehiculo.gestionar", "reportes.exportar", "admin.usuarios", "admin.config"]
    for action in all_actions:
        if _base_action_access(role, action):
            # Obtener el label legible desde SYSTEM_FUNCTIONS
            label = action
            for cat, funcs in SYSTEM_FUNCTIONS.items():
                if action in funcs:
                    label = funcs[action]
            perms["acciones"].append(label)
            
    return perms

def get_role_display(role: str) -> str:
    """Retorna el nombre legible del rol con su ícono."""
    icon = ROLE_ICONS.get(role, "")
    name = ROLES.get(role, role)
    return f"{icon}  {name}"
