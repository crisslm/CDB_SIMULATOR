"""
Ponto de Entrada Principal - Interface Gráfica Moderna
"""

import customtkinter as ctk
from src.ui.gui.app import ModernAppGUI

if __name__ == "__main__":
    ctk.set_appearance_mode("Light")
    ctk.set_default_color_theme("blue")
    
    app = ModernAppGUI()
    app.mainloop()
