"""
Configuração centralizada da aplicação via variáveis de ambiente.
=================================================================

Carrega variáveis de ambiente do arquivo ``.env`` (se existir) e expõe
configurações tipadas para toda a aplicação.

Biblioteca utilizada: ``python-dotenv`` (já listada em ``requirements.txt``).

Exemplo de arquivo ``.env``:

    CDB_DB_ENCRYPTION_KEY=sua_chave_fernet_aqui
    CDB_APP_THEME=Light
    CDB_MAX_SIMULATION_MONTHS=1200
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv

    _DOTENV_AVAILABLE = True
except ImportError:  # pragma: no cover
    _DOTENV_AVAILABLE = False

# Caminho do arquivo .env na raiz do projeto
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

if _DOTENV_AVAILABLE and _ENV_PATH.exists():
    load_dotenv(dotenv_path=_ENV_PATH)


def _get_bool(key: str, default: bool = False) -> bool:
    """Lê uma variável de ambiente como booleano."""
    raw = os.getenv(key, str(default)).strip().lower()
    return raw in ("1", "true", "yes", "on", "sim")


def _get_int(key: str, default: int) -> int:
    """Lê uma variável de ambiente como inteiro."""
    try:
        return int(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


def _get_float(key: str, default: float) -> float:
    """Lê uma variável de ambiente como float."""
    try:
        return float(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


def _get_str(key: str, default: str) -> str:
    """Lê uma variável de ambiente como string."""
    return os.getenv(key, default)


# -------------------------------------------------------------------------
# Configurações da Aplicação
# -------------------------------------------------------------------------

APP_NAME: str = _get_str("CDB_APP_NAME", "CDB Simulator")
APP_VERSION: str = _get_str("CDB_APP_VERSION", "1.0.0")

THEME_DEFAULT: str = _get_str("CDB_APP_THEME", "Light")
THEME_FILE_NAME: str = _get_str("CDB_THEME_FILE_NAME", ".cdb_simulator_theme.json")

DB_DIR_NAME: str = _get_str("CDB_DB_DIR_NAME", ".cdb_simulator")
DB_FILE_NAME: str = _get_str("CDB_DB_FILE_NAME", "financial.sqlite3")
DB_KEY_FILE_NAME: str = _get_str("CDB_DB_KEY_FILE_NAME", ".db_key")
DB_ENCRYPTION_KEY: Optional[str] = _get_str("CDB_DB_ENCRYPTION_KEY", None)

# -------------------------------------------------------------------------
# Segurança do Simulador
# -------------------------------------------------------------------------

MAX_SIMULATION_MONTHS: int = _get_int("CDB_MAX_SIMULATION_MONTHS", 1200)
MAX_SIMULATION_BALANCE: float = _get_float("CDB_MAX_SIMULATION_BALANCE", 10_000_000_000_000.0)

# -------------------------------------------------------------------------
# Limites de Entrada da UI
# -------------------------------------------------------------------------

LIMITE_MONETARIO: float = _get_float("CDB_LIMITE_MONETARIO", 1_000_000_000_000.0)
TAXA_JUROS_MAX: float = _get_float("CDB_TAXA_JUROS_MAX", 100.0)
CDI_PERCENTUAL_MAX: float = _get_float("CDB_CDI_PERCENTUAL_MAX", 500.0)
CDI_BASE_MAX: float = _get_float("CDB_CDI_BASE_MAX", 100.0)
