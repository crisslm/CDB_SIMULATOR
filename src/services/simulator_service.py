"""
Camada de Serviços - Simulador de Investimentos (CDB / Juros Compostos)
=======================================================================

Este módulo implementa o motor de simulação financeira para projeção de
patrimônio com juros compostos, aportes mensais e cálculo de Imposto de Renda.

Princípios SOLID aplicados:

1. Dependency Inversion Principle (DIP):
   - Depende da abstração YieldStrategy, não de classes concretas.

2. Single Responsibility Principle (SRP):
   - Focado unicamente na regra de evolução temporal e metas financeiras.

Constantes de negócio são importadas de src.domain.constants (single source of truth).
"""

import math
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from ..domain.constants import MAX_SIMULATION_BALANCE, MAX_SIMULATION_MONTHS, ZERO_TOLERANCE
from ..domain.models import (
    SimulationParams,
    SimulationResult,
    MonthlyRecord,
    calcular_aliquota_ir,
)
from ..domain.strategies import YieldStrategy


# Tolerância para comparação de taxa com zero (evita erro de ponto flutuante).
# Valores absolutos menores que este são considerados zero.
ZERO_TOLERANCE = ZERO_TOLERANCE  # reexportado para compatibilidade com testes existentes

# Limite máximo de segurança para períodos (100 anos = 1200 meses).
# Evita exaustão de memória (ataque DoS) com períodos absurdos.
MAX_SIMULATION_MONTHS = MAX_SIMULATION_MONTHS  # reexportado para compatibilidade com testes existentes

# Limite máximo de saldo simulado (10 trilhões de reais).
# Impede valores exorbitantes com taxas altas (ex: 50% a.m. por 100 anos)
# que causariam estouro de precisão do Decimal (InvalidOperation).
MAX_SIMULATION_BALANCE = MAX_SIMULATION_BALANCE  # reexportado para compatibilidade com testes existentes


class InvestmentSimulatorService:
    """
    Serviço responsável por coordenar a simulação de investimento e projeções.

    Este serviço encapsula toda a lógica de negócio do simulador de CDB,
    incluindo evolução patrimonial mês a mês, cálculo de IR regressivo e
    projeção analítica de metas financeiras.

    Atributos:
        Nenhum atributo de instância significativo (métodos são estateless
        em relação à configuração, exceto as constantes de classe).

    Exemplo de uso:
        service = InvestmentSimulatorService()
        strategy = CompoundInterestStrategy(rate_percent=12.0, is_annual=True)
        params = SimulationParams(initial_amount=5000, monthly_contribution=500, total_months=60)
        result = service.simulate(params, strategy)
        print(f"Saldo final: R$ {result.final_balance:,.2f}")
    """

    def _D(self, valor) -> Decimal:
        """
        Converte qualquer valor para Decimal com precisão de 2 casas decimais.

        Usado internamente para garantir que todos os cálculos monetários
        usem Decimal em vez de float, evitando erros de ponto flutuante.

        Parâmetros:
            valor: Qualquer valor numérico ou string.

        Retorna:
            Decimal: Valor arredondado para 2 casas decimais.
        """
        return Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def simulate(self, params: SimulationParams, strategy: YieldStrategy) -> SimulationResult:
        """
        Executa a simulação completa de investimento mês a mês.

        Fluxo para cada mês:
            1. Adiciona aporte mensal ao saldo (início do ciclo).
            2. Calcula rendimento = saldo_provisorio * taxa_mensal.
            3. Adiciona rendimento ao saldo.
            4. Registra no timeline.

        Após o loop, calcula:
            - Total de rendimentos brutos.
            - Imposto de Renda regressivo (baseado em dias reais ou meses*30).
            - Saldo líquido (após IR).
            - Tempo até atingir a meta (análise O(1) com fallback iterativo).

        Proteções:
            - total_months limitado a MAX_SIMULATION_MONTHS (anti-DoS).
            - current_balance limitado a MAX_SIMULATION_BALANCE (evita estouro).
            - Validação de parâmetros negativos.

        Parâmetros:
            params (SimulationParams): Parâmetros de entrada (valor, aporte, meses, meta).
            strategy (YieldStrategy): Estratégia de rendimento (prefixado ou CDI).

        Retorna:
            SimulationResult: Resultado completo com bruto, líquido, IR e timeline.

        Levanta:
            ValueError: Se total_months < 0, ou se o saldo projetado exceder
                        MAX_SIMULATION_BALANCE.
        """
        if params.total_months < 0:
            raise ValueError("O período de meses não pode ser negativo.")

        # Aplica limite de segurança para evitar exaustão de memória (DoS)
        total_months = min(params.total_months, MAX_SIMULATION_MONTHS)
        truncado = total_months < params.total_months

        # Converte taxa e valores iniciais para Decimal
        monthly_rate = self._D(strategy.get_monthly_rate())
        current_balance = self._D(params.initial_amount)
        total_invested = self._D(params.initial_amount)
        timeline = []

        # Loop de simulação mês a mês
        for month in range(1, total_months + 1):
            # Aporte ocorre no início do ciclo de capitalização mensal
            current_balance += self._D(params.monthly_contribution)
            total_invested += self._D(params.monthly_contribution)

            # Rendimento sobre o saldo total (arredondado a cada mês)
            interest_month = (current_balance * monthly_rate).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            current_balance += interest_month

            # Verifica limite de segurança para evitar estouro de Decimal
            if current_balance > MAX_SIMULATION_BALANCE:
                raise ValueError(
                    f"O montante projetado excede o limite de R$ "
                    f"{MAX_SIMULATION_BALANCE:,.2f} (10 trilhões). "
                    f"Reduza a taxa de rendimento, o prazo ou o valor inicial."
                )

            record = MonthlyRecord(
                month=month,
                invested_to_date=float(total_invested),
                interest_earned_month=float(interest_month),
                total_balance=float(current_balance)
            )
            timeline.append(record)

        # Total de rendimentos brutos (garante não negativo)
        total_interest = max(Decimal("0.0"), current_balance - total_invested)

        # Calcula tempo até atingir a meta (análise O(1) com fallback iterativo)
        months_to_target = self.calculate_months_to_target(params, strategy)

        # =====================================================================
        # Cálculo do Imposto de Renda regressivo (CDB / Renda Fixa)
        # =====================================================================
        # Usa dias reais entre start_date e end_date quando fornecidos;
        # caso contrário, mantém a aproximação meses * 30 como fallback.
        if params.start_date and params.end_date:
            dias_ir = (params.end_date - params.start_date).days
        else:
            dias_ir = total_months * 30

        ir_aliquota = calcular_aliquota_ir(dias_ir)
        ir_total = (total_interest * Decimal(str(ir_aliquota))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        net_interest = total_interest - ir_total
        net_balance = total_invested + net_interest

        return SimulationResult(
            total_invested=float(total_invested),
            total_interest=float(total_interest),
            final_balance=float(current_balance),
            total_months=total_months,
            months_to_target=months_to_target,
            ir_aliquota=float(ir_aliquota),
            ir_total=float(ir_total),
            net_interest=float(net_interest),
            net_balance=float(net_balance),
            timeline=timeline,
            truncado=truncado,
        )

    def calculate_months_to_target(
        self,
        params: SimulationParams,
        strategy: YieldStrategy,
        max_months: int = MAX_SIMULATION_MONTHS,
    ) -> Optional[int]:
        """
        Calcula o número de meses necessários para atingir a meta financeira.

        Usa resolução analítica O(1) baseada na fórmula de anuidade com
        aportes antecipados:

            B_n = PV*(1+r)^n + PMT*(1+r)*[((1+r)^n - 1) / r]
            n = ceil( ln((FV + k) / (PV + k)) / ln(1 + r) )
            onde k = PMT*(1+r) / r

        Se a fórmula analítica falhar, usa fallback iterativo (loop seguro).

        Parâmetros:
            params (SimulationParams): Parâmetros da simulação.
            strategy (YieldStrategy): Estratégia de rendimento.
            max_months (int): Limite máximo de meses para busca (padrão: 1200).

        Retorna:
            Optional[int]:
                - 0 se já atingiu a meta com o valor inicial.
                - N (int) se é possível atingir em N meses.
                - None se for inalcançável dentro de max_months.

        Casos especiais tratados:
            - target_amount <= 0: retorna None.
            - Taxa zero e aporte zero: retorna None (inalcançável).
            - Taxa negativa sem aporte suficiente: retorna None.
        """
        if params.target_amount <= 0:
            return None

        # Já começou na meta ou acima
        if params.initial_amount >= params.target_amount:
            return 0

        monthly_rate = strategy.get_monthly_rate()

        # Sem juros nem aportes (usa tolerância para evitar erro de float)
        if abs(monthly_rate) < ZERO_TOLERANCE and params.monthly_contribution <= 0:
            return None

        # Sem juros: acumulação puramente linear de aportes
        if abs(monthly_rate) < ZERO_TOLERANCE:
            meses = math.ceil((params.target_amount - params.initial_amount) / params.monthly_contribution)
            return meses if meses <= max_months else None

        # Se taxa for negativa e não houver aporte, nunca alcança
        if monthly_rate < 0 and params.monthly_contribution <= 0:
            return None

        # =====================================================================
        # Resolução analítica direta (O(1))
        # =====================================================================
        r = monthly_rate
        pmt = params.monthly_contribution
        pv = params.initial_amount
        fv = params.target_amount

        try:
            k = pmt * (1.0 + r) / r
            numerador = fv + k
            denominador = pv + k

            if numerador > 0 and denominador > 0 and (1.0 + r) > 0 and r != 0:
                razao = numerador / denominador
                if razao > 0:
                    n_analitico = math.log(razao) / math.log(1.0 + r)
                    meses_calculados = math.ceil(n_analitico)
                    if 0 <= meses_calculados <= max_months:
                        return meses_calculados
                    elif meses_calculados > max_months:
                        return None
        except (ValueError, ZeroDivisionError, OverflowError):
            pass

        # =====================================================================
        # Fallback iterativo determinístico (segurança)
        # =====================================================================
        balance = pv
        months = 0
        while balance < fv and months < max_months:
            balance += pmt
            balance += balance * r
            months += 1

        if balance >= fv:
            return months
        return None
