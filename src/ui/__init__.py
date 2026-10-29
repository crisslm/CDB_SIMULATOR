"""
Camada de Apresentação

Nota: ``executar_cli`` e o pacote ``gui`` sao importados sob demanda para evitar
ciclos de importacao (``cli`` depende de componentes de ``gui`` e vice-versa).
"""

__all__ = ["executar_cli"]


def __getattr__(name: str):
    if name == "executar_cli":
        from src.ui.cli import executar_cli

        return executar_cli
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__dir__ = lambda: list(__all__)  # noqa: E731
