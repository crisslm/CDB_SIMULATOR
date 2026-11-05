"""
Camada de Apresentação - Janela Principal da Aplicação Gráfica
================================================================

Este módulo contém a janela principal (ModernAppGUI) do CDB Simulator,
construída com CustomTkinter. É responsável por:

    1. Exibir a interface de simulação de CDB (juros compostos).
    2. Exibir a interface de Controle Financeiro (receitas/despesas).
    3. Coordenar a navegação entre as duas seções.
    4. Validar entradas do usuário e disparar simulações.
    5. Gerenciar layout responsivo (mobile/desktop).
    6. Gerenciar tema claro/escuro com persistência.

Arquitetura:
    - Herda de ctk.CTk (janela principal do CustomTkinter).
    - Usa injeção de dependência para serviços (simulador e financeiro).
    - Comunica com as camadas de serviço e domínio para cálculos.

Princípio SOLID: Dependency Inversion Principle (DIP)
- Depende de abstrações (InvestmentSimulatorService, FinancialService),
  não de implementações concretas.

Autor: CDB Simulator
Versão: 1.0.0
"""

import json
from pathlib import Path
from typing import Optional

import customtkinter as ctk
from tkinter import messagebox
from src.services.simulator_service import InvestmentSimulatorService, MAX_SIMULATION_MONTHS
from src.services.financial_service import FinancialService, parse_amount_to_cents
from src.domain.models import SimulationParams
from src.domain.strategies import CompoundInterestStrategy, CDIStrategy
from src.ui.gui.chart import InvestmentChart
from src.ui.gui.components import (
    MetricCard,
    PillButton,
    PALETTES,
    THEME_MODES,
    formatar_moeda,
    formatar_tempo,
)
from src.ui.gui.financial.dashboard import FinancialDashboard


class ModernAppGUI(ctk.CTk):
    """
    Janela Principal do CDB Simulator com design responsivo (Mobile-Friendly e Desktop).

    Esta classe é o ponto de entrada da interface gráfica. Ela orquestra:
        - A barra de navegação (Simulador CDB / Controle Financeiro).
        - A barra lateral com formulário de entrada (simulador).
        - A área principal com cards de métricas e gráficos.
        - O dashboard financeiro (seção separada).
        - O gerenciamento de tema claro/escuro.

    Atributos de classe:
        BREAKPOINT_MOBILE (int): Largura em pixels abaixo da qual o layout
                                 muda para mobile (coluna única). Padrão: 860.
        PALETTES (dict): Paletas de cores para temas Light e Dark.
        THEME_FILE (Path): Caminho do arquivo JSON que persiste a preferência
                           de tema do usuário.

    Atributos de instância:
        service (InvestmentSimulatorService): Serviço de simulação de CDB.
        financial_service (FinancialService): Serviço de controle financeiro.
        active_section (str): Seção ativa ("simulator" ou "financial").
        is_mobile_layout (bool|None): Indica se está em layout mobile.
        theme_mode (str): "Light" ou "Dark".

    Exemplo de uso:
        app = ModernAppGUI()
        app.mainloop()
    """

    BREAKPOINT_MOBILE = 860

    # Paletas de tema (Claro / Escuro) importadas de components/theme
    PALETTES = PALETTES
    THEME_FILE = Path.home() / ".cdb_simulator_theme.json"

    def __init__(self, simulator_service: InvestmentSimulatorService = None, financial_service: FinancialService = None):
        """
        Inicializa a janela principal e constrói toda a interface.

        Parâmetros:
            simulator_service: Serviço de simulação (ou None para criar novo).
            financial_service: Serviço financeiro (ou None para criar novo).

        Fluxo de inicialização:
            1. Configura serviços (injeção de dependência).
            2. Carrega tema salvo ou usa "Light" como padrão.
            3. Configura janela (título, tamanho, mínimo).
            4. Constrói navegação, barra lateral e área principal.
            5. Cria o dashboard financeiro.
            6. Configura evento de redimensionamento.
            7. Aplica layout inicial e tema.
        """
        super().__init__()

        # Injeção de dependência - permite substituir serviços em testes
        self.service = simulator_service or InvestmentSimulatorService()
        self.financial_service = financial_service or FinancialService()
        self.active_section = "simulator"
        self.is_mobile_layout = None
        self._last_width = 0
        self._last_height = 0
        self._resize_after_id: Optional[str] = None

        # Carrega preferência de tema salvo (padrão: Claro)
        self.theme_mode = self._load_theme()
        ctk.set_appearance_mode(self.theme_mode)
        self.configure(fg_color=self.PALETTES[self.theme_mode]["bg_root"])

        # Configurações básicas da janela
        self.title("CDB Simulator • Gestão & Rendimento")
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
            self.financial_service,
            self.PALETTES[self.theme_mode]
        )

        self._is_closing = False
        # Garante limpeza de recursos ao fechar a janela (evita processos órfãos)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Monitora redimensionamento para layout responsivo
        self.bind("<Configure>", self._on_window_resize)

        # Layout inicial e tema
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
            text="Simulador CDB",
            command=lambda: self._show_section("simulator"),
            variant="secondary",
            width=145,
        )
        self.nav_financial = PillButton(
            self.frame_navigation,
            text="Controle Financeiro",
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

        # Cabeçalho com título e botão de tema
        frame_header = ctk.CTkFrame(self.frame_sidebar, fg_color="transparent")
        frame_header.pack(fill="x", padx=16, pady=(16, 12))

        self.lbl_header = ctk.CTkLabel(
            frame_header,
            text="Configuração do Aporte",
            font=("Segoe UI", 16, "bold"),
            text_color=pal["text"],
            anchor="w"
        )
        self.lbl_header.pack(side="left")

        texto_tema = "☀️ Claro" if self.theme_mode == "Dark" else "🌙 Escuro"
        self.btn_tema = PillButton(
            frame_header,
            text=texto_tema,
            variant="secondary",
            command=self._toggle_theme,
            width=120,
        )
        self.btn_tema.pack(side="right", padx=(8, 0))
        self.btn_tema.apply_theme(pal)

        # 1. Tipo de Rendimento / Estratégia
        lbl_estrategia = ctk.CTkLabel(
            self.frame_sidebar,
            text="TIPO DE INVESTIMENTO",
            font=("Segoe UI", 11, "bold"),
            text_color="#8E8E93",
            anchor="w"
        )
        lbl_estrategia.pack(fill="x", padx=16, pady=(4, 4))

        self.combo_estrategia = ctk.CTkComboBox(
            self.frame_sidebar,
            values=["Taxa Prefixada (% a.a. / a.m.)", "Pós-fixado (% do CDI)"],
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
        self.combo_estrategia.set("Taxa Prefixada (% a.a. / a.m.)")
        self.combo_estrategia.pack(fill="x", padx=16, pady=(0, 12))

        # 2. Valor Inicial
        lbl_inicial = ctk.CTkLabel(
            self.frame_sidebar,
            text="VALOR INICIAL (R$)",
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
            text="APORTE MENSAL (R$)",
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
            text="TAXA DE RENDIMENTO (%)",
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
            text="CDI ANUAL BASE (% a.a.)",
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
            text="PRAZO DE INVESTIMENTO",
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
            values=["Anos", "Meses"],
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
        self.combo_tipo_periodo.set("Anos")
        self.combo_tipo_periodo.pack(side="right")

        # 6. Meta Desejada
        lbl_meta = ctk.CTkLabel(
            self.frame_sidebar,
            text="OBJETIVO / META (R$)",
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
            text="Simular Rendimento",
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
            text="☀️ Claro" if modo == "Dark" else "🌙 Escuro"
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
        if "CDI" in choice:
            self.lbl_taxa.configure(text="% DO CDI (ex: 110%):")
            self.entry_taxa.delete(0, "end")
            self.entry_taxa.insert(0, "110")
            self.combo_periodo_taxa.configure(state="disabled")
            self.frame_cdi_base.pack(fill="x", padx=16, pady=(0, 10), after=self.frame_taxa)
        else:
            self.lbl_taxa.configure(text="TAXA DE RENDIMENTO (%):")
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
            text="Visão Geral do Portfólio • Projeção & Rendimento",
            font=("Segoe UI", 18, "bold"),
            text_color="#1C1C1E",
            anchor="w"
        )
        self.lbl_section.pack(fill="x", pady=(0, 10))

        # Container dos Cards de Métricas
        self.frame_cards = ctk.CTkFrame(self.frame_main, fg_color="transparent")
        self.frame_cards.pack(fill="x", pady=(0, 12))

        # Cards estilizados
        self.card_investido = MetricCard(self.frame_cards, "Total Aportado", "R$ 0,00")
        self.card_juros = MetricCard(self.frame_cards, "Lucro Bruto", "R$ 0,00", badge_text="+0.0%")
        self.card_total = MetricCard(self.frame_cards, "Montante Bruto", "R$ 0,00")
        self.card_liquido = MetricCard(
            self.frame_cards,
            "Líquido (Pós-IR)",
            "R$ 0,00",
            badge_text="IR 15%",
            is_highlight=True
        )
        self.card_meta = MetricCard(self.frame_cards, "Tempo p/ Meta", "-")

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
    # Utilitários de Parsing
    # -------------------------------------------------------------------------

    def _parse_percent(self, value: str) -> float:
        """
        Converte uma string de percentual para float.

        Remove "R$", espaços, "%" e troca vírgula por ponto.
        Ex: "12,5" -> 12.5, "R$ 10%" -> 10.0

        Parâmetros:
            value (str): String do percentual.

        Retorna:
            float: Valor numérico do percentual.
        """
        raw = value.strip().replace("R$", "").replace(" ", "").replace("%", "").replace(",", ".")
        return float(raw)

    # -------------------------------------------------------------------------
    # Simulação - Ponto Principal de Ação
    # -------------------------------------------------------------------------

    def on_simulate_click(self):
        """
        Executa a lógica completa de simulação quando o usuário clica
        no botão "Simular Rendimento".

        Fluxo:
            1. Lê e valida todos os campos de entrada.
            2. Aplica limites de segurança (valor máximo 1 trilhão).
            3. Valida taxas (diferenciadas por estratégia: prefixado 0-100%, CDI 0-500%).
            4. Converte prazo para meses (máximo 1200 = anti-DoS).
            5. Cria estratégia de rendimento (CompoundInterestStrategy ou CDIStrategy).
            6. Cria SimulationParams e chama service.simulate().
            7. Atualiza cards e gráficos com o resultado.

        Todas as exceções são capturadas e exibidas em messagebox amigáveis.
        """
        try:
            # Leitura e conversão dos valores monetários (suporta formato brasileiro)
            inicial = parse_amount_to_cents(self.entry_inicial.get()) / 100.0
            mensal = parse_amount_to_cents(self.entry_mensal.get()) / 100.0
            taxa_raw = self._parse_percent(self.entry_taxa.get())
            periodo_raw = self._parse_percent(self.entry_periodo.get())
            meta_str = self.entry_meta.get().strip().replace(",", ".")
            meta_val = parse_amount_to_cents(meta_str) / 100.0 if meta_str else 1_000_000.0

            # Limite monetário de segurança (1 trilhão de reais)
            LIMITE_MONETARIO = 1_000_000_000_000.0
            for nome, valor in (("Valor Inicial", inicial), ("Aporte Mensal", mensal), ("Meta", meta_val)):
                if valor > LIMITE_MONETARIO:
                    messagebox.showerror(
                        "Erro de Valor",
                        f"{nome} não pode exceder R$ {LIMITE_MONETARIO:,.2f}."
                    )
                    return

            if inicial < 0 or mensal < 0:
                messagebox.showerror("Erro de Valor", "Os valores de aportes não podem ser negativos.")
                return

            # Validação de taxa diferenciada por estratégia
            if "CDI" in self.combo_estrategia.get():
                if taxa_raw <= 0 or taxa_raw > 500:
                    messagebox.showerror(
                        "Erro de Valor",
                        "O percentual do CDI deve estar entre 0% e 500%."
                    )
                    return
            else:
                if taxa_raw < 0 or taxa_raw > 100:
                    messagebox.showerror("Erro de Valor", "A taxa de rendimento deve estar entre 0% e 100%.")
                    return

            if periodo_raw <= 0:
                messagebox.showerror("Erro de Prazo", "O prazo de investimento deve ser maior que zero.")
                return

            if meta_val <= 0:
                messagebox.showerror("Erro de Meta", "O valor da meta financeira deve ser maior que zero.")
                return

        except ValueError:
            messagebox.showerror("Erro de Formato", "Por favor, preencha todos os campos apenas com números válidos.")
            return
        except Exception as exc:
            messagebox.showerror(
                "Erro Inesperado",
                f"Ocorreu um erro inesperado ao ler os dados: {exc}"
            )
            return

        try:
            # Conversão de prazo para meses
            if self.combo_tipo_periodo.get() == "Anos":
                meses = max(1, int(round(periodo_raw * 12)))
            else:
                meses = max(1, int(round(periodo_raw)))

            # Limite de segurança anti-DoS (máximo 1200 meses = 100 anos)
            if meses > MAX_SIMULATION_MONTHS:
                meses = MAX_SIMULATION_MONTHS
                messagebox.showwarning(
                    "Aviso de Prazo",
                    f"O prazo máximo para projeção foi ajustado para 100 anos ({MAX_SIMULATION_MONTHS} meses)."
                )

            # Cria estratégia de rendimento conforme seleção do usuário
            if "CDI" in self.combo_estrategia.get():
                try:
                    cdi_base = self._parse_percent(self.entry_cdi_base.get())
                    if cdi_base <= 0 or cdi_base > 100:
                        raise ValueError("A taxa CDI base deve estar entre 0 e 100.")
                except ValueError:
                    messagebox.showerror(
                        "Erro de Valor",
                        "Digite um valor válido para a Taxa CDI Base (ex: 10.75)."
                    )
                    return
                strategy = CDIStrategy(cdi_percentage=taxa_raw, cdi_annual_rate=cdi_base, use_effective_rate=True)
            else:
                is_annual = self.combo_periodo_taxa.get() == "% ao ano"
                strategy = CompoundInterestStrategy(rate_percent=taxa_raw, is_annual=is_annual, use_effective_rate=True)

            params = SimulationParams(
                initial_amount=inicial,
                monthly_contribution=mensal,
                total_months=meses,
                target_amount=meta_val
            )

            resultado = self.service.simulate(params, strategy)
        except ValueError as exc:
            messagebox.showerror("Erro de Simulação", str(exc))
            return
        except Exception as exc:
            messagebox.showerror(
                "Erro Inesperado",
                f"Ocorreu um erro inesperado durante a simulação: {exc}"
            )
            return

        # Atualiza cards de métrica com os resultados
        pct_ganho = (resultado.total_interest / resultado.total_invested * 100) if resultado.total_invested > 0 else 0
        badge_lucro = f"+{pct_ganho:.1f}%"
        badge_ir = f"IR {resultado.ir_aliquota * 100:.1f}%"

        self.card_investido.update_value(formatar_moeda(resultado.total_invested))
        self.card_juros.update_value(formatar_moeda(resultado.total_interest), badge_text=badge_lucro)
        self.card_total.update_value(formatar_moeda(resultado.final_balance))
        self.card_liquido.update_value(formatar_moeda(resultado.net_balance), badge_text=badge_ir)
        self.card_meta.update_value(formatar_tempo(resultado.months_to_target))

        # Atualiza gráficos com a paleta de cores atual
        monthly_rate_bars = strategy.get_monthly_rate()
        self.chart_controller.plot_timeline(params.initial_amount, resultado.timeline)
        self.chart_controller.plot_evolution_bars(
            params.initial_amount,
            resultado.timeline,
            target_amount=params.target_amount,
            months_to_target=resultado.months_to_target,
            monthly_contribution=mensal,
            monthly_rate=monthly_rate_bars
        )