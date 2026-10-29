"""
Camada de Serviços - Orquestrador da Simulação Financeira
Princípios SOLID:
 - Dependency Inversion Principle (DIP): O serviço depende da abstração YieldStrategy, e não de classes concretas.
 - Single Responsibility Principle (SRP): Focado unicamente na regra de evolução temporal e metas financeiras.
"""

import math
from typing import Optional
from src.domain.models import (
    SimulationParams, 
    SimulationResult, 
    MonthlyRecord, 
    calcular_aliquota_ir
)
from src.domain.strategies import YieldStrategy

# Limite máximo de segurança para períodos (100 anos = 1200 meses)
MAX_SIMULATION_MONTHS = 1200


class InvestmentSimulatorService:
    """
    Serviço responsável por coordenar a simulação do plano de investimento e projeções.
    """

    def simulate(self, params: SimulationParams, strategy: YieldStrategy) -> SimulationResult:
        """
        Executa a evolução patrimonial mês a mês com base nos parâmetros e na estratégia de rendimento.
        Protegido com limite máximo de meses para evitar exaustão de memória (DoS).
        """
        if params.total_months < 0:
            raise ValueError("O período de meses não pode ser negativo.")

        total_months = min(params.total_months, MAX_SIMULATION_MONTHS)
        monthly_rate = strategy.get_monthly_rate()
        current_balance = params.initial_amount
        total_invested = params.initial_amount
        timeline = []

        for month in range(1, total_months + 1):
            # Aporte ocorre no início do ciclo de capitalização mensal
            current_balance += params.monthly_contribution
            total_invested += params.monthly_contribution

            # Rendimento sobre o saldo total
            interest_month = current_balance * monthly_rate
            current_balance += interest_month

            record = MonthlyRecord(
                month=month,
                invested_to_date=round(total_invested, 2),
                interest_earned_month=round(interest_month, 2),
                total_balance=round(current_balance, 2)
            )
            timeline.append(record)

        total_interest = max(0.0, current_balance - total_invested)
        months_to_target = self.calculate_months_to_target(params, strategy)

        # Cálculo do Imposto de Renda regressivo (CDB / Renda Fixa)
        ir_aliquota = calcular_aliquota_ir(total_months)
        ir_total = total_interest * ir_aliquota
        net_interest = total_interest - ir_total
        net_balance = total_invested + net_interest

        return SimulationResult(
            total_invested=round(total_invested, 2),
            total_interest=round(total_interest, 2),
            final_balance=round(current_balance, 2),
            total_months=total_months,
            months_to_target=months_to_target,
            ir_aliquota=ir_aliquota,
            ir_total=round(ir_total, 2),
            net_interest=round(net_interest, 2),
            net_balance=round(net_balance, 2),
            timeline=timeline
        )

    def calculate_months_to_target(
        self, 
        params: SimulationParams, 
        strategy: YieldStrategy,
        max_months: int = MAX_SIMULATION_MONTHS
    ) -> Optional[int]:
        """
        Calcula o tempo necessário (em meses) para atingir o valor estipulado em target_amount.
        Utiliza resolução analítica quando viável ou simulação determinística segura.
        Retorna None se for inatingível dentro de max_months (padrão: 100 anos).
        """
        if params.target_amount <= 0:
            return None

        if params.initial_amount >= params.target_amount:
            return 0

        monthly_rate = strategy.get_monthly_rate()

        # Sem juros nem aportes
        if monthly_rate == 0 and params.monthly_contribution <= 0:
            return None

        # Sem juros: acumulação puramente linear de aportes
        if monthly_rate == 0:
            meses = math.ceil((params.target_amount - params.initial_amount) / params.monthly_contribution)
            return meses if meses <= max_months else None

        # Se taxa mensal for negativa ou aporte for zero sem juros suficientes
        if monthly_rate < 0 and params.monthly_contribution <= 0:
            return None

        # Resolução analítica direta (O(1)):
        # Fórmula de anuidade com aportes antecipados:
        # B_n = PV*(1+r)^n + PMT*(1+r)*[((1+r)^n - 1) / r]
        # B_n = (1+r)^n * [PV + PMT*(1+r)/r] - PMT*(1+r)/r
        # (1+r)^n = [FV + PMT*(1+r)/r] / [PV + PMT*(1+r)/r]
        # n = ln(...) / ln(1+r)
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

        # Fallback de segurança determinístico
        balance = pv
        months = 0
        while balance < fv and months < max_months:
            balance += pmt
            balance += balance * r
            months += 1

        if balance >= fv:
            return months
        return None
