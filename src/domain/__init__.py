"""
Inicializador da camada de domínio.
"""

from .models import MonthlyRecord, SimulationParams, SimulationResult
from .strategies import YieldStrategy, CompoundInterestStrategy, CDIStrategy
from .financial_models import FinancialCategory, FinancialSummary, FinancialTransaction, TransactionType

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
