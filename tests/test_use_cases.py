"""
Testes para a camada de Casos de Uso (Use Cases).
=================================================

Valida que os casos de uso orquestram corretamente a validação, os serviços
e o retorno de resultados, sem depender da interface gráfica.
"""

from datetime import date
from decimal import Decimal

import pytest

from src.domain.models import SimulationParams
from src.domain.strategies import CompoundInterestStrategy, CDIStrategy
from src.services.simulator_service import InvestmentSimulatorService
from src.use_cases.simulate_investment import (
    SimulateInvestmentUseCase,
    SimulationInput,
)


@pytest.fixture
def service():
    return InvestmentSimulatorService()


@pytest.fixture
def use_case(service):
    return SimulateInvestmentUseCase(service=service)


def test_simulate_use_case_prefixado(use_case):
    """Simulação com taxa prefixada deve retornar resultado consistente."""
    inp = SimulationInput(
        inicial="1.000,00",
        mensal="100,00",
        taxa="1,0",  # 1% ao mês
        periodo="2",
        tipo_periodo="Meses",
        meta="10.000,00",
        estrategia="Taxa Prefixada (% a.a. / a.m.)",
        cdi_base="10.75",
        use_effective_rate=False,
    )
    out = use_case.execute(inp)

    assert out.total_months == 2
    assert out.total_invested == 1200.0
    assert out.final_balance == pytest.approx(1223.11, abs=0.01)
    assert out.total_interest == pytest.approx(23.11, abs=0.01)
    assert out.ir_aliquota == 0.225  # 2 meses * 30 = 60 dias -> 22,5%
    assert out.truncado is False


def test_simulate_use_case_cdi(use_case):
    """Simulação com CDI deve criar CDIStrategy corretamente."""
    inp = SimulationInput(
        inicial="5.000,00",
        mensal="500,00",
        taxa="110",  # 110% do CDI
        periodo="60",
        tipo_periodo="Meses",
        meta="100.000,00",
        estrategia="Pós-fixado (% do CDI)",
        cdi_base="10.75",
        use_effective_rate=True,
    )
    out = use_case.execute(inp)

    assert out.total_months == 60
    assert out.total_invested > 0
    assert out.final_balance >= out.total_invested
    assert out.net_balance <= out.final_balance  # líquido <= bruto (IR)


def test_simulate_use_case_valores_negativos_rejeitados(use_case):
    """Valores negativos devem levantar ValueError."""
    inp = SimulationInput(
        inicial="-100,00",
        mensal="100,00",
        taxa="12,0",
        periodo="12",
        tipo_periodo="Meses",
        meta="10.000,00",
        estrategia="Taxa Prefixada (% a.a. / a.m.)",
    )
    with pytest.raises(ValueError):
        use_case.execute(inp)


def test_simulate_use_case_taxa_acima_limite_rejeitada(use_case):
    """Taxa acima de 100% para prefixado deve ser rejeitada."""
    inp = SimulationInput(
        inicial="1.000,00",
        mensal="100,00",
        taxa="150,0",  # acima de 100%
        periodo="12",
        tipo_periodo="Meses",
        meta="10.000,00",
        estrategia="Taxa Prefixada (% a.a. / a.m.)",
    )
    with pytest.raises(ValueError) as exc:
        use_case.execute(inp)
    assert "100" in str(exc.value)


def test_simulate_use_case_cdi_percentual_acima_limite_rejeitado(use_case):
    """Percentual do CDI acima de 500% deve ser rejeitado."""
    inp = SimulationInput(
        inicial="1.000,00",
        mensal="100,00",
        taxa="600",  # acima de 500%
        periodo="12",
        tipo_periodo="Meses",
        meta="10.000,00",
        estrategia="Pós-fixado (% do CDI)",
        cdi_base="10.75",
    )
    with pytest.raises(ValueError) as exc:
        use_case.execute(inp)
    assert "500%" in str(exc.value)


def test_simulate_use_case_cdi_base_invalido_rejeitado(use_case):
    """CDI base fora de 0-100 deve ser rejeitado."""
    inp = SimulationInput(
        inicial="1.000,00",
        mensal="100,00",
        taxa="110",
        periodo="12",
        tipo_periodo="Meses",
        meta="10.000,00",
        estrategia="Pós-fixado (% do CDI)",
        cdi_base="150",  # acima de 100
    )
    with pytest.raises(ValueError):
        use_case.execute(inp)


def test_simulate_use_case_meta_zero_rejeitada(use_case):
    """Meta menor ou igual a zero deve ser rejeitada."""
    inp = SimulationInput(
        inicial="1.000,00",
        mensal="100,00",
        taxa="12,0",
        periodo="12",
        tipo_periodo="Meses",
        meta="0",
        estrategia="Taxa Prefixada (% a.a. / a.m.)",
    )
    with pytest.raises(ValueError):
        use_case.execute(inp)


def test_simulate_use_case_prazo_excede_limite_trunca(use_case):
    """Prazo acima de 1200 meses deve ser truncado."""
    inp = SimulationInput(
        inicial="1.000,00",
        mensal="100,00",
        taxa="1,0",
        periodo="50000",  # 50000 meses -> truncado para 1200
        tipo_periodo="Meses",
        meta="10.000,00",
        estrategia="Taxa Prefixada (% a.a. / a.m.)",
    )
    out = use_case.execute(inp)
    assert out.total_months == 1200
    assert out.truncado is True

def test_simulate_use_case_datas_ir(use_case):
    """Datas de início e fim devem ser usadas para cálculo de IR."""
    inp = SimulationInput(
        inicial="1.000,00",
        mensal="100,00",
        taxa="1,0",
        periodo="2",
        tipo_periodo="Meses",
        meta="10.000,00",
        estrategia="Taxa Prefixada (% a.a. / a.m.)",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 8, 1),  # ~212 dias -> 20%
    )
    out = use_case.execute(inp)
    assert out.ir_aliquota == 0.20  # 212 dias -> faixa 181-360 -> 20%


def test_simulate_output_campos_obrigatorios(use_case):
    """O output deve conter todos os campos obrigatórios."""
    inp = SimulationInput(
        inicial="1.000,00",
        mensal="100,00",
        taxa="1,0",
        periodo="2",
        tipo_periodo="Meses",
        meta="10.000,00",
        estrategia="Taxa Prefixada (% a.a. / a.m.)",
    )
    out = use_case.execute(inp)

    assert isinstance(out.total_invested, float)
    assert isinstance(out.total_interest, float)
    assert isinstance(out.final_balance, float)
    assert isinstance(out.total_months, int)
    assert out.months_to_target is None or isinstance(out.months_to_target, int)
    assert isinstance(out.ir_aliquota, float)
    assert isinstance(out.net_balance, float)
    assert isinstance(out.timeline, list)
    assert isinstance(out.truncado, bool)
    assert isinstance(out.estrategia_descricao, str)


def test_use_case_injecao_dependencia():
    """O caso de uso deve aceitar serviço injetado."""
    service = InvestmentSimulatorService()
    uc = SimulateInvestmentUseCase(service=service)
    assert uc.service is service
