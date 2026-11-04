"""
Runtime hook para corrigir problema do NumPy com PyInstaller.

Evita que o NumPy seja importado do diretório de fonte (source tree)
em vez da instalação compilada, o que causa:
    ModuleNotFoundError: No module named 'numpy._core._exceptions'
"""

import os
import sys


def _remove_numpy_source_paths():
    """Remove do sys.path qualquer caminho que aponte para o diretório de fonte do NumPy."""
    filtered = []
    for p in sys.path:
        base = os.path.basename(p).lower()
        if "numpy" in base:
            continue
        filtered.append(p)
    sys.path[:] = filtered


_remove_numpy_source_paths()
