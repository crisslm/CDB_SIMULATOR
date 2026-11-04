"""
Camada de Apresentação - Componentes Reutilizáveis de UI
Inspirado na referência visual moderna (Fintech / Clean Warm Light):
- Cards brancos com bordas arredondadas e sutis divisórias
- Badges estilo 'pílula' (Tags verdes de valorização como no print)
- Formatação clara e tipografia balanceada
"""

import customtkinter as ctk

from src.ui.gui.theme import PALETTES, THEME_MODES


def formatar_moeda(valor: float) -> str:
    """Formata valor float no padrão monetário brasileiro."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_tempo(meses) -> str:
    """Formata número de meses em anos e meses de forma amigável."""
    if meses is None:
        return "Superior a 100 anos"
    if meses == 0:
        return "Já atingido!"
    anos = meses // 12
    meses_restantes = meses % 12
    partes = []
    if anos > 0:
        partes.append(f"{anos} {'ano' if anos == 1 else 'anos'}")
    if meses_restantes > 0:
        partes.append(f"{meses_restantes} {'mês' if meses_restantes == 1 else 'meses'}")
    return f"{meses} meses ({', '.join(partes)})"


class MetricCard(ctk.CTkFrame):
    """
    Card estilizado com fundo branco, cantos bem arredondados (corner_radius=16)
    e tipografia fiel à referência visual.
    """

    def __init__(
        self,
        master,
        titulo: str,
        valor_inicial: str = "R$ 0,00",
        badge_text: str = None,
        is_highlight: bool = False,
        **kwargs
    ):
        self._is_highlight = is_highlight

        # Fundo do card: branco ou tom pastel leve para destaque
        fg_color = "#EBF7EE" if is_highlight else "#FFFFFF"
        border_color = "#BCE8CB" if is_highlight else "#EBEBEB"
        border_width = 1

        super().__init__(
            master,
            corner_radius=16,
            fg_color=fg_color,
            border_color=border_color,
            border_width=border_width,
            **kwargs
        )

        # Cabeçalho do Card (Título + Badge Opcional)
        self.frame_header = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_header.pack(fill="x", padx=14, pady=(12, 4))

        self.lbl_titulo = ctk.CTkLabel(
            self.frame_header,
            text=titulo,
            font=("Segoe UI", 12, "bold"),
            text_color="#8E8E93"
        )
        self.lbl_titulo.pack(side="left")

        # Badge estilo pílula (ex: +1.21% ou tag de status)
        self.badge = None
        if badge_text:
            self.badge = ctk.CTkLabel(
                self.frame_header,
                text=badge_text,
                font=("Segoe UI", 11, "bold"),
                text_color="#107C41",
                fg_color="#D1F2D9",
                corner_radius=10,
                padx=8,
                pady=2
            )
            self.badge.pack(side="right")

        # Valor Principal em destaque grande
        self.lbl_valor = ctk.CTkLabel(
            self,
            text=valor_inicial,
            font=("Segoe UI", 17, "bold"),
            text_color="#1C1C1E"
        )
        self.lbl_valor.pack(anchor="w", padx=14, pady=(0, 12))

    def update_value(self, novo_valor: str, badge_text: str = None):
        """Atualiza o valor principal e opcionalmente o texto da badge."""
        self.lbl_valor.configure(text=novo_valor)
        if self.badge and badge_text:
            self.badge.configure(text=badge_text)

    def apply_theme(self, pal: dict):
        """Reaplica as cores do card de acordo com o tema (Claro/Escuro)."""
        self.configure(
            fg_color=pal["accent_bg"] if self._is_highlight else pal["surface"],
            border_color=pal["accent"] if self._is_highlight else pal["border"],
        )
        self.lbl_titulo.configure(text_color=pal["text_muted"])
        self.lbl_valor.configure(text_color=pal["text"])
        if self.badge:
            self.badge.configure(fg_color=pal["accent_bg"], text_color=pal["accent_text"])


class PillButton(ctk.CTkButton):
    """
    Botão em formato de pílula (alta curvatura, canto arredondado de 20px),
    seguindo o design dos botões 'Buy', 'Sell' e filtros do print.
    """

    def __init__(self, master, text: str, command=None, variant: str = "primary", **kwargs):
        self._variant = variant
        if variant == "primary":  # Preto/Carvão elegante estilo 'Buy' do print
            fg_color = "#1C1C1E"
            hover_color = "#3A3A3C"
            text_color = "#FFFFFF"
            border_width = 0
            border_color = None
        elif variant == "secondary":  # Estilo pill 'Sell' com borda sutil
            fg_color = "#FFFFFF"
            hover_color = "#F2F2F7"
            text_color = "#1C1C1E"
            border_width = 1
            border_color = "#D1D1D6"
        elif variant == "mint":  # Verde menta característico de ações positivas
            fg_color = "#24C270"
            hover_color = "#1EB264"
            text_color = "#FFFFFF"
            border_width = 0
            border_color = None
        else:
            fg_color = "#F2F2F7"
            hover_color = "#E5E5EA"
            text_color = "#1C1C1E"
            border_width = 0
            border_color = None

        super().__init__(
            master,
            text=text,
            command=command,
            corner_radius=22,
            fg_color=fg_color,
            hover_color=hover_color,
            text_color=text_color,
            border_width=border_width,
            border_color=border_color,
            font=("Segoe UI", 13, "bold"),
            height=42,
            **kwargs
        )

    def apply_theme(self, pal: dict):
        """Reaplica as cores do botão de acordo com o tema (Claro/Escuro)."""
        if self._variant == "primary":
            self.configure(
                fg_color=pal["button_fg"],
                hover_color=pal["button_hover"],
                text_color=pal["button_text"],
            )
        elif self._variant == "secondary":
            self.configure(
                fg_color=pal["button_outline_fg"],
                hover_color=pal["button_outline_hover"],
                text_color=pal["button_outline_text"],
                border_color=pal["button_outline_border"],
            )
        else:
            self.configure(
                fg_color=pal["surface_input"],
                hover_color=pal["border_input"],
                text_color=pal["text"],
            )
