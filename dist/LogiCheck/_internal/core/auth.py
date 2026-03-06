# core/auth.py
# ============================================================
#  LogiCheck — Autenticación con SQLite
#  Tabla: usuarios (id, username, password_hash, role, full_name, active)
#  Se usa hashlib SHA-256 (sin dependencias externas)
# ============================================================

import sqlite3
import hashlib
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "logicheck_users.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(os.path.abspath(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# ── Inicialización ───────────────────────────────────────────

def init_db():
    """Crea las tablas de usuarios y logs si no existen, y siembra datos iniciales."""
    from core.logger import init_logs_table   # import tardío para evitar circular
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role        TEXT NOT NULL,
                full_name   TEXT NOT NULL,
                active      INTEGER NOT NULL DEFAULT 1,
                created_at  TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()

        # Insertar usuarios por defecto si la tabla está vacía
        cursor = conn.execute("SELECT COUNT(*) FROM usuarios")
        count = cursor.fetchone()[0]
        if count == 0:
            _seed_users = [
                ("admin",   "admin123",   "admin",      "Administrador del Sistema"),
                ("juan",    "factura123", "op_factura",  "Juan García - Op. Factura"),
                ("carlos",  "video123",   "op_video",    "Carlos Ruiz - Op. Video"),
                ("gerente", "gerente123", "gerente",     "Ana Martínez - Gerente"),
                ("dueno",   "dueno123",   "dueno",       "Don Durán - Dueño"),
            ]
            for username, password, role, full_name in _seed_users:
                conn.execute("""
                    INSERT INTO usuarios (username, password_hash, role, full_name)
                    VALUES (?, ?, ?, ?)
                """, (username, _hash_password(password), role, full_name))
            conn.commit()
            print("[AUTH] BD inicializada con 5 usuarios de prueba.")

    # Crear tabla de logs (idempotente)
    init_logs_table()


# ── Autenticación ────────────────────────────────────────────

def authenticate(username: str, password: str) -> dict | None:
    """
    Verifica usuario y contraseña.
    Retorna dict con datos del usuario si es válido, None si falla.
    """
    with _get_conn() as conn:
        cursor = conn.execute(
            "SELECT * FROM usuarios WHERE username = ? AND active = 1",
            (username.strip().lower(),)
        )
        row = cursor.fetchone()

    if row is None:
        return None

    if row["password_hash"] != _hash_password(password):
        return None

    return {
        "id":        row["id"],
        "username":  row["username"],
        "role":      row["role"],
        "full_name": row["full_name"],
    }


# ── CRUD de Usuarios ─────────────────────────────────────────

def get_all_users() -> list[dict]:
    """Retorna todos los usuarios activos."""
    with _get_conn() as conn:
        cursor = conn.execute(
            "SELECT id, username, role, full_name, active, created_at FROM usuarios ORDER BY id"
        )
        return [dict(row) for row in cursor.fetchall()]


def create_user(username: str, password: str, role: str, full_name: str) -> bool:
    """Crea un nuevo usuario. Retorna True si fue exitoso."""
    try:
        with _get_conn() as conn:
            conn.execute("""
                INSERT INTO usuarios (username, password_hash, role, full_name)
                VALUES (?, ?, ?, ?)
            """, (username.strip().lower(), _hash_password(password), role, full_name))
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # username duplicado


def update_user(user_id: int, full_name: str, role: str) -> bool:
    """Actualiza nombre y rol de un usuario."""
    with _get_conn() as conn:
        conn.execute(
            "UPDATE usuarios SET full_name = ?, role = ? WHERE id = ?",
            (full_name, role, user_id)
        )
        conn.commit()
    return True


def change_password(user_id: int, new_password: str) -> bool:
    """Cambia la contraseña de un usuario."""
    with _get_conn() as conn:
        conn.execute(
            "UPDATE usuarios SET password_hash = ? WHERE id = ?",
            (_hash_password(new_password), user_id)
        )
        conn.commit()
    return True


def deactivate_user(user_id: int) -> bool:
    """Desactiva un usuario (no lo elimina físicamente)."""
    with _get_conn() as conn:
        conn.execute("UPDATE usuarios SET active = 0 WHERE id = ?", (user_id,))
        conn.commit()
    return True


def reactivate_user(user_id: int) -> bool:
    """Reactiva un usuario desactivado."""
    with _get_conn() as conn:
        conn.execute("UPDATE usuarios SET active = 1 WHERE id = ?", (user_id,))
        conn.commit()
    return True
