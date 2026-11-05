"""
Constantes centralizadas de negócio e segurança do CDB Simulator.
===============================================================

Este módulo concentra valores que antes estavam espalhados por
várias camadas (serviços, estratégias, UI), evitando duplicação
e facilitando a manutenção.

Princípio: Single Source of Truth.
"""

from decimal import Decimal

# -------------------------------------------------------------------------
# Segurança do Simulador
# -------------------------------------------------------------------------

# Limite máximo de segurança para períodos (100 anos = 1200 meses).
# Evita exaustão de memória (ataque DoS) com períodos absurdos.
MAX_SIMULATION_MONTHS: int = 1200

# Limite máximo de saldo simulado (10 trilhões de reais).
# Impede valores exorbitantes com taxas altas que causariam estouro
# de precisão do Decimal (InvalidOperation).
MAX_SIMULATION_BALANCE: Decimal = Decimal("10000000000000")  # 10 trilhões

# Tolerância para comparação de taxa com zero (evita erro de ponto flutuante).
# Valores absolutos menores que este são considerados zero.
ZERO_TOLERANCE: float = 1e-12

# -------------------------------------------------------------------------
# Limites de entrada da UI
# -------------------------------------------------------------------------

# Limite monetário de segurança para campos de entrada (1 trilhão de reais).
LIMITE_MONETARIO: float = 1_000_000_000_000.0

# Limites de taxa percentual (UI)
TAXA_JUROS_MIN: float = 0.0
TAXA_JUROS_MAX: float = 100.0   # 0–100% para juros prefixados
CDI_PERCENTUAL_MIN: float = 0.0
CDI_PERCENTUAL_MAX: float = 500.0  # 0–500% para % do CDI
CDI_BASE_MIN: float = 0.0
CDI_BASE_MAX: float = 100.0   # 0–100% para taxa base do CDI

# -------------------------------------------------------------------------
# Imposto de Renda (dias corridos)
# -------------------------------------------------------------------------

IR_FAIXA_1_DIAS: int = 180   # até 180 dias -> 22,5%
IR_FAIXA_2_DIAS: int = 360   # 181 a 360 dias -> 20,0%
IR_FAIXA_3_DIAS: int = 720   # 361 a 720 dias -> 17,5%
# acima de 720 dias -> 15,0%

# -------------------------------------------------------------------------
# Configuração de temas
# -------------------------------------------------------------------------

THEME_FILE_NAME: str = ".cdb_simulator_theme.json"
DB_DIR_NAME: str = ".cdb_simulator"
DB_FILE_NAME: str = "financial.sqlite3"
DB_KEY_FILE_NAME: str = ".db_key"

# -------------------------------------------------------------------------
# Validação de campos financeiros
# -------------------------------------------------------------------------

CATEGORY_NAME_MAX_LEN: int = 120
TRANSACTION_DESCRIPTION_MAX_LEN: int = 120
TRANSACTION_NOTES_MAX_LEN: int = 1000
