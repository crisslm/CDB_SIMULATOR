"""
Utilitários financeiros puros (sem dependência de UI ou repositório).
=====================================================================

Contém funções estáticas que antes estavam em ``FinancialService``
mas não usam ``self`` nem acessam o banco de dados. Separá-las melhora
o Single Responsibility Principle e permite reutilização em outros
contextos (ex: relatórios, exportação, API futura).

Princípio: SRP — cada função tem uma responsabilidade bem definida.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional

from .financial_models import (
    FinancialCategory,
    FinancialSummary,
    FinancialTransaction,
    TransactionType,
)


# =========================================================================
# Parsing de valores e datas
# =========================================================================

def parse_amount_to_cents(value: str | int | Decimal) -> int:
    """
    Converte uma string de valor monetário no formato brasileiro para centavos (int).

    Formatos aceitos:
        - "1.250,50"  -> 125050
        - "1250,50"   -> 125050
        - "1.250"     -> 125000
        - "R$ 1.250,50" -> 125050
        - "1 250,50"  -> 125050

    Parâmetros:
        value: String, int ou Decimal representando um valor monetário.

    Retorna:
        int: Valor em centavos (ex: R$ 1,50 -> 150).

    Levanta:
        ValueError: Se o valor for inválido, vazio, ou menor/igual a zero.
    """
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
    """
    Formata um valor em centavos para string monetária brasileira.

    Exemplo:
        125050 -> "R$ 1.250,50"
        500    -> "R$ 5,00"

    Parâmetros:
        cents (int): Valor em centavos.

    Retorna:
        str: String formatada no padrão "R$ 1.250,50".
    """
    return f"R$ {cents / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_br_date(value: str | date) -> date:
    """
    Converte uma string de data no formato brasileiro para objeto date.

    Formatos aceitos:
        - "03/11/2026" (DD/MM/AAAA)
        - "2026-11-03" (ISO AAAA-MM-DD)

    Parâmetros:
        value: String de data ou objeto date (retornado como está).

    Retorna:
        date: Objeto date correspondente.

    Levanta:
        ValueError: Se a data for inválida ou estiver em formato não reconhecido.
    """
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


# =========================================================================
# Períodos de filtro
# =========================================================================

def period_range(
    period: str,
    reference: date | None = None,
    custom_start: date | None = None,
    custom_end: date | None = None,
) -> tuple[date | None, date | None]:
    """
    Converte uma string de período em intervalo de datas (start, end).

    Períodos suportados:
        - "Todo o período": Retorna (None, None) - sem filtro de data.
        - "Mês atual": Do dia 1 do mês atual até hoje.
        - "Mês anterior": Do dia 1 até o último dia do mês anterior.
        - "Últimos 3 meses": Do dia 1 do mês (atual - 2) até hoje.
        - "Últimos 6 meses": Idem, 6 meses.
        - "Últimos 12 meses": Idem, 12 meses.
        - "Período personalizado": Usa custom_start e custom_end.

    Parâmetros:
        period: String identificando o período.
        reference: Data de referência (padrão: hoje).
        custom_start: Data inicial para período personalizado.
        custom_end: Data final para período personalizado.

    Retorna:
        tuple[date | None, date | None]: (data_inicial, data_final).

    Levanta:
        ValueError: Se o período for inválido ou personalizado sem datas válidas.
    """
    today = reference or date.today()
    period = (period or "Mês atual").strip()

    def month_start(year: int, month: int) -> date:
        return date(year, month, 1)

    if period == "Todo o período":
        return None, None
    if period == "Período personalizado":
        if not custom_start or not custom_end or custom_start > custom_end:
            raise ValueError("Informe um período personalizado válido.")
        return custom_start, custom_end
    months = {
        "Mês atual": 1,
        "Mês anterior": 1,
        "Últimos 3 meses": 3,
        "Últimos 6 meses": 6,
        "Últimos 12 meses": 12,
    }.get(period)
    if months is None:
        raise ValueError("Período inválido.")
    end_anchor = month_start(today.year, today.month)
    if period == "Mês anterior":
        end = end_anchor - timedelta(days=1)
        return month_start(end.year, end.month), end
    start_year, start_month = today.year, today.month - months + 1
    while start_month <= 0:
        start_year -= 1
        start_month += 12
    return month_start(start_year, start_month), today


# =========================================================================
# Agregações em Python (loop) — mantidas para retrocompatibilidade
# =========================================================================

def summary_for(transactions: list[FinancialTransaction]) -> FinancialSummary:
    """
    Calcula resumo financeiro a partir de uma lista de transações (loop Python).

    Para uso novo, prefira consultas SQL agregadas no repositório (mais eficiente).

    Parâmetros:
        transactions: Lista de transações já filtradas.

    Retorna:
        FinancialSummary: Totais de receitas, despesas e investimentos.
    """
    totals = defaultdict(int)
    for item in transactions:
        totals[item.transaction_type] += item.amount_cents
    return FinancialSummary(
        totals[TransactionType.INCOME],
        totals[TransactionType.EXPENSE],
        totals[TransactionType.INVESTMENT],
    )


def expense_by_category(
    transactions: list[FinancialTransaction],
) -> list[tuple[str, int, str]]:
    """
    Agrupa despesas por categoria a partir de uma lista (loop Python).

    Para uso novo, prefira ``expense_by_category_sql`` no repositório.

    Parâmetros:
        transactions: Lista de transações filtradas.

    Retorna:
        list[tuple[str, int, str]]: (nome, total_centavos, cor).
    """
    totals: dict[tuple[str, str], int] = defaultdict(int)
    for item in transactions:
        if item.transaction_type == TransactionType.EXPENSE:
            totals[(item.category_name, item.category_color or "#8E8E93")] += item.amount_cents
    return [
        (name, amount, color)
        for (name, color), amount in sorted(
            totals.items(), key=lambda item: item[1], reverse=True
        )
    ]


def allocation(transactions: list[FinancialTransaction]) -> list[tuple[str, int, str]]:
    """
    Retorna alocação financeira (despesas por categoria + investimentos).

    Para uso novo, prefira ``allocation_sql`` no repositório.

    Parâmetros:
        transactions: Lista de transações filtradas.

    Retorna:
        list[tuple[str, int, str]]: Alocação incluindo categoria "Investimentos".
    """
    result = expense_by_category(transactions)
    invested = sum(
        item.amount_cents
        for item in transactions
        if item.transaction_type == TransactionType.INVESTMENT
    )
    if invested:
        result.append(("Investimentos", invested, "#24C270"))
    return result


def monthly_expenses(
    transactions: list[FinancialTransaction],
) -> list[tuple[str, int]]:
    """
    Agrupa despesas por mês (AAAA-MM) a partir de uma lista (loop Python).

    Para uso novo, prefira ``monthly_expenses_sql`` no repositório.

    Parâmetros:
        transactions: Lista de transações filtradas.

    Retorna:
        list[tuple[str, int]]: ("AAAA-MM", total_centavos).
    """
    totals: dict[str, int] = defaultdict(int)
    for item in transactions:
        if item.transaction_type == TransactionType.EXPENSE:
            totals[item.occurred_on.strftime("%Y-%m")] += item.amount_cents
    return sorted(totals.items())


# =========================================================================
# Categorias padrão
# =========================================================================

DEFAULT_CATEGORIES = (
    # (nome, tipo, cor_hex)
    # Receitas
    ("Salário", TransactionType.INCOME, "#24C270"),
    ("Freelance", TransactionType.INCOME, "#4F8CFF"),
    ("Dividendos", TransactionType.INCOME, "#A970FF"),
    ("Rendimentos", TransactionType.INCOME, "#32B8C6"),
    ("Outros", TransactionType.INCOME, "#8E8E93"),
    # Despesas
    ("Alimentação", TransactionType.EXPENSE, "#FF9F43"),
    ("Transporte", TransactionType.EXPENSE, "#4F8CFF"),
    ("Moradia", TransactionType.EXPENSE, "#FF6B6B"),
    ("Saúde", TransactionType.EXPENSE, "#A970FF"),
    ("Educação", TransactionType.EXPENSE, "#32B8C6"),
    ("Lazer", TransactionType.EXPENSE, "#F368E0"),
    ("Assinaturas", TransactionType.EXPENSE, "#8395A7"),
    ("Compras", TransactionType.EXPENSE, "#F9CA24"),
    ("Contas", TransactionType.EXPENSE, "#576574"),
    ("Outros", TransactionType.EXPENSE, "#8E8E93"),
    # Investimentos
    ("CDB", TransactionType.INVESTMENT, "#24C270"),
    ("Tesouro Direto", TransactionType.INVESTMENT, "#4F8CFF"),
    ("Ações", TransactionType.INVESTMENT, "#FF9F43"),
    ("Fundos Imobiliários", TransactionType.INVESTMENT, "#A970FF"),
    ("ETFs", TransactionType.INVESTMENT, "#32B8C6"),
    ("Criptomoedas", TransactionType.INVESTMENT, "#F9CA24"),
    ("Reserva de Emergência", TransactionType.INVESTMENT, "#6FE29F"),
    ("Outros", TransactionType.INVESTMENT, "#8E8E93"),
)
