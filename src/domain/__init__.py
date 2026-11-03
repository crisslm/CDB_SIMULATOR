"""
Inicializador da camada de domínio.
"""

from src.domain.models import MonthlyRecord, SimulationParams, SimulationResult
from src.domain.strategies import YieldStrategy, CompoundInterestStrategy, CDIStrategy
from src.domain.financial_models import FinancialCategory, FinancialSummary, FinancialTransaction, TransactionType

__all__ = [
    "MonthlyRecord",
    "SimulationParams",
    "SimulationResult",
    "YieldStrategy",
    "CompoundInterestStrategy",
    "CDIStrategy",
    "FinancialCategory",
    "FinancialSummary",
    "FinancialTransaction",
    "TransactionType",
]
