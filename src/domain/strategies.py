"""
Camada de Domínio - Estratégias de Rendimento (Yield Strategies)
Princípios SOLID:
 - Open/Closed Principle (OCP): Aberto para novos tipos de investimento sem modificar código existente.
 - Liskov Substitution Principle (LSP): Qualquer subclasse de YieldStrategy pode ser usada intercambiavelmente.
 - Interface Segregation Principle (ISP): Contrato enxuto e focado no cálculo da taxa.
"""

from abc import ABC, abstractmethod


class YieldStrategy(ABC):
    """
    Interface base / contrato abstrato para cálculo de rendimento.
    Permite criar estratégias para Juros Compostos fixos, % CDI, IPCA+, etc.
    """

    @abstractmethod
    def get_monthly_rate(self) -> float:
        """
        Retorna a taxa de juros mensal em formato decimal (ex: 1% -> 0.01).
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """
        Retorna um texto descritivo da estratégia (ex: 'Taxa fixa: 12.0% a.a.').
        """
        pass


class CompoundInterestStrategy(YieldStrategy):
    """
    Estratégia clássica de taxa fixa (prefixada), expressa ao ano ou ao mês.
    Suporta cálculo pela taxa equivalente composta: (1 + i)^(1/12) - 1,
    ou nominal: i / 12.
    """

    def __init__(self, rate_percent: float, is_annual: bool = True, use_effective_rate: bool = True):
        self.rate_percent = rate_percent
        self.is_annual = is_annual
        self.use_effective_rate = use_effective_rate

    def get_monthly_rate(self) -> float:
        if not self.is_annual:
            return (self.rate_percent / 100.0)

        r_annual = self.rate_percent / 100.0
        if self.use_effective_rate:
            # Taxa equivalente composta: (1 + i_ano)^(1/12) - 1
            if r_annual <= -1.0:
                return -1.0
            return ((1.0 + r_annual) ** (1.0 / 12.0)) - 1.0
        else:
            # Conversão nominal simples (proporcional)
            return (r_annual / 12.0)

    def get_description(self) -> str:
        periodo = "a.a." if self.is_annual else "a.m."
        tipo = "equivalente" if (self.is_annual and self.use_effective_rate) else "nominal"
        return f"Taxa Prefixada de {self.rate_percent:.2f}% {periodo} ({tipo})"


class CDIStrategy(YieldStrategy):
    """
    Estratégia para CDBs pós-fixados baseados em percentual do CDI (ex: 110% do CDI).
    Utiliza taxa equivalente composta para conversão anual para mensal.
    """

    def __init__(self, cdi_percentage: float, cdi_annual_rate: float = 10.75, use_effective_rate: bool = True):
        """
        :param cdi_percentage: Ex: 100 para 100% do CDI, 110 para 110% do CDI.
        :param cdi_annual_rate: Taxa anual do CDI (ex: 10.75% ao ano).
        :param use_effective_rate: Se True, calcula a taxa mensal equivalente composta.
        """
        self.cdi_percentage = cdi_percentage
        self.cdi_annual_rate = cdi_annual_rate
        self.use_effective_rate = use_effective_rate

    def get_monthly_rate(self) -> float:
        taxa_anual_efetiva = (self.cdi_annual_rate * (self.cdi_percentage / 100.0)) / 100.0
        if self.use_effective_rate:
            if taxa_anual_efetiva <= -1.0:
                return -1.0
            return ((1.0 + taxa_anual_efetiva) ** (1.0 / 12.0)) - 1.0
        else:
            return taxa_anual_efetiva / 12.0

    def get_description(self) -> str:
        return f"CDB {self.cdi_percentage:.1f}% do CDI (CDI base: {self.cdi_annual_rate:.2f}% a.a.)"
