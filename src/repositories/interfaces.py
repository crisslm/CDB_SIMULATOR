"""
Interfaces (Protocol) para os repositórios de persistência.
=============================================================

Define o contrato que qualquer repositório financeiro deve implementar,
permitindo injeção de dependência, mock em testes e futura troca de
banco de dados (ex: PostgreSQL) sem alterar a camada de serviços.

Princípio: DIP — Dependência Inversão (os serviços dependem de abstrações,
não de classes concretas).
"""

from __future__ import annotations

from datetime import date
from typing import Iterable, Optional, Protocol

from src.domain.financial_models import (
    FinancialCategory,
    FinancialSummary,
    FinancialTransaction,
    TransactionType,
)


class FinancialRepositoryProtocol(Protocol):
    """
    Protocolo para repositórios de controle financeiro.

    Qualquer classe que implemente esses métodos pode ser usada como
    repositório pelos serviços, sem acoplamento à implementação SQLite.
    """

    SCHEMA_VERSION: int

    def list_categories(
        self,
        transaction_type: TransactionType | None = None,
        active_only: bool = True,
    ) -> list[FinancialCategory]:
        ...

    def get_category(self, category_id: int) -> Optional[FinancialCategory]:
        ...

    def add_category(self, category: FinancialCategory) -> FinancialCategory:
        ...

    def update_category(self, category: FinancialCategory) -> FinancialCategory:
        ...

    def archive_category(self, category_id: int) -> None:
        ...

    def delete_category(self, category_id: int) -> None:
        ...

    def add_transaction(self, transaction: FinancialTransaction) -> FinancialTransaction:
        ...

    def update_transaction(self, transaction: FinancialTransaction) -> FinancialTransaction:
        ...

    def delete_transaction(self, transaction_id: int) -> None:
        ...

    def list_transactions(
        self,
        start: date | None = None,
        end: date | None = None,
        transaction_type: TransactionType | None = None,
        category_id: int | None = None,
    ) -> list[FinancialTransaction]:
        ...

    def summary_sql(
        self,
        start: date | None = None,
        end: date | None = None,
        transaction_type: TransactionType | None = None,
        category_id: int | None = None,
    ) -> FinancialSummary:
        ...

    def expense_by_category_sql(
        self,
        start: date | None = None,
        end: date | None = None,
        category_id: int | None = None,
    ) -> list[tuple[str, int, str]]:
        ...

    def monthly_expenses_sql(
        self,
        start: date | None = None,
        end: date | None = None,
        category_id: int | None = None,
    ) -> list[tuple[str, int]]:
        ...

    def close(self) -> None:
        ...
