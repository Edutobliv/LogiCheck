# core/create_db.py
# ============================================================
#  LogiCheck — Script de inicialización / reset de la BD
#  Ejecutar directamente: python core/create_db.py
#  También importa los datos del Excel si existe.
# ============================================================

import os
import sys

# Asegurar que el directorio raíz del proyecto esté en el path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main():
    print("=" * 55)
    print("  LogiCheck — Inicializador de Base de Datos")
    print("=" * 55)

    # 1. Ejecutar migraciones
    print("\n[1/3] Ejecutando migraciones de esquema...")
    from core.db_migrations import run_migrations
    run_migrations()

    # 2. Inicializar usuarios por defecto
    print("\n[2/3] Verificando usuarios por defecto...")
    from core.auth import init_db
    init_db()

    # 3. Importar datos del Excel si existe
    excel_path = os.path.join(os.path.dirname(__file__), "..", "BaseDatos_Ferreteria.xlsx")
    if os.path.exists(excel_path):
        print(f"\n[3/3] Importando datos desde Excel: {excel_path}")
        from core.catalog_store import import_from_excel
        counts = import_from_excel(excel_path)
        print(f"      Materiales importados: {counts['materiales']}")
        print(f"      Vehiculos importados:  {counts['vehiculos']}")
    else:
        print("\n[3/3] Excel no encontrado. Usando datos base de migraciones.")

    print("\n" + "=" * 55)
    print("  Base de datos lista.")
    print("=" * 55)


if __name__ == "__main__":
    main()
