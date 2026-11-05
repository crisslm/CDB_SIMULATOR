"""
Camada de Casos de Uso (Use Cases) — CDB Simulator.
====================================================

Orquestram a execução de regras de negócio entre a Interface (UI)
e as camadas de Serviço / Domínio / Repositório.

Cada caso de uso representa uma ação do usuário (ex: simular um
investimento, criar uma transação financeira) e encapsula:

    1. Validação de entrada (DTO -> parâmetros validados)
    2. Chamada ao serviço apropriado
    3. Retorno de resultado para a UI

Princípio: Separação de preocupações — a UI não conhece a lógica de
negócio, apenas chama casos de uso e exibe resultados.
"""

from .simulate_investment import SimulateInvestmentUseCase
from .financial_use_cases import FinancialUseCases

__all__ = ["SimulateInvestmentUseCase", "FinancialUseCases"]
