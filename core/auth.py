# core/auth.py
# ============================================================
#  LogiCheck â€” AutenticaciÃ³n con SQLite
#  Tabla: usuarios (id, username, password_hash, password_salt, role, full_name, active, ...)
#  Seguridad: SHA-256 + salt Ãºnico por usuario (compatible con Python stdlib)
# ============================================================

import sqlite3
import hashlib
import os
import secrets
import hmac
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "logicheck_users.db")
PBKDF2_ITERATIONS = 310_000
LOCK_THRESHOLD = 5
LOCK_MINUTES = 10


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(os.path.abspath(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# â”€â”€ Hashing seguro (SHA-256 + salt) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _generate_salt() -> str:
    """Genera un salt criptogrÃ¡ficamente seguro de 32 bytes en hex."""
    return secrets.token_hex(32)


def _hash_password(password: str, salt: str) -> str:
    """
    Hashea la contraseÃ±a usando SHA-256 con salt Ãºnico.
    Formato: SHA256(salt + password)
    """
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def _verify_password(password: str, stored_hash: str, stored_salt: str) -> bool:
    """Verifica una contrasena contra su hash almacenado."""
    if stored_hash.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, salt, digest = stored_hash.split("$", 3)
            candidate = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                int(iterations),
            ).hex()
            return hmac.compare_digest(candidate, digest)
        except Exception:
            return False

    if not stored_salt:
        old_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(old_hash, stored_hash)

    legacy = hashlib.sha256((stored_salt + password).encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy, stored_hash)

# â”€â”€ InicializaciÃ³n â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

    # Migrar contraseÃ±as antiguas (sin salt) al nuevo sistema
    _migrate_passwords_to_salted()


def _seed_default_users(conn: sqlite3.Connection):
    """Siembra los usuarios por defecto con el nuevo sistema de hash+salt."""
    _seed_users = [
        ("admin",   "admin123",   "admin",      "Administrador del Sistema"),
        ("juan",    "factura123", "op_factura",  "Juan GarcÃ­a - Op. Factura"),
        ("carlos",  "video123",   "op_video",    "Carlos Ruiz - Op. Video"),
        ("gerente", "gerente123", "gerente",     "Ana MartÃ­nez - Gerente"),
        ("dueno",   "dueno123",   "dueno",       "Don DurÃ¡n - DueÃ±o"),
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
    MigraciÃ³n one-time: convierte hashes sin salt al nuevo sistema.
    Detecta usuarios con salt vacÃ­o y les genera un salt placeholder.
    NOTA: No podemos re-hashear sin la contraseÃ±a original, por lo que
    marcamos la siguiente vez que inicien sesiÃ³n para actualizar.
    """
    with _get_conn() as conn:
        users_no_salt = conn.execute(
            "SELECT id, password_hash FROM usuarios WHERE password_salt = '' OR password_salt IS NULL"
        ).fetchall()
        if users_no_salt:
            print(f"[AUTH] {len(users_no_salt)} usuarios con hash sin salt detectados. "
                  "Se actualizarÃ¡n al prÃ³ximo inicio de sesiÃ³n.")


# â”€â”€ AutenticaciÃ³n â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def authenticate(username: str, password: str) -> dict | None:
    """
    Verifica usuario y contrasena.
    Migra hashes heredados a PBKDF2 y bloquea temporalmente intentos repetidos.
    """
    clean_username = username.strip().lower()
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM usuarios WHERE username = ? AND active = 1",
            (clean_username,)
        ).fetchone()

    if row is None:
        return None

    locked_until = row["locked_until"] if "locked_until" in row.keys() else None
    if locked_until:
        try:
            if datetime.fromisoformat(locked_until) > datetime.now():
                return None
        except ValueError:
            pass

    stored_hash = row["password_hash"]
    stored_salt = row["password_salt"] or ""

    if not _verify_password(password, stored_hash, stored_salt):
        _register_failed_login(row["id"], row["failed_login_count"] if "failed_login_count" in row.keys() else 0)
        return None

    _clear_login_failures(row["id"])

    if not stored_hash.startswith("pbkdf2_sha256$"):
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
    print(f"[AUTH] ContraseÃ±a del usuario ID={user_id} actualizada a hash+salt.")


def _register_failed_login(user_id: int, current_count: int):
    next_count = int(current_count or 0) + 1
    locked_until = None
    if next_count >= LOCK_THRESHOLD:
        locked_until = (datetime.now() + timedelta(minutes=LOCK_MINUTES)).isoformat(timespec="seconds")
    with _get_conn() as conn:
        conn.execute(
            "UPDATE usuarios SET failed_login_count = ?, locked_until = ? WHERE id = ?",
            (next_count, locked_until, user_id),
        )
        conn.commit()


def _clear_login_failures(user_id: int):
    with _get_conn() as conn:
        conn.execute(
            "UPDATE usuarios SET failed_login_count = 0, locked_until = NULL WHERE id = ?",
            (user_id,),
        )
        conn.commit()


# â”€â”€ CRUD de Usuarios â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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
    """Cambia la contraseÃ±a de un usuario (genera nuevo salt)."""
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
    """Desactiva un usuario (no lo elimina fÃ­sicamente)."""
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


# â”€â”€ GestiÃ³n de Permisos â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def update_user_permissions(user_id: int, overrides: str | None,
                             expire_at: str | None, modified_by: int) -> bool:
    """
    Actualiza los overrides de permisos y la fecha de expiraciÃ³n.
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
