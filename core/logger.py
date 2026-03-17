# core/logger.py
# ============================================================
#  LogiCheck — Sistema de Logs de Actividad (SQLite)
#  Tabla: activity_logs
#  - Admin: ve todos los registros
#  - Otros roles: solo ven sus propios registros
# ============================================================

import sqlite3
import os
import datetime

# Misma BD que usuarios para mantener todo centralizado
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "logicheck_users.db")

# ── Constantes de Acciones ───────────────────────────────────
LOGIN               = "Inicio de Sesión"
LOGIN_FALLIDO       = "Intento de Acceso Fallido"
LOGOUT              = "Cierre de Sesión"
ACCESO_DENEGADO     = "Acceso Denegado"
FACTURA_CARGADA     = "Factura Cargada"
FACTURA_PROCESADA   = "Factura Procesada"
VIDEO_INICIADO      = "Video Iniciado"
VIDEO_DETENIDO      = "Video Detenido"
VIDEO_RESULTADO     = "Resultado de Análisis"
DISCREPANCIA        = "Discrepancia Detectada"
ASIGNACION_CREADA   = "Asignación Vehicular"
REPORTE_EXPORTADO   = "Reporte Exportado"
TEMA_CAMBIADO       = "Cambio de Tema"
FACTURA_ADVERTENCIA = "Factura con Advertencia"
USUARIO_CREADO      = "Usuario Creado"
USUARIO_EDITADO     = "Usuario Editado"
USUARIO_DESACTIVADO = "Usuario Desactivado"
USUARIO_ACTIVADO    = "Usuario Activado"
CONTRASENA_CAMBIADA = "Contraseña Cambiada"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(os.path.abspath(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_logs_table():
    """Crea la tabla de logs si no existe."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER,
                username    TEXT NOT NULL,
                role        TEXT NOT NULL,
                action      TEXT NOT NULL,
                description TEXT DEFAULT '',
                timestamp   TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)
        conn.commit()


def log_action(user_data: dict, action: str, description: str = ""):
    """
    Registra una acción en el log.
    user_data: dict con {id, username, role, full_name}
    action: constante de acción (usa las definidas arriba)
    description: texto libre adicional
    """
    if not user_data:
        return
    try:
        with _get_conn() as conn:
            conn.execute("""
                INSERT INTO activity_logs (user_id, username, role, action, description)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_data.get("id"),
                user_data.get("username", ""),
                user_data.get("role", ""),
                action,
                description,
            ))
            conn.commit()
    except Exception as e:
        print(f"[LOGGER] Error registrando log: {e}")


def get_logs(role: str, username: str) -> list:
    """
    Retorna logs filtrados según el rol:
      - 'admin'  → todos los registros (máx. 1000)
      - otros    → solo los registros de ese username (máx. 500)
    """
    with _get_conn() as conn:
        if role == "admin":
            cursor = conn.execute("""
                SELECT * FROM activity_logs
                ORDER BY id DESC LIMIT 1000
            """)
        else:
            cursor = conn.execute("""
                SELECT * FROM activity_logs
                WHERE username = ?
                ORDER BY id DESC LIMIT 500
            """, (username,))
        return [dict(row) for row in cursor.fetchall()]


def get_logs_filtered(role: str, username: str,
                      filter_user: str = "",
                      filter_action: str = "") -> list:
    """
    Retorna logs con filtros adicionales (para la UI).
      filter_user   → "" = todos, otro = filtrar por username específico
      filter_action → "" = todas, otro = filtrar por tipo de acción
    """
    conditions = []
    params = []

    if role != "admin":
        conditions.append("username = ?")
        params.append(username)
    elif filter_user:
        conditions.append("username = ?")
        params.append(filter_user)

    if filter_action:
        conditions.append("action = ?")
        params.append(filter_action)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    limit = 1000 if role == "admin" else 500

    with _get_conn() as conn:
        cursor = conn.execute(
            f"SELECT * FROM activity_logs {where} ORDER BY id DESC LIMIT {limit}",
            params
        )
        return [dict(row) for row in cursor.fetchall()]


def get_distinct_usernames() -> list:
    """Retorna lista de usernames únicos que tienen logs (para filtro del admin)."""
    with _get_conn() as conn:
        cursor = conn.execute(
            "SELECT DISTINCT username FROM activity_logs ORDER BY username"
        )
        return [row[0] for row in cursor.fetchall()]


def get_distinct_actions() -> list:
    """Retorna lista de tipos de acciones registrados."""
    with _get_conn() as conn:
        cursor = conn.execute(
            "SELECT DISTINCT action FROM activity_logs ORDER BY action"
        )
        return [row[0] for row in cursor.fetchall()]


def get_stats_today() -> dict:
    """Estadísticas rápidas del día de hoy."""
    today = datetime.date.today().isoformat()
    with _get_conn() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM activity_logs WHERE timestamp LIKE ?",
            (f"{today}%",)
        ).fetchone()[0]

        logins = conn.execute(
            "SELECT COUNT(*) FROM activity_logs WHERE action = ? AND timestamp LIKE ?",
            (LOGIN, f"{today}%")
        ).fetchone()[0]

        users_active = conn.execute(
            "SELECT COUNT(DISTINCT username) FROM activity_logs WHERE timestamp LIKE ?",
            (f"{today}%",)
        ).fetchone()[0]

    return {
        "total_today": total,
        "logins_today": logins,
        "users_active_today": users_active,
    }


def get_dashboard_metrics() -> dict:
    """Retorna métricas operativas del día de hoy para el Dashboard."""
    today = datetime.date.today().isoformat()
    metrics = {
        "despachos": 0,
        "discrepancias": 0,
        "vehiculos": 0,
        "accuracy": 100.0
    }
    
    try:
        with _get_conn() as conn:
            # 1. Despachos (Facturas procesadas hoy)
            metrics["despachos"] = conn.execute(
                "SELECT COUNT(*) FROM activity_logs WHERE action = ? AND timestamp LIKE ?",
                (FACTURA_PROCESADA, f"{today}%")
            ).fetchone()[0]

            # 2. Discrepancias detectadas hoy
            metrics["discrepancias"] = conn.execute(
                "SELECT COUNT(*) FROM activity_logs WHERE action = ? AND timestamp LIKE ?",
                (DISCREPANCIA, f"{today}%")
            ).fetchone()[0]

            # 3. Vehículos procesados (Asignaciones creadas hoy)
            metrics["vehiculos"] = conn.execute(
                "SELECT COUNT(*) FROM activity_logs WHERE action = ? AND timestamp LIKE ?",
                (ASIGNACION_CREADA, f"{today}%")
            ).fetchone()[0]

            # 4. Cálculo de Accuracy (100 - (discrepancias / despachos * 100))
            if metrics["despachos"] > 0:
                error_rate = (metrics["discrepancias"] / metrics["despachos"]) * 100
                metrics["accuracy"] = max(0.0, 100.0 - error_rate)
            else:
                metrics["accuracy"] = 100.0
    except Exception as e:
        print(f"[LOGGER] Error calculando métricas: {e}")

    return metrics
