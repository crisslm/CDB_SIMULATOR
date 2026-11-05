"""
Criptografia de Arquivo para Banco de Dados Financeiro
======================================================

Este módulo gerencia a criptografia simétrica do banco de dados SQLite do
Controle Financeiro usando Fernet (AES-128 em modo CBC + HMAC-SHA256).

Arquitetura de segurança:
    1. O banco SQLite real fica CRIPTOGRAFADO em disco (.enc).
    2. Ao iniciar a aplicação, ele é descriptografado para um arquivo temporário.
    3. A aplicação trabalha com o banco temporário (descriptografado).
    4. Ao encerrar, o banco é recriptografado e o temporário é excluído.

Objetivo: Proteger dados sensíveis (receitas, despesas, investimentos) contra
leitura não autorizada caso alguém obtenha acesso ao arquivo no disco.

Biblioteca utilizada: cryptography (Fernet)

Autor: CDB Simulator
Versão: 1.0.0
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

# Nome da variável de ambiente que pode conter a chave Fernet em base64
ENV_VAR_NAME = "CDB_DB_ENCRYPTION_KEY"


def _load_env() -> None:
    """
    Carrega variáveis de ambiente do arquivo .env na raiz do projeto.

    O caminho do .env é calculado subindo 2 níveis a partir deste arquivo
    (src/repositories/db_encryption.py -> src/ -> raiz do projeto).

    Esta função é privada (_prefixo) e é chamada internamente ao iniciar
    a criptografia para verificar se há uma chave definida via .env.

    Observação: Se python-dotenv não estiver instalado, a função simplesmente
    não faz nada (o uso da variável de ambiente direta ainda funciona).
    """
    if _DOTENV_AVAILABLE:
        env_path = Path(__file__).resolve().parents[2] / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)


class DatabaseEncryption:
    """
    Gerencia a criptografia simétrica do arquivo SQLite usando Fernet.

    Fernet garante:
        - Confidencialidade (AES-128 em modo CBC)
        - Autenticidade e integridade (HMAC-SHA256)
        - Não é possível modificar o conteúdo criptografado sem detectar.

    Fluxo de vida da chave:
        1. Prioridade 1: Variável de ambiente CDB_DB_ENCRYPTION_KEY.
        2. Prioridade 2: Arquivo .db_key existente no disco.
        3. Prioridade 3: Gera uma nova chave e salva em .db_key.

    Formatos do arquivo .db_key:
        - Versão \x00: chave Fernet direta (sem senha, legado).
        - Versão \x01: byte de versão + salt (16 bytes) + chave derivada (com senha).

    Exemplo de uso:
        enc = DatabaseEncryption(Path("/caminho/.db_key"), password="minha_senha")
        enc.encrypt_file(Path("banco.sqlite3"), Path("banco.sqlite3.enc"))
        enc.decrypt_file(Path("banco.sqlite3.enc"), Path("banco_dec.sqlite3"))
    """

    def __init__(self, key_path: Path, password: str | None = None):
        """
        Inicializa o gerenciador de criptografia.

        Parâmetros:
            key_path (Path): Caminho para o arquivo que armazenará a chave (.db_key).
            password (str | None): Senha opcional para derivar a chave via PBKDF2.
                                   Se None, uma chave aleatória é gerada.

        Fluxo:
            1. Chama _load_or_create_key() para obter uma instância Fernet.
            2. A instância é armazenada em self._fernet para uso posterior.
        """
        self.key_path = key_path
        self._fernet = self._load_or_create_key(password)

    def _load_or_create_key(self, password: str | None) -> Fernet:
        """
        Carrega ou cria a chave de criptografia seguindo ordem de prioridade:

            1. Variável de ambiente CDB_DB_ENCRYPTION_KEY (base64).
            2. Arquivo .db_key existente no disco (com ou sem senha).
            3. Geração de nova chave (salva em .db_key).

        Parâmetros:
            password (str | None): Senha para derivar chave (usado na opção 3).

        Retorna:
            Fernet: Instância pronta para criptografar/descriptografar.

        Observação de segurança:
            - Se a variável de ambiente for inválida, levanta ValueError.
            - Se o arquivo .db_key for versão \x01 e não houver senha, levanta ValueError.
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
            # Deriva chave da senha usando PBKDF2 com 480.000 iterações
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
            # Gera chave aleatória Fernet
            key = Fernet.generate_key()
            # Armazena: versão \x00 + chave Fernet direta
            self.key_path.write_bytes(b"\x00" + key)

        # Restringe permissões do arquivo de chave (apenas leitura/escrita para o dono)
        # Funciona em Unix/Linux. No Windows é ignorado silenciosamente.
        try:
            os.chmod(self.key_path, 0o600)
        except (OSError, NotImplementedError):
            pass

        return Fernet(key)

    @staticmethod
    def _create_fernet_from_stored(raw_key: bytes, password: str | None = None) -> Fernet:
        """
        Recria uma instância Fernet a partir dos bytes armazenados no .db_key.

        Suporta três formatos:
            1. \\x00 + chave Fernet direta (sem senha, formato legado).
            2. \\x01 + salt (16 bytes) + chave derivada base64 (com senha).
            3. Fallback: interpreta todo o conteúdo como chave Fernet (retrocompatibilidade).

        Parâmetros:
            raw_key (bytes): Conteúdo bruto do arquivo .db_key.
            password (str | None): Senha necessária se o formato for \x01.

        Retorna:
            Fernet: Instância pronta para uso.

        Levanta:
            ValueError: Se o arquivo estiver vazio, corrompido, ou precisar de senha
                        mas nenhuma for fornecida.

        Observação de manutenção:
            Se adicionar um novo formato de versão, adicione um novo bloco `if version == b"\x02":` aqui.
        """
        if not raw_key:
            raise ValueError("Arquivo de chave vazio.")

        version = raw_key[:1]
        if version == b"\x00":
            # Formato legado: apenas a chave Fernet
            return Fernet(raw_key[1:])
        if version == b"\x01":
            # Formato com senha: versão + salt + chave derivada
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
        """
        Criptografa o conteúdo de um arquivo e grava em outro.

        Lê TODO o conteúdo do arquivo de origem na memória, criptografa e grava
        no destino. Para bancos de uso pessoal (poucos MB), isso é aceitável.

        Parâmetros:
            source (Path): Caminho do arquivo descriptografado (origem).
            destination (Path): Caminho do arquivo criptografado (destino).

        Exemplo:
            enc.encrypt_file(Path("banco.sqlite3"), Path("banco.sqlite3.enc"))
        """
        data = source.read_bytes()
        encrypted = self._fernet.encrypt(data)
        destination.write_bytes(encrypted)

    def decrypt_file(self, source: Path, destination: Path) -> None:
        """
        Descriptografa o conteúdo de um arquivo e grava em outro.

        Lê TODO o conteúdo criptografado, descriptografa e grava no destino.
        Se o arquivo estiver corrompido ou a chave estiver errada, levanta
        InvalidToken (da biblioteca cryptography).

        Parâmetros:
            source (Path): Caminho do arquivo criptografado (origem).
            destination (Path): Caminho do arquivo descriptografado (destino).

        Exemplo:
            enc.decrypt_file(Path("banco.sqlite3.enc"), Path("banco_dec.sqlite3"))
        """
        encrypted = source.read_bytes()
        data = self._fernet.decrypt(encrypted)
        destination.write_bytes(data)