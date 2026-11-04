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
    assert calcular_aliquota_ir(180) == 0.225   # até 180 dias
    assert calcular_aliquota_ir(181) == 0.20    # 181 a 360 dias
    assert calcular_aliquota_ir(360) == 0.20
    assert calcular_aliquota_ir(361) == 0.175   # 361 a 720 dias
    assert calcular_aliquota_ir(720) == 0.175
    assert calcular_aliquota_ir(721) == 0.15    # acima de 720 dias
    assert calcular_aliquota_ir(1000) == 0.15
