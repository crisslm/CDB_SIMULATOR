"""
Gráficos Reutilizáveis do Dashboard Financeiro
==============================================

Este módulo implementa os componentes gráficos específicos do Controle
Financeiro Pessoal:

    1. Gráfico de Donut (pizza com furo): Mostra a alocação de despesas
       por categoria e investimentos (destino do dinheiro).

    2. Gráfico de Barras: Mostra despesas por categoria ou evolução
       mensal de despesas.

Ambos usam Matplotlib integrado ao Tkinter via FigureCanvasTkAgg.

Otimizações de desempenho:
    - Reutilização de Figure e Canvas (instanciados uma única vez).
    - Atualização incremental das barras via set_height() em vez de
      ax.clear() + redraw completo.
    - Reaplicação leve de cores no tema (sem recriar artistas).

Classes:
    FinancialCharts: Controlador dos gráficos de donut e barras.

Autor: CDB Simulator
Versão: 1.0.0
"""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import FuncFormatter

from src.services.financial_service import format_cents


class FinancialCharts:
    """
    Controlador de gráficos do dashboard financeiro (donut e barras).

    Gerencia duas figuras Matplotlib:
        1. donut_fig/donut_ax: Gráfico de donut para alocação de despesas.
        2. bar_fig/bar_ax: Gráfico de barras para despesas por categoria
           ou evolução mensal.

    Cada figura tem seu próprio Canvas TkAgg para renderização no Tkinter.

    Atributos:
        palette (dict): Paleta de cores do tema atual.
        donut_fig, donut_ax: Figure e eixos do gráfico donut.
        bar_fig, bar_ax: Figure e eixos do gráfico de barras.
        donut_canvas, bar_canvas: Canvases TkAgg.
        _bar_rects (list | None): Referências aos retângulos de barra
                                  para atualização incremental.
        _bar_annotations (list | None): Referências às anotações de valor
                                        sobre as barras.

    Exemplo de uso:
        charts = FinancialCharts(donut_frame, bar_frame, palette)
        charts.plot_donut(allocation_data)
        charts.plot_bars(category_data, monthly_data, mode="Por categoria")
    """

    def __init__(self, donut_master, bar_master, palette: dict):
        """
        Inicializa os gráficos de donut e barras.

        Parâmetros:
            donut_master: Widget pai para o gráfico donut.
            bar_master: Widget pai para o gráfico de barras.
            palette (dict): Paleta de cores do tema atual.
        """
        self.palette = palette

        # Cria Figure e Canvas do gráfico donut (instanciados uma única vez)
        self.donut_fig, self.donut_ax = plt.subplots(figsize=(5.2, 3.8), dpi=100)
        self.donut_canvas = FigureCanvasTkAgg(self.donut_fig, master=donut_master)
        self.donut_canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)

        # Cria Figure e Canvas do gráfico de barras (instanciados uma única vez)
        self.bar_fig, self.bar_ax = plt.subplots(figsize=(5.2, 3.8), dpi=100)
        self.bar_canvas = FigureCanvasTkAgg(self.bar_fig, master=bar_master)
        self.bar_canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)

        # Aplica o tema inicial
        self.apply_theme(palette)

        # Referências para atualização incremental das barras
        # (evita recriar todos os artistas a cada refresh)
        self._bar_rects = None
        self._bar_annotations = None

    def apply_theme(self, palette: dict) -> None:
        """
        Atualiza as cores dos gráficos conforme o tema (Claro/Escuro).

        Apenas reaplica cores de fundo de figure e axis.
        Não recria os artistas dos dados.

        Parâmetros:
            palette (dict): Dicionário de cores da paleta selecionada.
        """
        self.palette = palette
        for figure, axis in (
            (self.donut_fig, self.donut_ax),
            (self.bar_fig, self.bar_ax),
        ):
            figure.patch.set_facecolor(palette["chart_bg"])
            axis.set_facecolor(palette["chart_bg"])

    def _empty(self, axis, message: str) -> None:
        """
        Exibe uma mensagem de "vazio" em um eixo (sem dados).

        Limpa o eixo, remove spines, ticks e exibe uma mensagem centralizada
        informando que não há dados para exibir.

        Parâmetros:
            axis: Eixo Matplotlib a ser limpo.
            message (str): Mensagem a ser exibida.
        """
        axis.clear()
        axis.set_facecolor(self.palette["chart_bg"])
        axis.text(
            .5, .5, message, ha="center", va="center",
            transform=axis.transAxes,
            color=self.palette["text_muted"], fontsize=10, wrap=True
        )
        axis.set_xticks([])
        axis.set_yticks([])
        for spine in axis.spines.values():
            spine.set_visible(False)

    def plot_donut(self, allocation: list[tuple[str, int, str]]) -> None:
        """
        Desenha o gráfico de donut mostrando a alocação de despesas.

        O donut exibe cada categoria como uma fatia, com:
            - Tamanho proporcional ao valor total da categoria.
            - Cor da categoria.
            - Legenda abaixo com nome, percentual e valor formatado.
            - Texto central com o total geral ("DESTINO" + valor).

        Se não houver dados, exibe mensagem de vazio.

        Parâmetros:
            allocation (list[tuple[str, int, str]]): Lista de
                (nome_categoria, total_centavos, cor_hex).
        """
        if not allocation:
            self._empty(
                self.donut_ax,
                "Ainda não há despesas ou investimentos\nno período selecionado."
            )
            self.donut_fig.tight_layout()
            self.donut_canvas.draw_idle()
            return

        # Desempacota dados
        labels, values, colors = zip(*allocation)
        self.donut_ax.clear()
        self.donut_ax.set_facecolor(self.palette["chart_bg"])

        total = sum(values)

        # Desenha o donut (pizza com furo, width=0.38)
        self.donut_ax.pie(
            values,
            colors=colors,
            startangle=90,
            counterclock=False,
            wedgeprops={
                "width": 0.38,
                "edgecolor": self.palette["chart_bg"],
                "linewidth": 2
            }
        )

        # Textos centrais (DESTINO + total)
        self.donut_ax.text(
            0, 0.08, "DESTINO", ha="center",
            color=self.palette["text_muted"], fontsize=9, weight="bold"
        )
        self.donut_ax.text(
            0, -0.12, format_cents(total), ha="center",
            color=self.palette["text"], fontsize=12, weight="bold"
        )

        # Legenda abaixo do donut
        legend_labels = [
            f"{name}  {amount / total:.0%} · {format_cents(amount)}"
            for name, amount in zip(labels, values)
        ]
        legend = self.donut_ax.legend(
            legend_labels,
            loc="lower center",
            bbox_to_anchor=(0.5, -0.28),
            ncol=1,
            frameon=False,
            fontsize=8,
            labelcolor=self.palette["chart_legend_text"],
            handlelength=0.8
        )

        self.donut_ax.set_aspect("equal")
        self.donut_fig.subplots_adjust(bottom=0.25, top=0.95)
        self.donut_canvas.draw_idle()

    def plot_bars(
        self,
        category_values: list[tuple[str, int, str]],
        monthly_values: list[tuple[str, int]],
        mode: str
    ) -> None:
        """
        Desenha o gráfico de barras.

        Suporta dois modos:
            1. "Por categoria": Barras verticais para cada categoria de despesa,
               com cores individuais de cada categoria.
            2. "Evolução mensal": Barras verticais para cada mês (AAAA-MM),
               todas na cor verde menta.

        Se não houver dados, exibe mensagem de vazio.

        Otimização:
            Na primeira execução, cria as barras e anotações.
            Nas execuções subsequentes, usa set_height() e set_text()
            para atualizar apenas os valores, evitando recriar artistas.

        Parâmetros:
            category_values (list[tuple[str, int, str]]):
                Lista de (nome_categoria, total_centavos, cor_hex).
            monthly_values (list[tuple[str, int]]):
                Lista de ("AAAA-MM", total_centavos).
            mode (str): "Por categoria" ou "Evolução mensal".
        """
        # Determina dados com base no modo
        if mode == "Evolução mensal":
            labels, values = (
                zip(*monthly_values) if monthly_values else ((), ())
            )
            title, colors = "Evolução das despesas", "#24C270"
        else:
            labels = tuple(item[0] for item in category_values)
            values = tuple(item[1] for item in category_values)
            colors = [item[2] for item in category_values]
            title = "Despesas por categoria"

        # Sem dados: exibe mensagem de vazio
        if not values:
            self._empty(
                self.bar_ax,
                "Ainda não há despesas\nno período selecionado."
            )
            self.bar_fig.tight_layout()
            self.bar_canvas.draw_idle()
            return

        # Estilo dos eixos (feito uma vez, reaplicado levemente depois)
        if self._bar_rects is None:
            self.bar_ax.set_facecolor(self.palette["chart_bg"])
            self.bar_ax.set_title(
                title, loc="left",
                color=self.palette["text"],
                fontsize=11, weight="bold", pad=10
            )
            self.bar_ax.yaxis.set_major_formatter(
                FuncFormatter(lambda value, _: format_cents(int(value)))
            )
            self.bar_ax.grid(
                axis="y", color=self.palette["chart_grid"],
                alpha=0.15
            )
            self.bar_ax.set_axisbelow(True)
            self.bar_ax.tick_params(
                axis="x", colors=self.palette["chart_tick"], length=0
            )
            self.bar_ax.tick_params(
                axis="y", colors=self.palette["chart_tick"],
                labelsize=8, length=0
            )
            for spine in ("top", "right", "left"):
                self.bar_ax.spines[spine].set_visible(False)
            self.bar_ax.spines["bottom"].set_color(
                self.palette["chart_spine"]
            )
            self.bar_ax.set_ylim(bottom=0)

        # Cria barras na primeira execução; depois apenas atualiza alturas
        if self._bar_rects is None or len(self._bar_rects) != len(values):
            # Recria se o número de categorias mudou
            self.bar_ax.clear()
            self.bar_ax.set_facecolor(self.palette["chart_bg"])
            self._bar_rects = self.bar_ax.bar(
                range(len(values)), values,
                color=colors, alpha=0.9, width=0.62
            )
            self._bar_annotations = []
            for bar, amount in zip(self._bar_rects, values):
                ann = self.bar_ax.annotate(
                    format_cents(amount),
                    (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    xytext=(0, 4),
                    textcoords="offset points",
                    ha="center",
                    color=self.palette["text_muted"],
                    fontsize=7
                )
                self._bar_annotations.append(ann)
        else:
            # Execuções subsequentes: atualiza apenas altura e texto
            for rect, val in zip(self._bar_rects, values):
                rect.set_height(val)
            for ann, amount in zip(self._bar_annotations, values):
                ann.set_text(format_cents(amount))
                ann.set_position(
                    (ann.get_position()[0], max(values))
                )

        # Configura eixo X com rótulos
        self.bar_ax.set_xticks(range(len(labels)))
        self.bar_ax.set_xticklabels(
            [
                label[5:] if mode == "Evolução mensal" else label
                for label in labels
            ],
            rotation=25,
            ha="right",
            fontsize=8
        )

        # Atualiza título e limites
        self.bar_ax.set_title(
            title, loc="left",
            color=self.palette["text"],
            fontsize=11, weight="bold", pad=10
        )
        self.bar_ax.spines["bottom"].set_color(
            self.palette["chart_spine"]
        )
        self.bar_ax.set_ylim(
            bottom=0,
            top=max(values) * 1.15 if values else 1
        )

        self.bar_fig.tight_layout()
        self.bar_canvas.draw_idle()

    def dispose(self) -> None:
        """
        Fecha recursos Matplotlib antes de destruir a janela Tk.

        Deve ser chamado ao encerrar a janela principal para evitar
        processos Matplotlib/TkAgg residentes após o fechamento.

        Fecha:
            - Canvases (donut e barras).
            - Figures (donut e barras) via plt.close().
        """
        for canvas in (self.donut_canvas, self.bar_canvas):
            try:
                canvas.get_tk_widget().destroy()
            except Exception:
                pass
        plt.close(self.donut_fig)
        plt.close(self.bar_fig)