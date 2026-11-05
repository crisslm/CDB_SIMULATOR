"""
Paletas de Cores e Temas da Interface
=====================================

Este módulo define as paletas de cores para os temas Claro (Light) e Escuro (Dark)
da aplicação CDB Simulator.

É um módulo independente (sem dependências de outros módulos de UI) para evitar
ciclos de importação entre components.py e chart.py.

Estrutura:
    PALETTES: Dicionário com duas chaves ("Light", "Dark").
              Cada chave contém um dicionário com nomes semânticos de cor.
    THEME_MODES: Tupla com os nomes dos temas disponíveis.

Nomes semânticos de cor usados nas paletas:
    - bg_root: Fundo principal da janela.
    - surface: Fundo de cards e superfícies elevadas.
    - surface_input: Fundo de campos de entrada.
    - border: Cor de borda geral.
    - border_input: Cor de borda de campos de entrada.
    - text: Cor do texto principal.
    - text_muted: Cor do texto secundário (muted).
    - accent: Cor de destaque principal (verde menta).
    - accent_bg: Fundo de destaque (versão clara do accent).
    - accent_text: Texto sobre fundo de destaque.
    - button_fg: Fundo do botão primário.
    - button_hover: Fundo do botão primário no hover.
    - button_text: Texto do botão primário.
    - button_outline_*: Cores do botão secundário (contorno).
    - chart_*: Cores dos gráficos Matplotlib.
    - invested_line: Cor da linha de investido.
    - meta_line: Cor da linha da meta.

Autor: CDB Simulator
Versão: 1.0.0
"""

PALETTES = {
    "Light": {
        # Fundo e superfícies
        "bg_root": "#F9F9FB",      # Fundo principal da janela (off-white)
        "surface": "#FFFFFF",       # Fundo de cards (branco)
        "surface_input": "#F2F2F7", # Fundo de inputs e campos
        "border": "#EBEBEB",        # Borda geral
        "border_input": "#E5E5EA",  # Borda de inputs

        # Textos
        "text": "#1C1C1E",          # Texto principal (quase preto)
        "text_muted": "#8E8E93",    # Texto secundário (cinza médio)

        # Acentos (verde menta - cor de destaque)
        "accent": "#24C270",        # Verde menta vibrante
        "accent_bg": "#EBF7EE",     # Fundo de destaque (verde muito claro)
        "accent_text": "#107C41",   # Texto sobre fundo de destaque (verde escuro)

        # Botão primário (preto/carvão)
        "button_fg": "#1C1C1E",
        "button_hover": "#3A3A3C",
        "button_text": "#FFFFFF",

        # Botão secundário (contorno)
        "button_outline_fg": "#FFFFFF",
        "button_outline_hover": "#F2F2F7",
        "button_outline_text": "#1C1C1E",
        "button_outline_border": "#D1D1D6",

        # Gráficos
        "chart_bg": "#FFFFFF",
        "chart_spine": "#E5E5EA",
        "chart_grid": "#8E8E93",
        "chart_tick": "#8E8E93",
        "chart_legend_bg": "#F7F7F8",
        "chart_legend_edge": "#E5E5EA",
        "chart_legend_text": "#3A3A3C",
        "invested_line": "#A0A0A5",
        "meta_line": "#FF6B6B",
    },
    "Dark": {
        # Fundo e superfícies (tons escuros)
        "bg_root": "#121214",
        "surface": "#1C1C1E",
        "surface_input": "#2A2A2E",
        "border": "#333336",
        "border_input": "#3A3A3C",

        # Textos (tons claros)
        "text": "#F2F2F7",
        "text_muted": "#AEAEB3",

        # Acentos (verde menta mais suave para tema escuro)
        "accent": "#24C270",
        "accent_bg": "#103B24",
        "accent_text": "#6FE29F",

        # Botão primário (invertido para tema escuro)
        "button_fg": "#F2F2F7",
        "button_hover": "#FFFFFF",
        "button_text": "#1C1C1E",

        # Botão secundário (contorno)
        "button_outline_fg": "#2A2A2E",
        "button_outline_hover": "#3A3A3C",
        "button_outline_text": "#F2F2F7",
        "button_outline_border": "#4A4A4E",

        # Gráficos (fundo escuro)
        "chart_bg": "#1C1C1E",
        "chart_spine": "#3A3A3C",
        "chart_grid": "#3A3A3C",
        "chart_tick": "#AEAEB3",
        "chart_legend_bg": "#2A2A2E",
        "chart_legend_edge": "#3A3A3C",
        "chart_legend_text": "#D1D1D6",
        "invested_line": "#8E8E93",
        "meta_line": "#FF6B6B",
    },
}

THEME_MODES = ("Light", "Dark")