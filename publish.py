#!/usr/bin/env python3
"""Publica o executável compilado (dist/) na Área de Trabalho.

A Área de Trabalho deste projeto fica dentro do OneDrive. Arquivos ``.exe``
sincronizados (Files On-Demand) são "reparse points" e o Windows Explorer
costuma falhar ao substituir/apagar esses arquivos com erros de sincronização
("não foi possível excluir", "arquivo em uso", "erro 0x800701AA"...).

Este script faz a troca na ordem que funciona de forma confiável:

1. aborta se o executável estiver rodando (arquivo travado);
2. substitui o ``.exe`` antigo pelo novo (sem manter backup);
3. preserva a data/hora da compilação;
4. confere o SHA-256 da origem e do destino.

Uso:
    python publish.py                 # publica dist/CDB_Simulator.exe na Área de Trabalho
    python publish.py --dry-run       # apenas mostra o que seria feito
    python publish.py --dest PASTA    # publica em outra pasta (útil para testes)
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
from pathlib import Path

APP_NAME = "CDB_Simulator"
EXE_NAME = f"{APP_NAME}.exe"

PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_EXE = PROJECT_ROOT / "dist" / EXE_NAME

STATUS_UPDATED = "updated"
STATUS_UP_TO_DATE = "up-to-date"
STATUS_DRY_RUN = "dry-run"
STATUS_RUNNING = "running"
STATUS_MISSING = "missing"


def sha256(path: Path) -> str:
    """Calcula o SHA-256 em blocos, sem carregar o arquivo inteiro na memória."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def desktop_dir() -> Path:
    """Retorna a Área de Trabalho real (respeita redirecionamento do OneDrive)."""
    if os.name == "nt":
        try:
            from ctypes import create_unicode_buffer, windll
            from ctypes.wintypes import MAX_PATH

            buffer = create_unicode_buffer(MAX_PATH)
            # CSIDL_DESKTOPDIRECTORY = 0x0010
            if windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, buffer) == 0:
                if buffer.value:
                    return Path(buffer.value)
        except (AttributeError, OSError):
            pass

    for candidate in (Path.home() / "Desktop", Path.home() / "OneDrive" / "Desktop"):
        if candidate.is_dir():
            return candidate

    return Path.home() / "Desktop"


def is_running(exe_name: str = EXE_NAME) -> bool:
    """Verifica se o processo está em execução (sem depender de tasklist/PATH)."""
    if os.name != "nt":
        return False

    import ctypes
    from ctypes import wintypes

    TH32CS_SNAPPROCESS = 0x00000002
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_void_p),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * 260),
        ]

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == INVALID_HANDLE_VALUE:
        return False

    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        if not kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            return False
        while True:
            if entry.szExeFile.lower() == exe_name.lower():
                return True
            if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                return False
    finally:
        kernel32.CloseHandle(snapshot)


def publish(
    source: Path,
    destination: Path,
    *,
    dry_run: bool = False,
    running: bool | None = None,
) -> str:
    """Substitui ``destination`` por ``source`` de forma segura.

    Retorna um dos status: ``updated``, ``up-to-date``, ``dry-run``,
    ``running`` ou ``missing``.
    """
    if not source.is_file():
        return STATUS_MISSING

    if running is None:
        running = is_running(destination.name)
    if running:
        return STATUS_RUNNING

    new_hash = sha256(source)

    if destination.is_file() and sha256(destination) == new_hash:
        return STATUS_UP_TO_DATE

    if dry_run:
        return STATUS_DRY_RUN

    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(source, destination)
    except OSError:
        # Contorna placeholders do OneDrive que rejeitam sobrescrita direta.
        destination.unlink(missing_ok=True)
        shutil.copy2(source, destination)

    if sha256(destination) != new_hash:
        raise RuntimeError(f"Hash divergente após copiar para {destination}")

    return STATUS_UPDATED


def _force_utf8_output() -> None:
    """Força UTF-8 na saída (evita mojibake de acentos no Git Bash/cmd)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass


def main(argv: list[str] | None = None) -> int:
    _force_utf8_output()
    argv = list(sys.argv[1:] if argv is None else argv)
    dry_run = "--dry-run" in argv

    destination_dir = desktop_dir()
    if "--dest" in argv:
        index = argv.index("--dest")
        if index + 1 >= len(argv):
            print("[ERRO] Use: python publish.py --dest CAMINHO")
            return 2
        destination_dir = Path(argv[index + 1]).expanduser().resolve()

    destination = destination_dir / EXE_NAME

    print(f"Origem : {SOURCE_EXE}")
    print(f"Destino: {destination}")

    status = publish(SOURCE_EXE, destination, dry_run=dry_run)

    if status == STATUS_MISSING:
        print(f"[ERRO] Executável não encontrado: {SOURCE_EXE}")
        print("       Gere o build primeiro: project update")
        return 1

    if status == STATUS_RUNNING:
        print(f"[ERRO] {EXE_NAME} está em execução. Feche o programa e tente novamente.")
        return 1

    if status == STATUS_UP_TO_DATE:
        print("[OK] A Área de Trabalho já está com esta versão. Nada a fazer.")
        return 0

    if status == STATUS_DRY_RUN:
        print("[DRY-RUN] Nada foi alterado.")
        return 0

    size_mb = destination.stat().st_size / (1024 * 1024)
    print(f"[OK] Área de Trabalho atualizada ({size_mb:.1f} MB, SHA-256 conferido).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
