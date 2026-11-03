"""Gráficos reutilizáveis do dashboard financeiro."""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import FuncFormatter

from src.services.financial_service import format_cents


class FinancialCharts:
    def __init__(self, donut_master, bar_master, palette: dict):
        self.palette = palette
        self.donut_fig, self.donut_ax = plt.subplots(figsize=(5.2, 3.8), dpi=100)
        self.bar_fig, self.bar_ax = plt.subplots(figsize=(5.2, 3.8), dpi=100)
        self.donut_canvas = FigureCanvasTkAgg(self.donut_fig, master=donut_master)
        self.bar_canvas = FigureCanvasTkAgg(self.bar_fig, master=bar_master)
        self.donut_canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)
        self.bar_canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)
        self.apply_theme(palette)

    def apply_theme(self, palette: dict) -> None:
        self.palette = palette
        for figure, axis in ((self.donut_fig, self.donut_ax), (self.bar_fig, self.bar_ax)):
            figure.patch.set_facecolor(palette["chart_bg"])
            axis.set_facecolor(palette["chart_bg"])

    def _empty(self, axis, message: str) -> None:
        axis.clear(); axis.set_facecolor(self.palette["chart_bg"])
        axis.text(.5, .5, message, ha="center", va="center", transform=axis.transAxes,
                  color=self.palette["text_muted"], fontsize=10, wrap=True)
        axis.set_xticks([]); axis.set_yticks([])
        for spine in axis.spines.values(): spine.set_visible(False)

    def plot_donut(self, allocation: list[tuple[str, int, str]]) -> None:
        if not allocation:
            self._empty(self.donut_ax, "Ainda não há despesas ou investimentos\nno período selecionado.")
            self.donut_fig.tight_layout(); self.donut_canvas.draw_idle(); return
        labels, values, colors = zip(*allocation)
        self.donut_ax.clear(); self.donut_ax.set_facecolor(self.palette["chart_bg"])
        total = sum(values)
        self.donut_ax.pie(values, colors=colors, startangle=90, counterclock=False,
            wedgeprops={"width": .38, "edgecolor": self.palette["chart_bg"], "linewidth": 2})
        self.donut_ax.text(0, .08, "DESTINO", ha="center", color=self.palette["text_muted"], fontsize=9, weight="bold")
        self.donut_ax.text(0, -.12, format_cents(total), ha="center", color=self.palette["text"], fontsize=12, weight="bold")
        legend_labels = [f"{name}  {amount / total:.0%} · {format_cents(amount)}" for name, amount in zip(labels, values)]
        legend = self.donut_ax.legend(legend_labels, loc="lower center", bbox_to_anchor=(.5, -.28),
            ncol=1, frameon=False, fontsize=8, labelcolor=self.palette["chart_legend_text"], handlelength=.8)
        self.donut_ax.set_aspect("equal")
        self.donut_fig.subplots_adjust(bottom=.25, top=.95)
        self.donut_canvas.draw_idle()

    def plot_bars(self, category_values: list[tuple[str, int, str]], monthly_values: list[tuple[str, int]], mode: str) -> None:
        if mode == "Evolução mensal":
            labels, values = zip(*monthly_values) if monthly_values else ((), ())
            title, colors = "Evolução das despesas", "#24C270"
        else:
            labels = tuple(item[0] for item in category_values); values = tuple(item[1] for item in category_values)
            title, colors = "Despesas por categoria", [item[2] for item in category_values]
        if not values:
            self._empty(self.bar_ax, "Ainda não há despesas\nno período selecionado.")
            self.bar_fig.tight_layout(); self.bar_canvas.draw_idle(); return
        self.bar_ax.clear(); self.bar_ax.set_facecolor(self.palette["chart_bg"])
        bars = self.bar_ax.bar(range(len(values)), values, color=colors, alpha=.9, width=.62)
        self.bar_ax.set_title(title, loc="left", color=self.palette["text"], fontsize=11, weight="bold", pad=10)
        self.bar_ax.set_xticks(range(len(labels)))
        self.bar_ax.set_xticklabels([label[5:] if mode == "Evolução mensal" else label for label in labels], rotation=25, ha="right", fontsize=8)
        self.bar_ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: format_cents(int(value))))
        self.bar_ax.grid(axis="y", color=self.palette["chart_grid"], alpha=.15); self.bar_ax.set_axisbelow(True)
        self.bar_ax.tick_params(axis="x", colors=self.palette["chart_tick"], length=0)
        self.bar_ax.tick_params(axis="y", colors=self.palette["chart_tick"], labelsize=8, length=0)
        for spine in ("top", "right", "left"): self.bar_ax.spines[spine].set_visible(False)
        self.bar_ax.spines["bottom"].set_color(self.palette["chart_spine"])
        self.bar_ax.set_ylim(bottom=0)
        for bar, amount in zip(bars, values):
            self.bar_ax.annotate(format_cents(amount), (bar.get_x() + bar.get_width()/2, bar.get_height()),
                xytext=(0, 4), textcoords="offset points", ha="center", color=self.palette["text_muted"], fontsize=7)
        self.bar_fig.tight_layout(); self.bar_canvas.draw_idle()

    def dispose(self) -> None:
        """Fecha recursos Matplotlib antes de destruir a janela Tk."""
        for canvas in (self.donut_canvas, self.bar_canvas):
            try:
                canvas.get_tk_widget().destroy()
            except Exception:
                pass
        plt.close(self.donut_fig)
        plt.close(self.bar_fig)
