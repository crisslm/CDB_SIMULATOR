"""
Entidades Puras do Controle Financeiro
======================================

Este módulo contém as classes de dados (dataclasses) e o enum usado no
módulo de Controle Financeiro Pessoal (receitas, despesas, investimentos).

Princípio de design:
- Valores monetários são SEMPRE representados em CENTAVOS (inteiros).
  Isso elimina erros de ponto flutuante (float) em cálculos monetários.
  Ex: R$ 1,50 é armazenado como 150 (centavos).
- Todas as classes são imutáveis (frozen=True) para evitar modificações
  acidentais após a criação.

Princípio SOLID: Single Responsibility Principle (SRP)
- Cada classe representa uma entidade específica do domínio financeiro.
- Não há dependência de UI, banco de dados ou serviços externos.

Autor: CDB Simulator
Versão: 1.0.0
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional


class TransactionType(str, Enum):
    """
    Enumeração dos tipos de movimentação financeira.

    Usa str como tipo base para facilitar serialização e comparação com strings
    vindas do banco de dados ou da UI.

    Valores possíveis:
        INCOME   = "receita"   (dinheiro entrando, ex: salário)
        EXPENSE  = "despesa"   (dinheiro saindo, ex: mercado)
        INVESTMENT = "investimento" (dinheiro aplicado, ex: CDB)

    Exemplo de uso:
        >>> tipo = TransactionType.INCOME
        >>> tipo.label
        'Receita'
        >>> tipo.value
        'receita'
    """

    INCOME = "receita"
    EXPENSE = "despesa"
    INVESTMENT = "investimento"

    @property
    def label(self) -> str:
        """
        Retorna a versão amigável (em português) do tipo para exibição na UI.

        Retorna:
            str: "Receita", "Despesa" ou "Investimento".
        """
        return {
            TransactionType.INCOME: "Receita",
            TransactionType.EXPENSE: "Despesa",
            TransactionType.INVESTMENT: "Investimento",
        }[self]

    @classmethod
    def from_value(cls, value: str | "TransactionType") -> "TransactionType":
        """
        Converte uma string ou enum em TransactionType, aceitando aliases.

        Útil para normalizar dados vindos do banco de dados ou de inputs do usuário.

        Parâmetros:
            value: Pode ser uma string ("receita", "RECEITA", " Receita ")
                   ou já uma instância de TransactionType.

        Retorna:
            TransactionType: O enum correspondente.

        Levanta:
            ValueError: Se o valor não puder ser convertido.

        Exemplo:
            >>> TransactionType.from_value("receita")
            <TransactionType.INCOME: 'receita'>
            >>> TransactionType.from_value("despesa")
            <TransactionType.EXPENSE: 'despesa'>
        """
        if isinstance(value, cls):
            return value
        normalized = str(value).strip().lower()
        aliases = {
            "receita": cls.INCOME,
            "despesa": cls.EXPENSE,
            "investimento": cls.INVESTMENT,
        }
        try:
            return aliases.get(normalized, cls(normalized))
        except ValueError as exc:
            raise ValueError("Tipo de movimentação inválido.") from exc


def _validate_name(value: str, field: str) -> str:
    """
    Valida e normaliza um nome de campo (nome da categoria ou descrição).

    Esta é uma função privada (prefixo _), usada internamente pelas classes
    FinancialCategory e FinancialTransaction.

    Regras de validação:
        1. Não pode estar vazio ou conter apenas espaços.
        2. Não pode exceder 120 caracteres.

    Parâmetros:
        value (str): Valor bruto a ser validado.
        field (str): Nome do campo (usado apenas na mensagem de erro).

    Retorna:
        str: O valor normalizado (trimado).

    Levanta:
        ValueError: Se o valor for vazio ou exceder 120 caracteres.

    Observação de manutenção:
        Se mudar o limite de caracteres, atualize também:
        1. A mensagem de erro
        2. Os testes em tests/test_domain.py e tests/test_financial.py
        3. A documentação (README.md / DOCUMENTACAO_TECNICA.txt)
    """
    normalized = (value or "").strip()
    if not normalized:
        raise ValueError(f"{field} é obrigatório.")
    if len(normalized) > 120:
        raise ValueError(f"{field} deve ter no máximo 120 caracteres.")
    return normalized


@dataclass(frozen=True)
class FinancialCategory:
    """
    Representa uma categoria de movimentação financeira.

    Categorias agrupam lançamentos similares (ex: "Alimentação", "Salário", "CDB")
    e permitem filtrar e agrupar relatórios.

    Atributos:
        name (str): Nome da categoria (ex: "Salário", "Alimentação").
                    Máximo 120 caracteres, não pode estar vazio.
        transaction_type (TransactionType): Tipo da categoria (receita/despesa/investimento).
        color (str): Cor hexadecimal (#RRGGBB) para exibição na UI.
                     Padrão: "#24C270" (verde).
        id (Optional[int]): ID do banco de dados. None se ainda não foi salva.
        active (bool): Se True, a categoria está ativa. Se False, está arquivada.
                       Categorias arquivadas não aparecem em novos lançamentos
                       mas mantêm o histórico.

    Exemplo de criação:
        cat = FinancialCategory(
            name="Salário",
            transaction_type=TransactionType.INCOME,
            color="#24C270"
        )

    Observação de manutenção:
        - A validação de nome e cor ocorre automaticamente em __post_init__.
        - Como é frozen=True, para alterar um valor você deve criar uma nova instância.
    """
    name: str
    transaction_type: TransactionType
    color: str = "#24C270"
    id: Optional[int] = None
    active: bool = True

    def __post_init__(self) -> None:
        """
        Método chamado automaticamente após a criação da dataclass.

        Como frozen=True impede atribuição direta, usamos object.__setattr__
        para modificar os campos após a validação.

        Validações realizadas:
            1. Nome não vazio e com até 120 caracteres.
            2. transaction_type convertido corretamente via from_value.
            3. Cor no formato hexadecimal #RRGGBB válido.
        """
        object.__setattr__(self, "name", _validate_name(self.name, "Nome da categoria"))
        object.__setattr__(self, "transaction_type", TransactionType.from_value(self.transaction_type))
        color = (self.color or "").strip()
        if len(color) != 7 or not color.startswith("#"):
            raise ValueError("A cor da categoria deve estar no formato #RRGGBB.")
        try:
            int(color[1:], 16)  # Tenta converter a parte hexadecimal para inteiro
        except ValueError as exc:
            raise ValueError("A cor da categoria deve estar no formato #RRGGBB.") from exc
        object.__setattr__(self, "color", color.upper())


@dataclass(frozen=True)
class FinancialTransaction:
    """
    Representa uma única movimentação financeira (receita, despesa ou investimento).

    Esta é a entidade central do Controle Financeiro. Cada lançamento representa
    um movimento de dinheiro com valor, categoria, data e descrição.

    Atributos:
        transaction_type (TransactionType): Tipo da movimentação.
        description (str): Descrição do lançamento (ex: "Salário novembro").
                           Máximo 120 caracteres.
        amount_cents (int): Valor em CENTAVOS (inteiro).
                            Ex: R$ 1.250,50 = 125050 centavos.
                            Deve ser maior que zero.
        category_id (int): ID da categoria associada no banco de dados.
        occurred_on (date): Data em que a movimentação ocorreu.
        notes (str): Observações opcionais (máximo 1000 caracteres).
        id (Optional[int]): ID no banco de dados. None se novo lançamento.
        category_name (str): Nome da categoria (preenchido pelo repositório após join).
        category_color (str): Cor da categoria (preenchido pelo repositório após join).

    Exemplo de criação:
        tx = FinancialTransaction(
            transaction_type=TransactionType.EXPENSE,
            description="Mercado",
            amount_cents=35050,  # R$ 350,50
            category_id=5,
            occurred_on=date(2026, 11, 3),
            notes="Cartão de crédito"
        )

    Observação de manutenção:
        - Validações ocorrem automaticamente em __post_init__.
        - O campo amount_cents usa centavos para evitar erros de ponto flutuante.
    """
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
        """
        Validações automáticas após a criação da transação.

        Verifica:
            1. Tipo de transação válido.
            2. Descrição não vazia e com até 120 caracteres.
            3. Valor em centavos é inteiro positivo (não bool, não zero, não negativo).
            4. category_id é inteiro positivo.
            5. occurred_on é uma instância válida de date.
            6. notes tem no máximo 1000 caracteres.
        """
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
    """
    Resumo financeiro agregado de um período.

    Contém os totais de receitas, despesas e investimentos em centavos,
    além de propriedades calculadas como saldo disponível e taxa de investimento.

    Atributos:
        income_cents (int): Total de receitas em centavos.
        expense_cents (int): Total de despesas em centavos.
        investment_cents (int): Total de investimentos em centavos.

    Propriedades calculadas:
        available_balance_cents (int): Saldo disponível = receitas - despesas - investimentos.
        investment_rate (float): Percentual da renda investida (0-100).

    Exemplo:
        summary = FinancialSummary(income_cents=500000, expense_cents=150000, investment_cents=100000)
        # available_balance_cents = 250000 (R$ 2.500,00)
        # investment_rate = 20.0 (20% da renda foi investida)

    Observação de manutenção:
        - Todos os valores são em centavos (inteiros) para precisão monetária.
        - investment_rate retorna 0.0 se não houver renda (evita divisão por zero).
    """
    income_cents: int = 0
    expense_cents: int = 0
    investment_cents: int = 0

    @property
    def available_balance_cents(self) -> int:
        """
        Calcula o saldo disponível após despesas e investimentos.

        Fórmula: receitas - despesas - investimentos

        Retorna:
            int: Saldo em centavos. Pode ser negativo se despesas+inv > receitas.
        """
        return self.income_cents - self.expense_cents - self.investment_cents

    @property
    def investment_rate(self) -> float:
        """
        Calcula a taxa de investimento em percentual da renda.

        Fórmula: (investimentos / receitas) * 100

        Retorna:
            float: Percentual (0 a 100). Retorna 0.0 se não houver receitas.
        """
        return (self.investment_cents / self.income_cents * 100) if self.income_cents else 0.0