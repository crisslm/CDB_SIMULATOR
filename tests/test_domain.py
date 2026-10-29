import pytest
from src.domain.models import SimulationParams, MonthlyRecord, SimulationResult, calcular_aliquota_ir
from src.domain.strategies import CompoundInterestStrategy, CDIStrategy

def test_compound_interest_monthly():
    # 1% ao mês -> taxa decimal = 0.01
    strategy = CompoundInterestStrategy(rate_percent=1.0, is_annual=False)
    assert strategy.get_monthly_rate() == pytest.approx(0.01)

def test_compound_interest_annual_nominal():
    # 12% ao ano nominal -> 1% ao mês = 0.01
    strategy = CompoundInterestStrategy(rate_percent=12.0, is_annual=True, use_effective_rate=False)
    assert strategy.get_monthly_rate() == pytest.approx(0.01)

def test_compound_interest_annual_effective():
    # 12% ao ano composto equivalente: (1.12)^(1/12) - 1 ≈ 0.00948879
    strategy = CompoundInterestStrategy(rate_percent=12.0, is_annual=True, use_effective_rate=True)
    expected = (1.12 ** (1.0 / 12.0)) - 1.0
    assert strategy.get_monthly_rate() == pytest.approx(expected, rel=1e-6)

def test_cdi_strategy_nominal_and_effective():
    # 100% do CDI com CDI a 12% a.a. nominal
    strategy_nominal = CDIStrategy(cdi_percentage=100.0, cdi_annual_rate=12.0, use_effective_rate=False)
    assert strategy_nominal.get_monthly_rate() == pytest.approx(0.01)

    # 110% do CDI com CDI a 10% a.a. equivalente: taxa anual = 11% -> (1.11)^(1/12) - 1
    strategy_eff = CDIStrategy(cdi_percentage=110.0, cdi_annual_rate=10.0, use_effective_rate=True)
    expected_rate = (1.11 ** (1.0 / 12.0)) - 1.0
    assert strategy_eff.get_monthly_rate() == pytest.approx(expected_rate, rel=1e-6)

def test_aliquota_ir_regressiva():
    assert calcular_aliquota_ir(3) == 0.225   # <= 6 meses
    assert calcular_aliquota_ir(6) == 0.225
    assert calcular_aliquota_ir(10) == 0.20   # 7 a 12 meses
    assert calcular_aliquota_ir(12) == 0.20
    assert calcular_aliquota_ir(18) == 0.175  # 13 a 24 meses
    assert calcular_aliquota_ir(24) == 0.175
    assert calcular_aliquota_ir(25) == 0.15   # > 24 meses
    assert calcular_aliquota_ir(60) == 0.15
