"""
Configuração global do pytest para o CDB Simulator.

Garante que o pacote src esteja disponível no sys.path para todos os testes.
"""

import sys
from pathlib import Path

# Adiciona a raiz do projeto ao sys.path para imports absolutos funcionarem
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
