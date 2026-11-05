"""
Camada de Serviços - Controle Financeiro (Casos de Uso)
======================================================

Este módulo implementa os casos de uso e agregações do Controle Financeiro Pessoal,
funcionando como intermediário entre a Interface (UI) e o Repositório.

Responsabilidades:
    1. Validar e processar entradas do usuário (valores, datas, categorias).
    2. Coordenar operações de leitura/escrita no repositório.
    3. Calcular resumos, alocações e relatórios financeiros.
    4. Gerenciar períodos de filtro (mês atual, últimos 3 meses, etc.).

Princípio SOLID: Single Responsibility Principle (SRP)
- Cada método trata um caso de uso específico.
- Não contém lógica de interface (não importa módulos de UI).

Camada: Serviços (regras de negócio / casos de uso)
Depende de: src.domain.financial_models, src.repositories.financial_repository

Autor: CDB Simulator
Versão: 1.0.0
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Optional

from ..domain.financial_models import FinancialCategory, FinancialSummary, FinancialTransaction, TransactionType
from ..domain.financial_utils import (
    DEFAULT_CATEGORIES,
    allocation,
    expense_by_category,
    format_cents,
    monthly_expenses,
    parse_amount_to_cents,
    parse_br_date,
    period_range,
    summary_for,
)
from ..repositories.financial_repository import FinancialRepository


# Observação: DEFAULT_CATEGORIES é importado de financial_utils para
# evitar duplicação. Elas são inseridas no banco pelo
# FinancialRepository._initialize() e mantidas aqui para retrocompatibilidade.


# =============================================================================
# Classe Principal: FinancialService
# =============================================================================

class FinancialService:
    """
    Serviço de casos de uso do Controle Financeiro.

    Coordena operações entre a UI e o FinancialRepository, adicionando validações
    de negócio e lógica de agregação.

    Atributos:
        repository (FinancialRepository): Instância do repositório de persistência.

    Exemplo de uso:
        service = FinancialService(database_path="banco.sqlite3")
        service.create_transaction("receita", "Salário", "5.000,00", cat_id, "03/11/2026")
        summary = service.summary(period="Mês atual", reference=date(2026, 11, 3))
    """

    def __init__(self, repository: FinancialRepository | None = None, database_path: str | Path | None = None):
        """
        Inicializa o serviço com um repositório (ou cria um novo).

        Parâmetros:
            repository: Repositório existente ou None para criar um novo.
            database_path: Caminho do banco (usado se repository for None).
        """
        self.repository = repository or FinancialRepository(database_path)
        # Categorias padrão são inseridas uma única vez no _initialize() do repositório.
        # Mantemos a chamada para retrocompatibilidade, mas ela é um no-op se já existirem.
        self.ensure_default_categories()

    def ensure_default_categories(self) -> None:
        """
        Garante que as categorias padrão existam no banco.

        Se o banco já tiver categorias (ativa ou inativa), não faz nada.
        Caso contrário, insere a lista DEFAULT_CATEGORIES.

        Observação: A inserção real ocorre no FinancialRepository._initialize().
        Este método é mantido para retrocompatibilidade.
        """
        if self.repository.list_categories(active_only=False):
            return
        for name, kind, color in DEFAULT_CATEGORIES:
            self.repository.add_category(FinancialCategory(name, kind, color))

    # -------------------------------------------------------------------------
    # Períodos de Filtro (delegado para financial_utils)
    # -------------------------------------------------------------------------

    @staticmethod
    def period_range(period: str, reference: date | None = None, custom_start: date | None = None,
                     custom_end: date | None = None) -> tuple[date | None, date | None]:
        """
        Converte uma string de período em intervalo de datas (start, end).

        Delegado para ``src.domain.financial_utils.period_range``.
        """
        return period_range(period, reference, custom_start, custom_end)

    # -------------------------------------------------------------------------
    # Categorias
    # -------------------------------------------------------------------------

    def categories(self, transaction_type: TransactionType | str | None = None, active_only: bool = True) -> list[FinancialCategory]:
        """
        Retorna lista de categorias, com filtro opcional de tipo.

        Parâmetros:
            transaction_type: Tipo (receita/despesa/investimento) ou None para todos.
            active_only: Se True, retorna apenas categorias ativas.

        Retorna:
            list[FinancialCategory]: Categorias filtradas.
        """
        return self.repository.list_categories(TransactionType.from_value(transaction_type) if transaction_type else None, active_only)

    def create_category(self, name: str, transaction_type: TransactionType | str, color: str) -> FinancialCategory:
        """
        Cria uma nova categoria.

        Parâmetros:
            name: Nome da categoria.
            transaction_type: Tipo da categoria.
            color: Cor hexadecimal (#RRGGBB).

        Retorna:
            FinancialCategory: Categoria criada com ID atribuído.
        """
        return self.repository.add_category(FinancialCategory(name, TransactionType.from_value(transaction_type), color))

    def update_category(self, category_id: int, name: str, transaction_type: TransactionType | str, color: str,
                        active: bool = True) -> FinancialCategory:
        """
        Atualiza uma categoria existente pelo ID.

        Parâmetros:
            category_id: ID da categoria.
            name: Novo nome.
            transaction_type: Novo tipo.
            color: Nova cor.
            active: Se está ativa ou arquivada.

        Retorna:
            FinancialCategory: Categoria atualizada.
        """
        return self.repository.update_category(FinancialCategory(name, TransactionType.from_value(transaction_type), color, category_id, active))

    def delete_or_archive_category(self, category_id: int, archive_if_in_use: bool = True) -> str:
        """
        Tenta excluir uma categoria. Se tiver lançamentos, a arquiva (se archive_if_in_use=True).

        Parâmetros:
            category_id: ID da categoria.
            archive_if_in_use: Se True, arquiva ao invés de falhar quando há lançamentos.

        Retorna:
            str: "deleted" se excluída, "archived" se arquivada.

        Levanta:
            ValueError: Se archive_if_in_use=False e a categoria tem lançamentos.
        """
        try:
            self.repository.delete_category(category_id)
            return "deleted"
        except ValueError:
            if not archive_if_in_use:
                raise
            self.repository.archive_category(category_id)
            return "archived"

    # -------------------------------------------------------------------------
    # Transações
    # -------------------------------------------------------------------------

    def _make_transaction(self, transaction_type, description, amount, category_id, occurred_on, notes="", transaction_id=None) -> FinancialTransaction:
        """
        Cria um objeto FinancialTransaction validando entradas.

        Verifica:
            1. A categoria existe.
            2. O tipo da categoria corresponde ao tipo da transação.
            3. O valor é válido (converte para centavos).
            4. A data é válida.

        Este é um método privado (_prefixo) usado internamente por
        create_transaction e update_transaction.

        Parâmetros:
            transaction_type: Tipo da transação.
            description: Descrição.
            amount: Valor em string (ex: "1.250,50").
            category_id: ID da categoria.
            occurred_on: Data da ocorrência.
            notes: Observações opcionais.
            transaction_id: ID se for atualização.

        Retorna:
            FinancialTransaction: Objeto validado e pronto para salvar.
        """
        kind = TransactionType.from_value(transaction_type)
        category = self.repository.get_category(int(category_id))
        if not category:
            raise ValueError("Categoria não encontrada.")
        if category.transaction_type != kind:
            raise ValueError("A categoria deve pertencer ao mesmo tipo do lançamento.")
        return FinancialTransaction(kind, description, parse_amount_to_cents(amount), int(category_id), parse_br_date(occurred_on), notes or "", transaction_id)

    def create_transaction(self, transaction_type, description: str, amount, category_id: int, occurred_on, notes: str = "") -> FinancialTransaction:
        """
        Cria uma nova transação financeira.

        Parâmetros:
            transaction_type: Tipo (receita/despesa/investimento).
            description: Descrição do lançamento.
            amount: Valor em string brasileira.
            category_id: ID da categoria.
            occurred_on: Data da ocorrência.
            notes: Observações opcionais.

        Retorna:
            FinancialTransaction: Transação criada com ID atribuído.
        """
        return self.repository.add_transaction(self._make_transaction(transaction_type, description, amount, category_id, occurred_on, notes))

    def update_transaction(self, transaction_id: int, transaction_type, description: str, amount, category_id: int, occurred_on, notes: str = "") -> FinancialTransaction:
        """
        Atualiza uma transação existente pelo ID.

        Parâmetros:
            transaction_id: ID da transação.
            transaction_type: Novo tipo.
            description: Nova descrição.
            amount: Novo valor.
            category_id: Novo ID da categoria.
            occurred_on: Nova data.
            notes: Novas observações.

        Retorna:
            FinancialTransaction: Transação atualizada.
        """
        return self.repository.update_transaction(self._make_transaction(transaction_type, description, amount, category_id, occurred_on, notes, transaction_id))

    def delete_transaction(self, transaction_id: int) -> None:
        """
        Exclui uma transação pelo ID.

        Parâmetros:
            transaction_id: ID da transação a ser excluída.
        """
        self.repository.delete_transaction(transaction_id)

    # -------------------------------------------------------------------------
    # Consultas e Relatórios
    # -------------------------------------------------------------------------

    def transactions(self, period: str = "Todo o período", transaction_type: TransactionType | str | None = None,
                     category_id: int | None = None, custom_start: date | None = None, custom_end: date | None = None,
                     reference: date | None = None) -> list[FinancialTransaction]:
        """
        Retorna lista de transações filtradas por período, tipo e categoria.

        Parâmetros:
            period: String do período (ex: "Mês atual", "Últimos 3 meses").
            transaction_type: Filtro por tipo de transação.
            category_id: Filtro por ID de categoria.
            custom_start: Data inicial (para período personalizado).
            custom_end: Data final (para período personalizado).
            reference: Data de referência (padrão: hoje).

        Retorna:
            list[FinancialTransaction]: Transações ordenadas por data desc.
        """
        start, end = self.period_range(period, reference, custom_start, custom_end)
        kind = TransactionType.from_value(transaction_type) if transaction_type else None
        return self.repository.list_transactions(start, end, kind, category_id)

    @staticmethod
    def summary_for(transactions: list[FinancialTransaction]) -> FinancialSummary:
        """
        Calcula resumo financeiro a partir de uma lista de transações (loop Python).

        Este método é mantido para retrocompatibilidade. Para uso novo, prefira
        summary_sql() que consulta diretamente o banco via SQL (mais eficiente).

        Parâmetros:
            transactions: Lista de transações já filtradas.

        Retorna:
            FinancialSummary: Totais de receitas, despesas e investimentos.
        """
        return summary_for(transactions)

    def summary(self, **filters) -> FinancialSummary:
        """
        Retorna resumo financeiro agregado diretamente via SQL.

        Delegando para summary_sql(), que usa SUM(CASE...) no banco,
        evitando carregar todas as transações para o Python.

        Parâmetros:
            **filters: Mesmos parâmetros de summary_sql (period, transaction_type, etc.)

        Retorna:
            FinancialSummary: Resumo financeiro.
        """
        return self.summary_sql(**filters)

    @staticmethod
    def expense_by_category(transactions: list[FinancialTransaction]) -> list[tuple[str, int, str]]:
        """
        Agrupa despesas por categoria a partir de uma lista (loop Python).

        Mantido para retrocompatibilidade. Prefira expense_by_category_sql() para novo código.

        Parâmetros:
            transactions: Lista de transações filtradas.

        Retorna:
            list[tuple[str, int, str]]: (nome, total_centavos, cor).
        """
        return expense_by_category(transactions)

    @staticmethod
    def allocation(transactions: list[FinancialTransaction]) -> list[tuple[str, int, str]]:
        """
        Retorna alocação financeira (despesas por categoria + investimentos).

        Mantido para retrocompatibilidade. Prefira allocation_sql() para novo código.

        Parâmetros:
            transactions: Lista de transações filtradas.

        Retorna:
            list[tuple[str, int, str]]: Alocação incluindo categoria "Investimentos".
        """
        return allocation(transactions)

    @staticmethod
    def monthly_expenses(transactions: list[FinancialTransaction]) -> list[tuple[str, int]]:
        """
        Agrupa despesas por mês (AAAA-MM) a partir de uma lista (loop Python).

        Mantido para retrocompatibilidade. Prefira monthly_expenses_sql() para novo código.

        Parâmetros:
            transactions: Lista de transações filtradas.

        Retorna:
            list[tuple[str, int]]: ("AAAA-MM", total_centavos).
        """
        return monthly_expenses(transactions)

    # -------------------------------------------------------------------------
    # Versões SQL (mais eficientes - consultam diretamente o banco)
    # -------------------------------------------------------------------------

    def summary_sql(self, period: str = "Todo o período", transaction_type: TransactionType | str | None = None,
                    category_id: int | None = None, custom_start: date | None = None,
                    custom_end: date | None = None, reference: date | None = None) -> FinancialSummary:
        """
        Retorna resumo financeiro consultando diretamente o banco via SQL.

        Usa SUM(CASE ...) no SQLite, evitando carregar todas as transações
        para o Python. É significativamente mais rápido para muitos registros.

        Parâmetros:
            period: String do período.
            transaction_type: Filtro por tipo.
            category_id: Filtro por categoria.
            custom_start, custom_end: Datas para período personalizado.
            reference: Data de referência.

        Retorna:
            FinancialSummary: Totais agregados.
        """
        start, end = self.period_range(period, reference, custom_start, custom_end)
        kind = TransactionType.from_value(transaction_type) if transaction_type else None
        return self.repository.summary_sql(start, end, kind, category_id)

    def expense_by_category_sql(self, period: str = "Todo o período",
                                category_id: int | None = None, custom_start: date | None = None,
                                custom_end: date | None = None, reference: date | None = None
                                ) -> list[tuple[str, int, str]]:
        """
        Retorna despesas agregadas por categoria via SQL GROUP BY.

        Parâmetros:
            period: String do período.
            category_id: Filtro por categoria.
            custom_start, custom_end: Datas para período personalizado.
            reference: Data de referência.

        Retorna:
            list[tuple[str, int, str]]: (nome_categoria, total_centavos, cor_hex).
        """
        start, end = self.period_range(period, reference, custom_start, custom_end)
        return self.repository.expense_by_category_sql(start, end, category_id)

    def allocation_sql(self, period: str = "Todo o período",
                       category_id: int | None = None, custom_start: date | None = None,
                       custom_end: date | None = None, reference: date | None = None
                       ) -> list[tuple[str, int, str]]:
        """
        Retorna alocação financeira (despesas por categoria + total investido).

        Combina despesas por categoria com o total de investimentos no período.

        Parâmetros:
            period: String do período.
            category_id: Filtro por categoria.
            custom_start, custom_end: Datas para período personalizado.
            reference: Data de referência.

        Retorna:
            list[tuple[str, int, str]]: Alocação incluindo categoria "Investimentos".
        """
        result = self.expense_by_category_sql(period, category_id, custom_start, custom_end, reference)
        start, end = self.period_range(period, reference, custom_start, custom_end)
        invested = self.repository.summary_sql(start, end, TransactionType.INVESTMENT, category_id).investment_cents
        if invested:
            result = list(result)
            result.append(("Investimentos", invested, "#24C270"))
        return result

    def monthly_expenses_sql(self, period: str = "Todo o período",
                             category_id: int | None = None, custom_start: date | None = None,
                             custom_end: date | None = None, reference: date | None = None
                             ) -> list[tuple[str, int]]:
        """
        Retorna despesas agregadas por mês via SQL GROUP BY.

        Parâmetros:
            period: String do período.
            category_id: Filtro por categoria.
            custom_start, custom_end: Datas para período personalizado.
            reference: Data de referência.

        Retorna:
            list[tuple[str, int]]: ("AAAA-MM", total_centavos).
        """
        start, end = self.period_range(period, reference, custom_start, custom_end)
        return self.repository.monthly_expenses_sql(start, end, category_id)
