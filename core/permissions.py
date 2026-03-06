# core/permissions.py
# ============================================================
#  LogiCheck — Sistema de Permisos por Rol
# ============================================================
#  Roles disponibles:
#    admin         → Acceso total
#    op_factura    → Operador de Factura (carga PDFs)
#    op_video      → Operador de Video (ejecuta YOLO + vehículos)
#    gerente       → Supervisor operativo (ve + gestiona vehículos)
#    dueno         → Dueño (solo dashboard y reportes)
# ============================================================

ROLES = {
    "admin":      "Administrador",
    "op_factura": "Operador de Factura",
    "op_video":   "Operador de Video",
    "gerente":    "Gerente",
    "dueno":      "Dueño",
}

ROLE_ICONS = {
    "admin":      "👑",
    "op_factura": "📄",
    "op_video":   "📹",
    "gerente":    "👔",
    "dueno":      "👁️",
}

# ── Páginas del sidebar ──────────────────────────────────────
# True  → puede ver la página
# False → botón oculto / deshabilitado
PAGE_ACCESS = {
    #                      admin   op_fac  op_vid  gerente  dueno
    "Dashboard":         { "admin": True,  "op_factura": True,  "op_video": True,  "gerente": True,  "dueno": True  },
    "Factura PDF":       { "admin": True,  "op_factura": True,  "op_video": True,  "gerente": True,  "dueno": False },
    "Análisis de Video": { "admin": True,  "op_factura": True,  "op_video": True,  "gerente": True,  "dueno": False },
    "Asignación Vehicular":{"admin":True,  "op_factura": False, "op_video": True,  "gerente": True,  "dueno": False },
    "Reportes":          { "admin": True,  "op_factura": True,  "op_video": True,  "gerente": True,  "dueno": True  },
    "Actividad":         { "admin": True,  "op_factura": True,  "op_video": True,  "gerente": True,  "dueno": True  },
    "Gestión de Usuarios":{"admin": True,  "op_factura": False, "op_video": False, "gerente": False, "dueno": False },
}

# ── Acciones específicas dentro de cada página ───────────────
# Controla si un botón/acción concreta está habilitada
ACTION_ACCESS = {
    # Factura PDF
    "factura.cargar":       {"admin": True,  "op_factura": True,  "op_video": False, "gerente": False, "dueno": False},
    # Análisis de Video
    "video.iniciar":        {"admin": True,  "op_factura": False, "op_video": True,  "gerente": False, "dueno": False},
    "video.detener":        {"admin": True,  "op_factura": False, "op_video": True,  "gerente": False, "dueno": False},
    # Asignación Vehicular
    "vehiculo.gestionar":   {"admin": True,  "op_factura": False, "op_video": True,  "gerente": True,  "dueno": False},
    # Reportes
    "reportes.exportar":    {"admin": True,  "op_factura": True,  "op_video": True,  "gerente": True,  "dueno": True },
    # Administración
    "admin.usuarios":       {"admin": True,  "op_factura": False, "op_video": False, "gerente": False, "dueno": False},
    "admin.config":         {"admin": True,  "op_factura": False, "op_video": False, "gerente": False, "dueno": False},
}


def can_access_page(role: str, page: str) -> bool:
    """Retorna True si el rol puede ver la página."""
    return PAGE_ACCESS.get(page, {}).get(role, False)


def can_do_action(role: str, action: str) -> bool:
    """Retorna True si el rol puede ejecutar la acción."""
    return ACTION_ACCESS.get(action, {}).get(role, False)


def get_role_display(role: str) -> str:
    """Retorna el nombre legible del rol con su ícono."""
    icon = ROLE_ICONS.get(role, "")
    name = ROLES.get(role, role)
    return f"{icon}  {name}"
