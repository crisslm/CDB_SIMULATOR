"""
Camada de Apresentação - Janela Principal da Aplicação Gráfica
Design Mobile-Friendly & Desktop Responsivo:
- Adaptação dinâmica ao redimensionar a janela (< 850px ativa modo coluna única / vertical estilo mobile)
- >= 850px ativa layout em 2 colunas estilo desktop
- Métricas em grid fluido (2 colunas em telas estreitas, 5 colunas em telas largas)
- Paleta Clean Warm Light (#F9F9FB, superfícies #FFFFFF)
"""

import json
from pathlib import Path

import customtkinter as ctk
from tkinter import messagebox
from src.services.simulator_service import InvestmentSimulatorService, MAX_SIMULATION_MONTHS
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


class ModernAppGUI(ctk.CTk):
    """
    Janela Principal do CDB Simulator com design responsivo (Mobile-Friendly e Desktop).
    """

    BREAKPOINT_MOBILE = 860

    # Paletas de tema (Claro / Escuro) e arquivo de persistência da preferência
    PALETTES = PALETTES
    THEME_FILE = Path.home() / ".cdb_simulator_theme.json"

    def __init__(self, simulator_service: InvestmentSimulatorService = None):
        super().__init__()

        self.service = simulator_service or InvestmentSimulatorService()
        self.is_mobile_layout = None
        self._last_width = 0
        self._last_height = 0

        # Visual e Cores - o tema é carregado da preferência salva (padrão: Claro)
        self.theme_mode = self._load_theme()
        ctk.set_appearance_mode(self.theme_mode)
        self.configure(fg_color=self.PALETTES[self.theme_mode]["bg_root"])

        # Configurações de Janela
        self.title("CDB Simulator • Gestão & Rendimento")
        self.geometry("1160x780")
        self.minsize(360, 520)  # Suporte a janelas estreitas estilo mobile

        # Container principal com scroll para comportar telas pequenas verticalmente
        self.root_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="#F9F9FB",
            corner_radius=0
        )
        self.root_scroll.pack(fill="both", expand=True)

        self._build_sidebar()
        self._build_main_area()

        # Monitoramento contínuo de redimensionamento da janela
        self.bind("<Configure>", self._on_window_resize)

        # Dispara layout inicial e aplica o tema salvo (renderiza a simulação com as cores do tema)
        self._apply_responsive_layout(1160)
        self._apply_theme(self.theme_mode)

    def _build_sidebar(self):
        """Constrói o formulário de configuração com acabamento limpo e moderno."""
        self.frame_sidebar = ctk.CTkFrame(
            self.root_scroll,
            fg_color="#FFFFFF",
            corner_radius=20,
            border_width=1,
            border_color="#EBEBEB"
        )

        pal = self.PALETTES[self.theme_mode]

        # Cabeçalho da sidebar com título e botão de alternância de tema (Claro/Escuro)
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

        # Campo Extra para Taxa Base do CDI (exibido apenas no modo CDI)
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

        # Botão Principal
        self.btn_simular = PillButton(
            self.frame_sidebar,
            text="Simular Rendimento",
            variant="primary",
            command=self.on_simulate_click
        )
        self.btn_simular.pack(fill="x", padx=16, pady=(4, 16))
        self.btn_simular.apply_theme(pal)

        # Referências de widgets cujas cores mudam ao alternar o tema
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

    def _toggle_theme(self):
        """Alterna entre modo claro e escuro e persiste a preferência."""
        novo_modo = "Dark" if self.theme_mode == "Light" else "Light"
        self._apply_theme(novo_modo)

    def _apply_theme(self, modo: str):
        """Aplica a paleta de cores (Claro/Escuro) em toda a interface."""
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

        # Gráficos (re-renderiza com as cores do novo tema)
        self.chart_controller.apply_theme(pal)
        self.on_simulate_click()

        # Persiste a escolha do usuário
        self._save_theme()

    def _load_theme(self) -> str:
        """Carrega o tema salvo em preferência (padrão: Claro)."""
        try:
            dados = json.loads(self.THEME_FILE.read_text(encoding="utf-8"))
            modo = dados.get("mode", "Light")
            return modo if modo in THEME_MODES else "Light"
        except Exception:
            return "Light"

    def _save_theme(self):
        """Salva a preferência de tema em disco."""
        try:
            self.THEME_FILE.write_text(
                json.dumps({"mode": self.theme_mode}), encoding="utf-8"
            )
        except Exception:
            pass

    def _on_strategy_change(self, choice: str):
        """Alterna a interface conforme o tipo de taxa selecionada."""
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

    def _build_main_area(self):
        """Constrói o painel de resultados com cards e visualizador gráfico."""
        self.frame_main = ctk.CTkFrame(self.root_scroll, fg_color="transparent")

        # Cabeçalho da seção
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
        self.card_liquido = MetricCard(self.frame_cards, "Líquido (Pós-IR)", "R$ 0,00", badge_text="IR 15%", is_highlight=True)
        self.card_meta = MetricCard(self.frame_cards, "Tempo p/ Meta", "-")

        self.cards_list = [
            self.card_investido,
            self.card_juros,
            self.card_total,
            self.card_liquido,
            self.card_meta
        ]

        # Container dos Gráficos
        self.frame_charts_container = ctk.CTkFrame(self.frame_main, fg_color="transparent")
        self.frame_charts_container.pack(fill="both", expand=True, pady=(0, 10))
        self.frame_charts_container.grid_rowconfigure((0, 1), weight=1)
        self.frame_charts_container.grid_columnconfigure(0, weight=1)

        # Container do Gráfico de Linha
        self.frame_chart_card = ctk.CTkFrame(
            self.frame_charts_container,
            fg_color="#FFFFFF",
            corner_radius=20,
            border_width=1,
            border_color="#EBEBEB"
        )
        self.frame_chart_card.grid(row=0, column=0, sticky="nsew", pady=(0, 8))

        # Container do Gráfico de Barras
        self.frame_bar_card = ctk.CTkFrame(
            self.frame_charts_container,
            fg_color="#FFFFFF",
            corner_radius=20,
            border_width=1,
            border_color="#EBEBEB"
        )
        self.frame_bar_card.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        self.chart_controller = InvestmentChart(self.frame_chart_card, bar_widget=self.frame_bar_card)

    def _on_window_resize(self, event):
        """Disparado quando a janela é redimensionada para recalcular layout responsivo."""
        # Filtra apenas eventos da janela principal (evita disparos de sub-widgets)
        if event.widget == self:
            if abs(event.width - self._last_width) > 15:
                self._last_width = event.width
                self._last_height = event.height
                self._apply_responsive_layout(event.width)

    def _apply_responsive_layout(self, window_width: int):
        """
        Alterna dinamicamente entre layout Mobile (coluna vertical fluida)
        e layout Desktop (painel lateral + área principal expandida).
        """
        is_mobile = window_width < self.BREAKPOINT_MOBILE

        if is_mobile != self.is_mobile_layout:
            self.is_mobile_layout = is_mobile

            # Reseta o grid do container principal
            self.root_scroll.grid_columnconfigure(0, weight=1)
            self.root_scroll.grid_columnconfigure(1, weight=1 if not is_mobile else 0)

            # Remove da tela para reposicionar
            self.frame_sidebar.grid_forget()
            self.frame_main.grid_forget()

            if is_mobile:
                # Layout Mobile: Empilhado verticalmente
                self.frame_sidebar.grid(row=0, column=0, padx=12, pady=(12, 10), sticky="ew")
                self.frame_main.grid(row=1, column=0, padx=12, pady=(0, 16), sticky="nsew")

                # Reconfigura os Cards para 2 colunas no celular
                self._configure_cards_grid(columns=2)
            else:
                # Layout Desktop: 2 Colunas lado a lado
                self.root_scroll.grid_columnconfigure(0, weight=0, minsize=340)
                self.root_scroll.grid_columnconfigure(1, weight=1)

                self.frame_sidebar.grid(row=0, column=0, padx=(18, 10), pady=18, sticky="nsew")
                self.frame_main.grid(row=0, column=1, padx=(10, 18), pady=18, sticky="nsew")

                # Reconfigura os Cards para linha única (5 colunas) no Desktop
                self._configure_cards_grid(columns=5)

    def _configure_cards_grid(self, columns: int):
        """Posiciona os cards de métricas de forma fluida conforme o número de colunas."""
        # Limpa configurações anteriores do grid
        for c in range(5):
            self.frame_cards.grid_columnconfigure(c, weight=0)

        for card in self.cards_list:
            card.grid_forget()

        for c in range(columns):
            self.frame_cards.grid_columnconfigure(c, weight=1)

        for index, card in enumerate(self.cards_list):
            row = index // columns
            col = index % columns
            
            # Se for mobile (2 colunas) e for o último card (5º), expande ocupando as 2 colunas
            if columns == 2 and index == 4:
                card.grid(row=row, column=0, columnspan=2, padx=4, pady=3, sticky="nsew")
            else:
                card.grid(row=row, column=col, padx=4, pady=3, sticky="nsew")

    def on_simulate_click(self):
        """Executa a lógica de simulação com validação completa e atualiza a interface."""
        try:
            inicial = float(self.entry_inicial.get().strip().replace(",", "."))
            mensal = float(self.entry_mensal.get().strip().replace(",", "."))
            taxa_raw = float(self.entry_taxa.get().strip().replace(",", "."))
            periodo_raw = float(self.entry_periodo.get().strip().replace(",", "."))
            meta_str = self.entry_meta.get().strip().replace(",", ".")
            meta_val = float(meta_str) if meta_str else 1_000_000.0

            if inicial < 0 or mensal < 0 or taxa_raw < 0:
                messagebox.showerror("Erro de Valor", "Os valores de aportes e taxa não podem ser negativos.")
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

        # Conversão de prazo em meses com proteção contra período fracionário menor que 1 mês
        if self.combo_tipo_periodo.get() == "Anos":
            meses = max(1, int(round(periodo_raw * 12)))
        else:
            meses = max(1, int(round(periodo_raw)))

        # Proteção contra DoS / Estouro de memória (máximo 1200 meses = 100 anos)
        if meses > MAX_SIMULATION_MONTHS:
            meses = MAX_SIMULATION_MONTHS
            messagebox.showwarning("Aviso de Prazo", f"O prazo máximo para projeção foi ajustado para 100 anos ({MAX_SIMULATION_MONTHS} meses).")

        # Estratégia de rendimento
        if "CDI" in self.combo_estrategia.get():
            try:
                cdi_base = float(self.entry_cdi_base.get().strip().replace(",", "."))
            except ValueError:
                cdi_base = 10.75
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

        # Percentual de ganho gerado por juros
        pct_ganho = (resultado.total_interest / resultado.total_invested * 100) if resultado.total_invested > 0 else 0
        badge_lucro = f"+{pct_ganho:.1f}%"
        badge_ir = f"IR {resultado.ir_aliquota * 100:.1f}%"

        # Atualização dos Cards
        self.card_investido.update_value(formatar_moeda(resultado.total_invested))
        self.card_juros.update_value(formatar_moeda(resultado.total_interest), badge_text=badge_lucro)
        self.card_total.update_value(formatar_moeda(resultado.final_balance))
        self.card_liquido.update_value(formatar_moeda(resultado.net_balance), badge_text=badge_ir)
        self.card_meta.update_value(formatar_tempo(resultado.months_to_target))

        # Atualização dos Gráficos com paleta limpa
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
