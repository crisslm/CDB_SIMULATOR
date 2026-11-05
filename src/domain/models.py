"""
Camada de Domínio - Entidades e Modelos de Dados
Contém classes puras de dados (dataclasses) para entrada e saída das simulações.
Princípio SOLID: Single Responsibility Principle (SRP)
"""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


def calcular_aliquota_ir(dias: int) -> float:
    """
    Retorna a alíquota regressiva do Imposto de Renda para renda fixa (CDB):
    - Até 180 dias: 22.5%
    - De 181 a 360 dias: 20.0%
    - De 361 a 720 dias: 17.5%
    - Acima de 720 dias: 15.0%
    """
    if dias <= 180:
        return 0.225
    elif dias <= 360:
        return 0.20
    elif dias <= 720:
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
    start_date: Optional[date] = None
    end_date: Optional[date] = None


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
    truncado: bool = False
