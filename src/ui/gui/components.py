"""
Camada de Apresentação - Componentes Reutilizáveis de UI
========================================================

Este módulo contém componentes visuais reutilizáveis da interface gráfica
do CDB Simulator, inspirados em design moderno de fintech (Clean Warm Light).

Componentes incluídos:
    1. formatar_moeda()  - Formata valores no padrão brasileiro (R$ 1.234,56)
    2. formatar_tempo()  - Formata meses em "X anos e Y meses"
    3. MetricCard        - Card de métrica com título, valor e badge opcional
    4. PillButton        - Botão estilo pílula com cantos arredondados

Funções auxiliares privadas:
    - _hex_to_rgb()      - Converte hex para RGB
    - _rgb_to_hex()      - Converte RGB para hex
    - _interpolate_color() - Interpola entre duas cores

Princípio de design:
- Componentes puros de apresentação, sem lógica de negócio.
- Cores são gerenciadas através de paletas (theme.py) para suporte a tema claro/escuro.

Autor: CDB Simulator
Versão: 1.0.0
"""

import customtkinter as ctk
from colorsys import rgb_to_hsv, hsv_to_rgb
from decimal import Decimal
import locale

from src.ui.gui.theme import PALETTES, THEME_MODES

# Tenta definir locale brasileiro para formatação monetária eficiente.
# Se falhar (ex: locale não instalado no sistema), mantém fallback com replace().
try:
    locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")
except Exception:
    try:
        locale.setlocale(locale.LC_ALL, "Portuguese_Brazil.1252")
    except Exception:
        pass


def formatar_moeda(valor) -> str:
    """
    Formata um valor numérico no padrão monetário brasileiro (pt-BR).

    Exemplo de saída: "R$ 1.250,50"

    Parâmetros:
        valor: Pode ser float, int, Decimal ou string numérica.
               Valores float são convertidos via Decimal(str(valor)) para
               evitar representações imprecisas como 1223.1100000000002.

    Retorna:
        str: String formatada com prefixo "R$ " e separadores brasileiros.

    Algoritmo:
        1. Converte para Decimal se necessário.
        2. Tenta usar locale pt_BR (mais eficiente, menos operações de string).
        3. Se locale falhar, usa fallback com .replace() encadeado.

    Observação de manutenção:
        Se o locale do sistema não suportar pt_BR, o fallback funciona
        corretamente em qualquer ambiente.
    """
    if not isinstance(valor, Decimal):
        valor = Decimal(str(valor))
    try:
        # locale.format_string já retorna no formato pt_BR: "1.234,56"
        formatted = locale.format_string("%.2f", float(valor), grouping=True)
        return f"R$ {formatted}"
    except Exception:
        # Fallback: replace encadeado (mais operações, mas funciona sempre)
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_tempo(meses) -> str:
    """
    Formata um número de meses em string amigável em português.

    Exemplos:
        None      -> "Superior a 100 anos"
        0         -> "Já atingido!"
        5         -> "5 meses (5 meses)"
        13        -> "13 meses (1 ano, 1 mês)"
        25        -> "25 meses (2 anos, 1 mês)"

    Parâmetros:
        meses: Número inteiro de meses, ou None.

    Retorna:
        str: String formatada em português.
    """
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


# =============================================================================
# Funções Auxiliares de Cor (Privadas)
# =============================================================================

def _hex_to_rgb(hex_color: str) -> tuple:
    """
    Converte uma cor hexadecimal (#RRGGBB) para tupla RGB (0-255).

    Parâmetros:
        hex_color (str): Cor no formato "#RRGGBB" ou "RRGGBB".

    Retorna:
        tuple: (R, G, B) com valores inteiros de 0 a 255.
    """
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb: tuple) -> str:
    """
    Converte uma tupla RGB (0-255) para cor hexadecimal (#RRGGBB).

    Parâmetros:
        rgb (tuple): Tupla (R, G, B) com valores de 0 a 255.

    Retorna:
        str: Cor no formato "#RRGGBB".
    """
    return "#{:02x}{:02x}{:02x}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))


def _interpolate_color(color1: str, color2: str, factor: float) -> str:
    """
    Interpola linearmente entre duas cores hexadecimais.

    Parâmetros:
        color1 (str): Cor inicial (#RRGGBB). Usada quando factor=0.0.
        color2 (str): Cor final (#RRGGBB). Usada quando factor=1.0.
        factor (float): Fator de interpolação de 0.0 a 1.0.

    Retorna:
        str: Cor interpolada no formato "#RRGGBB".

    Exemplo:
        _interpolate_color("#FFFFFF", "#000000", 0.5) -> "#808080" (cinza)
    """
    r1, g1, b1 = _hex_to_rgb(color1)
    r2, g2, b2 = _hex_to_rgb(color2)
    r = r1 + (r2 - r1) * factor
    g = g1 + (g2 - g1) * factor
    b = b1 + (b2 - b1) * factor
    return _rgb_to_hex((r, g, b))


# =============================================================================
# Classe MetricCard
# =============================================================================

class MetricCard(ctk.CTkFrame):
    """
    Card estilizado para exibição de métricas financeiras.

    Possui fundo branco (ou pastel se destacado), cantos arredondados,
    título, valor principal em destaque e um badge opcional (ex: "+12.5%").

    Usado para exibir:
        - Total Aportado
        - Lucro Bruto
        - Montante Bruto
        - Líquido (Pós-IR)
        - Tempo para Meta

    Atributos visuais:
        - lbl_titulo: Título da métrica (ex: "Total Aportado").
        - lbl_valor: Valor formatado (ex: "R$ 5.000,00").
        - badge: Badge opcional estilo pílula (ex: "+12.5%").

    Parâmetros:
        master: Widget pai do Tkinter.
        titulo (str): Título exibido no card.
        valor_inicial (str): Valor inicial formatado (ex: "R$ 0,00").
        badge_text (str | None): Texto opcional do badge.
        is_highlight (bool): Se True, usa fundo pastel e borda verde para destacar.
        **kwargs: Argumentos adicionais para CTkFrame.

    Exemplo de uso:
        card = MetricCard(frame, "Total Aportado", "R$ 5.000,00")
        card.update_value("R$ 10.000,00", badge_text="+100.0%")
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

        # Define cores com base se é destaque ou não
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

        # Cabeçalho do card (título + badge opcional)
        self.frame_header = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_header.pack(fill="x", padx=14, pady=(12, 4))

        self.lbl_titulo = ctk.CTkLabel(
            self.frame_header,
            text=titulo,
            font=("Segoe UI", 12, "bold"),
            text_color="#8E8E93"
        )
        self.lbl_titulo.pack(side="left")

        # Badge estilo pílula (ex: "+1.21%" ou tag de status)
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

        # Valor principal em destaque (fonte grande)
        self.lbl_valor = ctk.CTkLabel(
            self,
            text=valor_inicial,
            font=("Segoe UI", 17, "bold"),
            text_color="#1C1C1E"
        )
        self.lbl_valor.pack(anchor="w", padx=14, pady=(0, 12))

    def update_value(self, novo_valor: str, badge_text: str = None):
        """
        Atualiza o valor principal e opcionalmente o texto do badge.

        Parâmetros:
            novo_valor (str): Novo valor formatado (ex: "R$ 10.000,00").
            badge_text (str | None): Novo texto do badge, se houver.
        """
        self.lbl_valor.configure(text=novo_valor)
        if self.badge and badge_text:
            self.badge.configure(text=badge_text)

    def apply_theme(self, pal: dict):
        """
        Reaplica as cores do card conforme o tema (Claro/Escuro).

        Parâmetros:
            pal (dict): Dicionário de cores da paleta selecionada.
        """
        self._original_fg = pal["accent_bg"] if self._is_highlight else pal["surface"]
        self._original_border = pal["accent"] if self._is_highlight else pal["border"]

        self.configure(
            fg_color=self._original_fg,
            border_color=self._original_border,
        )
        self.lbl_titulo.configure(text_color=pal["text_muted"])
        self.lbl_valor.configure(text_color=pal["text"])
        if self.badge:
            self.badge.configure(fg_color=pal["accent_bg"], text_color=pal["accent_text"])


# =============================================================================
# Classe PillButton
# =============================================================================

class PillButton(ctk.CTkButton):
    """
    Botão em formato de pílula (cantos altamente arredondados, corner_radius=22).

    Variantes disponíveis:
        - "primary":  Fundo preto/carvão, texto branco (estilo "Buy").
        - "secondary": Fundo branco com borda, texto escuro (estilo "Sell").
        - "mint":     Fundo verde menta, texto branco (ações positivas).
        - outro:      Fundo cinza claro (neutro).

    O comando é executado pelo mecanismo nativo do CTkButton via parâmetro
    command. O efeito de hover usa o hover_color nativo do CTkButton.

    Parâmetros:
        master: Widget pai.
        text (str): Texto exibido no botão.
        command (callable | None): Função executada ao clicar.
        variant (str): Variante de estilo ("primary", "secondary", "mint").
        **kwargs: Argumentos adicionais para CTkButton.

    Exemplo de uso:
        btn = PillButton(frame, text="Simular", command=self.simular, variant="primary")
    """

    def __init__(self, master, text: str, command=None, variant: str = "primary", **kwargs):
        self._variant = variant

        # Define cores por variante
        if variant == "primary":
            fg_color = "#1C1C1E"
            hover_color = "#3A3A3C"
            text_color = "#FFFFFF"
            border_width = 0
            border_color = None
        elif variant == "secondary":
            fg_color = "#FFFFFF"
            hover_color = "#F2F2F7"
            text_color = "#1C1C1E"
            border_width = 1
            border_color = "#D1D1D6"
        elif variant == "mint":
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
        """
        Reaplica as cores do botão conforme o tema (Claro/Escuro).

        Parâmetros:
            pal (dict): Dicionário de cores da paleta selecionada.
        """
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