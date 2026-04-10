# core/auth.py
# ============================================================
#  LogiCheck — Autenticación con SQLite
#  Tabla: usuarios (id, username, password_hash, password_salt, role, full_name, active, ...)
#  Seguridad: SHA-256 + salt único por usuario (compatible con Python stdlib)
# ============================================================

import sqlite3
import hashlib
import os
import secrets

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "logicheck_users.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(os.path.abspath(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ── Hashing seguro (SHA-256 + salt) ─────────────────────────

def _generate_salt() -> str:
    """Genera un salt criptográficamente seguro de 32 bytes en hex."""
    return secrets.token_hex(32)


def _hash_password(password: str, salt: str) -> str:
    """
    Hashea la contraseña usando SHA-256 con salt único.
    Formato: SHA256(salt + password)
    """
    salted = (salt + password).encode("utf-8")
    return hashlib.sha256(salted).hexdigest()


def _verify_password(password: str, stored_hash: str, stored_salt: str) -> bool:
    """Verifica una contraseña contra su hash y salt almacenados."""
    # Compatibilidad retroactiva: si no hay salt (BD antigua), verifica sin salt
    if not stored_salt:
        old_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return old_hash == stored_hash
    return _hash_password(password, stored_salt) == stored_hash


# ── Inicialización ───────────────────────────────────────────

def init_db():
    """
    Ejecuta las migraciones de BD y siembra datos iniciales si es necesario.
    Delega todo el manejo de esquema a db_migrations.
    """
    from core.db_migrations import run_migrations
    run_migrations()

    # Verificar si necesitamos usuarios semilla
    with _get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
        if count == 0:
            _seed_default_users(conn)

    # Migrar contraseñas antiguas (sin salt) al nuevo sistema
    _migrate_passwords_to_salted()


def _seed_default_users(conn: sqlite3.Connection):
    """Siembra los usuarios por defecto con el nuevo sistema de hash+salt."""
    _seed_users = [
        ("admin",   "admin123",   "admin",      "Administrador del Sistema"),
        ("juan",    "factura123", "op_factura",  "Juan García - Op. Factura"),
        ("carlos",  "video123",   "op_video",    "Carlos Ruiz - Op. Video"),
        ("gerente", "gerente123", "gerente",     "Ana Martínez - Gerente"),
        ("dueno",   "dueno123",   "dueno",       "Don Durán - Dueño"),
    ]
    for username, password, role, full_name in _seed_users:
        salt = _generate_salt()
        pw_hash = _hash_password(password, salt)
        conn.execute("""
            INSERT INTO usuarios (username, password_hash, password_salt, role, full_name)
            VALUES (?, ?, ?, ?, ?)
        """, (username, pw_hash, salt, role, full_name))
    conn.commit()
    print("[AUTH] BD inicializada con 5 usuarios de prueba (hash + salt).")


def _migrate_passwords_to_salted():
    """
    Migración one-time: convierte hashes sin salt al nuevo sistema.
    Detecta usuarios con salt vacío y les genera un salt placeholder.
    NOTA: No podemos re-hashear sin la contraseña original, por lo que
    marcamos la siguiente vez que inicien sesión para actualizar.
    """
    with _get_conn() as conn:
        users_no_salt = conn.execute(
            "SELECT id, password_hash FROM usuarios WHERE password_salt = '' OR password_salt IS NULL"
        ).fetchall()
        if users_no_salt:
            print(f"[AUTH] {len(users_no_salt)} usuarios con hash sin salt detectados. "
                  "Se actualizarán al próximo inicio de sesión.")


# ── Autenticación ────────────────────────────────────────────

def authenticate(username: str, password: str) -> dict | None:
    """
    Verifica usuario y contraseña.
    Si el usuario tiene hash antiguo (sin salt), lo actualiza al nuevo sistema.
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

    stored_hash = row["password_hash"]
    stored_salt = row["password_salt"] or ""

    if not _verify_password(password, stored_hash, stored_salt):
        return None

    # Actualizar hash al nuevo sistema si venía sin salt
    if not stored_salt:
        _upgrade_password_hash(row["id"], password)

    return {
        "id":        row["id"],
        "username":  row["username"],
        "role":      row["role"],
        "full_name": row["full_name"],
        "overrides": row["permissions_override"],
        "expires_at": row["permissions_expire_at"],
    }


def _upgrade_password_hash(user_id: int, plain_password: str):
    """Actualiza un hash sin salt al nuevo sistema (salt + SHA256)."""
    new_salt = _generate_salt()
    new_hash = _hash_password(plain_password, new_salt)
    with _get_conn() as conn:
        conn.execute(
            "UPDATE usuarios SET password_hash = ?, password_salt = ? WHERE id = ?",
            (new_hash, new_salt, user_id)
        )
        conn.commit()
    print(f"[AUTH] Contraseña del usuario ID={user_id} actualizada a hash+salt.")


# ── CRUD de Usuarios ─────────────────────────────────────────

def get_all_users() -> list[dict]:
    """Retorna todos los usuarios (activos e inactivos)."""
    with _get_conn() as conn:
        cursor = conn.execute(
            """SELECT id, username, role, full_name, active, created_at,
                      permissions_override, permissions_expire_at
               FROM usuarios ORDER BY id"""
        )
        return [dict(row) for row in cursor.fetchall()]


def create_user(username: str, password: str, role: str, full_name: str) -> bool:
    """Crea un nuevo usuario con hash+salt. Retorna True si fue exitoso."""
    try:
        salt = _generate_salt()
        pw_hash = _hash_password(password, salt)
        with _get_conn() as conn:
            conn.execute("""
                INSERT INTO usuarios (username, password_hash, password_salt, role, full_name)
                VALUES (?, ?, ?, ?, ?)
            """, (username.strip().lower(), pw_hash, salt, role, full_name))
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
    """Cambia la contraseña de un usuario (genera nuevo salt)."""
    new_salt = _generate_salt()
    new_hash = _hash_password(new_password, new_salt)
    with _get_conn() as conn:
        conn.execute(
            "UPDATE usuarios SET password_hash = ?, password_salt = ? WHERE id = ?",
            (new_hash, new_salt, user_id)
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


# ── Gestión de Permisos ───────────────────────────────────────

def update_user_permissions(user_id: int, overrides: str | None,
                             expire_at: str | None, modified_by: int) -> bool:
    """
    Actualiza los overrides de permisos y la fecha de expiración.
    overrides: string JSON o None
    expire_at: string ISO date o None
    """
    with _get_conn() as conn:
        conn.execute("""
            UPDATE usuarios
            SET permissions_override = ?,
                permissions_expire_at = ?,
                permissions_modified_by = ?
            WHERE id = ?
        """, (overrides, expire_at, modified_by, user_id))
        conn.commit()
    return True


def clone_permissions(from_user_id: int, to_user_id: int, modified_by: int) -> bool:
    """Copia los permisos y el rol de un usuario a otro."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT role, permissions_override, permissions_expire_at FROM usuarios WHERE id = ?",
            (from_user_id,)
        ).fetchone()
        if not row:
            return False

        conn.execute("""
            UPDATE usuarios
            SET role = ?,
                permissions_override = ?,
                permissions_expire_at = ?,
                permissions_modified_by = ?
            WHERE id = ?
        """, (row["role"], row["permissions_override"],
              row["permissions_expire_at"], modified_by, to_user_id))
        conn.commit()
    return True
