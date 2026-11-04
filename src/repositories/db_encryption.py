"""
Criptografia de arquivo para o banco de dados financeiro.

Utiliza Fernet (AES-128 em modo CBC com HMAC-SHA256 para autenticação)
da biblioteca ``cryptography``. O arquivo SQLite é mantido criptografado
em disco (``financial.sqlite3.enc``) e somente descriptografado para um
arquivo temporário enquanto a aplicação está em execução.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class DatabaseEncryption:
    """Gerencia a criptografia simétrica do arquivo SQLite."""

    def __init__(self, key_path: Path, password: str | None = None):
        self.key_path = key_path
        self._fernet = self._load_or_create_key(password)

    def _load_or_create_key(self, password: str | None) -> Fernet:
        """Carrega uma chave existente ou gera uma nova protegida por senha."""
        if self.key_path.exists():
            raw_key = self.key_path.read_bytes()
            return Fernet(raw_key)

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
            # Armazena salt + chave derivada para permitir rederivação futura
            self.key_path.write_bytes(salt + key)
        else:
            key = Fernet.generate_key()
            self.key_path.write_bytes(key)

        # Restringe permissões do arquivo de chave quando possível (Unix)
        try:
            os.chmod(self.key_path, 0o600)
        except (OSError, NotImplementedError):
            pass

        return Fernet(key)

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
