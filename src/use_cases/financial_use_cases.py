"""
Casos de uso: Controle Financeiro Pessoal.
==========================================

Encapsula os fluxos de negócio do Controle Financeiro:

    - Criar/atualizar/excluir categorias
    - Criar/atualizar/excluir transações
    - Consultar resumos e agregações

Princípio: SRP — este caso de uso só cuida do controle financeiro.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from ..domain.financial_models import FinancialCategory, FinancialTransaction, TransactionType
from ..domain.financial_utils import (
    DEFAULT_CATEGORIES,
    allocation,
    expense_by_category,
    monthly_expenses,
    parse_amount_to_cents,
    parse_br_date,
    period_range,
    summary_for,
)
from ..repositories.financial_repository import CategoryInUseError, FinancialRepository


class FinancialUseCases:
    """
    Casos de uso para o Controle Financeiro Pessoal.

    Atributos:
        repository: Repositório de persistência (implementa FinancialRepositoryProtocol).
    """

    def __init__(self, repository: FinancialRepository | None = None, database_path=None):
        self.repository = repository or FinancialRepository(database_path=database_path)
        self._ensure_default_categories()

    def _ensure_default_categories(self) -> None:
        """Garante que categorias padrão existam no banco."""
        if self.repository.list_categories(active_only=False):
            return
        for name, kind, color in DEFAULT_CATEGORIES:
            self.repository.add_category(
                FinancialCategory(name, kind, color)
            )

    # ------------------------------------------------------------------
    # Categorias
    # ------------------------------------------------------------------

    def categories(
        self,
        transaction_type: TransactionType | str | None = None,
        active_only: bool = True,
    ):
        """Retorna lista de categorias (alias para list_categories)."""
        kind = TransactionType.from_value(transaction_type) if transaction_type else None
        return self.repository.list_categories(kind, active_only)

    def list_categories(
        self,
        transaction_type: TransactionType | str | None = None,
        active_only: bool = True,
    ):
        kind = TransactionType.from_value(transaction_type) if transaction_type else None
        return self.repository.list_categories(kind, active_only)

    def create_category(self, name: str, transaction_type, color: str) -> FinancialCategory:
        kind = TransactionType.from_value(transaction_type)
        return self.repository.add_category(FinancialCategory(name, kind, color))

    def update_category(
        self,
        category_id: int,
        name: str,
        transaction_type,
        color: str,
        active: bool = True,
    ) -> FinancialCategory:
        kind = TransactionType.from_value(transaction_type)
        return self.repository.update_category(
            FinancialCategory(name, kind, color, category_id, active)
        )

    def delete_or_archive_category(self, category_id: int, archive_if_in_use: bool = True) -> str:
        try:
            self.repository.delete_category(category_id)
            return "deleted"
        except ValueError:
            if not archive_if_in_use:
                raise
        except CategoryInUseError:
            if not archive_if_in_use:
                raise
        self.repository.archive_category(category_id)
        return "archived"

    # ------------------------------------------------------------------
    # Transações
    # ------------------------------------------------------------------

    def create_transaction(
        self,
        transaction_type,
        description: str,
        amount,
        category_id: int,
        occurred_on,
        notes: str = "",
    ) -> FinancialTransaction:
        return self._build_and_save(transaction_type, description, amount, category_id, occurred_on, notes)

    def update_transaction(
        self,
        transaction_id: int,
        transaction_type,
        description: str,
        amount,
        category_id: int,
        occurred_on,
        notes: str = "",
    ) -> FinancialTransaction:
        return self._build_and_save(
            transaction_type, description, amount, category_id, occurred_on, notes, transaction_id
        )

    def delete_transaction(self, transaction_id: int) -> None:
        self.repository.delete_transaction(transaction_id)

    def _build_and_save(
        self,
        transaction_type,
        description: str,
        amount,
        category_id: int,
        occurred_on,
        notes: str = "",
        transaction_id=None,
    ) -> FinancialTransaction:
        kind = TransactionType.from_value(transaction_type)
        category = self.repository.get_category(int(category_id))
        if not category:
            raise ValueError("Categoria não encontrada.")
        if category.transaction_type != kind:
            raise ValueError("A categoria deve pertencer ao mesmo tipo do lançamento.")
        tx = FinancialTransaction(
            kind,
            description,
            parse_amount_to_cents(amount),
            int(category_id),
            parse_br_date(occurred_on),
            notes or "",
            transaction_id,
        )
        if transaction_id is None:
            return self.repository.add_transaction(tx)
        return self.repository.update_transaction(tx)

    # ------------------------------------------------------------------
    # Consultas e relatórios
    # ------------------------------------------------------------------

    def transactions(
        self,
        period: str = "Todo o período",
        transaction_type: TransactionType | str | None = None,
        category_id: int | None = None,
        custom_start: date | None = None,
        custom_end: date | None = None,
        reference: date | None = None,
    ):
        start, end = period_range(period, reference, custom_start, custom_end)
        kind = TransactionType.from_value(transaction_type) if transaction_type else None
        return self.repository.list_transactions(start, end, kind, category_id)

    def summary(self, **filters):
        start, end = period_range(
            filters.get("period"),
            filters.get("reference"),
            filters.get("custom_start"),
            filters.get("custom_end"),
        )
        kind = TransactionType.from_value(filters.get("transaction_type")) if filters.get("transaction_type") else None
        return self.repository.summary_sql(start, end, kind, filters.get("category_id"))

    def summary_sql(self, **filters):
        start, end = period_range(
            filters.get("period"),
            filters.get("reference"),
            filters.get("custom_start"),
            filters.get("custom_end"),
        )
        kind = TransactionType.from_value(filters.get("transaction_type")) if filters.get("transaction_type") else None
        return self.repository.summary_sql(start, end, kind, filters.get("category_id"))

    def allocation_sql(self, **filters):
        start, end = period_range(
            filters.get("period"),
            filters.get("reference"),
            filters.get("custom_start"),
            filters.get("custom_end"),
        )
        expense_filters = {k: v for k, v in filters.items() if k != "transaction_type"}
        result = self.repository.expense_by_category_sql(start, end, expense_filters.get("category_id"))
        invested = self.repository.summary_sql(
            start, end, TransactionType.INVESTMENT, expense_filters.get("category_id")
        ).investment_cents
        if invested:
            result = list(result)
            result.append(("Investimentos", invested, "#24C270"))
        return result

    def expense_by_category_sql(self, **filters):
        start, end = period_range(
            filters.get("period"),
            filters.get("reference"),
            filters.get("custom_start"),
            filters.get("custom_end"),
        )
        return self.repository.expense_by_category_sql(start, end, filters.get("category_id"))

    def monthly_expenses_sql(self, **filters):
        start, end = period_range(
            filters.get("period"),
            filters.get("reference"),
            filters.get("custom_start"),
            filters.get("custom_end"),
        )
        return self.repository.monthly_expenses_sql(start, end, filters.get("category_id"))

    # Mantidos para retrocompatibilidade (loop Python)
    def summary_for(self, transactions):
        return summary_for(transactions)

    def expense_by_category_py(self, transactions):
        return expense_by_category(transactions)

    def allocation_py(self, transactions):
        return allocation(transactions)

    def monthly_expenses_py(self, transactions):
        return monthly_expenses(transactions)
