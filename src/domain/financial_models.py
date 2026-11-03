"""Entidades puras do Controle Financeiro.

Valores monetários são sempre representados em centavos. Isso mantém os
cálculos exatos e impede que a camada de interface introduza erros de float.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional


class TransactionType(str, Enum):
    INCOME = "receita"
    EXPENSE = "despesa"
    INVESTMENT = "investimento"

    @property
    def label(self) -> str:
        return {
            TransactionType.INCOME: "Receita",
            TransactionType.EXPENSE: "Despesa",
            TransactionType.INVESTMENT: "Investimento",
        }[self]

    @classmethod
    def from_value(cls, value: str | "TransactionType") -> "TransactionType":
        if isinstance(value, cls):
            return value
        normalized = str(value).strip().lower()
        aliases = {"receita": cls.INCOME, "despesa": cls.EXPENSE, "investimento": cls.INVESTMENT}
        try:
            return aliases.get(normalized, cls(normalized))
        except ValueError as exc:
            raise ValueError("Tipo de movimentação inválido.") from exc


def _validate_name(value: str, field: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise ValueError(f"{field} é obrigatório.")
    if len(normalized) > 120:
        raise ValueError(f"{field} deve ter no máximo 120 caracteres.")
    return normalized


@dataclass(frozen=True)
class FinancialCategory:
    name: str
    transaction_type: TransactionType
    color: str = "#24C270"
    id: Optional[int] = None
    active: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _validate_name(self.name, "Nome da categoria"))
        object.__setattr__(self, "transaction_type", TransactionType.from_value(self.transaction_type))
        color = (self.color or "").strip()
        if len(color) != 7 or not color.startswith("#"):
            raise ValueError("A cor da categoria deve estar no formato #RRGGBB.")
        try:
            int(color[1:], 16)
        except ValueError as exc:
            raise ValueError("A cor da categoria deve estar no formato #RRGGBB.") from exc
        object.__setattr__(self, "color", color.upper())


@dataclass(frozen=True)
class FinancialTransaction:
    transaction_type: TransactionType
    description: str
    amount_cents: int
    category_id: int
    occurred_on: date
    notes: str = ""
    id: Optional[int] = None
    category_name: str = ""
    category_color: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "transaction_type", TransactionType.from_value(self.transaction_type))
        object.__setattr__(self, "description", _validate_name(self.description, "Descrição"))
        if not isinstance(self.amount_cents, int) or isinstance(self.amount_cents, bool) or self.amount_cents <= 0:
            raise ValueError("O valor deve ser maior que zero.")
        if not isinstance(self.category_id, int) or self.category_id <= 0:
            raise ValueError("Selecione uma categoria válida.")
        if not isinstance(self.occurred_on, date):
            raise ValueError("A data da movimentação é inválida.")
        if len(self.notes or "") > 1000:
            raise ValueError("A observação deve ter no máximo 1000 caracteres.")


@dataclass(frozen=True)
class FinancialSummary:
    income_cents: int = 0
    expense_cents: int = 0
    investment_cents: int = 0

    @property
    def available_balance_cents(self) -> int:
        return self.income_cents - self.expense_cents - self.investment_cents

    @property
    def investment_rate(self) -> float:
        return (self.investment_cents / self.income_cents * 100) if self.income_cents else 0.0
