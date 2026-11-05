"""
Repositório SQLite do Controle Financeiro com Criptografia Opcional
===================================================================

Este módulo implementa o padrão Repository para persistência de dados do
Controle Financeiro (categorias, transações, auditoria) em SQLite.

Funcionalidades principais:
    1. CRUD completo de categorias e transações.
    2. Criptografia opcional do banco em repouso (via DatabaseEncryption).
    3. Tabela de auditoria (audit_log) registrando INSERT/UPDATE/DELETE.
    4. Consultas agregadas diretas em SQL (SUM, GROUP BY) para eficiência.
    5. Conexão SQLite persistente (reutilizada entre chamadas).

Camada: Repositório (infraestrutura de persistência)
Depende de: src.domain.financial_models, src.repositories.db_encryption

Autor: CDB Simulator
Versão: 1.0.0
"""

from __future__ import annotations

import atexit
import os
import sqlite3
import tempfile
from datetime import date
from pathlib import Path
from typing import Iterable, Optional

from ..domain.financial_models import FinancialCategory, FinancialSummary, FinancialTransaction, TransactionType
from ..repositories.db_encryption import DatabaseEncryption
from .interfaces import FinancialRepositoryProtocol


class CategoryInUseError(ValueError):
    """
    Exceção lançada quando se tenta excluir uma categoria que possui lançamentos.

    Em vez de excluir, o usuário deve arquivar a categoria (archive_category)
    para preservar o histórico financeiro.
    """

    pass


class FinancialRepository(FinancialRepositoryProtocol):
    """
    Repositório SQLite para o Controle Financeiro.

    Gerencia a persistência de categorias, transações e log de auditoria em
    um banco SQLite local. Suporta criptografia opcional em repouso.

    Fluxo de criptografia (quando habilitado):
        1. Banco .enc (criptografado) é descriptografado para um temp file.
        2. Todas as operações usam o temp file.
        3. Ao fechar (close()), o temp é recriptografado de volta para .enc
           e o temp é excluído.

    Atributos:
        SCHEMA_VERSION (int): Versão do esquema do banco (para migrações futuras).
        database_path (Path): Caminho do arquivo SQLite.
        encrypt (bool): Se True, usa criptografia em repouso.
        _temp_path (Path | None): Caminho do arquivo temporário descriptografado.
        _encryption (DatabaseEncryption | None): Instância de criptografia.
        _connection (sqlite3.Connection | None): Conexão SQLite persistente.

    Exemplo de uso:
        repo = FinancialRepository(database_path="banco.sqlite3", encrypt=False)
        cat = repo.add_category(FinancialCategory("Salário", TransactionType.INCOME, "#24C270"))
        tx = repo.add_transaction(FinancialTransaction(...))

    Observação de manutenção:
        - A conexão SQLite é persistente (self._connection). Não feche manualmente
          a menos que chame close().
        - Ao adicionar novas tabelas, atualize SCHEMA_VERSION e _initialize().
    """

    SCHEMA_VERSION = 1

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        encrypt: bool | None = None,
        password: str | None = None,
    ):
        """
        Inicializa o repositório e cria as tabelas se não existirem.

        Parâmetros:
            database_path (str | Path | None): Caminho do banco SQLite.
                                               Se None, usa ~/.cdb_simulator/financial.sqlite3.
            encrypt (bool | None): Se True, criptografa o banco. Se None,
                                   criptografa apenas no caminho padrão do usuário.
            password (str | None): Senha para criptografia (se encrypt=True).

        Fluxo de inicialização:
            1. Define o caminho do banco (padrão ou customizado).
            2. Determina se criptografia está ativa.
            3. Se criptografado, descriptografa o banco para um temp file.
            4. Registra close() no atexit para recriptografar ao encerrar.
            5. Cria diretórios e chama _initialize().
            6. Limpa arquivos temporários órfãos de execuções anteriores.
        """
        if database_path is None:
            database_path = Path.home() / ".cdb_simulator" / "financial.sqlite3"
        self.database_path = Path(database_path)

        # Habilita criptografia apenas no caminho padrão do usuário,
        # salvo sobrescrita explícita via parâmetro encrypt.
        if encrypt is None:
            encrypt = database_path == Path.home() / ".cdb_simulator" / "financial.sqlite3"
        self.encrypt = encrypt
        self._temp_path: Optional[Path] = None
        self._encryption: Optional[DatabaseEncryption] = None
        self._connection: Optional[sqlite3.Connection] = None

        if self.encrypt:
            self._encryption = DatabaseEncryption(
                self.database_path.parent / ".db_key",
                password=password,
            )
            self._temp_path = self._decrypt_to_temp()
            # Garante que o banco seja recriptografado ao encerrar o processo
            atexit.register(self.close)

        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

        # Limpa arquivos temporários órfãos deixados por execuções anteriores
        # que não conseguiram encerrar corretamente (ex: travamento, kill).
        for tmp in self.database_path.parent.glob("tmp*.sqlite3"):
            try: tmp.unlink()
            except OSError: pass

    def _decrypt_to_temp(self) -> Path:
        """
        Descriptografa o banco .enc para um arquivo temporário.

        Se o arquivo criptografado existir, ele é descriptografado para o temp.
        Se não existir (primeira execução), o temp começa vazio e é inicializado
        por _initialize().

        Retorna:
            Path: Caminho do arquivo temporário descriptografado.
        """
        fd, temp_name = tempfile.mkstemp(suffix=".sqlite3", dir=str(self.database_path.parent))
        os.close(fd)
        temp_path = Path(temp_name)

        encrypted_path = self.database_path.with_suffix(self.database_path.suffix + ".enc")
        if encrypted_path.exists() and self._encryption is not None:
            self._encryption.decrypt_file(encrypted_path, temp_path)
        # Se não existir arquivo criptografado, o temp começa vazio
        # e será inicializado por _initialize().

        return temp_path

    def _connect(self) -> sqlite3.Connection:
        """
        Retorna uma conexão SQLite persistente, criando apenas na primeira vez.

        A conexão é reutilizada em todas as operações subsequentes, evitando
        o overhead de abrir/fechar o banco a cada chamada.

        Configurações aplicadas:
            - row_factory = sqlite3.Row (acesso por nome de coluna).
            - PRAGMA foreign_keys = ON (integridade referencial).

        Retorna:
            sqlite3.Connection: Conexão ativa com o banco.
        """
        if self._connection is None:
            path = self._temp_path if self._temp_path is not None else self.database_path
            self._connection = sqlite3.connect(path)
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection

    def close(self) -> None:
        """
        Fecha a conexão, recriptografa o banco temporário e limpa resíduos.

        Este método é chamado automaticamente via atexit ao encerrar o processo.
        Também pode ser chamado manualmente.

        Fluxo:
            1. Fecha a conexão SQLite persistente.
            2. Recriptografa o temp file de volta para o .enc.
            3. Exclui o temp file.

        Observação de segurança:
            Se o processo for encerrado abruptamente (SIGKILL, falta de energia),
            o atexit NÃO será executado e o temp file pode permanecer descriptografado.
            Isso é um risco conhecido mitigado pela limpeza de órfãos no __init__.
        """
        if self._connection is not None:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None

        if self._temp_path is not None and self._encryption is not None:
            encrypted_path = self.database_path.with_suffix(self.database_path.suffix + ".enc")
            try:
                self._encryption.encrypt_file(self._temp_path, encrypted_path)
            finally:
                try:
                    self._temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
                self._temp_path = None

    def _initialize(self) -> None:
        """
        Cria as tabelas do banco se não existirem e insere categorias padrão.

        Tabelas criadas:
            - schema_metadata: Armazena a versão do esquema.
            - categories: Categorias financeiras.
            - transactions: Lançamentos financeiros.
            - audit_log: Log de alterações (auditoria).

        Índices criados para melhorar performance de consultas por data e categoria.

        Após criar as tabelas, insere categorias padrão apenas se o banco estiver
        vazio (primeira execução).
        """
        with self._connect() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS schema_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    transaction_type TEXT NOT NULL CHECK(transaction_type IN ('receita','despesa','investimento')),
                    color TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
                    UNIQUE(name, transaction_type)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_type TEXT NOT NULL CHECK(transaction_type IN ('receita','despesa','investimento')),
                    description TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
                    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
                    occurred_on TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT ''
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(occurred_on)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id)")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name TEXT NOT NULL,
                    record_id INTEGER NOT NULL,
                    action TEXT NOT NULL CHECK(action IN ('INSERT','UPDATE','DELETE')),
                    old_data TEXT,
                    new_data TEXT,
                    changed_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_record ON audit_log(table_name, record_id)")
            conn.execute("INSERT OR REPLACE INTO schema_metadata(key, value) VALUES ('schema_version', ?)", (str(self.SCHEMA_VERSION),))

            # Insere categorias padrão apenas uma vez, se o banco estiver vazio
            if conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
                default_categories = (
                    ("Salário", "receita", "#24C270"), ("Freelance", "receita", "#4F8CFF"),
                    ("Dividendos", "receita", "#A970FF"), ("Rendimentos", "receita", "#32B8C6"),
                    ("Outros", "receita", "#8E8E93"),
                    ("Alimentação", "despesa", "#FF9F43"), ("Transporte", "despesa", "#4F8CFF"),
                    ("Moradia", "despesa", "#FF6B6B"), ("Saúde", "despesa", "#A970FF"),
                    ("Educação", "despesa", "#32B8C6"), ("Lazer", "despesa", "#F368E0"),
                    ("Assinaturas", "despesa", "#8395A7"), ("Compras", "despesa", "#F9CA24"),
                    ("Contas", "despesa", "#576574"), ("Outros", "despesa", "#8E8E93"),
                    ("CDB", "investimento", "#24C270"), ("Tesouro Direto", "investimento", "#4F8CFF"),
                    ("Ações", "investimento", "#FF9F43"), ("Fundos Imobiliários", "investimento", "#A970FF"),
                    ("ETFs", "investimento", "#32B8C6"), ("Criptomoedas", "investimento", "#F9CA24"),
                    ("Reserva de Emergência", "investimento", "#6FE29F"), ("Outros", "investimento", "#8E8E93"),
                )
                for name, ttype, color in default_categories:
                    conn.execute(
                        "INSERT INTO categories(name, transaction_type, color, active) VALUES (?, ?, ?, 1)",
                        (name, ttype, color),
                    )

    @staticmethod
    def _category(row: sqlite3.Row) -> FinancialCategory:
        """
        Converte uma linha do banco (sqlite3.Row) em um objeto FinancialCategory.

        Parâmetros:
            row (sqlite3.Row): Linha do resultado de SELECT nas categorias.

        Retorna:
            FinancialCategory: Objeto de domínio preenchido.
        """
        return FinancialCategory(row["name"], TransactionType(row["transaction_type"]), row["color"], row["id"], bool(row["active"]))

    @staticmethod
    def _transaction(row: sqlite3.Row) -> FinancialTransaction:
        """
        Converte uma linha do banco (sqlite3.Row) em um objeto FinancialTransaction.

        O JOIN com categorias traz category_name e category_color para exibição na UI.

        Parâmetros:
            row (sqlite3.Row): Linha do resultado de SELECT nas transações.

        Retorna:
            FinancialTransaction: Objeto de domínio preenchido.
        """
        return FinancialTransaction(
            TransactionType(row["transaction_type"]), row["description"], row["amount_cents"],
            row["category_id"], date.fromisoformat(row["occurred_on"]), row["notes"], row["id"],
            row["category_name"], row["category_color"],
        )

    def _audit(
        self,
        conn: sqlite3.Connection,
        table_name: str,
        record_id: int,
        action: str,
        old_data: str | None = None,
        new_data: str | None = None,
    ) -> None:
        """
        Registra uma alteração na tabela de auditoria (audit_log).

        Usado para rastrear quem alterou o quê e quando, proporcionando
        rastreabilidade completa das mudanças nos dados financeiros.

        Parâmetros:
            conn: Conexão SQLite ativa.
            table_name: Nome da tabela alterada ('categories' ou 'transactions').
            record_id: ID do registro alterado.
            action: Tipo de ação ('INSERT', 'UPDATE' ou 'DELETE').
            old_data: Dados antes da alteração (string, pode ser None).
            new_data: Dados após a alteração (string, pode ser None).
        """
        conn.execute(
            "INSERT INTO audit_log(table_name, record_id, action, old_data, new_data) VALUES (?, ?, ?, ?, ?)",
            (table_name, record_id, action, old_data, new_data),
        )

    def list_categories(self, transaction_type: TransactionType | None = None, active_only: bool = True) -> list[FinancialCategory]:
        """
        Lista categorias do banco, com filtros opcionais.

        Parâmetros:
            transaction_type: Se fornecido, filtra por tipo (receita/despesa/investimento).
            active_only: Se True (padrão), retorna apenas categorias ativas.

        Retorna:
            list[FinancialCategory]: Lista ordenada por nome (case-insensitive).
        """
        clauses, params = [], []
        if transaction_type:
            clauses.append("transaction_type = ?")
            params.append(TransactionType.from_value(transaction_type).value)
        if active_only:
            clauses.append("active = 1")
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as conn:
            return [self._category(row) for row in conn.execute(f"SELECT * FROM categories{where} ORDER BY name COLLATE NOCASE", params)]

    def get_category(self, category_id: int) -> Optional[FinancialCategory]:
        """
        Busca uma categoria pelo ID.

        Parâmetros:
            category_id (int): ID da categoria.

        Retorna:
            Optional[FinancialCategory]: A categoria ou None se não encontrada.
        """
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
        return self._category(row) if row else None

    def add_category(self, category: FinancialCategory) -> FinancialCategory:
        """
        Insere uma nova categoria no banco.

        Registra a ação na tabela de auditoria (audit_log).

        Parâmetros:
            category (FinancialCategory): Categoria a ser inserida.

        Retorna:
            FinancialCategory: A categoria com o ID atribuído pelo banco.

        Levanta:
            ValueError: Se já existir uma categoria com mesmo nome e tipo.
        """
        try:
            with self._connect() as conn:
                cursor = conn.execute("INSERT INTO categories(name, transaction_type, color, active) VALUES (?, ?, ?, ?)",
                    (category.name, category.transaction_type.value, category.color, int(category.active)))
                self._audit(conn, "categories", cursor.lastrowid, "INSERT", None, str(category.__dict__))
                return FinancialCategory(category.name, category.transaction_type, category.color, cursor.lastrowid, category.active)
        except sqlite3.IntegrityError as exc:
            raise ValueError("Já existe uma categoria com esse nome para este tipo.") from exc

    def update_category(self, category: FinancialCategory) -> FinancialCategory:
        """
        Atualiza uma categoria existente.

        Não permite alterar o tipo de uma categoria que já possui lançamentos.

        Parâmetros:
            category (FinancialCategory): Categoria com ID e novos valores.

        Retorna:
            FinancialCategory: A categoria atualizada.

        Levanta:
            ValueError: Se categoria não tiver ID, não for encontrada, ou tentar
                        mudar tipo de categoria com lançamentos.
        """
        if category.id is None:
            raise ValueError("Categoria sem identificador.")
        try:
            with self._connect() as conn:
                current = conn.execute("SELECT transaction_type FROM categories WHERE id = ?", (category.id,)).fetchone()
                if current is None:
                    raise ValueError("Categoria não encontrada.")
                old_data = str(dict(current))
                if current["transaction_type"] != category.transaction_type.value and conn.execute("SELECT COUNT(*) FROM transactions WHERE category_id=?", (category.id,)).fetchone()[0]:
                    raise ValueError("Não é possível alterar o tipo de uma categoria que já possui lançamentos.")
                conn.execute("UPDATE categories SET name=?, transaction_type=?, color=?, active=? WHERE id=?",
                    (category.name, category.transaction_type.value, category.color, int(category.active), category.id))
                self._audit(conn, "categories", category.id, "UPDATE", old_data, str(category.__dict__))
        except sqlite3.IntegrityError as exc:
            raise ValueError("Já existe uma categoria com esse nome para este tipo.") from exc
        return category

    def archive_category(self, category_id: int) -> None:
        """
        Arquiva uma categoria (define active=0) em vez de excluí-la.

        Arquivamento preserva o histórico de lançamentos associados.
        A categoria arquivada não aparece em novos lançamentos.

        Parâmetros:
            category_id (int): ID da categoria a ser arquivada.

        Levanta:
            ValueError: Se a categoria não for encontrada.
        """
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM categories WHERE id=?", (category_id,)).fetchone()
            if row is None:
                raise ValueError("Categoria não encontrada.")
            old_data = str(dict(row))
            if conn.execute("UPDATE categories SET active=0 WHERE id=?", (category_id,)).rowcount == 0:
                raise ValueError("Categoria não encontrada.")
            self._audit(conn, "categories", category_id, "UPDATE", old_data, str(dict(row)) + ", active=0")

    def delete_category(self, category_id: int) -> None:
        """
        Exclui uma categoria apenas se ela não tiver lançamentos associados.

        Se a categoria estiver em uso, levanta CategoryInUseError.
        Recomenda-se usar archive_category() em vez disso para preservar histórico.

        Parâmetros:
            category_id (int): ID da categoria a ser excluída.

        Levanta:
            ValueError: Se a categoria não for encontrada.
            CategoryInUseError: Se a categoria possui lançamentos associados.
        """
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM categories WHERE id=?", (category_id,)).fetchone()
            if row is None:
                raise ValueError("Categoria não encontrada.")
            old_data = str(dict(row))
            if conn.execute("SELECT COUNT(*) FROM transactions WHERE category_id=?", (category_id,)).fetchone()[0]:
                raise CategoryInUseError("A categoria possui lançamentos. Arquive-a ou reatribua seus registros.")
            if conn.execute("DELETE FROM categories WHERE id=?", (category_id,)).rowcount == 0:
                raise ValueError("Categoria não encontrada.")
            self._audit(conn, "categories", category_id, "DELETE", old_data, None)

    def add_transaction(self, transaction: FinancialTransaction) -> FinancialTransaction:
        """
        Insere uma nova transação no banco.

        Registra a ação na tabela de auditoria.

        Parâmetros:
            transaction (FinancialTransaction): Transação a ser inserida.

        Retorna:
            FinancialTransaction: A transação com o ID atribuído pelo banco.
        """
        with self._connect() as conn:
            cursor = conn.execute("""INSERT INTO transactions(transaction_type, description, amount_cents, category_id, occurred_on, notes)
                VALUES (?, ?, ?, ?, ?, ?)""", (transaction.transaction_type.value, transaction.description, transaction.amount_cents,
                transaction.category_id, transaction.occurred_on.isoformat(), transaction.notes or ""))
            self._audit(conn, "transactions", cursor.lastrowid, "INSERT", None, str(transaction.__dict__))
        return FinancialTransaction(**{**transaction.__dict__, "id": cursor.lastrowid})

    def update_transaction(self, transaction: FinancialTransaction) -> FinancialTransaction:
        """
        Atualiza uma transação existente.

        Parâmetros:
            transaction (FinancialTransaction): Transação com ID e novos valores.

        Retorna:
            FinancialTransaction: A transação atualizada.

        Levanta:
            ValueError: Se a transação não tiver ID ou não for encontrada.
        """
        if transaction.id is None:
            raise ValueError("Lançamento sem identificador.")
        old_data = None
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction.id,)).fetchone()
            if row is None:
                raise ValueError("Lançamento não encontrado.")
            old_data = str(dict(row))
            if conn.execute("""UPDATE transactions SET transaction_type=?, description=?, amount_cents=?, category_id=?, occurred_on=?, notes=? WHERE id=?""",
                (transaction.transaction_type.value, transaction.description, transaction.amount_cents, transaction.category_id,
                 transaction.occurred_on.isoformat(), transaction.notes or "", transaction.id)).rowcount == 0:
                raise ValueError("Lançamento não encontrado.")
            self._audit(conn, "transactions", transaction.id, "UPDATE", old_data, str(transaction.__dict__))
        return transaction

    def delete_transaction(self, transaction_id: int) -> None:
        """
        Exclui uma transação pelo ID.

        Registra a exclusão na tabela de auditoria.

        Parâmetros:
            transaction_id (int): ID da transação a ser excluída.

        Levanta:
            ValueError: Se a transação não for encontrada.
        """
        old_data = None
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
            if row is None:
                raise ValueError("Lançamento não encontrado.")
            old_data = str(dict(row))
            if conn.execute("DELETE FROM transactions WHERE id=?", (transaction_id,)).rowcount == 0:
                raise ValueError("Lançamento não encontrado.")
            self._audit(conn, "transactions", transaction_id, "DELETE", old_data, None)

    def list_transactions(self, start: date | None = None, end: date | None = None,
                          transaction_type: TransactionType | None = None, category_id: int | None = None) -> list[FinancialTransaction]:
        """
        Lista transações com filtros opcionais de data, tipo e categoria.

        Faz um JOIN com categorias para incluir category_name e category_color
        no resultado (útil para exibição na UI).

        Parâmetros:
            start (date | None): Data inicial do filtro (inclusive).
            end (date | None): Data final do filtro (inclusive).
            transaction_type (TransactionType | None): Filtro por tipo.
            category_id (int | None): Filtro por ID de categoria.

        Retorna:
            list[FinancialTransaction]: Transações ordenadas por data (mais recente primeiro).
        """
        clauses, params = [], []
        if start:
            clauses.append("t.occurred_on >= ?"); params.append(start.isoformat())
        if end:
            clauses.append("t.occurred_on <= ?"); params.append(end.isoformat())
        if transaction_type:
            clauses.append("t.transaction_type = ?"); params.append(TransactionType.from_value(transaction_type).value)
        if category_id:
            clauses.append("t.category_id = ?"); params.append(category_id)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = """SELECT t.*, c.name AS category_name, c.color AS category_color FROM transactions t
                 JOIN categories c ON c.id=t.category_id""" + where + " ORDER BY t.occurred_on DESC, t.id DESC"
        with self._connect() as conn:
            return [self._transaction(row) for row in conn.execute(sql, params)]

    def _where_clauses(self, start: date | None = None, end: date | None = None,
                       transaction_type: TransactionType | None = None,
                       category_id: int | None = None) -> tuple[str, list]:
        """
        Constrói cláusula WHERE e parâmetros para consultas de transações.

        Método auxiliar privado usado pelos métodos de agregação SQL
        (summary_sql, expense_by_category_sql, monthly_expenses_sql).

        Retorna:
            tuple[str, list]: (cláusula WHERE, lista de parâmetros).
        """
        clauses, params = [], []
        if start:
            clauses.append("t.occurred_on >= ?"); params.append(start.isoformat())
        if end:
            clauses.append("t.occurred_on <= ?"); params.append(end.isoformat())
        if transaction_type:
            clauses.append("t.transaction_type = ?"); params.append(TransactionType.from_value(transaction_type).value)
        if category_id:
            clauses.append("t.category_id = ?"); params.append(category_id)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        return where, params

    def summary_sql(self, start: date | None = None, end: date | None = None,
                    transaction_type: TransactionType | None = None,
                    category_id: int | None = None) -> FinancialSummary:
        """
        Retorna resumo financeiro agregado diretamente via SQL.

        Usa SUM(CASE ...) no banco para evitar carregar todas as transações
        para o Python e fazer loops em Python. Muito mais eficiente para
        grandes volumes de dados.

        Parâmetros:
            start, end: Filtro de data.
            transaction_type: Filtro por tipo (receita/despesa/investimento).
            category_id: Filtro por categoria.

        Retorna:
            FinancialSummary: Totais de receitas, despesas e investimentos em centavos.
        """
        where, params = self._where_clauses(start, end, transaction_type, category_id)
        with self._connect() as conn:
            row = conn.execute(f"""
                SELECT
                    COALESCE(SUM(CASE WHEN t.transaction_type = 'receita' THEN t.amount_cents ELSE 0 END), 0) AS income,
                    COALESCE(SUM(CASE WHEN t.transaction_type = 'despesa' THEN t.amount_cents ELSE 0 END), 0) AS expense,
                    COALESCE(SUM(CASE WHEN t.transaction_type = 'investimento' THEN t.amount_cents ELSE 0 END), 0) AS investment
                FROM transactions t{where}
            """, params).fetchone()
        return FinancialSummary(
            income_cents=int(row["income"]),
            expense_cents=int(row["expense"]),
            investment_cents=int(row["investment"]),
        )

    def expense_by_category_sql(self, start: date | None = None, end: date | None = None,
                                category_id: int | None = None) -> list[tuple[str, int, str]]:
        """
        Retorna despesas agregadas por categoria via SQL GROUP BY.

        Usado para gerar gráficos de donut e barras no dashboard financeiro.

        Parâmetros:
            start, end: Filtro de data.
            category_id: Filtro por categoria específico.

        Retorna:
            list[tuple[str, int, str]]: Lista de (nome_categoria, total_centavos, cor_hex).
                                        Ordenada por total decrescente.
        """
        where, params = self._where_clauses(start, end, TransactionType.EXPENSE, category_id)
        with self._connect() as conn:
            rows = conn.execute(f"""
                SELECT c.name AS name, c.color AS color, SUM(t.amount_cents) AS total
                FROM transactions t
                JOIN categories c ON c.id = t.category_id{where}
                GROUP BY c.id, c.name, c.color
                ORDER BY total DESC
            """, params).fetchall()
        return [(row["name"], int(row["total"]), row["color"] or "#8E8E93") for row in rows]

    def monthly_expenses_sql(self, start: date | None = None, end: date | None = None,
                             category_id: int | None = None) -> list[tuple[str, int]]:
        """
        Retorna despesas agregadas por mês via SQL GROUP BY.

        Usado para gerar gráfico de evolução mensal de despesas.

        Parâmetros:
            start, end: Filtro de data.
            category_id: Filtro por categoria específico.

        Retorna:
            list[tuple[str, int]]: Lista de ("AAAA-MM", total_centavos).
                                   Ordenada por mês crescente.
        """
        where, params = self._where_clauses(start, end, TransactionType.EXPENSE, category_id)
        with self._connect() as conn:
            rows = conn.execute(f"""
                SELECT substr(t.occurred_on, 1, 7) AS month, SUM(t.amount_cents) AS total
                FROM transactions t{where}
                GROUP BY month
                ORDER BY month
            """, params).fetchall()
        return [(row["month"], int(row["total"])) for row in rows]
