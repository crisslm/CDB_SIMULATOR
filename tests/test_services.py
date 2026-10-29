import pytest
from src.domain.models import SimulationParams
from src.domain.strategies import CompoundInterestStrategy
from src.services.simulator_service import InvestmentSimulatorService, MAX_SIMULATION_MONTHS

def test_simulator_service_calculation_with_nominal():
    # R$ 1.000 inicial, R$ 100 mensal, 1% a.m., por 2 meses
    # Mês 1: saldo = (1000 + 100) = 1100 -> rendimento = 11 -> saldo = 1111, investido = 1100
    # Mês 2: saldo = (1111 + 100) = 1211 -> rendimento = 12.11 -> saldo = 1223.11, investido = 1200
    strategy = CompoundInterestStrategy(rate_percent=1.0, is_annual=False)
    service = InvestmentSimulatorService()
    
    params = SimulationParams(
        initial_amount=1000.0,
        monthly_contribution=100.0,
        total_months=2,
        target_amount=10_000.0
    )

    result = service.simulate(params, strategy)

    assert result.total_months == 2
    assert result.total_invested == 1200.0
    assert result.final_balance == pytest.approx(1223.11, 0.01)
    assert result.total_interest == pytest.approx(23.11, 0.01)
    assert len(result.timeline) == 2
    
    # 2 meses -> IR de 22.5%
    assert result.ir_aliquota == 0.225
    assert result.ir_total == pytest.approx(23.11 * 0.225, 0.01)
    assert result.net_balance == pytest.approx(1200.0 + (23.11 * 0.775), 0.01)

def test_time_to_target_analytical():
    strategy = CompoundInterestStrategy(rate_percent=1.0, is_annual=False)
    service = InvestmentSimulatorService()
    
    # Já começa na meta
    params_reached = SimulationParams(
        initial_amount=10_000.0,
        monthly_contribution=0.0,
        total_months=12,
        target_amount=10_000.0
    )
    assert service.calculate_months_to_target(params_reached, strategy) == 0

    # Meta inalcançável (juros 0 e aporte 0)
    strategy_zero = CompoundInterestStrategy(rate_percent=0.0, is_annual=False)
    params_unreachable = SimulationParams(
        initial_amount=100.0,
        monthly_contribution=0.0,
        total_months=12,
        target_amount=10_000.0
    )
    assert service.calculate_months_to_target(params_unreachable, strategy_zero) is None

    # Meta com acúmulo linear sem juros
    params_linear = SimulationParams(
        initial_amount=0.0,
        monthly_contribution=500.0,
        total_months=12,
        target_amount=5_000.0
    )
    assert service.calculate_months_to_target(params_linear, strategy_zero) == 10

    # Meta clássica com juros
    params_with_interest = SimulationParams(
        initial_amount=5000.0,
        monthly_contribution=500.0,
        total_months=60,
        target_amount=100_000.0
    )
    months = service.calculate_months_to_target(params_with_interest, strategy)
    assert months is not None
    assert months > 0

    # Meta negativa ou zerada deve retornar None
    params_invalid_target = SimulationParams(
        initial_amount=100.0,
        monthly_contribution=100.0,
        total_months=12,
        target_amount=-500.0
    )
    assert service.calculate_months_to_target(params_invalid_target, strategy) is None

def test_max_months_safety_limit():
    strategy = CompoundInterestStrategy(rate_percent=1.0, is_annual=False)
    service = InvestmentSimulatorService()

    # Período absurdo (ex: 50.000 meses) é limitado ao teto seguro MAX_SIMULATION_MONTHS
    params_huge = SimulationParams(
        initial_amount=1000.0,
        monthly_contribution=100.0,
        total_months=50_000,
        target_amount=1_000_000.0
    )
    result = service.simulate(params_huge, strategy)
    assert result.total_months == MAX_SIMULATION_MONTHS
    assert len(result.timeline) == MAX_SIMULATION_MONTHS
