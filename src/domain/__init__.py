"""
Inicializador da camada de domínio.
"""

from src.domain.models import MonthlyRecord, SimulationParams, SimulationResult
from src.domain.strategies import YieldStrategy, CompoundInterestStrategy, CDIStrategy

__all__ = [
    "MonthlyRecord",
    "SimulationParams",
    "SimulationResult",
    "YieldStrategy",
    "CompoundInterestStrategy",
    "CDIStrategy",
]
