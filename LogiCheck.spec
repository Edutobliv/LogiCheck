# -*- mode: python ; coding: utf-8 -*-
# LogiCheck v1.1 — PyInstaller spec file

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
        # Módulos del core
        ('core/__init__.py',          'core'),
        ('core/invoice_parser.py',    'core'),
        ('core/auth.py',              'core'),
        ('core/permissions.py',       'core'),
        ('core/logger.py',            'core'),
        # Módulos de la UI
        ('ui/__init__.py',            'ui'),
        ('ui/login_dialog.py',        'ui'),
        ('ui/users_page.py',          'ui'),
        ('ui/logs_page.py',           'ui'),
        # Base de datos Excel (referencia materiales/vehículos)
        ('BaseDatos_Ferreteria.xlsx', '.'),
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
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'ultralytics',   # YOLO — excluir por ahora (versión beta)
        'cv2',           # OpenCV — excluir por ahora
        'torch',
        'torchvision',
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
    upx=True,
    console=False,          # Sin ventana de consola
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # Puedes agregar un .ico aquí cuando tengas uno
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LogiCheck',
)
