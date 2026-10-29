"""
Camada de Domínio - Entidades e Modelos de Dados
Contém classes puras de dados (dataclasses) para entrada e saída das simulações.
Princípio SOLID: Single Responsibility Principle (SRP)
"""

from dataclasses import dataclass, field
from typing import List, Optional


def calcular_aliquota_ir(meses: int) -> float:
    """
    Retorna a alíquota regressiva do Imposto de Renda para renda fixa (CDB):
    - Até 180 dias (aprox. até 6 meses): 22.5%
    - De 181 a 360 dias (aprox. de 7 a 12 meses): 20.0%
    - De 361 a 720 dias (aprox. de 13 a 24 meses): 17.5%
    - Acima de 720 dias (mais de 24 meses): 15.0%
    """
    if meses <= 6:
        return 0.225
    elif meses <= 12:
        return 0.20
    elif meses <= 24:
        return 0.175
    else:
        return 0.15


@dataclass(frozen=True)
class MonthlyRecord:
    """
    Representa a 'fotografia' financeira de um mês específico da simulação.
    """
    month: int
    invested_to_date: float
    interest_earned_month: float
    total_balance: float


@dataclass(frozen=True)
class SimulationParams:
    """
    Parâmetros imutáveis de entrada necessários para executar uma simulação.
    """
    initial_amount: float
    monthly_contribution: float
    total_months: int
    target_amount: float = 1_000_000.0


@dataclass(frozen=True)
class SimulationResult:
    """
    Resultado consolidado da simulação após o término do período (bruto e líquido de IR).
    """
    total_invested: float
    total_interest: float
    final_balance: float
    total_months: int
    months_to_target: Optional[int]
    ir_aliquota: float = 0.15
    ir_total: float = 0.0
    net_interest: float = 0.0
    net_balance: float = 0.0
    timeline: List[MonthlyRecord] = field(default_factory=list)
