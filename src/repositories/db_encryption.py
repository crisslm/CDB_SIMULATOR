"""
Criptografia de arquivo para o banco de dados financeiro.

Utiliza Fernet (AES-128 em modo CBC + HMAC-SHA256 para autenticação)
da biblioteca ``cryptography``. O arquivo SQLite é mantido criptografado
em disco (``financial.sqlite3.enc``) e somente descriptografado para um
arquivo temporário enquanto a aplicação está em execução.

A chave de criptografia pode ser fornecida via:

1. Variável de ambiente ``CDB_DB_ENCRYPTION_KEY`` (chave Fernet em base64)
2. Arquivo ``.env`` na raiz do projeto com ``CDB_DB_ENCRYPTION_KEY=...``

Se nenhuma chave for fornecida, uma nova será gerada automaticamente e
armazenada localmente (compatível com versões anteriores).
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

try:
    from dotenv import load_dotenv

    _DOTENV_AVAILABLE = True
except ImportError:  # pragma: no cover - python-dotenv é uma dependência opcional
    _DOTENV_AVAILABLE = False

ENV_VAR_NAME = "CDB_DB_ENCRYPTION_KEY"


def _load_env() -> None:
    """Carrega variáveis de ambiente do arquivo .env, se existir e python-dotenv estiver instalado."""
    if _DOTENV_AVAILABLE:
        env_path = Path(__file__).resolve().parents[2] / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)


class DatabaseEncryption:
    """Gerencia a criptografia simétrica do arquivo SQLite."""

    def __init__(self, key_path: Path, password: str | None = None):
        self.key_path = key_path
        self._fernet = self._load_or_create_key(password)

    def _load_or_create_key(self, password: str | None) -> Fernet:
        """Carrega a chave de criptografia.

        Ordem de prioridade:
        1. Variável de ambiente CDB_DB_ENCRYPTION_KEY
        2. Arquivo .db_key existente (comportamento legado)
        3. Geração de nova chave (salva em .db_key)
        """
        _load_env()

        # 1. Tentar chave via variável de ambiente
        env_key = os.getenv(ENV_VAR_NAME)
        if env_key:
            try:
                return Fernet(env_key.encode("utf-8"))
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    f"A variável de ambiente {ENV_VAR_NAME} não é uma chave Fernet válida."
                ) from exc

        # 2. Tentar carregar chave existente do disco (legado ou novo formato com versão)
        if self.key_path.exists():
            raw_key = self.key_path.read_bytes()
            return self._create_fernet_from_stored(raw_key, password=password)

        # 3. Gerar nova chave
        self.key_path.parent.mkdir(parents=True, exist_ok=True)

        if password:
            salt = os.urandom(16)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=480_000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
            # Armazena: versão \x01 + salt (16 bytes) + chave derivada base64
            self.key_path.write_bytes(b"\x01" + salt + key)
        else:
            key = Fernet.generate_key()
            # Armazena: versão \x00 + chave Fernet direta
            self.key_path.write_bytes(b"\x00" + key)

        # Restringe permissões do arquivo de chave quando possível (Unix)
        try:
            os.chmod(self.key_path, 0o600)
        except (OSError, NotImplementedError):
            pass

        return Fernet(key)

    @staticmethod
    def _create_fernet_from_stored(raw_key: bytes, password: str | None = None) -> Fernet:
        """Recria Fernet a partir de bytes armazenados, respeitando formato com versão.

        Formatos suportados:
        - \\x00 + chave Fernet (legado / sem senha)
        - \\x01 + salt (16 bytes) + chave derivada base64 (com senha)
        - Fallback: interpreta tudo como chave Fernet (retrocompatibilidade)
        """
        if not raw_key:
            raise ValueError("Arquivo de chave vazio.")

        version = raw_key[:1]
        if version == b"\x00":
            return Fernet(raw_key[1:])
        if version == b"\x01":
            if len(raw_key) < 17:
                raise ValueError("Arquivo de chave corrompido: salt ausente.")
            if password is None:
                raise ValueError("Senha é necessária para carregar este arquivo de chave.")
            salt = raw_key[1:17]
            derived_key_b64 = raw_key[17:]
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=480_000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
            return Fernet(key)

        # Fallback legado: tenta interpretar todo o conteúdo como chave Fernet
        return Fernet(raw_key)

    def encrypt_file(self, source: Path, destination: Path) -> None:
        """Criptografa o conteúdo de ``source`` e grava em ``destination``."""
        data = source.read_bytes()
        encrypted = self._fernet.encrypt(data)
        destination.write_bytes(encrypted)

    def decrypt_file(self, source: Path, destination: Path) -> None:
        """Descriptografa o conteúdo de ``source`` e grava em ``destination``."""
        encrypted = source.read_bytes()
        data = self._fernet.decrypt(encrypted)
        destination.write_bytes(data)
