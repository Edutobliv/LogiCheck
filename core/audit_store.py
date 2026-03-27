# core/audit_store.py
# ============================================================
#  LogiCheck — Persistencia de Auditorías (SQLite)
#  Tabla: auditorias
# ============================================================

import sqlite3
import os
import json
import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "logicheck_users.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(os.path.abspath(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_audits_table():
    """Crea la tabla de auditorías si no existe."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS auditorias (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                username         TEXT NOT NULL,
                role             TEXT NOT NULL,
                fecha            TEXT DEFAULT (datetime('now', 'localtime')),
                factura_no       TEXT DEFAULT '',
                cliente          TEXT DEFAULT '',
                video_nombre     TEXT DEFAULT '',
                conteo_ia        TEXT DEFAULT '{}',
                conteo_factura   TEXT DEFAULT '{}',
                discrepancias    TEXT DEFAULT '{}',
                vehiculo         TEXT DEFAULT '',
                resultado        TEXT DEFAULT 'SIN_ANALISIS',
                notas            TEXT DEFAULT '',
                capturas         TEXT DEFAULT '[]'
            )
        """)
        
        try:
            conn.execute("ALTER TABLE auditorias ADD COLUMN capturas TEXT DEFAULT '[]'")
        except sqlite3.OperationalError:
            pass # Ya existe
            
        conn.commit()


def save_audit(user_data: dict, audit_data: dict) -> int:
    """
    Guarda una auditoría completa. Retorna el ID insertado.

    audit_data esperado:
    {
        'factura_no':     str,
        'cliente':        str,
        'video_nombre':   str,
        'conteo_ia':      {'Cemento': 5, ...},
        'conteo_factura': {'Cemento': 6, ...},
        'vehiculo':       str,
        'notas':          str   (opcional)
    }
    """
    try:
        init_audits_table()

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
                    (username, role, factura_no, cliente, video_nombre,
                     conteo_ia, conteo_factura, discrepancias, vehiculo, resultado, notas, capturas)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_data.get("username", ""),
                user_data.get("role", ""),
                audit_data.get("factura_no", ""),
                audit_data.get("cliente", ""),
                audit_data.get("video_nombre", ""),
                json.dumps(conteo_ia, ensure_ascii=False),
                json.dumps(conteo_factura, ensure_ascii=False),
                json.dumps(discrepancias, ensure_ascii=False),
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
    """Retorna las últimas N auditorías."""
    try:
        init_audits_table()
        with _get_conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM auditorias ORDER BY id DESC LIMIT ?", (limit,)
            )
            rows = []
            for row in cursor.fetchall():
                d = dict(row)
                # Deserializar JSON
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
    """
    Retorna estadísticas reales del día de hoy para el Dashboard.
    """
    today = datetime.date.today().isoformat()
    stats = {
        "despachos_hoy":    0,
        "discrepancias_hoy": 0,
        "vehiculos_hoy":     0,
        "accuracy_pct":      100.0,
        "recent_audits":     [],
    }
    try:
        init_audits_table()
        with _get_conn() as conn:
            # Despachos del día
            stats["despachos_hoy"] = conn.execute(
                "SELECT COUNT(*) FROM auditorias WHERE fecha LIKE ?", (f"{today}%",)
            ).fetchone()[0]

            # Discrepancias del día
            stats["discrepancias_hoy"] = conn.execute(
                "SELECT COUNT(*) FROM auditorias WHERE fecha LIKE ? AND resultado = 'DISCREPANCIA'",
                (f"{today}%",)
            ).fetchone()[0]

            # Vehículos asignados del día (auditorías con vehículo no vacío)
            stats["vehiculos_hoy"] = conn.execute(
                "SELECT COUNT(*) FROM auditorias WHERE fecha LIKE ? AND vehiculo != ''",
                (f"{today}%",)
            ).fetchone()[0]

            # Accuracy: (conformes / total) * 100
            total = stats["despachos_hoy"]
            if total > 0:
                conformes = total - stats["discrepancias_hoy"]
                stats["accuracy_pct"] = round((conformes / total) * 100, 1)

            # Últimas 5 auditorías para tabla Dashboard
            cursor = conn.execute(
                "SELECT fecha, factura_no, resultado, vehiculo, username FROM auditorias ORDER BY id DESC LIMIT 5"
            )
            stats["recent_audits"] = [dict(r) for r in cursor.fetchall()]

    except Exception as e:
        print(f"[AUDIT_STORE] Error en get_dashboard_stats: {e}")

    return stats


def get_monthly_trends() -> list:
    """
    Retorna datos de tendencia diaria de los últimos 30 días:
    [(fecha, despachos, discrepancias), ...]
    """
    trends = []
    try:
        init_audits_table()
        # Generamos una lista de los últimos 30 días (inclusive hoy)
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
            trends = cursor.fetchall()
            # Convertir rows de sqlite a lista de dicts simple
            return [{"date": r[0], "total": r[1], "discrepancies": r[2]} for r in trends]
    except Exception as e:
        print(f"[AUDIT_STORE] Error en get_monthly_trends: {e}")
    return []
