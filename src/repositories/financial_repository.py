"""Repositório SQLite do Controle Financeiro com criptografia opcional em repouso."""

from __future__ import annotations

import atexit
import os
import sqlite3
import tempfile
from datetime import date
from pathlib import Path
from typing import Iterable, Optional

from src.domain.financial_models import FinancialCategory, FinancialTransaction, TransactionType
from src.repositories.db_encryption import DatabaseEncryption


class CategoryInUseError(ValueError):
    """A categoria não pode ser removida pois possui lançamentos."""


class FinancialRepository:
    SCHEMA_VERSION = 1

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        encrypt: bool | None = None,
        password: str | None = None,
    ):
        if database_path is None:
            database_path = Path.home() / ".cdb_simulator" / "financial.sqlite3"
        self.database_path = Path(database_path)

        # Habilita criptografia apenas no caminho padrão do usuário,
        # salvo sobrescrita explícita via parâmetro ``encrypt``.
        if encrypt is None:
            encrypt = database_path == Path.home() / ".cdb_simulator" / "financial.sqlite3"
        self.encrypt = encrypt
        self._temp_path: Optional[Path] = None
        self._encryption: Optional[DatabaseEncryption] = None

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

    def _decrypt_to_temp(self) -> Path:
        """Descriptografa o banco .enc (se existir) para um arquivo temporário."""
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
        # Quando criptografado, todas as conexões usam o arquivo temporário
        # descriptografado em vez do caminho original.
        path = self._temp_path if self._temp_path is not None else self.database_path
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def close(self) -> None:
        """Recriptografa o banco temporário de volta para o .enc e limpa resíduos."""
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

    @staticmethod
    def _category(row: sqlite3.Row) -> FinancialCategory:
        return FinancialCategory(row["name"], TransactionType(row["transaction_type"]), row["color"], row["id"], bool(row["active"]))

    @staticmethod
    def _transaction(row: sqlite3.Row) -> FinancialTransaction:
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
        """Registra uma alteração na tabela de auditoria."""
        conn.execute(
            "INSERT INTO audit_log(table_name, record_id, action, old_data, new_data) VALUES (?, ?, ?, ?, ?)",
            (table_name, record_id, action, old_data, new_data),
        )

    def list_categories(self, transaction_type: TransactionType | None = None, active_only: bool = True) -> list[FinancialCategory]:
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
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
        return self._category(row) if row else None

    def add_category(self, category: FinancialCategory) -> FinancialCategory:
        try:
            with self._connect() as conn:
                cursor = conn.execute("INSERT INTO categories(name, transaction_type, color, active) VALUES (?, ?, ?, ?)",
                    (category.name, category.transaction_type.value, category.color, int(category.active)))
                return FinancialCategory(category.name, category.transaction_type, category.color, cursor.lastrowid, category.active)
        except sqlite3.IntegrityError as exc:
            raise ValueError("Já existe uma categoria com esse nome para este tipo.") from exc

    def update_category(self, category: FinancialCategory) -> FinancialCategory:
        if category.id is None:
            raise ValueError("Categoria sem identificador.")
        try:
            with self._connect() as conn:
                current = conn.execute("SELECT transaction_type FROM categories WHERE id = ?", (category.id,)).fetchone()
                if current is None:
                    raise ValueError("Categoria não encontrada.")
                if current["transaction_type"] != category.transaction_type.value and conn.execute("SELECT COUNT(*) FROM transactions WHERE category_id=?", (category.id,)).fetchone()[0]:
                    raise ValueError("Não é possível alterar o tipo de uma categoria que já possui lançamentos.")
                conn.execute("UPDATE categories SET name=?, transaction_type=?, color=?, active=? WHERE id=?",
                    (category.name, category.transaction_type.value, category.color, int(category.active), category.id))
        except sqlite3.IntegrityError as exc:
            raise ValueError("Já existe uma categoria com esse nome para este tipo.") from exc
        return category

    def archive_category(self, category_id: int) -> None:
        with self._connect() as conn:
            if conn.execute("UPDATE categories SET active=0 WHERE id=?", (category_id,)).rowcount == 0:
                raise ValueError("Categoria não encontrada.")

    def delete_category(self, category_id: int) -> None:
        with self._connect() as conn:
            if conn.execute("SELECT COUNT(*) FROM transactions WHERE category_id=?", (category_id,)).fetchone()[0]:
                raise CategoryInUseError("A categoria possui lançamentos. Arquive-a ou reatribua seus registros.")
            if conn.execute("DELETE FROM categories WHERE id=?", (category_id,)).rowcount == 0:
                raise ValueError("Categoria não encontrada.")

    def add_transaction(self, transaction: FinancialTransaction) -> FinancialTransaction:
        with self._connect() as conn:
            cursor = conn.execute("""INSERT INTO transactions(transaction_type, description, amount_cents, category_id, occurred_on, notes)
                VALUES (?, ?, ?, ?, ?, ?)""", (transaction.transaction_type.value, transaction.description, transaction.amount_cents,
                transaction.category_id, transaction.occurred_on.isoformat(), transaction.notes or ""))
            self._audit(conn, "transactions", cursor.lastrowid, "INSERT", None, str(transaction.__dict__))
        return FinancialTransaction(**{**transaction.__dict__, "id": cursor.lastrowid})

    def update_transaction(self, transaction: FinancialTransaction) -> FinancialTransaction:
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
