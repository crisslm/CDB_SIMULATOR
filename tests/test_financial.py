from datetime import date

import pytest

from src.domain.financial_models import TransactionType
from src.services.financial_service import FinancialService, parse_amount_to_cents


@pytest.fixture
def service(tmp_path):
    return FinancialService(database_path=tmp_path / "financial.sqlite3")


def category_id(service, kind, name):
    return next(category.id for category in service.categories(kind) if category.name == name)


def test_transactions_summary_and_investment_rate(service):
    salary = category_id(service, TransactionType.INCOME, "Salário")
    food = category_id(service, TransactionType.EXPENSE, "Alimentação")
    cdb = category_id(service, TransactionType.INVESTMENT, "CDB")
    service.create_transaction("receita", "Salário", "5.000,00", salary, "03/11/2026")
    service.create_transaction("despesa", "Mercado", "350,50", food, "2026-11-03")
    service.create_transaction("investimento", "Aporte", "1.000,00", cdb, date(2026, 11, 3))
    summary = service.summary(period="Mês atual", reference=date(2026, 11, 3))
    assert (summary.income_cents, summary.expense_cents, summary.investment_cents) == (500_000, 35_050, 100_000)
    assert summary.available_balance_cents == 364_950
    assert summary.investment_rate == 20


def test_invalid_amounts_and_category_type_are_rejected(service):
    income = category_id(service, TransactionType.INCOME, "Salário")
    with pytest.raises(ValueError):
        parse_amount_to_cents("0")
    with pytest.raises(ValueError):
        parse_amount_to_cents("-10")
    with pytest.raises(ValueError):
        service.create_transaction("despesa", "Inválido", "10", income, "01/01/2026")


def test_period_filtering_and_aggregations(service):
    food = category_id(service, TransactionType.EXPENSE, "Alimentação")
    transport = category_id(service, TransactionType.EXPENSE, "Transporte")
    service.create_transaction("despesa", "Mercado", "100", food, "2026-10-10")
    service.create_transaction("despesa", "Ônibus", "50", transport, "2026-11-02")
    service.create_transaction("despesa", "Mercado", "80", food, "2026-11-18")
    current = service.transactions(period="Mês atual", reference=date(2026, 11, 20))
    assert len(current) == 2
    assert service.expense_by_category(current) == [("Alimentação", 8000, "#FF9F43"), ("Transporte", 5000, "#4F8CFF")]
    assert service.monthly_expenses(service.transactions(period="Últimos 3 meses", reference=date(2026, 11, 20))) == [("2026-10", 10000), ("2026-11", 13000)]


def test_persistence_update_deletion_and_safe_category_archive(service, tmp_path):
    food = category_id(service, TransactionType.EXPENSE, "Alimentação")
    record = service.create_transaction("despesa", "Mercado", "40", food, "01/01/2026")
    service.update_transaction(record.id, "despesa", "Mercado semanal", "45,25", food, "02/01/2026", "cartão")
    reloaded = FinancialService(database_path=tmp_path / "financial.sqlite3")
    records = reloaded.transactions(period="Todo o período")
    assert records[0].description == "Mercado semanal"
    assert records[0].amount_cents == 4525
    assert reloaded.delete_or_archive_category(food) == "archived"
    assert all(category.id != food for category in reloaded.categories(TransactionType.EXPENSE))
    reloaded.delete_transaction(record.id)
    assert reloaded.transactions(period="Todo o período") == []


def test_zero_income_has_zero_investment_rate(service):
    cdb = category_id(service, TransactionType.INVESTMENT, "CDB")
    service.create_transaction("investimento", "Aporte", "250", cdb, "01/11/2026")
    summary = service.summary(period="Mês atual", reference=date(2026, 11, 2))
    assert summary.investment_rate == 0
    assert summary.available_balance_cents == -25_000
