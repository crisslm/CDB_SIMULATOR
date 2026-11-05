"""
Camada de Apresentação - Componente Gráfico (Matplotlib Canvas)
Estilizado fielmente à referência visual de Fintech / Neumorphic Clean:
- Curva verde menta (#24C270)
- Área sombreada com preenchimento em gradiente suave verde (#24C270 com alpha)
- Linha pontilhada suave para o total aportado (#8E8E93)
- Fundo branco limpo (#FFFFFF)
- Eixos limpos, sem moldura pesada (despined)
- Destaque no ponto final do valor atingido (marker dot com anel)
- Reutilização inteligente da Figure e do Canvas para máxima eficiência e fluidez.
"""

from typing import List, Optional
import math
from decimal import Decimal, ROUND_HALF_UP
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import FuncFormatter
from src.domain.models import MonthlyRecord
from src.ui.gui.theme import PALETTES  # importado de módulo independente para evitar ciclo


class InvestmentChart:
    """
    Controlador do gráfico integrado ao Tkinter/CustomTkinter com alto desempenho.
    Instancia Figure e Canvas uma única vez e reutiliza os eixos.
    """

    def __init__(self, master_widget, bar_widget=None):

        self.master = master_widget
        self.bar_master = bar_widget
        self.palette = PALETTES["Light"]
        self.fig, self.ax = plt.subplots(figsize=(7, 3.8), dpi=100)
        self.fig.patch.set_facecolor(self.palette["chart_bg"])
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.master)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        # Referências aos artistas para atualização incremental (sem clear/redraw completo)
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
        """Atualiza as cores dos gráficos para o tema (Claro/Escuro)."""
        self.palette = pal
        self.fig.patch.set_facecolor(pal["chart_bg"])
        self.ax.set_facecolor(pal["chart_bg"])
        if self.fig_bar is not None:
            self.fig_bar.patch.set_facecolor(pal["chart_bg"])
        if self.ax_bar is not None:
            self.ax_bar.set_facecolor(pal["chart_bg"])

    def plot_timeline(self, initial_amount: float, timeline: List[MonthlyRecord]):
        """
        Atualiza o gráfico reutilizando artistas existentes (set_data) sempre que possível,
        evitando ax.clear() e recriação completa de linhas, legenda e eixos.
        """
        self.ax.set_facecolor(self.palette["chart_bg"])

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

        # Cria artistas na primeira execução; depois apenas atualiza dados
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
            # Atualiza dados dos artistas existentes (muito mais rápido que clear/redraw)
            self._line_total.set_data(raw_months, raw_totals)
            self._line_invested.set_data(raw_months, raw_invested)
            self._fill_area.set_paths([])  # limpa polígonos antigos
            self._fill_area = self.ax.fill_between(
                raw_months, 0, raw_totals, color=mint_line, alpha=0.12, zorder=1,
            )
            self._scatter_final.set_offsets([[final_x, final_y]])
            self._vline_final.set_segments([[(final_x, 0), (final_x, final_y)]])

        # Ajusta limites dos eixos
        self.ax.set_xlim(0, max(raw_months) * 1.02 if raw_months else 1)
        self.ax.set_ylim(bottom=0, top=max(raw_totals) * 1.1 if raw_totals else 1)

        # Atualiza cores dos elementos de eixo conforme tema (leve, sem recriar)
        self.ax.spines['bottom'].set_color(pal["chart_spine"])
        self.ax.grid(axis='y', color=pal["chart_grid"])
        self.ax.tick_params(axis='x', colors=pal["chart_tick"])
        self.ax.tick_params(axis='y', colors=pal["chart_tick"])

        # Atualiza legenda se existir
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
            # Atualiza apenas cores da legenda
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
        Gráfico de barras mostrando a evolução do capital (investido vs montante)
        conforme meses/anos, até o tempo necessário para atingir a meta estabelecida.
        """
        if self.ax_bar is None or self.canvas_bar is None:
            return

        self.ax_bar.clear()
        self.ax_bar.set_facecolor(self.palette["chart_bg"])

        if target_amount is None or target_amount <= 0:
            self.fig_bar.tight_layout()
            self.canvas_bar.draw_idle()
            return

        # Se já atingiu com valor inicial
        if months_to_target == 0 or initial_amount >= target_amount:
            labels = ["Inicial"]
            invested_vals = [initial_amount]
            total_vals = [initial_amount]
        elif months_to_target is None or months_to_target <= 0:
            # Meta não atingível no prazo máximo - não exibe gráfico de barras
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
            # Projetar evolução até a meta usando os mesmos parâmetros (Decimal para evitar erro de float)
            saldo_atual = Decimal(str(initial_amount))
            investido_atual = Decimal(str(initial_amount))
            monthly_rate_d = Decimal(str(monthly_rate))
            monthly_contrib_d = Decimal(str(monthly_contribution))
            # Construir timeline projetado até max_month_show
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

            # Agrupa por ano para melhor visualização quando período longo
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

        # Cria barras na primeira execução; depois apenas atualiza alturas
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
            for rect, val in zip(self._bars_invested, invested_vals):
                rect.set_height(val)
            for rect, val in zip(self._bars_total, total_vals):
                rect.set_height(val)

        # Linha da meta se especificada
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

        # Estilo
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
        """Libera canvases e figures ao encerrar a janela principal."""
        for canvas in (self.canvas, self.canvas_bar):
            if canvas is not None:
                try:
                    canvas.get_tk_widget().destroy()
                except Exception:
                    pass
        for figure in (self.fig, self.fig_bar):
            if figure is not None:
                plt.close(figure)
