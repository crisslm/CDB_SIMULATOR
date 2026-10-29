"""
Camada de Apresentação - Interface Gráfica

Nota: ``ModernAppGUI`` e o pacote ``ui`` sao importados sob demanda para evitar
ciclos de importacao entre os pacotes ``ui`` e ``ui.gui``.
"""

__all__ = ["ModernAppGUI"]


def __getattr__(name: str):
    if name == "ModernAppGUI":
        from src.ui.gui.app import ModernAppGUI

        return ModernAppGUI
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__dir__ = lambda: list(__all__)  # noqa: E731
