"""
Camada de Apresentação - Componente Gráfico (Matplotlib Canvas)
================================================================

Este módulo implementa o controlador de gráficos integrado ao Tkinter/CustomTkinter
para visualização de simulações de investimento.

Principais características:
    - Reutilização de Figure e Canvas (instanciados uma única vez).
    - Atualização incremental via set_data() em vez de ax.clear() + redraw completo.
    - Suporte a tema claro/escuro.
    - Formatação de eixo Y em moeda brasileira simplificada (R$ 0, R$ 1k, R$ 1M).
    - Estilo minimalista (despined: remove spines desnecessárias).

Classes:
    InvestmentChart: Controlador de gráficos de linha (timeline) e barras.

Autor: CDB Simulator
Versão: 1.0.0
"""

from typing import List, Optional
import math
from decimal import Decimal, ROUND_HALF_UP
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import FuncFormatter
from src.domain.models import MonthlyRecord
from src.ui.gui.theme import PALETTES  # módulo independente para evitar ciclo de importação


class InvestmentChart:
    """
    Controlador de gráficos Matplotlib integrado ao Tkinter.

    Instancia Figure e Canvas uma única vez e reutiliza os eixos para
    atualizações incrementais, evitando flicker e vazamento de memória.

    Gráficos gerenciados:
        1. Gráfico de linha (timeline): Evolução do patrimônio ao longo dos meses.
        2. Gráfico de barras (evolução): Comparação investido vs montante até a meta.

    Atributos:
        master: Widget pai do gráfico principal.
        bar_master: Widget pai do gráfico de barras (opcional).
        palette (dict): Paleta de cores do tema atual.
        fig, ax: Figure e eixos do gráfico principal.
        canvas: Canvas TkAgg do gráfico principal.
        fig_bar, ax_bar: Figure e eixos do gráfico de barras.
        canvas_bar: Canvas do gráfico de barras.

    Referências para atualização incremental (evita recriar artistas):
        _line_total, _line_invested: Linhas do gráfico de timeline.
        _fill_area, _scatter_final, _vline_final: Elementos de destaque.
        _legend: Legenda do gráfico principal.
        _bars_invested, _bars_total, _line_meta: Elementos do gráfico de barras.
        _legend_bar: Legenda do gráfico de barras.

    Exemplo de uso:
        chart = InvestmentChart(frame_pai, bar_widget=frame_barras)
        chart.plot_timeline(1000, timeline)
        chart.plot_evolution_bars(1000, timeline, target_amount=100000, ...)
    """

    def __init__(self, master_widget, bar_widget=None):
        """
        Inicializa o controlador de gráficos.

        Parâmetros:
            master_widget: Widget pai onde o gráfico principal será colocado.
            bar_widget: Widget pai onde o gráfico de barras será colocado (opcional).
        """
        self.master = master_widget
        self.bar_master = bar_widget
        self.palette = PALETTES["Light"]

        # Cria Figure e Canvas principais (instanciados uma única vez)
        self.fig, self.ax = plt.subplots(figsize=(7, 3.8), dpi=100)
        self.fig.patch.set_facecolor(self.palette["chart_bg"])

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.master)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        # Referências para atualização incremental do gráfico principal
        self._line_total = None
        self._line_invested = None
        self._fill_area = None
        self._scatter_final = None
        self._vline_final = None
        self._legend = None

        # Gráfico de barras para evolução até a meta
        self.fig_bar = None
        self.ax_bar = None
        self.canvas_bar = None
        self._bars_invested = None
        self._bars_total = None
        self._line_meta = None
        self._legend_bar = None

        if self.bar_master is not None:
            self.fig_bar, self.ax_bar = plt.subplots(figsize=(7, 3.2), dpi=100)
            self.fig_bar.patch.set_facecolor(self.palette["chart_bg"])
            self.canvas_bar = FigureCanvasTkAgg(self.fig_bar, master=self.bar_master)
            self.canvas_bar.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

    def apply_theme(self, pal: dict):
        """
        Atualiza as cores dos gráficos conforme o tema (Claro/Escuro).

        Apenas reaplica cores de fundo, spines, grid, ticks e legendas.
        Não reexecuta a simulação nem redesenha os dados.

        Parâmetros:
            pal (dict): Dicionário de cores da paleta selecionada.
        """
        self.palette = pal
        self.fig.patch.set_facecolor(pal["chart_bg"])
        self.ax.set_facecolor(pal["chart_bg"])
        if self.fig_bar is not None:
            self.fig_bar.patch.set_facecolor(pal["chart_bg"])
        if self.ax_bar is not None:
            self.ax_bar.set_facecolor(pal["chart_bg"])

    def plot_timeline(self, initial_amount: float, timeline: List[MonthlyRecord]):
        """
        Desenha ou atualiza o gráfico de linha da evolução patrimonial.

        Mostra duas linhas:
            1. Montante Bruto (com juros) - linha verde sólida.
            2. Total Aportado (do bolso) - linha cinza tracejada.

        Também exibe:
            - Preenchimento de área sob a linha do montante.
            - Ponto de destaque no valor final.
            - Linha vertical pontilhada indicando o ponto final.
            - Eixo Y formatado em moeda simplificada (R$ 0, R$ 1k, R$ 1M).

        Na primeira execução, cria todos os artistas.
        Nas execuções subsequentes, usa set_data() para atualizar apenas os dados,
        evitando ax.clear() + redraw completo (muito mais rápido, sem flicker).

        Parâmetros:
            initial_amount (float): Valor inicial do investimento.
            timeline (List[MonthlyRecord]): Lista de registros mensais da simulação.
        """
        self.ax.set_facecolor(self.palette["chart_bg"])

        # Prepara dados para plotagem
        if not timeline:
            raw_months = [0]
            raw_invested = [initial_amount]
            raw_totals = [initial_amount]
        else:
            raw_months = [0] + [record.month for record in timeline]
            raw_invested = [initial_amount] + [record.invested_to_date for record in timeline]
            raw_totals = [initial_amount] + [record.total_balance for record in timeline]

        pal = self.palette
        mint_line = "#24C270"
        invested_line = pal["invested_line"]

        final_x = raw_months[-1]
        final_y = raw_totals[-1]

        # Primeira execução: cria os artistas
        if self._line_total is None:
            self._line_total, = self.ax.plot(
                raw_months, raw_totals,
                label="Montante Bruto (com juros)", color=mint_line,
                linewidth=3.0, zorder=3,
            )
            self._line_invested, = self.ax.plot(
                raw_months, raw_invested,
                label="Total Aportado (do bolso)", color=invested_line,
                linestyle="--", linewidth=1.8, zorder=2,
            )
            self._fill_area = self.ax.fill_between(
                raw_months, 0, raw_totals, color=mint_line, alpha=0.12, zorder=1,
            )
            self._scatter_final = self.ax.scatter(
                [final_x], [final_y], color=self.palette["chart_bg"],
                edgecolors=mint_line, s=80, linewidths=3.0, zorder=4,
            )
            self._vline_final = self.ax.vlines(
                x=final_x, ymin=0, ymax=final_y, colors=mint_line,
                linestyles=":", linewidth=1.5, alpha=0.6, zorder=2,
            )
            # Estilo dos eixos (feito apenas uma vez)
            self.ax.spines['top'].set_visible(False)
            self.ax.spines['right'].set_visible(False)
            self.ax.spines['left'].set_visible(False)
            self.ax.spines['bottom'].set_color(pal["chart_spine"])
            self.ax.spines['bottom'].set_linewidth(1.2)
            self.ax.grid(axis='y', linestyle='-', alpha=0.15, color=pal["chart_grid"])
            self.ax.grid(axis='x', visible=False)
            self.ax.tick_params(axis='x', colors=pal["chart_tick"], labelsize=9, length=0)
            self.ax.tick_params(axis='y', colors=pal["chart_tick"], labelsize=9, length=0)
            self.ax.set_ylim(bottom=0)

            # Formatter de moeda para o eixo Y
            def _formato_moeda(x, pos):
                if x >= 1_000_000:
                    return f"R$ {x*1e-6:.1f}M"
                elif x >= 1_000:
                    return f"R$ {x*1e-3:.0f}k"
                elif x == 0:
                    return "R$ 0"
                return f"R$ {x:.0f}"

            self.ax.yaxis.set_major_formatter(FuncFormatter(_formato_moeda))
        else:
            # Execuções subsequentes: atualiza apenas os dados (muito mais rápido)
            self._line_total.set_data(raw_months, raw_totals)
            self._line_invested.set_data(raw_months, raw_invested)
            self._fill_area.set_paths([])
            self._fill_area = self.ax.fill_between(
                raw_months, 0, raw_totals, color=mint_line, alpha=0.12, zorder=1,
            )
            self._scatter_final.set_offsets([[final_x, final_y]])
            self._vline_final.set_segments([[(final_x, 0), (final_x, final_y)]])

        # Ajusta limites dos eixos
        self.ax.set_xlim(0, max(raw_months) * 1.02 if raw_months else 1)
        self.ax.set_ylim(bottom=0, top=max(raw_totals) * 1.1 if raw_totals else 1)

        # Atualiza cores de elementos do eixo conforme tema (leve, sem recriar)
        self.ax.spines['bottom'].set_color(pal["chart_spine"])
        self.ax.grid(axis='y', color=pal["chart_grid"])
        self.ax.tick_params(axis='x', colors=pal["chart_tick"])
        self.ax.tick_params(axis='y', colors=pal["chart_tick"])

        # Atualiza ou cria legenda
        if self._legend is None:
            self._legend = self.ax.legend(
                loc="upper left", frameon=True,
                facecolor=pal["chart_legend_bg"],
                edgecolor=pal["chart_legend_edge"],
                fontsize=9,
            )
            for text in self._legend.get_texts():
                text.set_color(pal["chart_legend_text"])
        else:
            self._legend.get_frame().set_facecolor(pal["chart_legend_bg"])
            self._legend.get_frame().set_edgecolor(pal["chart_legend_edge"])
            for text in self._legend.get_texts():
                text.set_color(pal["chart_legend_text"])

        self.fig.tight_layout()
        self.canvas.draw_idle()

    def plot_evolution_bars(self, initial_amount: float, timeline: List[MonthlyRecord],
                            target_amount: Optional[float] = None,
                            months_to_target: Optional[int] = None,
                            monthly_contribution: float = 0.0,
                            monthly_rate: float = 0.0):
        """
        Desenha ou atualiza o gráfico de barras mostrando evolução até a meta.

        Exibe barras comparando:
            - Total Aportado (cinza)
            - Montante Total (verde)

        Opcionalmente exibe uma linha horizontal indicando a meta financeira.

        Se months_to_target for None ou 0, exibe mensagem "Meta não atingível".

        A projeção usa Decimal para evitar erros de ponto flutuante em períodos longos.

        Parâmetros:
            initial_amount (float): Valor inicial do investimento.
            timeline (List[MonthlyRecord]): Timeline da simulação principal.
            target_amount (Optional[float]): Valor da meta financeira.
            months_to_target (Optional[int]): Meses para atingir a meta.
            monthly_contribution (float): Aporte mensal.
            monthly_rate (float): Taxa de rendimento mensal.
        """
        if self.ax_bar is None or self.canvas_bar is None:
            return

        self.ax_bar.set_facecolor(self.palette["chart_bg"])

        # Caso: meta não informada ou inválida
        if target_amount is None or target_amount <= 0:
            self.fig_bar.tight_layout()
            self.canvas_bar.draw_idle()
            return

        # Caso: já atingiu com valor inicial
        if months_to_target == 0 or initial_amount >= target_amount:
            labels = ["Inicial"]
            invested_vals = [initial_amount]
            total_vals = [initial_amount]
        # Caso: meta não atingível
        elif months_to_target is None or months_to_target <= 0:
            self.ax_bar.text(0.5, 0.5, "Meta não atingível dentro do prazo projetado",
                            ha='center', va='center', transform=self.ax_bar.transAxes,
                            color=self.palette["text_muted"], fontsize=10)
            self.ax_bar.set_xticks([])
            self.ax_bar.set_yticks([])
            self.fig_bar.tight_layout()
            self.canvas_bar.draw_idle()
            return
        else:
            max_month_show = months_to_target

            # Projeta evolução usando Decimal para precisão monetária
            saldo_atual = Decimal(str(initial_amount))
            investido_atual = Decimal(str(initial_amount))
            monthly_rate_d = Decimal(str(monthly_rate))
            monthly_contrib_d = Decimal(str(monthly_contribution))

            projected_records = []
            for mes in range(1, max_month_show + 1):
                saldo_atual += monthly_contrib_d
                investido_atual += monthly_contrib_d
                if monthly_rate_d > 0:
                    rendimento = (saldo_atual * monthly_rate_d).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                    saldo_atual += rendimento
                else:
                    rendimento = Decimal("0.00")
                projected_records.append(MonthlyRecord(
                    month=mes,
                    invested_to_date=float(investido_atual),
                    interest_earned_month=float(rendimento),
                    total_balance=float(saldo_atual)
                ))

            # Agrupa por mês (até 24) ou por ano (mais de 24 meses)
            if max_month_show <= 24:
                labels = []
                invested_vals = []
                total_vals = []
                labels.append("Mês 0")
                invested_vals.append(initial_amount)
                total_vals.append(initial_amount)
                for r in projected_records:
                    labels.append(f"Mês {r.month}")
                    invested_vals.append(r.invested_to_date)
                    total_vals.append(r.total_balance)
            else:
                labels = []
                invested_vals = []
                total_vals = []
                labels.append("Ano 0")
                invested_vals.append(initial_amount)
                total_vals.append(initial_amount)
                years_to_show = math.ceil(max_month_show / 12)
                for year in range(1, years_to_show + 1):
                    month_target = min(year * 12, max_month_show)
                    record_at = None
                    for r in projected_records:
                        if r.month == month_target:
                            record_at = r
                            break
                    if record_at is None:
                        for r in reversed(projected_records):
                            if r.month <= month_target:
                                record_at = r
                                break
                    if record_at is not None:
                        labels.append(f"Ano {year}")
                        invested_vals.append(record_at.invested_to_date)
                        total_vals.append(record_at.total_balance)

        x = range(len(labels))
        width = 0.35
        pal = self.palette

        # Primeira execução: cria as barras
        if self._bars_invested is None:
            self._bars_invested = self.ax_bar.bar(
                [i - width/2 for i in x], invested_vals, width,
                label="Total Aportado", color=pal["invested_line"], alpha=0.85,
            )
            self._bars_total = self.ax_bar.bar(
                [i + width/2 for i in x], total_vals, width,
                label="Montante Total", color="#24C270", alpha=0.9,
            )
        else:
            # Execuções subsequentes: atualiza apenas as alturas
            for rect, val in zip(self._bars_invested, invested_vals):
                rect.set_height(val)
            for rect, val in zip(self._bars_total, total_vals):
                rect.set_height(val)

        # Linha da meta
        if target_amount is not None and target_amount > 0:
            if self._line_meta is None:
                self._line_meta = self.ax_bar.axhline(
                    y=target_amount, color=pal["meta_line"], linestyle="--",
                    linewidth=2, alpha=0.8,
                )
            else:
                self._line_meta.set_ydata([target_amount, target_amount])

            self.ax_bar.legend(
                loc="upper left", frameon=True,
                facecolor=pal["chart_legend_bg"],
                edgecolor=pal["chart_legend_edge"],
                fontsize=8,
            )

        # Estilo dos eixos do gráfico de barras
        self.ax_bar.spines['top'].set_visible(False)
        self.ax_bar.spines['right'].set_visible(False)
        self.ax_bar.spines['left'].set_color(pal["chart_spine"])
        self.ax_bar.spines['bottom'].set_color(pal["chart_spine"])
        self.ax_bar.grid(axis='y', linestyle='-', alpha=0.15, color=pal["chart_grid"])
        self.ax_bar.grid(axis='x', visible=False)
        self.ax_bar.tick_params(axis='x', colors=pal["chart_tick"], labelsize=8, rotation=45)
        self.ax_bar.tick_params(axis='y', colors=pal["chart_tick"], labelsize=8)

        def _formato_moeda(x, pos):
            if x >= 1_000_000:
                return f"R$ {x*1e-6:.1f}M"
            elif x >= 1_000:
                return f"R$ {x*1e-3:.0f}k"
            elif x == 0:
                return "R$ 0"
            return f"R$ {x:.0f}"

        self.ax_bar.yaxis.set_major_formatter(FuncFormatter(_formato_moeda))
        self.ax_bar.set_ylim(bottom=0)
        self.ax_bar.set_xticks(x)
        self.ax_bar.set_xticklabels(labels, ha='right')

        # Legenda quando não há meta (apenas barras)
        if target_amount is None or target_amount <= 0:
            if self._legend_bar is None:
                self._legend_bar = self.ax_bar.legend(
                    loc="upper left", frameon=True,
                    facecolor=pal["chart_legend_bg"],
                    edgecolor=pal["chart_legend_edge"],
                    fontsize=8,
                )
                for text in self._legend_bar.get_texts():
                    text.set_color(pal["chart_legend_text"])
            else:
                self._legend_bar.get_frame().set_facecolor(pal["chart_legend_bg"])
                self._legend_bar.get_frame().set_edgecolor(pal["chart_legend_edge"])
                for text in self._legend_bar.get_texts():
                    text.set_color(pal["chart_legend_text"])

        self.ax_bar.set_title("Evolução do Capital até a Meta", color=pal["text"], fontsize=11, pad=10)
        self.fig_bar.tight_layout()
        self.canvas_bar.draw_idle()

    def dispose(self):
        """
        Libera recursos Matplotlib (canvases e figures) ao encerrar a janela.

        Deve ser chamado antes de destruir a janela principal para evitar
        processos TkAgg residentes após o encerramento.
        """
        for canvas in (self.canvas, self.canvas_bar):
            if canvas is not None:
                try:
                    canvas.get_tk_widget().destroy()
                except Exception:
                    pass
        for figure in (self.fig, self.fig_bar):
            if figure is not None:
                plt.close(figure)