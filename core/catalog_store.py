# core/catalog_store.py
# ============================================================
#  LogiCheck — Catálogo de Materiales y Vehículos (SQLite)
#  Tablas: materiales, vehiculos
#  Reemplaza la dependencia del archivo BaseDatos_Ferreteria.xlsx
#  en tiempo de ejecución (el Excel se mantiene como respaldo/importación).
# ============================================================

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "logicheck_users.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(os.path.abspath(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ════════════════════════════════════════════════════════════
#  MATERIALES
# ════════════════════════════════════════════════════════════

def get_all_materiales(solo_activos: bool = True) -> list[dict]:
    """Retorna todos los materiales del catálogo."""
    with _get_conn() as conn:
        query = "SELECT * FROM materiales"
        if solo_activos:
            query += " WHERE activo = 1"
        query += " ORDER BY nombre"
        return [dict(r) for r in conn.execute(query).fetchall()]


def get_material_by_codigo(codigo: str) -> dict | None:
    """Busca un material por su código único."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM materiales WHERE codigo = ?", (codigo,)
        ).fetchone()
        return dict(row) if row else None


def get_material_by_nombre(nombre: str) -> dict | None:
    """Busca un material por nombre (búsqueda exacta, case-insensitive)."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM materiales WHERE LOWER(nombre) = LOWER(?)", (nombre,)
        ).fetchone()
        return dict(row) if row else None


def get_materiales_nombres() -> list[str]:
    """Retorna sólo los nombres de materiales activos (para listas de selección)."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT nombre FROM materiales WHERE activo = 1 ORDER BY nombre"
        ).fetchall()
        return [r[0] for r in rows]


def create_material(codigo: str, nombre: str, categoria: str,
                    peso_kg: float, vol_m3: float) -> bool:
    """Crea un nuevo material. Retorna True si fue exitoso."""
    try:
        with _get_conn() as conn:
            conn.execute("""
                INSERT INTO materiales (codigo, nombre, categoria, peso_unitario_kg, volumen_unitario_m3)
                VALUES (?, ?, ?, ?, ?)
            """, (codigo, nombre, categoria, peso_kg, vol_m3))
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Código duplicado


def update_material(material_id: int, nombre: str, categoria: str,
                    peso_kg: float, vol_m3: float) -> bool:
    """Actualiza los datos de un material existente."""
    with _get_conn() as conn:
        conn.execute("""
            UPDATE materiales
            SET nombre = ?, categoria = ?, peso_unitario_kg = ?, volumen_unitario_m3 = ?
            WHERE id = ?
        """, (nombre, categoria, peso_kg, vol_m3, material_id))
        conn.commit()
    return True


def deactivate_material(material_id: int) -> bool:
    """Desactiva un material (borrado lógico)."""
    with _get_conn() as conn:
        conn.execute("UPDATE materiales SET activo = 0 WHERE id = ?", (material_id,))
        conn.commit()
    return True


# ════════════════════════════════════════════════════════════
#  VEHÍCULOS
# ════════════════════════════════════════════════════════════

def get_all_vehiculos(solo_activos: bool = True) -> list[dict]:
    """Retorna todos los vehículos del catálogo."""
    with _get_conn() as conn:
        query = "SELECT * FROM vehiculos"
        if solo_activos:
            query += " WHERE activo = 1"
        query += " ORDER BY tipo"
        return [dict(r) for r in conn.execute(query).fetchall()]


def get_vehiculo_by_placa(placa: str) -> dict | None:
    """Busca un vehículo por su placa."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM vehiculos WHERE UPPER(placa) = UPPER(?)", (placa,)
        ).fetchone()
        return dict(row) if row else None


def get_vehiculo_by_codigo(codigo: str) -> dict | None:
    """Busca un vehículo por su código."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM vehiculos WHERE codigo = ?", (codigo,)
        ).fetchone()
        return dict(row) if row else None


def get_vehiculos_opciones() -> list[str]:
    """Retorna lista 'Tipo — Placa' de vehículos activos (para ComboBox en UI)."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT tipo, placa FROM vehiculos WHERE activo = 1 ORDER BY tipo"
        ).fetchall()
        return [f"{r['tipo']} — {r['placa']}" for r in rows]


def create_vehiculo(codigo: str, tipo: str, placa: str,
                    max_peso_kg: float, max_vol_m3: float) -> bool:
    """Crea un nuevo vehículo. Retorna True si fue exitoso."""
    try:
        with _get_conn() as conn:
            conn.execute("""
                INSERT INTO vehiculos (codigo, tipo, placa, capacidad_max_peso_kg, capacidad_max_vol_m3)
                VALUES (?, ?, ?, ?, ?)
            """, (codigo, tipo, placa.upper(), max_peso_kg, max_vol_m3))
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Código o placa duplicada


def update_vehiculo(vehiculo_id: int, tipo: str, placa: str,
                    max_peso_kg: float, max_vol_m3: float) -> bool:
    """Actualiza los datos de un vehículo existente."""
    with _get_conn() as conn:
        conn.execute("""
            UPDATE vehiculos
            SET tipo = ?, placa = ?, capacidad_max_peso_kg = ?, capacidad_max_vol_m3 = ?
            WHERE id = ?
        """, (tipo, placa.upper(), max_peso_kg, max_vol_m3, vehiculo_id))
        conn.commit()
    return True


def deactivate_vehiculo(vehiculo_id: int) -> bool:
    """Desactiva un vehículo (borrado lógico)."""
    with _get_conn() as conn:
        conn.execute("UPDATE vehiculos SET activo = 0 WHERE id = ?", (vehiculo_id,))
        conn.commit()
    return True


# ════════════════════════════════════════════════════════════
#  IMPORTACIÓN DESDE EXCEL (migración one-time)
# ════════════════════════════════════════════════════════════

def import_from_excel(excel_path: str) -> dict:
    """
    Importa materiales y vehículos desde el Excel de Ferretería.
    Hace UPSERT: inserta si no existe (por código), ignora si ya está.
    Retorna {'materiales': N, 'vehiculos': N} con las filas importadas.
    """
    import pandas as pd

    counts = {"materiales": 0, "vehiculos": 0}

    try:
        # --- Materiales ---
        df_mat = pd.read_excel(excel_path, sheet_name="Materiales")
        with _get_conn() as conn:
            for _, row in df_mat.iterrows():
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO materiales
                            (codigo, nombre, categoria, peso_unitario_kg, volumen_unitario_m3)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        str(row.get("ID_Producto", "")).strip(),
                        str(row.get("Nombre_Material", "")).strip(),
                        str(row.get("Categoria", "")).strip(),
                        float(row.get("Peso_Unitario (Kg)", 0) or 0),
                        float(row.get("Volumen_Unitario (m3)", 0) or 0),
                    ))
                    if conn.execute("SELECT changes()").fetchone()[0] > 0:
                        counts["materiales"] += 1
                except Exception as e:
                    print(f"[CATALOG] Error importando material: {e}")
            conn.commit()
    except Exception as e:
        print(f"[CATALOG] Error leyendo hoja Materiales del Excel: {e}")

    try:
        # --- Vehículos ---
        df_veh = pd.read_excel(excel_path, sheet_name="Vehiculos")
        with _get_conn() as conn:
            for _, row in df_veh.iterrows():
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO vehiculos
                            (codigo, tipo, placa, capacidad_max_peso_kg, capacidad_max_vol_m3)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        str(row.get("ID_Vehiculo", "")).strip(),
                        str(row.get("Tipo_Vehiculo", "")).strip(),
                        str(row.get("Placa", "")).strip().upper(),
                        float(row.get("Capacidad_Max_Peso (Kg)", 0) or 0),
                        float(row.get("Capacidad_Max_Volumen (m3)", 0) or 0),
                    ))
                    if conn.execute("SELECT changes()").fetchone()[0] > 0:
                        counts["vehiculos"] += 1
                except Exception as e:
                    print(f"[CATALOG] Error importando vehiculo: {e}")
            conn.commit()
    except Exception as e:
        print(f"[CATALOG] Error leyendo hoja Vehiculos del Excel: {e}")

    print(f"[CATALOG] Importación completada: {counts}")
    return counts
