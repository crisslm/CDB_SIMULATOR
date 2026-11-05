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

from src.domain.financial_models import FinancialCategory, FinancialSummary, FinancialTransaction, TransactionType
from src.repositories.financial_repository import FinancialRepository


# =============================================================================
# Categorias Padrão
# =============================================================================

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

# Observação: Estas mesmas categorias são inseridas no banco pelo
# FinancialRepository._initialize(). Elas são mantidas aqui para retrocompatibilidade
# e uso pelo FinancialService.ensure_default_categories().


# =============================================================================
# Funções Utilitárias
# =============================================================================

def parse_amount_to_cents(value: str | int | Decimal) -> int:
    """
    Converte uma string de valor monetário no formato brasileiro para centavos (int).

    Formatos aceitos:
        - "1.250,50"  -> 125050
        - "1250,50"   -> 125050
        - "1.250"     -> 125000
        - "R$ 1.250,50" -> 125050
        - "1 250,50"  -> 125050

    Regras de parsing:
        1. Remove "R$", espaços.
        2. Se tiver vírgula e ponto:
           - Se vírgula for o último separador (formato BR): remove pontos, troca vírgula por ponto.
           - Senão (formato EN): remove vírgulas.
        3. Se tiver apenas vírgula: troca por ponto.
        4. Se tiver múltiplos pontos: remove todos (formato milhar sem decimal).
        5. Converte para Decimal com 2 casas, arredondamento ROUND_HALF_UP.
        6. Multiplica por 100 e converte para int (centavos).

    Parâmetros:
        value: String, int ou Decimal representando um valor monetário.

    Retorna:
        int: Valor em centavos (ex: R$ 1,50 -> 150).

    Levanta:
        ValueError: Se o valor for inválido, vazio, ou menor/igual a zero.

    Exemplo:
        >>> parse_amount_to_cents("1.250,50")
        125050
        >>> parse_amount_to_cents("R$ 100")
        10000
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
    # Períodos de Filtro
    # -------------------------------------------------------------------------

    @staticmethod
    def period_range(period: str, reference: date | None = None, custom_start: date | None = None,
                     custom_end: date | None = None) -> tuple[date | None, date | None]:
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
        totals = defaultdict(int)
        for item in transactions:
            totals[item.transaction_type] += item.amount_cents
        return FinancialSummary(totals[TransactionType.INCOME], totals[TransactionType.EXPENSE], totals[TransactionType.INVESTMENT])

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
        totals: dict[tuple[str, str], int] = defaultdict(int)
        for item in transactions:
            if item.transaction_type == TransactionType.EXPENSE:
                totals[(item.category_name, item.category_color or "#8E8E93")] += item.amount_cents
        return [(name, amount, color) for (name, color), amount in sorted(totals.items(), key=lambda item: item[1], reverse=True)]

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
        result = FinancialService.expense_by_category(transactions)
        invested = sum(item.amount_cents for item in transactions if item.transaction_type == TransactionType.INVESTMENT)
        if invested:
            result.append(("Investimentos", invested, "#24C270"))
        return result

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
        totals: dict[str, int] = defaultdict(int)
        for item in transactions:
            if item.transaction_type == TransactionType.EXPENSE:
                totals[item.occurred_on.strftime("%Y-%m")] += item.amount_cents
        return sorted(totals.items())

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
            list[tuple[str, int, str]]: (nome_categoria, total_centavos, cor).
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