"""Repositório SQLite do Controle Financeiro."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Iterable, Optional

from src.domain.financial_models import FinancialCategory, FinancialTransaction, TransactionType


class CategoryInUseError(ValueError):
    """A categoria não pode ser removida pois possui lançamentos."""


class FinancialRepository:
    SCHEMA_VERSION = 1

    def __init__(self, database_path: str | Path | None = None):
        if database_path is None:
            database_path = Path.home() / ".cdb_simulator" / "financial.sqlite3"
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

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
        return FinancialTransaction(**{**transaction.__dict__, "id": cursor.lastrowid})

    def update_transaction(self, transaction: FinancialTransaction) -> FinancialTransaction:
        if transaction.id is None:
            raise ValueError("Lançamento sem identificador.")
        with self._connect() as conn:
            if conn.execute("""UPDATE transactions SET transaction_type=?, description=?, amount_cents=?, category_id=?, occurred_on=?, notes=? WHERE id=?""",
                (transaction.transaction_type.value, transaction.description, transaction.amount_cents, transaction.category_id,
                 transaction.occurred_on.isoformat(), transaction.notes or "", transaction.id)).rowcount == 0:
                raise ValueError("Lançamento não encontrado.")
        return transaction

    def delete_transaction(self, transaction_id: int) -> None:
        with self._connect() as conn:
            if conn.execute("DELETE FROM transactions WHERE id=?", (transaction_id,)).rowcount == 0:
                raise ValueError("Lançamento não encontrado.")

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
