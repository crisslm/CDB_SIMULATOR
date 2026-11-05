"""
Camada de Apresentação - Janela Principal da Aplicação Gráfica
===============================================================

Este módulo contém a janela principal (ModernAppGUI) do CDB Simulator,
construída com CustomTkinter. É responsável por:

    1. Exibir a interface de simulação de CDB (juros compostos).
    2. Exibir a interface de Controle Financeiro (receitas/despesas).
    3. Coordenar a navegação entre as duas seções.
    4. Validar entradas do usuário e disparar simulações via Casos de Uso.
    5. Gerenciar layout responsivo (mobile/desktop).
    6. Gerenciar tema claro/escuro com persistência.
    7. Gerenciar internacionalização (i18n) da interface.

Arquitetura:
    - Herda de ctk.CTk (janela principal do CustomTkinter).
    - Usa injeção de dependência para casos de uso e serviços.
    - Comunica com as camadas de serviço e domínio para cálculos.
    - A UI não contém lógica de negócio; delega para SimulateInvestmentUseCase
      e FinancialUseCases.

Princípio SOLID: Dependency Inversion Principle (DIP)
- Depende de abstrações (casos de uso), não de implementações concretas.

Autor: CDB Simulator
Versão: 1.1.0
"""

import json
import sys as _sys
from pathlib import Path
from typing import Optional

# Garante que o pacote src seja importável como pacote absoluto
# (útil quando executado via pytest a partir de tests/)
_sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import customtkinter as ctk
from tkinter import messagebox

from src.i18n.manager import t, set_language, get_language, get_translation_manager
from ...domain.constants import LIMITE_MONETARIO
from ...use_cases.simulate_investment import SimulateInvestmentUseCase, SimulationInput
from ...use_cases.financial_use_cases import FinancialUseCases
from ...domain.models import SimulationParams
from ...domain.strategies import CompoundInterestStrategy, CDIStrategy
from .chart import InvestmentChart
from .components import (
    MetricCard,
    PillButton,
    PALETTES,
    THEME_MODES,
    formatar_moeda,
    formatar_tempo,
)
from .financial.dashboard import FinancialDashboard


class ModernAppGUI(ctk.CTk):
    """
    Janela Principal do CDB Simulator com design responsivo (Mobile-Friendly e Desktop).

    Esta classe é o ponto de entrada da interface gráfica. Ela orquestra:
        - A barra de navegação (Simulador CDB / Controle Financeiro).
        - A barra lateral com formulário de entrada (simulador).
        - A área principal com cards de métricas e gráficos.
        - O dashboard financeiro (seção separada).
        - O gerenciamento de tema claro/escuro.
        - O gerenciamento de idioma (i18n).

    Atributos de classe:
        BREAKPOINT_MOBILE (int): Largura em pixels abaixo da qual o layout
                                 muda para mobile (coluna única). Padrão: 860.
        PALETTES (dict): Paletas de cores para temas Light e Dark.
        THEME_FILE (Path): Caminho do arquivo JSON que persiste a preferência
                           de tema do usuário.
        LANGUAGE_FILE (Path): Caminho do arquivo JSON que persiste a preferência
                              de idioma do usuário.

    Atributos de instância:
        simulator_use_case (SimulateInvestmentUseCase): Caso de uso de simulação.
        financial_use_cases (FinancialUseCases): Caso de uso de controle financeiro.
        active_section (str): Seção ativa ("simulator" ou "financial").
        is_mobile_layout (bool|None): Indica se está em layout mobile.
        theme_mode (str): "Light" ou "Dark".
        language (str): Código do idioma atual (ex: "pt_BR", "en_US").

    Exemplo de uso:
        app = ModernAppGUI()
        app.mainloop()
    """

    BREAKPOINT_MOBILE = 860

    # Paletas de tema (Claro / Escuro) importadas de components/theme
    PALETTES = PALETTES
    THEME_FILE = Path.home() / ".cdb_simulator_theme.json"
    LANGUAGE_FILE = Path.home() / ".cdb_simulator_language.json"

    def __init__(
        self,
        simulator_use_case: SimulateInvestmentUseCase | None = None,
        financial_use_cases: FinancialUseCases | None = None,
    ):
        """
        Inicializa a janela principal e constrói toda a interface.

        Parâmetros:
            simulator_use_case: Caso de uso de simulação (ou None para criar novo).
            financial_use_cases: Caso de uso financeiro (ou None para criar novo).

        Fluxo de inicialização:
            1. Configura casos de uso (injeção de dependência).
            2. Carrega tema e idioma salvos ou usa padrões.
            3. Configura janela (título, tamanho, mínimo).
            4. Constrói navegação, barra lateral e área principal.
            5. Cria o dashboard financeiro.
            6. Configura evento de redimensionamento.
            7. Aplica layout inicial, tema e idioma.
        """
        super().__init__()

        # Injeção de dependência - permite substituir casos de uso em testes
        self.simulator_use_case = simulator_use_case or SimulateInvestmentUseCase()
        self.financial_use_cases = financial_use_cases or FinancialUseCases()
        self.active_section = "simulator"
        self.is_mobile_layout = None
        self._last_width = 0
        self._last_height = 0
        self._resize_after_id: Optional[str] = None

        # Carrega preferência de tema salvo (padrão: Claro)
        self.theme_mode = self._load_theme()
        ctk.set_appearance_mode(self.theme_mode)
        self.configure(fg_color=self.PALETTES[self.theme_mode]["bg_root"])

        # Carrega preferência de idioma salvo (padrão: pt_BR)
        self.language = self._load_language()
        set_language(self.language)

        # Configurações básicas da janela
        self.title(t("app.title"))
        self.geometry("1160x780")  # Tamanho inicial
        self.minsize(360, 520)     # Suporte a janelas estreitas estilo mobile

        # Container principal com scroll (permite telas pequenas verticais)
        self.root_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="#F9F9FB",
            corner_radius=0
        )

        # Constrói os elementos da interface
        self._build_navigation()
        self.root_scroll.pack(fill="both", expand=True)
        self._build_sidebar()
        self._build_main_area()

        # Dashboard financeiro (seção separada do simulador)
        self.financial_dashboard = FinancialDashboard(
            self.root_scroll,
            self.financial_use_cases,
            self.PALETTES[self.theme_mode]
        )

        self._is_closing = False
        # Garante limpeza de recursos ao fechar a janela (evita processos órfãos)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Monitora redimensionamento para layout responsivo
        self.bind("<Configure>", self._on_window_resize)

        # Layout inicial, tema e idioma
        self._apply_responsive_layout(1160)
        self._apply_theme(self.theme_mode)

    # -------------------------------------------------------------------------
    # Encerramento e Limpeza
    # -------------------------------------------------------------------------

    def _on_close(self):
        """
        Encerra completamente o Tk e libera recursos gráficos.

        Este método é chamado quando o usuário fecha a janela (botão X).
        Ele garante que:
            1. Canvases do Matplotlib sejam destruídos (evita processos órfãos).
            2. Recursos Tk sejam liberados corretamente.
        """
        if self._is_closing:
            return
        self._is_closing = True
        try:
            self.financial_dashboard.fin_charts.dispose()
            self.chart_controller.dispose()
        finally:
            self.quit()
            self.destroy()

    # -------------------------------------------------------------------------
    # Navegação e Seções
    # -------------------------------------------------------------------------

    def _build_navigation(self):
        """
        Constrói a barra de navegação superior com dois botões:
            - Simulador CDB
            - Controle Financeiro
        """
        pal = self.PALETTES[self.theme_mode]
        self.frame_navigation = ctk.CTkFrame(self, fg_color=pal["surface"], height=58, corner_radius=0)
        self.frame_navigation.pack(fill="x")

        self.nav_simulator = PillButton(
            self.frame_navigation,
            text=t("nav.simulator"),
            command=lambda: self._show_section("simulator"),
            variant="secondary",
            width=145,
        )
        self.nav_financial = PillButton(
            self.frame_navigation,
            text=t("nav.financial"),
            command=lambda: self._show_section("financial"),
            variant="secondary",
            width=170,
        )
        self.nav_simulator.pack(side="left", padx=(18, 6), pady=11)
        self.nav_financial.pack(side="left", padx=6, pady=11)
        self.nav_simulator.apply_theme(pal)
        self.nav_financial.apply_theme(pal)

    def _show_section(self, section: str):
        """
        Alterna entre a seção do simulador e a de controle financeiro.

        Esconde a seção atual e exibe a solicitada, ajustando o layout
        responsivo conforme necessário.

        Parâmetros:
            section (str): "simulator" ou "financial".
        """
        self.active_section = section
        self.frame_sidebar.grid_forget()
        self.frame_main.grid_forget()
        self.financial_dashboard.grid_forget()

        width = max(self.winfo_width(), self.BREAKPOINT_MOBILE)

        if section == "financial":
            # Exibe dashboard financeiro ocupando a largura total
            self.root_scroll.grid_columnconfigure(0, weight=1)
            self.root_scroll.grid_columnconfigure(1, weight=0)
            self.financial_dashboard.grid(
                row=0, column=0, columnspan=2,
                padx=18 if width >= self.BREAKPOINT_MOBILE else 12,
                pady=18 if width >= self.BREAKPOINT_MOBILE else 12,
                sticky="nsew"
            )
            self.financial_dashboard.apply_layout(width)
            self.financial_dashboard.refresh()
        else:
            # Volta para o simulador
            self.is_mobile_layout = None
            self._apply_responsive_layout(width)

        self._update_navigation()

    def _update_navigation(self):
        """
        Atualiza o estado visual dos botões de navegação
        (qual está ativo: primary ou secondary).
        """
        pal = self.PALETTES[self.theme_mode]
        for button, is_active in (
            (self.nav_simulator, self.active_section == "simulator"),
            (self.nav_financial, self.active_section == "financial"),
        ):
            button._variant = "primary" if is_active else "secondary"
            button.apply_theme(pal)

    # -------------------------------------------------------------------------
    # Barra Lateral (Sidebar) - Formulário do Simulador
    # -------------------------------------------------------------------------

    def _build_sidebar(self):
        """
        Constrói o formulário de entrada de parâmetros do simulador.

        Campos incluídos:
            1. Tipo de investimento (Taxa Prefixada ou CDI)
            2. Valor inicial
            3. Aporte mensal
            4. Taxa de rendimento / % do CDI
            5. Taxa base do CDI (apenas no modo CDI)
            6. Prazo (anos ou meses)
            7. Meta financeira
            8. Botão "Simular Rendimento"
            9. Seletor de idioma

        Também configura listas de referências para atualização de tema.
        """
        self.frame_sidebar = ctk.CTkFrame(
            self.root_scroll,
            fg_color="#FFFFFF",
            corner_radius=20,
            border_width=1,
            border_color="#EBEBEB"
        )

        pal = self.PALETTES[self.theme_mode]

        # Cabeçalho com título, botão de tema e seletor de idioma
        frame_header = ctk.CTkFrame(self.frame_sidebar, fg_color="transparent")
        frame_header.pack(fill="x", padx=16, pady=(16, 12))

        self.lbl_header = ctk.CTkLabel(
            frame_header,
            text=t("sidebar.header"),
            font=("Segoe UI", 16, "bold"),
            text_color=pal["text"],
            anchor="w"
        )
        self.lbl_header.pack(side="left")

        # Botão de tema
        texto_tema = t("nav.theme.dark") if self.theme_mode == "Dark" else t("nav.theme.light")
        self.btn_tema = PillButton(
            frame_header,
            text=texto_tema,
            variant="secondary",
            command=self._toggle_theme,
            width=120,
        )
        self.btn_tema.pack(side="right", padx=(8, 4))
        self.btn_tema.apply_theme(pal)

        # Seletor de idioma
        self.combo_idioma = ctk.CTkComboBox(
            frame_header,
            values=list(get_translation_manager().get_available_languages().values()),
            width=120,
            corner_radius=12,
            height=30,
            fg_color="#F2F2F7",
            border_color="#E5E5EA",
            button_color="#E5E5EA",
            button_hover_color="#D1D1D6",
            text_color="#1C1C1E",
            dropdown_fg_color="#FFFFFF",
            dropdown_text_color="#1C1C1E",
            command=self._on_language_change,
        )
        # Define o idioma atual no combo
        idiomas = get_translation_manager().get_available_languages()
        nome_atual = idiomas.get(self.language, "Português")
        self.combo_idioma.set(nome_atual)
        self.combo_idioma.pack(side="right", padx=(4, 0))

        # 1. Tipo de Rendimento / Estratégia
        lbl_estrategia = ctk.CTkLabel(
            self.frame_sidebar,
            text=t("sidebar.strategy.label"),
            font=("Segoe UI", 11, "bold"),
            text_color="#8E8E93",
            anchor="w"
        )
        lbl_estrategia.pack(fill="x", padx=16, pady=(4, 4))

        self.combo_estrategia = ctk.CTkComboBox(
            self.frame_sidebar,
            values=[t("sidebar.strategy.prefix"), t("sidebar.strategy.cdi")],
            command=self._on_strategy_change,
            corner_radius=12,
            height=38,
            fg_color="#F2F2F7",
            border_color="#E5E5EA",
            button_color="#E5E5EA",
            button_hover_color="#D1D1D6",
            text_color="#1C1C1E",
            dropdown_fg_color="#FFFFFF",
            dropdown_text_color="#1C1C1E"
        )
        self.combo_estrategia.set(t("sidebar.strategy.prefix"))
        self.combo_estrategia.pack(fill="x", padx=16, pady=(0, 12))

        # 2. Valor Inicial
        lbl_inicial = ctk.CTkLabel(
            self.frame_sidebar,
            text=t("sidebar.initial.label"),
            font=("Segoe UI", 11, "bold"),
            text_color="#8E8E93",
            anchor="w"
        )
        lbl_inicial.pack(fill="x", padx=16, pady=(2, 4))

        self.entry_inicial = ctk.CTkEntry(
            self.frame_sidebar,
            corner_radius=12,
            height=38,
            fg_color="#F2F2F7",
            border_color="#E5E5EA",
            text_color="#1C1C1E"
        )
        self.entry_inicial.insert(0, "5000")
        self.entry_inicial.pack(fill="x", padx=16, pady=(0, 12))

        # 3. Aporte Mensal
        lbl_mensal = ctk.CTkLabel(
            self.frame_sidebar,
            text=t("sidebar.monthly.label"),
            font=("Segoe UI", 11, "bold"),
            text_color="#8E8E93",
            anchor="w"
        )
        lbl_mensal.pack(fill="x", padx=16, pady=(2, 4))

        self.entry_mensal = ctk.CTkEntry(
            self.frame_sidebar,
            corner_radius=12,
            height=38,
            fg_color="#F2F2F7",
            border_color="#E5E5EA",
            text_color="#1C1C1E"
        )
        self.entry_mensal.insert(0, "500")
        self.entry_mensal.pack(fill="x", padx=16, pady=(0, 12))

        # 4. Taxa de Juros / Percentual CDI
        self.lbl_taxa = ctk.CTkLabel(
            self.frame_sidebar,
            text=t("sidebar.rate.label"),
            font=("Segoe UI", 11, "bold"),
            text_color="#8E8E93",
            anchor="w"
        )
        self.lbl_taxa.pack(fill="x", padx=16, pady=(2, 4))

        self.frame_taxa = ctk.CTkFrame(self.frame_sidebar, fg_color="transparent")
        self.frame_taxa.pack(fill="x", padx=16, pady=(0, 10))

        self.entry_taxa = ctk.CTkEntry(
            self.frame_taxa,
            corner_radius=12,
            height=38,
            fg_color="#F2F2F7",
            border_color="#E5E5EA",
            text_color="#1C1C1E"
        )
        self.entry_taxa.insert(0, "12.0")
        self.entry_taxa.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.combo_periodo_taxa = ctk.CTkComboBox(
            self.frame_taxa,
            values=["% ao ano", "% ao mês"],
            width=115,
            corner_radius=12,
            height=38,
            fg_color="#F2F2F7",
            border_color="#E5E5EA",
            button_color="#E5E5EA",
            button_hover_color="#D1D1D6",
            text_color="#1C1C1E",
            dropdown_fg_color="#FFFFFF",
            dropdown_text_color="#1C1C1E"
        )
        self.combo_periodo_taxa.set("% ao ano")
        self.combo_periodo_taxa.pack(side="right")

        # Campo Extra para Taxa Base do CDI (apenas no modo CDI)
        self.frame_cdi_base = ctk.CTkFrame(self.frame_sidebar, fg_color="transparent")
        self.lbl_cdi_base = ctk.CTkLabel(
            self.frame_cdi_base,
            text=t("sidebar.cdi_base.label"),
            font=("Segoe UI", 11, "bold"),
            text_color="#8E8E93",
            anchor="w"
        )
        self.lbl_cdi_base.pack(fill="x", pady=(2, 4))
        self.entry_cdi_base = ctk.CTkEntry(
            self.frame_cdi_base,
            corner_radius=12,
            height=38,
            fg_color="#F2F2F7",
            border_color="#E5E5EA",
            text_color="#1C1C1E"
        )
        self.entry_cdi_base.insert(0, "10.75")
        self.entry_cdi_base.pack(fill="x", pady=(0, 10))

        # 5. Tempo / Período
        lbl_periodo = ctk.CTkLabel(
            self.frame_sidebar,
            text=t("sidebar.period.label"),
            font=("Segoe UI", 11, "bold"),
            text_color="#8E8E93",
            anchor="w"
        )
        lbl_periodo.pack(fill="x", padx=16, pady=(2, 4))

        frame_periodo = ctk.CTkFrame(self.frame_sidebar, fg_color="transparent")
        frame_periodo.pack(fill="x", padx=16, pady=(0, 12))

        self.entry_periodo = ctk.CTkEntry(
            frame_periodo,
            corner_radius=12,
            height=38,
            fg_color="#F2F2F7",
            border_color="#E5E5EA",
            text_color="#1C1C1E"
        )
        self.entry_periodo.insert(0, "5")
        self.entry_periodo.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.combo_tipo_periodo = ctk.CTkComboBox(
            frame_periodo,
            values=[t("sidebar.period.years"), t("sidebar.period.months")],
            width=115,
            corner_radius=12,
            height=38,
            fg_color="#F2F2F7",
            border_color="#E5E5EA",
            button_color="#E5E5EA",
            button_hover_color="#D1D1D6",
            text_color="#1C1C1E",
            dropdown_fg_color="#FFFFFF",
            dropdown_text_color="#1C1C1E"
        )
        self.combo_tipo_periodo.set(t("sidebar.period.years"))
        self.combo_tipo_periodo.pack(side="right")

        # 6. Meta Desejada
        lbl_meta = ctk.CTkLabel(
            self.frame_sidebar,
            text=t("sidebar.target.label"),
            font=("Segoe UI", 11, "bold"),
            text_color="#8E8E93",
            anchor="w"
        )
        lbl_meta.pack(fill="x", padx=16, pady=(2, 4))

        self.entry_meta = ctk.CTkEntry(
            self.frame_sidebar,
            corner_radius=12,
            height=38,
            fg_color="#F2F2F7",
            border_color="#E5E5EA",
            text_color="#1C1C1E"
        )
        self.entry_meta.insert(0, "1000000")
        self.entry_meta.pack(fill="x", padx=16, pady=(0, 16))

        # Botão Principal - dispara a simulação
        self.btn_simular = PillButton(
            self.frame_sidebar,
            text=t("sidebar.simulate.button"),
            variant="primary",
            command=self.on_simulate_click
        )
        self.btn_simular.pack(fill="x", padx=16, pady=(4, 16))
        self.btn_simular.apply_theme(pal)

        # Referências de widgets para atualização de tema
        self._entries = [
            self.entry_inicial,
            self.entry_mensal,
            self.entry_taxa,
            self.entry_cdi_base,
            self.entry_periodo,
            self.entry_meta,
        ]
        self._combos = [
            self.combo_estrategia,
            self.combo_periodo_taxa,
            self.combo_tipo_periodo,
            self.combo_idioma,
        ]
        self._labels_muted = [
            lbl_estrategia,
            lbl_inicial,
            lbl_mensal,
            self.lbl_taxa,
            lbl_periodo,
            lbl_meta,
            self.lbl_cdi_base,
        ]

    # -------------------------------------------------------------------------
    # Tema (Claro / Escuro)
    # -------------------------------------------------------------------------

    def _toggle_theme(self):
        """
        Alterna entre modo Claro e Escuro e persiste a preferência.
        """
        novo_modo = "Dark" if self.theme_mode == "Light" else "Light"
        self._apply_theme(novo_modo)

    def _apply_theme(self, modo: str):
        """
        Aplica a paleta de cores (Claro/Escuro) em toda a interface.

        Atualiza cores de janela, containers, textos, entradas, botões,
        cards e gráficos. Não reexecuta a simulação (apenas reaplica cores).

        Parâmetros:
            modo (str): "Light" ou "Dark".
        """
        self.theme_mode = modo
        ctk.set_appearance_mode(modo)
        pal = self.PALETTES[modo]

        # Janela e containers principais
        self.configure(fg_color=pal["bg_root"])
        self.root_scroll.configure(fg_color=pal["bg_root"])
        self.frame_sidebar.configure(fg_color=pal["surface"], border_color=pal["border"])
        self.frame_main.configure(fg_color="transparent")
        self.frame_cards.configure(fg_color="transparent")
        self.frame_chart_card.configure(fg_color=pal["surface"], border_color=pal["border"])
        self.frame_bar_card.configure(fg_color=pal["surface"], border_color=pal["border"])
        self.frame_navigation.configure(fg_color=pal["surface"])

        # Textos
        self.lbl_header.configure(text_color=pal["text"])
        self.lbl_section.configure(text_color=pal["text"])
        self.btn_tema.configure(
            text=t("nav.theme.dark") if modo == "Dark" else t("nav.theme.light")
        )
        for lbl in self._labels_muted:
            lbl.configure(text_color=pal["text_muted"])

        # Campos de entrada e comboboxes
        for ent in self._entries:
            ent.configure(
                fg_color=pal["surface_input"],
                border_color=pal["border_input"],
                text_color=pal["text"],
            )
        for cb in self._combos:
            cb.configure(
                fg_color=pal["surface_input"],
                border_color=pal["border_input"],
                button_color=pal["surface_input"],
                button_hover_color=pal["border_input"],
                text_color=pal["text"],
                dropdown_fg_color=pal["surface"],
                dropdown_text_color=pal["text"],
            )

        # Botões e cards
        self.btn_simular.apply_theme(pal)
        self.btn_tema.apply_theme(pal)
        for card in self.cards_list:
            card.apply_theme(pal)

        # Gráficos (reaplica cores, não reexecuta simulação)
        self.chart_controller.apply_theme(pal)
        if hasattr(self, "financial_dashboard"):
            self.financial_dashboard.apply_theme(pal)
        self._update_navigation()

        # Persiste a escolha do usuário em arquivo JSON
        self._save_theme()

    def _load_theme(self) -> str:
        """
        Carrega o tema salvo no arquivo de preferência.

        Retorna:
            str: "Light" ou "Dark". Padrão: "Light".
        """
        try:
            dados = json.loads(self.THEME_FILE.read_text(encoding="utf-8"))
            modo = dados.get("mode", "Light")
            return modo if modo in THEME_MODES else "Light"
        except Exception:
            return "Light"

    def _save_theme(self):
        """
        Salva a preferência de tema atual em arquivo JSON.
        """
        try:
            self.THEME_FILE.write_text(
                json.dumps({"mode": self.theme_mode}), encoding="utf-8"
            )
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Idioma (i18n)
    # -------------------------------------------------------------------------

    def _load_language(self) -> str:
        """
        Carrega o idioma salvo no arquivo de preferência.

        Retorna:
            str: Código do idioma (ex: "pt_BR", "en_US"). Padrão: "pt_BR".
        """
        try:
            dados = json.loads(self.LANGUAGE_FILE.read_text(encoding="utf-8"))
            idioma = dados.get("language", "pt_BR")
            return idioma if idioma in get_translation_manager().get_available_languages() else "pt_BR"
        except Exception:
            return "pt_BR"

    def _save_language(self):
        """
        Salva a preferência de idioma atual em arquivo JSON.
        """
        try:
            self.LANGUAGE_FILE.write_text(
                json.dumps({"language": self.language}), encoding="utf-8"
            )
        except Exception:
            pass

    def _on_language_change(self, nome_idioma: str):
        """
        Altera o idioma da interface quando o usuário seleciona um novo idioma.

        Parâmetros:
            nome_idioma (str): Nome nativo do idioma selecionado (ex: "English").
        """
        # Encontra o código do idioma pelo nome nativo
        idiomas = get_translation_manager().get_available_languages()
        codigo_idioma = None
        for codigo, nome in idiomas.items():
            if nome == nome_idioma:
                codigo_idioma = codigo
                break

        if codigo_idioma and codigo_idioma != self.language:
            self.language = codigo_idioma
            set_language(codigo_idioma)
            self._save_language()
            self._rebuild_ui_texts()

    def _rebuild_ui_texts(self):
        """
        Reaplica todos os textos da interface no novo idioma.

        Atualiza labels, botões, placeholders e títulos conforme o idioma
        atualmente selecionado. Não reexecuta a simulação.
        """
        # Título da janela
        self.title(t("app.title"))

        # Navegação
        self.nav_simulator.configure(text=t("nav.simulator"))
        self.nav_financial.configure(text=t("nav.financial"))

        # Cabeçalho da sidebar
        self.lbl_header.configure(text=t("sidebar.header"))

        # Botão de tema
        texto_tema = t("nav.theme.dark") if self.theme_mode == "Dark" else t("nav.theme.light")
        self.btn_tema.configure(text=texto_tema)

        # Seletor de idioma - atualizar seleção atual
        idiomas = get_translation_manager().get_available_languages()
        nome_atual = idiomas.get(self.language, "Português")
        self.combo_idioma.set(nome_atual)

        # Estratégia
        self.lbl_estrategia = None  # já existe, vamos atualizar via labels_muted
        # Reconstroi valores do combo de estratégia
        self.combo_estrategia.configure(values=[t("sidebar.strategy.prefix"), t("sidebar.strategy.cdi")])
        # Mantém a seleção atual traduzindo de volta
        atual = self.combo_estrategia.get()
        if "CDI" in atual or "CDI" in t("sidebar.strategy.cdi"):
            self.combo_estrategia.set(t("sidebar.strategy.cdi"))
        else:
            self.combo_estrategia.set(t("sidebar.strategy.prefix"))

        # Labels de campos
        self.lbl_inicial = None
        self.lbl_mensal = None
        self.lbl_taxa.configure(text=t("sidebar.rate.label"))
        self.lbl_cdi_base.configure(text=t("sidebar.cdi_base.label"))
        self.lbl_periodo = None
        self.lbl_meta = None

        # Atualiza labels muted (precisamos recriar ou acessar diretamente)
        # Para simplificar, atualizamos os labels conhecidos
        for lbl in self._labels_muted:
            # Cada label tem um texto específico; mapeamos por conteúdo aproximado
            texto_atual = lbl.cget("text")
            novo_texto = self._traduzir_label_sidebar(texto_atual)
            lbl.configure(text=novo_texto)

        # Placeholder dos campos de entrada (CustomTkinter usa placeholder_text)
        # Não temos placeholders nos entries atuais, então pulamos

        # Botão simular
        self.btn_simular.configure(text=t("sidebar.simulate.button"))

        # Combo de período da taxa
        # Mantém valores em português/inglês conforme contexto (não traduzido no JSON)
        # O combo de período da taxa usa valores fixos "% ao ano" / "% ao mês"
        # que são específicos do Brasil; mantemos como estão ou traduzimos

        # Combo de tipo de período (Anos/Meses)
        self.combo_tipo_periodo.configure(values=[t("sidebar.period.years"), t("sidebar.period.months")])
        atual_periodo = self.combo_tipo_periodo.get()
        if atual_periodo in ["Anos", "Years"]:
            self.combo_tipo_periodo.set(t("sidebar.period.years"))
        elif atual_periodo in ["Meses", "Months"]:
            self.combo_tipo_periodo.set(t("sidebar.period.months"))

        # Título da seção principal
        if hasattr(self, "lbl_section"):
            self.lbl_section.configure(text=t("app.section.title"))

        # Atualiza cards se existirem
        if hasattr(self, "cards_list"):
            # Os cards serão atualizados na próxima simulação
            pass

        # Atualiza dashboard financeiro se existir
        if hasattr(self, "financial_dashboard"):
            self.financial_dashboard.apply_theme(self.PALETTES[self.theme_mode])
            self.financial_dashboard.refresh()

        # Persiste idioma
        self._save_language()

    def _traduzir_label_sidebar(self, texto_atual: str) -> str:
        """
        Mapeia um texto de label da sidebar para a chave de tradução correspondente.

        Como os labels são criados com textos hardcoded originalmente, este método
        faz o mapeamento reverso para atualizar quando o idioma muda.

        Parâmetros:
            texto_atual (str): Texto atual do label.

        Retorna:
            str: Texto traduzido.
        """
        mapeamento = {
            "TIPO DE INVESTIMENTO": t("sidebar.strategy.label"),
            "VALOR INICIAL (R$)": t("sidebar.initial.label"),
            "APORTE MENSAL (R$)": t("sidebar.monthly.label"),
            "TAXA DE RENDIMENTO (%)": t("sidebar.rate.label"),
            "PRAZO DE INVESTIMENTO": t("sidebar.period.label"),
            "OBJETIVO / META (R$)": t("sidebar.target.label"),
            "CDI ANUAL BASE (% a.a.)": t("sidebar.cdi_base.label"),
            "% DO CDI (ex: 110%:)": t("sidebar.rate.cdi"),
        }
        return mapeamento.get(texto_atual, texto_atual)

    # -------------------------------------------------------------------------
    # Mudança de Estratégia (Prefixado vs CDI)
    # -------------------------------------------------------------------------

    def _on_strategy_change(self, choice: str):
        """
        Altera a interface conforme o tipo de taxa selecionada.

        Quando "CDI" é selecionado:
            - Exibe campo "CDI ANUAL BASE".
            - Desabilita combo "% ao ano / % ao mês".
            - Define valor padrão 110% no campo de taxa.

        Quando "Taxa Prefixada" é selecionado:
            - Esconde campo CDI base.
            - Habilita combo de período da taxa.
            - Define valor padrão 12.0%.

        Parâmetros:
            choice (str): Texto selecionado no combo de estratégia.
        """
        # Detecta se é CDI baseado no texto atual ou traduzido
        é_cdi = "CDI" in choice or choice == t("sidebar.strategy.cdi")
        if é_cdi:
            self.lbl_taxa.configure(text=t("sidebar.rate.cdi"))
            self.entry_taxa.delete(0, "end")
            self.entry_taxa.insert(0, "110")
            self.combo_periodo_taxa.configure(state="disabled")
            self.frame_cdi_base.pack(fill="x", padx=16, pady=(0, 10), after=self.frame_taxa)
        else:
            self.lbl_taxa.configure(text=t("sidebar.rate.label"))
            self.entry_taxa.delete(0, "end")
            self.entry_taxa.insert(0, "12.0")
            self.combo_periodo_taxa.configure(state="normal")
            self.frame_cdi_base.pack_forget()

    # -------------------------------------------------------------------------
    # Área Principal - Cards e Gráficos
    # -------------------------------------------------------------------------

    def _build_main_area(self):
        """
        Constrói o painel de resultados com:
            - 5 cards de métrica (Total Aportado, Lucro Bruto, Montante Bruto,
              Líquido Pós-IR, Tempo p/ Meta).
            - 2 gráficos (Timeline de evolução e Barras até a meta).
        """
        self.frame_main = ctk.CTkFrame(self.root_scroll, fg_color="transparent")

        self.lbl_section = ctk.CTkLabel(
            self.frame_main,
            text=t("app.section.title"),
            font=("Segoe UI", 18, "bold"),
            text_color="#1C1C1E",
            anchor="w"
        )
        self.lbl_section.pack(fill="x", pady=(0, 10))

        # Container dos Cards de Métricas
        self.frame_cards = ctk.CTkFrame(self.frame_main, fg_color="transparent")
        self.frame_cards.pack(fill="x", pady=(0, 12))

        # Cards estilizados
        self.card_investido = MetricCard(self.frame_cards, t("card.total_invested"), "R$ 0,00")
        self.card_juros = MetricCard(self.frame_cards, t("card.gross_profit"), "R$ 0,00", badge_text="+0.0%")
        self.card_total = MetricCard(self.frame_cards, t("card.gross_balance"), "R$ 0,00")
        self.card_liquido = MetricCard(
            self.frame_cards,
            t("card.net_balance"),
            "R$ 0,00",
            badge_text="IR 15%",
            is_highlight=True
        )
        self.card_meta = MetricCard(self.frame_cards, t("card.time_to_target"), "-")

        self.cards_list = [
            self.card_investido,
            self.card_juros,
            self.card_total,
            self.card_liquido,
            self.card_meta
        ]

        # Container dos Gráficos (2 linhas: linha e barras)
        self.frame_charts_container = ctk.CTkFrame(self.frame_main, fg_color="transparent")
        self.frame_charts_container.pack(fill="both", expand=True, pady=(0, 10))
        self.frame_charts_container.grid_rowconfigure((0, 1), weight=1)
        self.frame_charts_container.grid_columnconfigure(0, weight=1)

        # Card do Gráfico de Linha (Timeline)
        self.frame_chart_card = ctk.CTkFrame(
            self.frame_charts_container,
            fg_color="#FFFFFF",
            corner_radius=20,
            border_width=1,
            border_color="#EBEBEB"
        )
        self.frame_chart_card.grid(row=0, column=0, sticky="nsew", pady=(0, 8))

        # Card do Gráfico de Barras (Evolução até a meta)
        self.frame_bar_card = ctk.CTkFrame(
            self.frame_charts_container,
            fg_color="#FFFFFF",
            corner_radius=20,
            border_width=1,
            border_color="#EBEBEB"
        )
        self.frame_bar_card.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        self.chart_controller = InvestmentChart(self.frame_chart_card, bar_widget=self.frame_bar_card)

    # -------------------------------------------------------------------------
    # Layout Responsivo
    # -------------------------------------------------------------------------

    def _on_window_resize(self, event):
        """
        Disparado quando a janela é redimensionada.

        Usa debounce (150ms) para evitar recálculos contínuos durante o
        arraste da borda da janela. Só recalcula se a mudança for > 15px.

        Parâmetros:
            event: Evento de <Configure> do Tkinter.
        """
        if event.widget == self:
            if abs(event.width - self._last_width) > 15:
                self._last_width = event.width
                self._last_height = event.height
                if self._resize_after_id is not None:
                    self.after_cancel(self._resize_after_id)
                self._resize_after_id = self.after(
                    150, lambda: self._apply_responsive_layout(event.width)
                )

    def _apply_responsive_layout(self, window_width: int):
        """
        Alterna dinamicamente entre layout Mobile e Desktop.

        Mobile (< 860px): Sidebar empilhada acima, cards em 2 colunas.
        Desktop (>= 860px): Sidebar à esquerda (340px fixo), área principal à direita,
                            cards em 5 colunas.

        Parâmetros:
            window_width (int): Largura atual da janela em pixels.
        """
        if self.active_section == "financial":
            self.frame_sidebar.grid_forget()
            self.frame_main.grid_forget()
            self.financial_dashboard.grid(
                row=0, column=0, columnspan=2,
                padx=18 if window_width >= self.BREAKPOINT_MOBILE else 12,
                pady=18 if window_width >= self.BREAKPOINT_MOBILE else 12,
                sticky="nsew"
            )
            self.financial_dashboard.apply_layout(window_width)
            return

        is_mobile = window_width < self.BREAKPOINT_MOBILE

        if is_mobile != self.is_mobile_layout:
            self.is_mobile_layout = is_mobile

            self.root_scroll.grid_columnconfigure(0, weight=1)
            self.root_scroll.grid_columnconfigure(1, weight=1 if not is_mobile else 0)

            self.frame_sidebar.grid_forget()
            self.frame_main.grid_forget()

            if is_mobile:
                # Layout Mobile: empilhado verticalmente
                self.frame_sidebar.grid(row=0, column=0, padx=12, pady=(12, 10), sticky="ew")
                self.frame_main.grid(row=1, column=0, padx=12, pady=(0, 16), sticky="nsew")
                self._configure_cards_grid(columns=2)
            else:
                # Layout Desktop: 2 colunas lado a lado
                self.root_scroll.grid_columnconfigure(0, weight=0, minsize=340)
                self.root_scroll.grid_columnconfigure(1, weight=1)
                self.frame_sidebar.grid(row=0, column=0, padx=(18, 10), pady=18, sticky="nsew")
                self.frame_main.grid(row=0, column=1, padx=(10, 18), pady=18, sticky="nsew")
                self._configure_cards_grid(columns=5)

    def _configure_cards_grid(self, columns: int):
        """
        Reconfigura o grid dos cards de métrica conforme o número de colunas.

        No mobile (2 colunas), o 5º card (Tempo p/ Meta) expande ocupando
        as 2 colunas da última linha.

        Parâmetros:
            columns (int): Número de colunas (2 para mobile, 5 para desktop).
        """
        for c in range(5):
            self.frame_cards.grid_columnconfigure(c, weight=0)

        for card in self.cards_list:
            card.grid_forget()

        for c in range(columns):
            self.frame_cards.grid_columnconfigure(c, weight=1)

        for index, card in enumerate(self.cards_list):
            row = index // columns
            col = index % columns

            if columns == 2 and index == 4:
                card.grid(row=row, column=0, columnspan=2, padx=4, pady=3, sticky="nsew")
            else:
                card.grid(row=row, column=col, padx=4, pady=3, sticky="nsew")

    # -------------------------------------------------------------------------
    # Simulação - Ponto Principal de Ação (via Caso de Uso)
    # -------------------------------------------------------------------------

    def on_simulate_click(self):
        """
        Executa a lógica completa de simulação quando o usuário clica
        no botão "Simular Rendimento".

        Fluxo:
            1. Coleta dados brutos dos campos de entrada.
            2. Cria SimulationInput e chama o Caso de Uso.
            3. O Caso de Uso valida, converte e executa a simulação.
            4. Atualiza cards e gráficos com o resultado.

        Todas as exceções de validação são capturadas e exibidas em
        messagebox amigáveis.
        """
        try:
            input_data = SimulationInput(
                inicial=self.entry_inicial.get(),
                mensal=self.entry_mensal.get(),
                taxa=self.entry_taxa.get(),
                periodo=self.entry_periodo.get(),
                tipo_periodo=self.combo_tipo_periodo.get(),
                meta=self.entry_meta.get(),
                estrategia=self.combo_estrategia.get(),
                cdi_base=self.entry_cdi_base.get(),
                use_effective_rate=True,
            )

            resultado = self.simulator_use_case.execute(input_data)

        except ValueError as exc:
            messagebox.showerror(t("error.simulation"), str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - exceção inesperada na UI, exibida ao usuário
            messagebox.showerror(
                t("error.simulation"),
                t("error.unexpected", error=exc)
            )
            return

        # Atualiza cards de métrica com os resultados
        pct_ganho = (resultado.total_interest / resultado.total_invested * 100) if resultado.total_invested > 0 else 0
        badge_lucro = t("profit.badge", percent=pct_ganho)
        badge_ir = t("ir.badge", aliquota=resultado.ir_aliquota)

        self.card_investido.update_value(formatar_moeda(resultado.total_invested))
        self.card_juros.update_value(formatar_moeda(resultado.total_interest), badge_text=badge_lucro)
        self.card_total.update_value(formatar_moeda(resultado.final_balance))
        self.card_liquido.update_value(formatar_moeda(resultado.net_balance), badge_text=badge_ir)
        self.card_meta.update_value(formatar_tempo(resultado.months_to_target))

        # Atualiza gráficos com os dados já calculados pelo serviço
        self.chart_controller.plot_timeline(
            resultado.total_invested - resultado.total_interest,
            resultado.timeline
        )
        self.chart_controller.plot_evolution_bars(
            resultado.total_invested - resultado.total_interest,
            resultado.timeline,
            target_amount=resultado.total_invested + resultado.total_interest,
            months_to_target=resultado.months_to_target,
            monthly_contribution=resultado.total_invested / resultado.total_months if resultado.total_months > 0 else 0,
            monthly_rate=resultado.taxa_mensal if hasattr(resultado, 'taxa_mensal') else 0.0,
        )
