"""Casos de uso e agregações do Controle Financeiro."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Optional

from src.domain.financial_models import FinancialCategory, FinancialSummary, FinancialTransaction, TransactionType
from src.repositories.financial_repository import FinancialRepository


DEFAULT_CATEGORIES = (
    ("Salário", TransactionType.INCOME, "#24C270"), ("Freelance", TransactionType.INCOME, "#4F8CFF"),
    ("Dividendos", TransactionType.INCOME, "#A970FF"), ("Rendimentos", TransactionType.INCOME, "#32B8C6"),
    ("Outros", TransactionType.INCOME, "#8E8E93"),
    ("Alimentação", TransactionType.EXPENSE, "#FF9F43"), ("Transporte", TransactionType.EXPENSE, "#4F8CFF"),
    ("Moradia", TransactionType.EXPENSE, "#FF6B6B"), ("Saúde", TransactionType.EXPENSE, "#A970FF"),
    ("Educação", TransactionType.EXPENSE, "#32B8C6"), ("Lazer", TransactionType.EXPENSE, "#F368E0"),
    ("Assinaturas", TransactionType.EXPENSE, "#8395A7"), ("Compras", TransactionType.EXPENSE, "#F9CA24"),
    ("Contas", TransactionType.EXPENSE, "#576574"), ("Outros", TransactionType.EXPENSE, "#8E8E93"),
    ("CDB", TransactionType.INVESTMENT, "#24C270"), ("Tesouro Direto", TransactionType.INVESTMENT, "#4F8CFF"),
    ("Ações", TransactionType.INVESTMENT, "#FF9F43"), ("Fundos Imobiliários", TransactionType.INVESTMENT, "#A970FF"),
    ("ETFs", TransactionType.INVESTMENT, "#32B8C6"), ("Criptomoedas", TransactionType.INVESTMENT, "#F9CA24"),
    ("Reserva de Emergência", TransactionType.INVESTMENT, "#6FE29F"), ("Outros", TransactionType.INVESTMENT, "#8E8E93"),
)


def parse_amount_to_cents(value: str | int | Decimal) -> int:
    """Converte entrada brasileira (ex. ``R$ 1.250,50``) em centavos."""
    raw = str(value).strip().replace("R$", "").replace(" ", "")
    if not raw:
        raise ValueError("Informe um valor.")
    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        raw = raw.replace(",", ".")
    elif raw.count(".") > 1:
        raw = raw.replace(".", "")
    try:
        amount = Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Informe um valor monetário válido.") from exc
    cents = int(amount * 100)
    if cents <= 0:
        raise ValueError("O valor deve ser maior que zero.")
    return cents


def format_cents(cents: int) -> str:
    return f"R$ {cents / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_br_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    normalized = (value or "").strip()
    try:
        if "/" in normalized:
            day, month, year = (int(part) for part in normalized.split("/"))
            return date(year, month, day)
        return date.fromisoformat(normalized)
    except (TypeError, ValueError) as exc:
        raise ValueError("Informe uma data válida no formato DD/MM/AAAA.") from exc


class FinancialService:
    def __init__(self, repository: FinancialRepository | None = None, database_path: str | Path | None = None):
        self.repository = repository or FinancialRepository(database_path)
        self.ensure_default_categories()

    def ensure_default_categories(self) -> None:
        if self.repository.list_categories(active_only=False):
            return
        for name, kind, color in DEFAULT_CATEGORIES:
            self.repository.add_category(FinancialCategory(name, kind, color))

    @staticmethod
    def period_range(period: str, reference: date | None = None, custom_start: date | None = None,
                     custom_end: date | None = None) -> tuple[date | None, date | None]:
        today = reference or date.today()
        period = (period or "Mês atual").strip()
        def month_start(year: int, month: int) -> date: return date(year, month, 1)
        if period == "Todo o período": return None, None
        if period == "Período personalizado":
            if not custom_start or not custom_end or custom_start > custom_end:
                raise ValueError("Informe um período personalizado válido.")
            return custom_start, custom_end
        months = {"Mês atual": 1, "Mês anterior": 1, "Últimos 3 meses": 3, "Últimos 6 meses": 6, "Últimos 12 meses": 12}.get(period)
        if months is None: raise ValueError("Período inválido.")
        end_anchor = month_start(today.year, today.month)
        if period == "Mês anterior":
            end = end_anchor - timedelta(days=1)
            return month_start(end.year, end.month), end
        start_year, start_month = today.year, today.month - months + 1
        while start_month <= 0:
            start_year -= 1; start_month += 12
        return month_start(start_year, start_month), today

    def categories(self, transaction_type: TransactionType | str | None = None, active_only: bool = True) -> list[FinancialCategory]:
        return self.repository.list_categories(TransactionType.from_value(transaction_type) if transaction_type else None, active_only)

    def create_category(self, name: str, transaction_type: TransactionType | str, color: str) -> FinancialCategory:
        return self.repository.add_category(FinancialCategory(name, TransactionType.from_value(transaction_type), color))

    def update_category(self, category_id: int, name: str, transaction_type: TransactionType | str, color: str,
                        active: bool = True) -> FinancialCategory:
        return self.repository.update_category(FinancialCategory(name, TransactionType.from_value(transaction_type), color, category_id, active))

    def delete_or_archive_category(self, category_id: int, archive_if_in_use: bool = True) -> str:
        try:
            self.repository.delete_category(category_id)
            return "deleted"
        except ValueError:
            if not archive_if_in_use: raise
            self.repository.archive_category(category_id)
            return "archived"

    def _make_transaction(self, transaction_type, description, amount, category_id, occurred_on, notes="", transaction_id=None) -> FinancialTransaction:
        kind = TransactionType.from_value(transaction_type)
        category = self.repository.get_category(int(category_id))
        if not category:
            raise ValueError("Categoria não encontrada.")
        if category.transaction_type != kind:
            raise ValueError("A categoria deve pertencer ao mesmo tipo do lançamento.")
        return FinancialTransaction(kind, description, parse_amount_to_cents(amount), int(category_id), parse_br_date(occurred_on), notes or "", transaction_id)

    def create_transaction(self, transaction_type, description: str, amount, category_id: int, occurred_on, notes: str = "") -> FinancialTransaction:
        return self.repository.add_transaction(self._make_transaction(transaction_type, description, amount, category_id, occurred_on, notes))

    def update_transaction(self, transaction_id: int, transaction_type, description: str, amount, category_id: int, occurred_on, notes: str = "") -> FinancialTransaction:
        return self.repository.update_transaction(self._make_transaction(transaction_type, description, amount, category_id, occurred_on, notes, transaction_id))

    def delete_transaction(self, transaction_id: int) -> None:
        self.repository.delete_transaction(transaction_id)

    def transactions(self, period: str = "Todo o período", transaction_type: TransactionType | str | None = None,
                     category_id: int | None = None, custom_start: date | None = None, custom_end: date | None = None,
                     reference: date | None = None) -> list[FinancialTransaction]:
        start, end = self.period_range(period, reference, custom_start, custom_end)
        kind = TransactionType.from_value(transaction_type) if transaction_type else None
        return self.repository.list_transactions(start, end, kind, category_id)

    @staticmethod
    def summary_for(transactions: list[FinancialTransaction]) -> FinancialSummary:
        totals = defaultdict(int)
        for item in transactions: totals[item.transaction_type] += item.amount_cents
        return FinancialSummary(totals[TransactionType.INCOME], totals[TransactionType.EXPENSE], totals[TransactionType.INVESTMENT])

    def summary(self, **filters) -> FinancialSummary:
        return self.summary_for(self.transactions(**filters))

    @staticmethod
    def expense_by_category(transactions: list[FinancialTransaction]) -> list[tuple[str, int, str]]:
        totals: dict[tuple[str, str], int] = defaultdict(int)
        for item in transactions:
            if item.transaction_type == TransactionType.EXPENSE:
                totals[(item.category_name, item.category_color or "#8E8E93")] += item.amount_cents
        return [(name, amount, color) for (name, color), amount in sorted(totals.items(), key=lambda item: item[1], reverse=True)]

    @staticmethod
    def allocation(transactions: list[FinancialTransaction]) -> list[tuple[str, int, str]]:
        result = FinancialService.expense_by_category(transactions)
        invested = sum(item.amount_cents for item in transactions if item.transaction_type == TransactionType.INVESTMENT)
        if invested: result.append(("Investimentos", invested, "#24C270"))
        return result

    @staticmethod
    def monthly_expenses(transactions: list[FinancialTransaction]) -> list[tuple[str, int]]:
        totals: dict[str, int] = defaultdict(int)
        for item in transactions:
            if item.transaction_type == TransactionType.EXPENSE:
                totals[item.occurred_on.strftime("%Y-%m")] += item.amount_cents
        return sorted(totals.items())
