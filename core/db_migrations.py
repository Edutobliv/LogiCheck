# core/db_migrations.py
# ============================================================
#  LogiCheck — Sistema de Migraciones de Base de Datos
#  Gestiona la evolución del esquema de forma ordenada y segura.
#  Cada migración es idempotente y versionada.
# ============================================================

import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "logicheck_users.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(os.path.abspath(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ── Versión actual del esquema ───────────────────────────────
SCHEMA_VERSION = 8


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Obtiene la versión actual del esquema desde la BD."""
    try:
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        return 0


def set_schema_version(conn: sqlite3.Connection, version: int):
    """Actualiza la versión del esquema."""
    conn.execute("DELETE FROM schema_version")
    conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))


# ── Migraciones individuales ─────────────────────────────────

def _migration_1_create_schema_version(conn: sqlite3.Connection):
    """v1: Crea la tabla de control de versiones del esquema."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL
        )
    """)
    if conn.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0] == 0:
        conn.execute("INSERT INTO schema_version (version) VALUES (0)")


def _migration_2_create_base_tables(conn: sqlite3.Connection):
    """v2: Crea las tablas base (usuarios, activity_logs, auditorias)."""
    # --- Tabla: usuarios ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            username                TEXT UNIQUE NOT NULL,
            password_hash           TEXT NOT NULL,
            password_salt           TEXT NOT NULL DEFAULT '',
            role                    TEXT NOT NULL,
            full_name               TEXT NOT NULL,
            active                  INTEGER NOT NULL DEFAULT 1,
            created_at              TEXT DEFAULT (datetime('now')),
            permissions_override    TEXT,
            permissions_expire_at   TEXT,
            permissions_modified_by INTEGER,
            FOREIGN KEY (permissions_modified_by) REFERENCES usuarios(id)
                ON DELETE SET NULL
        )
    """)

    # --- Tabla: activity_logs ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            username    TEXT NOT NULL,
            role        TEXT NOT NULL,
            action      TEXT NOT NULL,
            description TEXT DEFAULT '',
            timestamp   TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (user_id) REFERENCES usuarios(id)
                ON DELETE SET NULL
        )
    """)

    # --- Tabla: auditorias ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS auditorias (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER,
            username        TEXT NOT NULL,
            role            TEXT NOT NULL,
            fecha           TEXT DEFAULT (datetime('now', 'localtime')),
            factura_no      TEXT DEFAULT '',
            cliente         TEXT DEFAULT '',
            video_nombre    TEXT DEFAULT '',
            conteo_ia       TEXT DEFAULT '{}',
            conteo_factura  TEXT DEFAULT '{}',
            discrepancias   TEXT DEFAULT '{}',
            vehiculo        TEXT DEFAULT '',
            resultado       TEXT DEFAULT 'SIN_ANALISIS',
            notas           TEXT DEFAULT '',
            capturas        TEXT DEFAULT '[]',
            FOREIGN KEY (user_id) REFERENCES usuarios(id)
                ON DELETE SET NULL
        )
    """)


def _migration_3_create_catalogs(conn: sqlite3.Connection):
    """v3: Crea las tablas de catálogo (materiales y vehiculos) migradas desde Excel."""
    # --- Tabla: materiales ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS materiales (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo              TEXT UNIQUE NOT NULL,
            nombre              TEXT NOT NULL,
            categoria           TEXT NOT NULL DEFAULT '',
            peso_unitario_kg    REAL NOT NULL DEFAULT 0.0,
            volumen_unitario_m3 REAL NOT NULL DEFAULT 0.0,
            activo              INTEGER NOT NULL DEFAULT 1,
            created_at          TEXT DEFAULT (datetime('now'))
        )
    """)

    # --- Tabla: vehiculos ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vehiculos (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo                  TEXT UNIQUE NOT NULL,
            tipo                    TEXT NOT NULL,
            placa                   TEXT UNIQUE NOT NULL,
            capacidad_max_peso_kg   REAL NOT NULL DEFAULT 0.0,
            capacidad_max_vol_m3    REAL NOT NULL DEFAULT 0.0,
            activo                  INTEGER NOT NULL DEFAULT 1,
            created_at              TEXT DEFAULT (datetime('now'))
        )
    """)

    # Insertar datos base si las tablas están vacías
    if conn.execute("SELECT COUNT(*) FROM materiales").fetchone()[0] == 0:
        materiales = [
            ("001", "Cemento Argos Gris",         "Cemento",            50.0, 0.035),
            ("002", 'Tubo Presion PVC 1/2" 6m',   "Tuberia_Presion",    0.8,  0.005),
            ("003", 'Tubo Sanitario PVC 4" 6m',   "Tuberia_Sanitaria",  4.5,  0.025),
        ]
        conn.executemany("""
            INSERT INTO materiales (codigo, nombre, categoria, peso_unitario_kg, volumen_unitario_m3)
            VALUES (?, ?, ?, ?, ?)
        """, materiales)
        print("[MIGRATION] Materiales base insertados.")

    if conn.execute("SELECT COUNT(*) FROM vehiculos").fetchone()[0] == 0:
        vehiculos = [
            ("V01", "Motocarro",     "ABC-123", 500.0,  2.5),
            ("V02", "Camion Turbo",  "DEF-456", 4500.0, 18.0),
        ]
        conn.executemany("""
            INSERT INTO vehiculos (codigo, tipo, placa, capacidad_max_peso_kg, capacidad_max_vol_m3)
            VALUES (?, ?, ?, ?, ?)
        """, vehiculos)
        print("[MIGRATION] Vehiculos base insertados.")


def _migration_4_add_salt_column(conn: sqlite3.Connection):
    """v4: Añade la columna password_salt a usuarios si no existe."""
    # La tabla puede haber sido creada sin el campo salt (BD existente)
    col_names = [r[1] for r in conn.execute("PRAGMA table_info(usuarios)").fetchall()]
    if "password_salt" not in col_names:
        conn.execute("ALTER TABLE usuarios ADD COLUMN password_salt TEXT NOT NULL DEFAULT ''")
        print("[MIGRATION] Columna 'password_salt' añadida a 'usuarios'.")


def _migration_5_add_user_id_to_auditorias(conn: sqlite3.Connection):
    """v5: Añade user_id (FK) a auditorias si no existe."""
    col_names = [r[1] for r in conn.execute("PRAGMA table_info(auditorias)").fetchall()]
    if "user_id" not in col_names:
        conn.execute("ALTER TABLE auditorias ADD COLUMN user_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL")
        print("[MIGRATION] Columna 'user_id' añadida a 'auditorias'.")


def _migration_6_advanced_features(conn: sqlite3.Connection):
    """v6: Triggers de auditoría, Notificaciones Queue y SQL Views."""
    
    # 1. Sistema de Notificaciones (Queue)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notificaciones_queue (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo            TEXT NOT NULL,
            mensaje         TEXT NOT NULL,
            destinatario    TEXT DEFAULT '',
            estado          TEXT DEFAULT 'PENDIENTE', -- PENDIENTE, ENVIADO, ERROR
            intentos        INTEGER DEFAULT 0,
            fecha_creacion  TEXT DEFAULT (datetime('now', 'localtime')),
            fecha_envio     TEXT
        )
    """)
    
    # 2. Tabla para Triggers de Auditoría
    conn.execute("""
        CREATE TABLE IF NOT EXISTS auditorias_historico (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            auditoria_id        INTEGER,
            operacion           TEXT NOT NULL, -- INSERT, UPDATE, DELETE
            usuario_modificador TEXT,
            fecha_cambio        TEXT DEFAULT (datetime('now', 'localtime')),
            datos_anteriores    TEXT,
            datos_nuevos        TEXT
        )
    """)
    
    # 3. Triggers para registrar cambios en Auditorías
    # Trigger para INSERT
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_auditorias_insert
        AFTER INSERT ON auditorias
        BEGIN
            INSERT INTO auditorias_historico (auditoria_id, operacion, usuario_modificador, datos_nuevos)
            VALUES (NEW.id, 'INSERT', NEW.username, 
                    'Factura: ' || NEW.factura_no || ', Resultado: ' || NEW.resultado);
        END;
    """)
    
    # Trigger para UPDATE
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_auditorias_update
        AFTER UPDATE ON auditorias
        BEGIN
            INSERT INTO auditorias_historico (auditoria_id, operacion, usuario_modificador, datos_anteriores, datos_nuevos)
            VALUES (NEW.id, 'UPDATE', NEW.username,
                    'Resultado: ' || OLD.resultado || ', Vehículo: ' || OLD.vehiculo,
                    'Resultado: ' || NEW.resultado || ', Vehículo: ' || NEW.vehiculo);
            
            -- Insertar notificación si la auditoría cambia a DISCREPANCIA
            INSERT INTO notificaciones_queue (tipo, mensaje)
            SELECT 'ALERTA', 'La auditoría de la factura ' || NEW.factura_no || ' ha registrado una DISCREPANCIA.'
            WHERE NEW.resultado = 'DISCREPANCIA' AND OLD.resultado != 'DISCREPANCIA';
        END;
    """)
    
    # Trigger para DELETE
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_auditorias_delete
        AFTER DELETE ON auditorias
        BEGIN
            INSERT INTO auditorias_historico (auditoria_id, operacion, usuario_modificador, datos_anteriores)
            VALUES (OLD.id, 'DELETE', OLD.username,
                    'Factura: ' || OLD.factura_no || ', Resultado: ' || OLD.resultado);
        END;
    """)

    # 4. SQL Views (Vistas de Reporte)
    conn.execute("""
        CREATE VIEW IF NOT EXISTS view_resumen_mensual AS
        SELECT 
            strftime('%Y-%m', fecha) as mes,
            COUNT(*) as total_auditorias,
            SUM(CASE WHEN resultado = 'CONFORME' THEN 1 ELSE 0 END) as total_conformes,
            SUM(CASE WHEN resultado = 'DISCREPANCIA' THEN 1 ELSE 0 END) as total_discrepancias
        FROM auditorias
        GROUP BY strftime('%Y-%m', fecha)
        ORDER BY mes DESC;
    """)

def _migration_7_expand_catalogs(conn: sqlite3.Connection):
    """v7: Expande catálogos con todas las medidas de tubería y vehículos del mercado colombiano."""

    # ── MATERIALES: Todas las medidas de tubería ─────────────
    import math
    def _vol(diam_mm, length_m):
        r = (diam_mm / 2.0) / 1000.0
        return round(math.pi * r ** 2 * length_m, 6)

    materiales_nuevos = [
        # Tubería Sanitaria PVC — tramo 6m
        ('SAN-112', 'Tubo Sanitario PVC 1 1/2" x 6m', 'Tuberia_Sanitaria', 1.80, _vol(48.0, 6)),
        ('SAN-2',   'Tubo Sanitario PVC 2" x 6m',     'Tuberia_Sanitaria', 2.80, _vol(60.0, 6)),
        ('SAN-3',   'Tubo Sanitario PVC 3" x 6m',     'Tuberia_Sanitaria', 5.20, _vol(88.0, 6)),
        ('SAN-4',   'Tubo Sanitario PVC 4" x 6m',     'Tuberia_Sanitaria', 11.7, _vol(114.0, 6)),
        # Tubería Presión PVC — tramo 6m
        ('PRE-12',  'Tubo Presión PVC 1/2" x 6m',     'Tuberia_Presion',   0.95, _vol(21.0, 6)),
        ('PRE-34',  'Tubo Presión PVC 3/4" x 6m',     'Tuberia_Presion',   1.35, _vol(26.7, 6)),
        ('PRE-1',   'Tubo Presión PVC 1" x 6m',       'Tuberia_Presion',   2.10, _vol(33.4, 6)),
        ('PRE-114', 'Tubo Presión PVC 1 1/4" x 6m',   'Tuberia_Presion',   3.00, _vol(42.2, 6)),
        ('PRE-112', 'Tubo Presión PVC 1 1/2" x 6m',   'Tuberia_Presion',   3.80, _vol(48.3, 6)),
    ]
    for codigo, nombre, cat, peso, vol in materiales_nuevos:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO materiales (codigo, nombre, categoria, peso_unitario_kg, volumen_unitario_m3)
                VALUES (?, ?, ?, ?, ?)
            """, (codigo, nombre, cat, peso, vol))
        except Exception:
            pass

    # ── VEHÍCULOS: Flota ampliada del mercado ferretero ──────
    vehiculos_nuevos = [
        ('V03', 'Camioneta / NHR',      'XXX-000', 2500.0, 10.0),
        ('V04', 'Camión Sencillo (C2)',  'XXX-001', 8500.0, 35.0),
        ('V05', 'Dobletroque (C3)',      'XXX-002', 17000.0, 48.0),
    ]
    for codigo, tipo, placa, peso, vol in vehiculos_nuevos:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO vehiculos (codigo, tipo, placa, capacidad_max_peso_kg, capacidad_max_vol_m3)
                VALUES (?, ?, ?, ?, ?)
            """, (codigo, tipo, placa, peso, vol))
        except Exception:
            pass

    print("[MIGRATION] Catálogos expandidos con medidas de tubería y vehículos adicionales.")


# ── Registro de todas las migraciones ────────────────────────
def _migration_8_login_hardening(conn: sqlite3.Connection):
    """v8: Agrega columnas para bloqueo temporal por intentos fallidos."""
    col_names = [r[1] for r in conn.execute("PRAGMA table_info(usuarios)").fetchall()]
    if "failed_login_count" not in col_names:
        conn.execute("ALTER TABLE usuarios ADD COLUMN failed_login_count INTEGER NOT NULL DEFAULT 0")
    if "locked_until" not in col_names:
        conn.execute("ALTER TABLE usuarios ADD COLUMN locked_until TEXT")


MIGRATIONS = [
    (1, _migration_1_create_schema_version),
    (2, _migration_2_create_base_tables),
    (3, _migration_3_create_catalogs),
    (4, _migration_4_add_salt_column),
    (5, _migration_5_add_user_id_to_auditorias),
    (6, _migration_6_advanced_features),
    (7, _migration_7_expand_catalogs),
    (8, _migration_8_login_hardening),
]


# ── Runner principal ─────────────────────────────────────────
def run_migrations():
    """
    Ejecuta todas las migraciones pendientes de forma segura y ordenada.
    Cada migración corre dentro de una transacción independiente.
    """
    # Primera migración fuera de transacción (crea la tabla de versiones)
    with _get_conn() as conn:
        _migration_1_create_schema_version(conn)
        conn.commit()

    for version, migration_fn in MIGRATIONS:
        with _get_conn() as conn:
            current = get_schema_version(conn)
            if current < version:
                try:
                    print(f"[MIGRATION] Aplicando migración v{version}: {migration_fn.__doc__}")
                    migration_fn(conn)
                    set_schema_version(conn, version)
                    conn.commit()
                    print(f"[MIGRATION] v{version} aplicada correctamente.")
                except Exception as e:
                    conn.rollback()
                    logger.error(f"[MIGRATION] Error en migración v{version}: {e}")
                    raise RuntimeError(f"Fallo en migración v{version}: {e}") from e

    print(f"[MIGRATION] Base de datos actualizada a version {SCHEMA_VERSION}.")
