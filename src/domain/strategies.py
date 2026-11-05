"""
Camada de Domínio - Estratégias de Rendimento (Yield Strategies)
================================================================

Este módulo define o contrato abstrato e as implementações concretas para
cálculo de taxas de rendimento de diferentes tipos de investimento.

Princípios SOLID aplicados:

1. Open/Closed Principle (OCP):
   - Aberto para criar novos tipos de investimento (IPCA+, LCI, etc.)
   - Fechado para modificação do código existente.

2. Liskov Substitution Principle (LSP):
   - Qualquer subclasse de YieldStrategy pode ser usada intercambiavelmente.

3. Interface Segregation Principle (ISP):
   - Contrato enxuto: apenas get_monthly_rate() e get_description().

4. Dependency Inversion Principle (DIP):
   - Os serviços dependem da abstração YieldStrategy, não de classes concretas.

Autor: CDB Simulator
Versão: 1.0.0
"""

from abc import ABC, abstractmethod

# Tolerância para comparação de taxa com zero (evita erro de ponto flutuante)
# Valores menores que este são considerados zero.
ZERO_TOLERANCE = 1e-12


class YieldStrategy(ABC):
    """
    Interface abstrata / contrato para cálculo de taxa de rendimento mensal.

    Qualquer novo tipo de investimento deve estender esta classe e implementar
    os dois métodos abstratos.

    Métodos abstratos:
        get_monthly_rate(): Retorna a taxa mensal em decimal (ex: 0.01 = 1% a.m.)
        get_description():  Retorna texto descritivo para exibição na UI.

    Exemplo de criação de nova estratégia:
        class IPCAplusStrategy(YieldStrategy):
            def get_monthly_rate(self) -> float:
                return 0.005  # 0,5% a.m. exemplo
            def get_description(self) -> str:
                return "IPCA + 0,5% a.a."
    """

    @abstractmethod
    def get_monthly_rate(self) -> float:
        """
        Retorna a taxa de juros mensal em formato decimal.

        Exemplo:
            - 1% ao mês  -> retorna 0.01
            - 12% ao ano -> retorna ~0.00949 (taxa equivalente composta)

        Retorna:
            float: Taxa mensal decimal.
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """
        Retorna um texto descritivo da estratégia para exibição na interface.

        Exemplo:
            "Taxa Prefixada de 12,00% a.a. (equivalente)"
            "CDB 110,0% do CDI (CDI base: 10,75% a.a.)"

        Retorna:
            str: Descrição legível.
        """
        pass


class CompoundInterestStrategy(YieldStrategy):
    """
    Estratégia de juros compostos com taxa fixa (prefixada).

    Suporta duas formas de conversão de taxa anual para mensal:

    1. Taxa equivalente composta (recomendada):
       i_mensal = (1 + i_anual)^(1/12) - 1
       Esta é a forma matematicamente correta para capitalização mensal.

    2. Taxa nominal simples (proporcional):
       i_mensal = i_anual / 12
       Mais simples, mas menos precisa para longos períodos.

    Atributos:
        rate_percent (float): Taxa percentual (ex: 12.0 para 12%).
        is_annual (bool): Se True, rate_percent é anual. Se False, é mensal.
        use_effective_rate (bool): Se True, usa taxa equivalente composta.
                                   Se False, usa taxa nominal proporcional.

    Exemplo de uso:
        # 12% ao ano, taxa equivalente composta
        strat = CompoundInterestStrategy(rate_percent=12.0, is_annual=True, use_effective_rate=True)
        mensal = strat.get_monthly_rate()  # ~0.00949

        # 1% ao mês direto
        strat = CompoundInterestStrategy(rate_percent=1.0, is_annual=False)
        mensal = strat.get_monthly_rate()  # 0.01
    """

    def __init__(self, rate_percent: float, is_annual: bool = True, use_effective_rate: bool = True):
        self.rate_percent = rate_percent
        self.is_annual = is_annual
        self.use_effective_rate = use_effective_rate

    def get_monthly_rate(self) -> float:
        """
        Calcula e retorna a taxa de rendimento mensal em decimal.

        Se is_annual for False, retorna rate_percent/100 diretamente.
        Se is_annual for True:
          - Se use_effective_rate: (1 + r)^(1/12) - 1
          - Se não: r / 12

        Proteção contra taxa anual <= -100% (evita raiz de número negativo).

        Retorna:
            float: Taxa mensal em decimal (ex: 0.01 para 1% a.m.).
        """
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
        """
        Retorna descrição legível da estratégia de taxa prefixada.

        Retorna:
            str: Ex: "Taxa Prefixada de 12,00% a.a. (equivalente)"
        """
        periodo = "a.a." if self.is_annual else "a.m."
        tipo = "equivalente" if (self.is_annual and self.use_effective_rate) else "nominal"
        return f"Taxa Prefixada de {self.rate_percent:.2f}% {periodo} ({tipo})"


class CDIStrategy(YieldStrategy):
    """
    Estratégia para CDBs pós-fixados baseados em percentual do CDI.

    O CDI (Certificado de Depósito Interbancário) é a taxa de referência do
    mercado brasileiro. CDBs são frequentemente negociados como percentual do CDI
    (ex: 100% do CDI, 110% do CDI, 120% do CDI).

    Fórmula:
        taxa_anual_efetiva = cdi_annual_rate * (cdi_percentage / 100) / 100
        taxa_mensal = (1 + taxa_anual_efetiva)^(1/12) - 1  (se use_effective_rate)

    Atributos:
        cdi_percentage (float): Percentual do CDI (ex: 110 para 110% do CDI).
        cdi_annual_rate (float): Taxa anual do CDI base (ex: 10.75 para 10,75% a.a.).
        use_effective_rate (bool): Se True, usa taxa equivalente composta.

    Exemplo de uso:
        # 110% do CDI com CDI base a 10,75% a.a.
        strat = CDIStrategy(cdi_percentage=110.0, cdi_annual_rate=10.75, use_effective_rate=True)
        mensal = strat.get_monthly_rate()
    """

    def __init__(self, cdi_percentage: float, cdi_annual_rate: float = 10.75, use_effective_rate: bool = True):
        """
        Inicializa a estratégia CDI.

        Parâmetros:
            cdi_percentage: Ex: 100 para 100%, 110 para 110%, 120 para 120%.
            cdi_annual_rate: Taxa anual do CDI base (padrão: 10.75%).
            use_effective_rate: Se True, usa conversão equivalente composta.
        """
        self.cdi_percentage = cdi_percentage
        self.cdi_annual_rate = cdi_annual_rate
        self.use_effective_rate = use_effective_rate

    def get_monthly_rate(self) -> float:
        """
        Calcula a taxa mensal baseada no percentual do CDI.

        Passos:
            1. Calcula taxa anual efetiva: CDI_base * (percentual / 100) / 100
            2. Converte para mensal (equivalente composta ou nominal).

        Proteção contra taxa anual <= -100%.

        Retorna:
            float: Taxa mensal em decimal.
        """
        taxa_anual_efetiva = (self.cdi_annual_rate * (self.cdi_percentage / 100.0)) / 100.0
        if self.use_effective_rate:
            if taxa_anual_efetiva <= -1.0:
                return -1.0
            return ((1.0 + taxa_anual_efetiva) ** (1.0 / 12.0)) - 1.0
        else:
            return taxa_anual_efetiva / 12.0

    def get_description(self) -> str:
        """
        Retorna descrição legível da estratégia CDI.

        Retorna:
            str: Ex: "CDB 110,0% do CDI (CDI base: 10,75% a.a.)"
        """
        return f"CDB {self.cdi_percentage:.1f}% do CDI (CDI base: {self.cdi_annual_rate:.2f}% a.a.)"