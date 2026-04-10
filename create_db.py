# create_db.py  (raíz del proyecto)
# ============================================================
#  LogiCheck — Punto de entrada para inicializar la BD
#  Ejecutar: python create_db.py
# ============================================================

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))


def main():
    from core.create_db import main as _main
    _main()


if __name__ == "__main__":
    main()
