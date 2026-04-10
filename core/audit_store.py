# core/audit_store.py
# ============================================================
#  LogiCheck — Persistencia de Auditorías (SQLite)
#  Tabla: auditorias (con FK a usuarios)
# ============================================================

import sqlite3
import os
import json
import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "logicheck_users.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(os.path.abspath(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_audits_table():
    """
    Crea la tabla de auditorías si no existe.
    NOTA: A partir de v3 el esquema lo gestiona db_migrations.run_migrations().
    Este método se mantiene por compatibilidad.
    """
    from core.db_migrations import run_migrations
    run_migrations()


def save_audit(user_data: dict, audit_data: dict) -> int:
    """
    Guarda una auditoría completa. Retorna el ID insertado.

    user_data: dict con {id, username, role, ...}
    audit_data esperado:
    {
        'factura_no':     str,
        'cliente':        str,
        'video_nombre':   str,
        'conteo_ia':      {'Cemento': 5, ...},
        'conteo_factura': {'Cemento': 6, ...},
        'vehiculo':       str,
        'notas':          str   (opcional),
        'capturas':       list  (opcional)
    }
    """
    try:
        conteo_ia      = audit_data.get("conteo_ia", {})
        conteo_factura = audit_data.get("conteo_factura", {})

        # Calcular discrepancias automáticamente
        discrepancias = {}
        for mat in set(list(conteo_ia.keys()) + list(conteo_factura.keys())):
            ia_val  = int(conteo_ia.get(mat, 0))
            fac_val = int(conteo_factura.get(mat, 0))
            diff    = ia_val - fac_val
            if diff != 0:
                discrepancias[mat] = diff

        resultado = "CONFORME" if not discrepancias else "DISCREPANCIA"

        with _get_conn() as conn:
            cursor = conn.execute("""
                INSERT INTO auditorias
                    (user_id, username, role, factura_no, cliente, video_nombre,
                     conteo_ia, conteo_factura, discrepancias, vehiculo,
                     resultado, notas, capturas)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_data.get("id"),
                user_data.get("username", ""),
                user_data.get("role", ""),
                audit_data.get("factura_no", ""),
                audit_data.get("cliente", ""),
                audit_data.get("video_nombre", ""),
                json.dumps(conteo_ia,      ensure_ascii=False),
                json.dumps(conteo_factura, ensure_ascii=False),
                json.dumps(discrepancias,  ensure_ascii=False),
                audit_data.get("vehiculo", ""),
                resultado,
                audit_data.get("notas", ""),
                json.dumps(audit_data.get("capturas", []), ensure_ascii=False),
            ))
            conn.commit()
            return cursor.lastrowid
    except Exception as e:
        print(f"[AUDIT_STORE] Error guardando auditoría: {e}")
        return -1


def get_audits(limit: int = 100) -> list:
    """Retorna las últimas N auditorías con datos deserializados."""
    try:
        with _get_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM auditorias ORDER BY id DESC LIMIT ?", (limit,)
            )
            rows = []
            for row in cursor.fetchall():
                d = dict(row)
                for key in ("conteo_ia", "conteo_factura", "discrepancias"):
                    try:
                        d[key] = json.loads(d[key])
                    except Exception:
                        d[key] = {}
                try:
                    d["capturas"] = json.loads(d.get("capturas", "[]"))
                except Exception:
                    d["capturas"] = []
                rows.append(d)
            return rows
    except Exception as e:
        print(f"[AUDIT_STORE] Error leyendo auditorías: {e}")
        return []


def get_dashboard_stats() -> dict:
    """Retorna estadísticas reales del día de hoy para el Dashboard."""
    today = datetime.date.today().isoformat()
    stats = {
        "despachos_hoy":     0,
        "discrepancias_hoy": 0,
        "vehiculos_hoy":     0,
        "accuracy_pct":      100.0,
        "recent_audits":     [],
    }
    try:
        with _get_conn() as conn:
            stats["despachos_hoy"] = conn.execute(
                "SELECT COUNT(*) FROM auditorias WHERE fecha LIKE ?", (f"{today}%",)
            ).fetchone()[0]

            stats["discrepancias_hoy"] = conn.execute(
                "SELECT COUNT(*) FROM auditorias WHERE fecha LIKE ? AND resultado = 'DISCREPANCIA'",
                (f"{today}%",)
            ).fetchone()[0]

            stats["vehiculos_hoy"] = conn.execute(
                "SELECT COUNT(*) FROM auditorias WHERE fecha LIKE ? AND vehiculo != ''",
                (f"{today}%",)
            ).fetchone()[0]

            total = stats["despachos_hoy"]
            if total > 0:
                conformes = total - stats["discrepancias_hoy"]
                stats["accuracy_pct"] = round((conformes / total) * 100, 1)

            cursor = conn.execute(
                "SELECT fecha, factura_no, resultado, vehiculo, username "
                "FROM auditorias ORDER BY id DESC LIMIT 5"
            )
            stats["recent_audits"] = [dict(r) for r in cursor.fetchall()]

    except Exception as e:
        print(f"[AUDIT_STORE] Error en get_dashboard_stats: {e}")

    return stats


def get_monthly_trends() -> list:
    """
    Retorna datos de tendencia diaria de los últimos 30 días:
    [{'date': ..., 'total': ..., 'discrepancies': ...}, ...]
    """
    try:
        with _get_conn() as conn:
            cursor = conn.execute("""
                SELECT
                    date(fecha) as d,
                    count(*) as total,
                    sum(CASE WHEN resultado = 'DISCREPANCIA' THEN 1 ELSE 0 END) as disc
                FROM auditorias
                WHERE date(fecha) >= date('now', 'localtime', '-30 days')
                GROUP BY d
                ORDER BY d ASC
            """)
            return [{"date": r[0], "total": r[1], "discrepancies": r[2]}
                    for r in cursor.fetchall()]
    except Exception as e:
        print(f"[AUDIT_STORE] Error en get_monthly_trends: {e}")
    return []
