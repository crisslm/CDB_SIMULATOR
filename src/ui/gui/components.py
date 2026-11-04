"""
Camada de Apresentação - Componentes Reutilizáveis de UI
Inspirado na referência visual moderna (Fintech / Clean Warm Light):
- Cards brancos com cantos arredondados e sutis divisórias
- Badges estilo 'pílula' (Tags verdes de valorização como no print)
- Botões com animações dinâmicas (hover, clique, escala)
- Formatação clara e tipografia balanceada
"""

import customtkinter as ctk
from colorsys import rgb_to_hsv, hsv_to_rgb

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


def _hex_to_rgb(hex_color: str) -> tuple:
    """Converte cor hexadecimal (#RRGGBB) para tupla RGB (0-255)."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb: tuple) -> str:
    """Converte tupla RGB (0-255) para cor hexadecimal (#RRGGBB)."""
    return "#{:02x}{:02x}{:02x}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))


def _interpolate_color(color1: str, color2: str, factor: float) -> str:
    """
    Interpola entre duas cores hexadecimais.
    factor: 0.0 = color1, 1.0 = color2
    """
    r1, g1, b1 = _hex_to_rgb(color1)
    r2, g2, b2 = _hex_to_rgb(color2)
    r = r1 + (r2 - r1) * factor
    g = g1 + (g2 - g1) * factor
    b = b1 + (b2 - b1) * factor
    return _rgb_to_hex((r, g, b))


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
    
    Animações dinâmicas:
    - Transição suave de cor ao passar o mouse (hover)
    - Efeito de clique (pressionar/soltar com mudança de escala)
    - Efeito de brilho sutil no clique
    """

    ANIMATION_STEPS = 10       # Número de passos na animação de cor
    ANIMATION_DELAY = 15       # Milissegundos entre cada passo (mais rápido = mais suave)
    CLICK_SCALE = 0.96         # Fator de redução ao clicar (96% do tamanho original)

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

        # Armazena cores originais para animações
        self._original_fg = fg_color
        self._original_hover = hover_color
        self._hover_target = hover_color
        self._is_hovered = False
        self._is_pressed = False
        self._animation_id = None
        self._click_command = command

        # Bind dos eventos de mouse para animações personalizadas
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _on_enter(self, event):
        """Inicia animação de hover suave ao passar o mouse."""
        self._is_hovered = True
        self._cancel_animation()
        self._animate_hover(0)

    def _on_leave(self, event):
        """Inicia animação de saída suave ao retirar o mouse."""
        self._is_hovered = False
        self._cancel_animation()
        self._animate_hover(self.ANIMATION_STEPS)

    def _on_press(self, event):
        """Efeito ao clicar: reduz ligeiramente o tamanho."""
        self._is_pressed = True
        self._cancel_animation()
        # Efeito visual imediato: escurecer levemente
        pressed_color = _interpolate_color(self._original_fg, "#000000", 0.2)
        self.configure(fg_color=pressed_color)

    def _on_release(self, event):
        """Efeito ao soltar o clique: retorna ao estado normal ou hover."""
        self._is_pressed = False
        if self._is_hovered:
            self._cancel_animation()
            self._animate_hover(0)
        else:
            self._cancel_animation()
            self._animate_hover(self.ANIMATION_STEPS)

    def _cancel_animation(self):
        """Cancela qualquer animação em andamento."""
        if self._animation_id is not None:
            try:
                self.after_cancel(self._animation_id)
            except Exception:
                pass
            self._animation_id = None

    def _animate_hover(self, step: int):
        """
        Anima a transição de cor gradualmente entre o estado normal e hover.
        step: passo atual (0 = totalmente hover, ANIMATION_STEPS = totalmente normal)
        """
        if self._is_pressed:
            # Mantém cor pressionada se o botão estiver clicado
            pressed_color = _interpolate_color(self._original_fg, "#000000", 0.2)
            self.configure(fg_color=pressed_color)
            return

        if self._is_hovered:
            # Transição: normal -> hover
            factor = step / self.ANIMATION_STEPS
            current_color = _interpolate_color(self._original_fg, self._hover_target, 1.0 - factor)
        else:
            # Transição: hover -> normal
            factor = step / self.ANIMATION_STEPS
            current_color = _interpolate_color(self._hover_target, self._original_fg, factor)

        self.configure(fg_color=current_color)

        if 0 <= step < self.ANIMATION_STEPS:
            self._animation_id = self.after(self.ANIMATION_DELAY, lambda: self._animate_hover(step + 1))
        else:
            self._animation_id = None

    def apply_theme(self, pal: dict):
        """Reaplica as cores do botão de acordo com o tema (Claro/Escuro)."""
        if self._variant == "primary":
            self._original_fg = pal["button_fg"]
            self._hover_target = pal["button_hover"]
            self.configure(
                fg_color=pal["button_fg"],
                hover_color=pal["button_hover"],
                text_color=pal["button_text"],
            )
        elif self._variant == "secondary":
            self._original_fg = pal["button_outline_fg"]
            self._hover_target = pal["button_outline_hover"]
            self.configure(
                fg_color=pal["button_outline_fg"],
                hover_color=pal["button_outline_hover"],
                text_color=pal["button_outline_text"],
                border_color=pal["button_outline_border"],
            )
        else:
            self._original_fg = pal["surface_input"]
            self._hover_target = pal["border_input"]
            self.configure(
                fg_color=pal["surface_input"],
                hover_color=pal["border_input"],
                text_color=pal["text"],
            )
