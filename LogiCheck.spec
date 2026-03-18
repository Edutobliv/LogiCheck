# LogiCheck v1.2 — PyInstaller spec file

import os
from pathlib import Path

project_dir = os.path.abspath('.')

a = Analysis(
    ['main.py'],
    pathex=[project_dir],
    binaries=[],
    datas=[
        # Recursos de styles
        ('resources/style.qss',       'resources'),
        ('resources/style_light.qss', 'resources'),
        # Módulos del core (PyInstaller los detecta, pero los mantenemos si se usan dinámicamente)
        ('core/__init__.py',          'core'),
        ('core/invoice_parser.py',    'core'),
        ('core/auth.py',              'core'),
        ('core/permissions.py',       'core'),
        ('core/logger.py',            'core'),
        ('core/yolo_manager.py',      'core'),
        # Módulos de la UI
        ('ui/__init__.py',            'ui'),
        ('ui/login_dialog.py',        'ui'),
        ('ui/users_page.py',          'ui'),
        ('ui/logs_page.py',           'ui'),
        ('ui/splash_screen.py',       'ui'),
        ('ui/main_window.py',         'ui'),
        # Modelos YOLO
        ('training/runs/bultos_cemento/weights/best.pt', 'training/runs/bultos_cemento/weights'),
        ('training/runs/bultos_cemento2/weights/best.pt', 'training/runs/bultos_cemento2/weights'),
        ('yolo11n.pt', '.'),
        ('yolo26n.pt', '.'),
        # Base de datos y Excel
        ('BaseDatos_Ferreteria.xlsx', '.'),
        ('logicheck_users.db', '.'),
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtSvg',
        'fitz',           # PyMuPDF
        'openpyxl',
        'pandas',
        'sqlite3',        # Base de datos de usuarios
        'hashlib',
        'ultralytics',
        'torch',
        'torchvision',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'notebook',
        'IPython',
        'tkinter',
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LogiCheck',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,              # Desactivado ya que no está instalado
    console=False,          # Sin ventana de consola
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='LogiCheck',
)
