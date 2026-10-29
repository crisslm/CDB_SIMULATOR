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
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import FuncFormatter
from src.domain.models import MonthlyRecord


class InvestmentChart:
    """
    Controlador do gráfico integrado ao Tkinter/CustomTkinter com alto desempenho.
    Instancia Figure e Canvas uma única vez e reutiliza os eixos.
    """

    def __init__(self, master_widget, bar_widget=None):
        from src.ui.gui.components import PALETTES  # importado aqui para evitar ciclo de importacao

        self.master = master_widget
        self.bar_master = bar_widget
        self.palette = PALETTES["Light"]
        self.fig, self.ax = plt.subplots(figsize=(7, 3.8), dpi=100)
        self.fig.patch.set_facecolor(self.palette["chart_bg"])
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.master)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        # Gráfico de barras para evolução até a meta
        self.fig_bar = None
        self.ax_bar = None
        self.canvas_bar = None
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
        Redesenha o gráfico de forma performática limpando apenas os eixos (ax.clear()).
        """
        self.ax.clear()
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
        mint_line = "#24C270"      # Verde menta característico (mantido nos dois temas)
        mint_fill = "#24C270"
        invested_line = pal["invested_line"]

        # 1. Linha do Montante Total (Curva Verde Suave)
        self.ax.plot(raw_months, raw_totals, label="Montante Bruto (com juros)", color=mint_line, linewidth=3.0, zorder=3)

        # 2. Linha do Total Investido (Tracejada sutil)
        self.ax.plot(raw_months, raw_invested, label="Total Aportado (do bolso)", color=invested_line, linestyle="--", linewidth=1.8, zorder=2)

        # 3. Preenchimento sutil de área com transparência
        self.ax.fill_between(raw_months, 0, raw_totals, color=mint_fill, alpha=0.12, zorder=1)

        # 4. Ponto de destaque no valor final (marcador do print)
        final_x = raw_months[-1]
        final_y = raw_totals[-1]
        self.ax.scatter([final_x], [final_y], color=self.palette["chart_bg"], edgecolors=mint_line, s=80, linewidths=3.0, zorder=4)

        # Linha vertical pontilhada indicando o ponto final
        self.ax.vlines(x=final_x, ymin=0, ymax=final_y, colors=mint_line, linestyles=":", linewidth=1.5, alpha=0.6, zorder=2)

        # Limpeza visual dos eixos (estilo minimalista despined)
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_visible(False)
        self.ax.spines['bottom'].set_color(pal["chart_spine"])
        self.ax.spines['bottom'].set_linewidth(1.2)

        # Grade horizontal suave
        self.ax.grid(axis='y', linestyle='-', alpha=0.15, color=pal["chart_grid"])
        self.ax.grid(axis='x', visible=False)

        self.ax.tick_params(axis='x', colors=pal["chart_tick"], labelsize=9, length=0)
        self.ax.tick_params(axis='y', colors=pal["chart_tick"], labelsize=9, length=0)

        # Formatação de Moeda Simplificada para o Eixo Y
        def _formato_moeda(x, pos):
            if x >= 1_000_000:
                return f"R$ {x*1e-6:.1f}M"
            elif x >= 1_000:
                return f"R$ {x*1e-3:.0f}k"
            elif x == 0:
                return "R$ 0"
            return f"R$ {x:.0f}"

        self.ax.yaxis.set_major_formatter(FuncFormatter(_formato_moeda))
        self.ax.set_ylim(bottom=0)

        # Legenda no topo em estilo pílula limpa
        legend = self.ax.legend(
            loc="upper left",
            frameon=True,
            facecolor=pal["chart_legend_bg"],
            edgecolor=pal["chart_legend_edge"],
            fontsize=9
        )
        if legend:
            for text in legend.get_texts():
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
            # Projetar evolução até a meta usando os mesmos parâmetros
            saldo_atual = initial_amount
            investido_atual = initial_amount
            # Construir timeline projetado até max_month_show
            projected_records = []
            for mes in range(1, max_month_show + 1):
                saldo_atual += monthly_contribution
                investido_atual += monthly_contribution
                if monthly_rate > 0:
                    rendimento = saldo_atual * monthly_rate
                    saldo_atual += rendimento
                projected_records.append(MonthlyRecord(
                    month=mes,
                    invested_to_date=round(investido_atual, 2),
                    interest_earned_month=round(rendimento if monthly_rate > 0 else 0.0, 2),
                    total_balance=round(saldo_atual, 2)
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
        bar_invested = self.ax_bar.bar([i - width/2 for i in x], invested_vals, width,
                                       label="Total Aportado", color=pal["invested_line"], alpha=0.85)
        bar_total = self.ax_bar.bar([i + width/2 for i in x], total_vals, width,
                                    label="Montante Total", color="#24C270", alpha=0.9)

        # Linha da meta se especificada
        if target_amount is not None and target_amount > 0:
            self.ax_bar.axhline(y=target_amount, color=pal["meta_line"], linestyle="--", linewidth=2,
                               label=f"Meta: {target_amount:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."),
                               alpha=0.8)
            self.ax_bar.legend(loc="upper left", frameon=True, facecolor=pal["chart_legend_bg"],
                              edgecolor=pal["chart_legend_edge"], fontsize=8)

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
            legend = self.ax_bar.legend(loc="upper left", frameon=True, facecolor=pal["chart_legend_bg"],
                                       edgecolor=pal["chart_legend_edge"], fontsize=8)
            if legend:
                for text in legend.get_texts():
                    text.set_color(pal["chart_legend_text"])

        self.ax_bar.set_title("Evolução do Capital até a Meta", color=pal["text"], fontsize=11, pad=10)
        self.fig_bar.tight_layout()
        self.canvas_bar.draw_idle()
