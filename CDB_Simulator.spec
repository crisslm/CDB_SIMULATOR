# -*- mode: python ; coding: utf-8 -*-

# Especificação de build do CDB Simulator (Desktop .exe)
# Gera um executável único (--onefile) sem janela de console (--noconsole/console=False).

import sys

a = Analysis(
    ['main_gui.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        # CustomTkinter e Tkinter
        "customtkinter",
        "tkinter",
        "tkinter.font",
        "tkinter.ttk",
        # Matplotlib (gráficos)
        "matplotlib",
        "matplotlib.backends.backend_tkagg",
        "matplotlib.pyplot",
        "matplotlib.ticker",
        "matplotlib.font_manager",
        "matplotlib.colors",
        "numpy",  # dependência do matplotlib
        # NumPy 2.x + PyInstaller: módulos internos necessários pelo matplotlib
        "numpy._core._exceptions",
        "numpy._core.multiarray",
        "numpy._core.umath",
        "numpy._core._multiarray_umath",
        # Criptografia do banco financeiro
        "cryptography",
        "cryptography.fernet",
        # Variáveis de ambiente (.env)
        "dotenv",
        # Módulos próprios do projeto
        "src.domain.models",
        "src.domain.strategies",
        "src.services.simulator_service",
        "src.services.financial_service",
        "src.repositories.financial_repository",
        "src.repositories.db_encryption",
        "src.ui.gui.theme",
        "src.ui.gui.components",
        "src.ui.gui.chart",
        "src.ui.gui.app",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['src/runtime_hooks/fix_numpy_path.py'],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CDB_Simulator',
    icon='CDB_Simulator.ico',  # Ícone personalizado do executável
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Sem janela de terminal ao abrir o app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
