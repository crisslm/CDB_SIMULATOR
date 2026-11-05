"""
Caso de uso: Simulação de Investimento (CDB / Juros Compostos).
===============================================================

Encapsula o fluxo completo de simulação:

    1. Recebe dados brutos da UI (DTO de entrada).
    2. Valida valores, taxas e prazos.
    3. Cria a estratégia de rendimento e os parâmetros de simulação.
    4. Chama o serviço de simulação.
    5. Retorna o resultado para a UI.

Princípio: SRP — este caso de uso só cuida da simulação de investimento.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from ..domain.constants import (
    CDI_BASE_MAX,
    CDI_BASE_MIN,
    CDI_PERCENTUAL_MAX,
    CDI_PERCENTUAL_MIN,
    LIMITE_MONETARIO,
    MAX_SIMULATION_MONTHS,
    TAXA_JUROS_MAX,
    TAXA_JUROS_MIN,
    ZERO_TOLERANCE,
)
from ..domain.models import SimulationParams, calcular_aliquota_ir
from ..domain.strategies import CDIStrategy, CompoundInterestStrategy, YieldStrategy
from ..services.simulator_service import InvestmentSimulatorService


@dataclass
class SimulationInput:
    """
    DTO de entrada para o caso de uso de simulação.

    Campos são strings ou números crus vindos da UI, ainda não validados.
    """

    inicial: str
    mensal: str
    taxa: str
    periodo: str
    tipo_periodo: str  # "Anos" ou "Meses"
    meta: str
    estrategia: str  # "Taxa Prefixada..." ou "Pós-fixado (% do CDI)"
    cdi_base: str = "10.75"
    use_effective_rate: bool = True
    start_date: Optional[date] = None
    end_date: Optional[date] = None


@dataclass
class SimulationOutput:
    """
    DTO de saída do caso de uso de simulação.

    Contém os dados prontos para exibição na UI, já formatados.
    """

    total_invested: float
    total_interest: float
    final_balance: float
    total_months: int
    months_to_target: Optional[int]
    ir_aliquota: float
    ir_total: float
    net_interest: float
    net_balance: float
    timeline: list
    truncado: bool
    estrategia_descricao: str
    taxa_mensal: float


class SimulateInvestmentUseCase:
    """
    Caso de uso para simulação de investimento.

    Atributos:
        service: Instância do InvestmentSimulatorService.
    """

    def __init__(self, service: InvestmentSimulatorService | None = None):
        self.service = service or InvestmentSimulatorService()

    def execute(self, input_data: SimulationInput) -> SimulationOutput:
        """
        Executa a simulação completa.

        Fluxo:
            1. Lê e converte valores monetários (suporta formato brasileiro).
            2. Valida limites monetários e negativos.
            3. Valida taxas conforme a estratégia selecionada.
            4. Valida prazo e meta.
            5. Converte prazo para meses (máximo 1200 = anti-DoS).
            6. Cria estratégia de rendimento (CompoundInterestStrategy ou CDIStrategy).
            7. Cria SimulationParams e chama service.simulate().
            8. Retorna SimulationOutput pronto para a UI.

        Levanta:
            ValueError: Se qualquer validação falhar.
        """
        # --- 1. Conversão de valores monetários ---
        try:
            inicial = self._parse_moeda(input_data.inicial)
            mensal = self._parse_moeda(input_data.mensal)
            taxa_raw = self._parse_percent(input_data.taxa)
            periodo_raw = self._parse_percent(input_data.periodo)
            meta_str = input_data.meta.strip().replace(",", ".")
            meta_val = self._parse_moeda(meta_str) if meta_str else 1_000_000.0
        except ValueError as exc:
            raise ValueError("Por favor, preencha todos os campos apenas com números válidos.") from exc

        # --- 2. Limite monetário de segurança ---
        for nome, valor in (("Valor Inicial", inicial), ("Aporte Mensal", mensal), ("Meta", meta_val)):
            if valor > LIMITE_MONETARIO:
                raise ValueError(f"{nome} não pode exceder R$ {LIMITE_MONETARIO:,.2f}.")

        if inicial < 0 or mensal < 0:
            raise ValueError("Os valores de aportes não podem ser negativos.")

        # --- 3. Validação de taxa diferenciada por estratégia ---
        if "CDI" in input_data.estrategia:
            if taxa_raw <= CDI_PERCENTUAL_MIN or taxa_raw > CDI_PERCENTUAL_MAX:
                raise ValueError(
                    f"O percentual do CDI deve estar entre {CDI_PERCENTUAL_MIN:.0f}% e {CDI_PERCENTUAL_MAX:.0f}%."
                )
        else:
            if taxa_raw < TAXA_JUROS_MIN or taxa_raw > TAXA_JUROS_MAX:
                raise ValueError(
                    f"A taxa de rendimento deve estar entre {TAXA_JUROS_MIN:.0f}% e {TAXA_JUROS_MAX:.0f}."
                )

        if periodo_raw <= 0:
            raise ValueError("O prazo de investimento deve ser maior que zero.")

        if meta_val <= 0:
            raise ValueError("O valor da meta financeira deve ser maior que zero.")

        # --- 4. Conversão de prazo para meses ---
        meses_original = None
        if input_data.tipo_periodo == "Anos":
            meses = max(1, int(round(periodo_raw * 12)))
        else:
            meses = max(1, int(round(periodo_raw)))

        truncado = False
        if meses > MAX_SIMULATION_MONTHS:
            meses_original = meses
            meses = MAX_SIMULATION_MONTHS
            truncado = True

        # --- 5. Cria estratégia de rendimento ---
        strategy: YieldStrategy
        if "CDI" in input_data.estrategia:
            try:
                cdi_base = self._parse_percent(input_data.cdi_base)
                if cdi_base <= CDI_BASE_MIN or cdi_base > CDI_BASE_MAX:
                    raise ValueError(
                        f"A taxa CDI base deve estar entre {CDI_BASE_MIN:.0f} e {CDI_BASE_MAX:.0f}."
                    )
            except ValueError as exc:
                raise ValueError(
                    "Digite um valor válido para a Taxa CDI Base (ex: 10.75)."
                ) from exc
            strategy = CDIStrategy(
                cdi_percentage=taxa_raw,
                cdi_annual_rate=cdi_base,
                use_effective_rate=input_data.use_effective_rate,
            )
        else:
            is_annual = input_data.tipo_periodo == "% ao ano" or input_data.tipo_periodo == "Anos"
            # Para taxa prefixada, o combo de período da taxa é "% ao ano" / "% ao mês"
            # mas o tipo_periodo é "Anos" / "Meses". Ajustamos is_annual conforme o
            # campo de período da taxa, que vem no tipo_periodo quando prefixado.
            # Na UI, tipo_periodo é "Anos"/"Meses" para o prazo, e há combo separado
            # para taxa. Aqui tratamos de forma defensiva.
            is_annual = input_data.tipo_periodo == "Anos"
            strategy = CompoundInterestStrategy(
                rate_percent=taxa_raw,
                is_annual=is_annual,
                use_effective_rate=input_data.use_effective_rate,
            )

        # --- 6. Executa simulação ---
        # Passa o prazo original (antes do truncamento) para que o serviço
        # detecte corretamente o truncamento anti-DoS.
        total_months_para_servico = meses_original if meses_original is not None else meses
        params = SimulationParams(
            initial_amount=inicial,
            monthly_contribution=mensal,
            total_months=total_months_para_servico,
            target_amount=meta_val,
            start_date=input_data.start_date,
            end_date=input_data.end_date,
        )

        resultado = self.service.simulate(params, strategy)

        # --- 7. Monta output ---
        taxa_mensal = strategy.get_monthly_rate()
        return SimulationOutput(
            total_invested=resultado.total_invested,
            total_interest=resultado.total_interest,
            final_balance=resultado.final_balance,
            total_months=resultado.total_months,
            months_to_target=resultado.months_to_target,
            ir_aliquota=resultado.ir_aliquota,
            ir_total=resultado.ir_total,
            net_interest=resultado.net_interest,
            net_balance=resultado.net_balance,
            timeline=resultado.timeline,
            truncado=resultado.truncado,
            estrategia_descricao=strategy.get_description(),
            taxa_mensal=taxa_mensal,
        )

    # ---------------------------------------------------------------------
    # Utilitários privados de parsing
    # ---------------------------------------------------------------------

    @staticmethod
    def _parse_moeda(value: str) -> float:
        """
        Converte uma string monetária brasileira para float.

        Aceita: "1.250,50", "1250,50", "R$ 1.250,50", etc.
        """
        from src.domain.financial_utils import parse_amount_to_cents

        cents = parse_amount_to_cents(value)
        return cents / 100.0

    @staticmethod
    def _parse_percent(value: str) -> float:
        """
        Converte uma string de percentual para float.

        Remove "R$", espaços, "%" e troca vírgula por ponto.
        Ex: "12,5" -> 12.5, "R$ 10%" -> 10.0
        """
        raw = value.strip().replace("R$", "").replace(" ", "").replace("%", "").replace(",", ".")
        if not raw:
            raise ValueError("Valor inválido.")
        return float(raw)
