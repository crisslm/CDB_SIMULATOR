"""
==============================================================================
PREVIEW COM LIVE-RELOAD PARA INTERFACE GRÁFICA (WATCHDOG)
==============================================================================
Monitora alterações em arquivos Python (.py) e reinicia a janela do aplicativo
instantaneamente assim que você salva alterações (Ctrl + S) no código.
"""

import sys
import os
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Diretórios e arquivos vigiados
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENTRYPOINT = os.path.join(BASE_DIR, "main_gui.py")
WATCH_PATHS = [
    os.path.join(BASE_DIR, "src"),
    ENTRYPOINT
]


class GuiReloaderHandler(FileSystemEventHandler):
    def __init__(self, start_callback):
        super().__init__()
        self.start_callback = start_callback
        self.last_reload = 0
        self.debounce_seconds = 0.5  # Evita disparos duplicados do editor de texto

    def on_any_event(self, event):
        # Apenas reage a arquivos Python salvos/modificados
        if event.is_directory or not event.src_path.endswith(".py"):
            return

        # Ignora arquivos de compilação ou temporários
        if "__pycache__" in event.src_path or ".git" in event.src_path:
            return

        now = time.time()
        if now - self.last_reload > self.debounce_seconds:
            self.last_reload = now
            rel_path = os.path.relpath(event.src_path, BASE_DIR)
            print(f"\n[LIVE RELOAD] Alteracao detectada em '{rel_path}' -> Reiniciando aplicacao...")
            self.start_callback()


class AppRunner:
    def __init__(self):
        self.process = None

    def start_app(self):
        """Mata o processo anterior (se ativo) e inicia a interface novamente."""
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=1.5)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass

        # Inicia a janela gráfica em processo independente com diretório de trabalho correto
        self.process = subprocess.Popen([sys.executable, ENTRYPOINT], cwd=BASE_DIR)

    def stop_app(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()


def main():
    print("=" * 65)
    print("      INICIANDO MODO PREVIEW COM AUTO-RELOAD (LIVE RELOAD)       ")
    print("=" * 65)
    print(f"Monitorando arquivos .py em: {BASE_DIR}\\src\\")
    print("Altere o codigo e salve (Ctrl + S) para ver a interface atualizar.")
    print("Pressione Ctrl + C no terminal para encerrar o modo preview.")
    print("=" * 65 + "\n")

    runner = AppRunner()
    runner.start_app()

    handler = GuiReloaderHandler(runner.start_app)
    observer = Observer()

    # Registra monitoramento nos caminhos de código
    for path in WATCH_PATHS:
        if os.path.exists(path):
            observer.schedule(handler, path=path, recursive=True)

    observer.start()

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[PREVIEW] Encerrando modo preview...")
        observer.stop()
        runner.stop_app()

    observer.join()
    print("[PREVIEW] Concluido com sucesso!")


if __name__ == "__main__":
    main()
