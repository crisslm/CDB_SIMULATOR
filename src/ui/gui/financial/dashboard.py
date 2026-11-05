"""
Tela Completa e Responsiva do Controle Financeiro
=================================================

Este módulo implementa a interface do Controle Financeiro Pessoal, uma seção
independente do simulador de CDB focada em:
    - Registrar receitas, despesas e investimentos.
    - Gerenciar categorias personalizadas.
    - Filtrar lançamentos por período, tipo e categoria.
    - Visualizar resumos, gráficos (donut e barras) e histórico detalhado.
    - Fazer backup e restauração do banco de dados criptografado.

Classes:
    CategoryDialog: Janela modal para gerenciar categorias (adicionar/editar/remover).
    FinancialDashboard: Painel principal com filtros, métricas, gráficos e histórico.

Princípio de design:
- Separação de preocupações: UI aqui, lógica de negócio em FinancialService,
  persistência em FinancialRepository.
- Uso de consultas SQL agregadas (summary_sql, expense_by_category_sql, etc.)
  para evitar carregar todas as transações para o Python.
- Reutilização de widgets no histórico (não destrói/recria a cada refresh).
- Singleton do diálogo de categorias (não abre múltiplas janelas).

Autor: CDB Simulator
Versão: 1.0.0
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional

# Garante que o pacote src seja importável como pacote absoluto
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))

import customtkinter as ctk

from src.i18n.manager import t
from ....domain.financial_models import FinancialTransaction, TransactionType
from ....services.financial_service import FinancialService, format_cents, parse_br_date
from ..components import MetricCard, PillButton
from .financial_charts import FinancialCharts


# Mapeamento de labels amigáveis para TransactionType (traduzido dinamicamente)
TYPE_LABELS = {
    t("financial.transaction.type.income"): TransactionType.INCOME,
    t("financial.transaction.type.expense"): TransactionType.EXPENSE,
    t("financial.transaction.type.investment"): TransactionType.INVESTMENT,
}

# Mapeamento reverso (valor do enum -> label amigável)
TYPE_BY_VALUE = {item.value: label for label, item in TYPE_LABELS.items()}

# Períodos disponíveis para filtro no dashboard (traduzidos dinamicamente)
PERIODS = [
    t("financial.filter.period.current_month"),
    t("financial.filter.period.previous_month"),
    t("financial.filter.period.last_3_months"),
    t("financial.filter.period.last_6_months"),
    t("financial.filter.period.last_12_months"),
    t("financial.filter.period.all"),
    t("financial.filter.period.custom"),
]

# Cores pré-definidas para categorias (nome amigável -> código hex)
# Usadas no diálogo de categorias para seleção rápida de cor
CATEGORY_COLORS = [
    (t("financial.category.color.green"), "#24C270"),
    (t("financial.category.color.blue"), "#4F8CFF"),
    (t("financial.category.color.orange"), "#FF9F43"),
    (t("financial.category.color.red"), "#FF6B6B"),
    (t("financial.category.color.purple"), "#A970FF"),
    (t("financial.category.color.cyan"), "#32B8C6"),
    (t("financial.category.color.pink"), "#F368E0"),
    (t("financial.category.color.gray"), "#8395A7"),
    (t("financial.category.color.yellow"), "#F9CA24"),
    (t("financial.category.color.dark_blue"), "#1C1C1E"),
    (t("financial.category.color.dark_green"), "#107C41"),
    (t("financial.category.color.dark_orange"), "#D9534F"),
]


# =============================================================================
# Classe CategoryDialog
# =============================================================================

class CategoryDialog(ctk.CTkToplevel):
    """
    Janela modal (Toplevel) para gerenciamento de categorias financeiras.

    Permite ao usuário:
        - Adicionar nova categoria (nome, tipo, cor).
        - Editar categoria existente.
        - Remover categoria (ou arquivar se tiver lançamentos).

    A janela é modal (grab_set) e fica sobreposta à janela principal.
    Implementa padrão singleton: apenas uma instância pode estar aberta por vez,
    controlada pelo FinancialDashboard via _category_dialog.

    Atributos:
        dashboard (FinancialDashboard): Referência ao dashboard pai.
        service (FinancialService): Serviço de controle financeiro.
        palette (dict): Paleta de cores do tema atual.
        edit_id (int | None): ID da categoria sendo editada (None se adicionando).

    Exemplo de uso:
        dialog = CategoryDashboard(dashboard_instance)
        dialog.mainloop()  # não é necessário, é Toplevel
    """

    def __init__(self, dashboard: "FinancialDashboard"):
        """
        Inicializa o diálogo de gerenciamento de categorias.

        Parâmetros:
            dashboard (FinancialDashboard): Instância do dashboard pai.
        """
        super().__init__(dashboard.winfo_toplevel())
        self.dashboard, self.service, self.palette = dashboard, dashboard.service, dashboard.palette
        self.edit_id = None  # ID da categoria em edição (None = adicionando nova)
        self.title(t("financial.dialog.title"))
        self.geometry("580x620")
        self.minsize(440, 480)
        self.configure(fg_color=self.palette["bg_root"])

        # Torna a janela modal (bloqueia interação com a janela pai)
        self.transient(dashboard.winfo_toplevel())
        self.grab_set()

        # Limpa a referência no dashboard quando a janela for fechada (incluindo o botão X)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build()

    def _on_close(self):
        """
        Fecha o diálogo e limpa a referência no dashboard.

        Chamado quando o usuário clica no botão X da janela.
        Garante que o dashboard saiba que o diálogo foi fechado,
        permitindo abrir um novo posteriormente.
        """
        self.dashboard._clear_category_dialog_ref()
        self.destroy()

    def _input(self, master, placeholder=""):
        """
        Cria um campo de entrada (CTkEntry) com estilo padronizado.

        Parâmetros:
            master: Widget pai.
            placeholder (str): Texto de placeholder.

        Retorna:
            ctk.CTkEntry: Campo de entrada configurado.
        """
        return ctk.CTkEntry(
            master,
            placeholder_text=placeholder,
            height=36,
            corner_radius=10,
            fg_color=self.palette["surface_input"],
            border_color=self.palette["border_input"],
            text_color=self.palette["text"],
        )

    def _build(self):
        """
        Constrói a interface do diálogo:
            - Cabeçalho com título.
            - Formulário (nome, tipo, cor, botão salvar).
            - Lista rolável de categorias existentes.
        """
        header = ctk.CTkLabel(
            self, text=t("financial.dialog.header"),
            font=("Segoe UI", 18, "bold"),
            text_color=self.palette["text"]
        )
        header.pack(anchor="w", padx=18, pady=(18, 8))

        # Formulário de cadastro/edição
        form = ctk.CTkFrame(
            self,
            fg_color=self.palette["surface"],
            corner_radius=14,
            border_width=1,
            border_color=self.palette["border"]
        )
        form.pack(fill="x", padx=18, pady=(0, 10))

        self.name_entry = self._input(form, t("financial.dialog.name_placeholder"))
        self.type_combo = ctk.CTkComboBox(
            form, values=list(TYPE_LABELS), height=36, corner_radius=10,
            command=lambda _: None
        )
        self.color_combo = ctk.CTkComboBox(
            form, values=[name for name, _ in CATEGORY_COLORS],
            height=36, corner_radius=10, command=lambda _: None
        )
        self.color_combo.set(CATEGORY_COLORS[0][0])

        self.name_entry.grid(row=0, column=0, sticky="ew", padx=12, pady=12)
        self.type_combo.grid(row=0, column=1, padx=5, pady=12)
        self.color_combo.grid(row=0, column=2, padx=5, pady=12)
        form.grid_columnconfigure(0, weight=1)

        self.type_combo.set(list(TYPE_LABELS)[1] if len(TYPE_LABELS) > 1 else list(TYPE_LABELS)[0])

        self.save_button = PillButton(
            form, text=t("financial.dialog.add"), command=self._save,
            variant="primary", width=110
        )
        self.save_button.grid(row=0, column=3, padx=(5, 12), pady=12)
        self.save_button.apply_theme(self.palette)

        # Lista rolável de categorias existentes
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        self._style_combo(self.type_combo)
        self._style_combo(self.color_combo)
        self._render_list()

    def _style_combo(self, combo):
        """
        Aplica cores do tema a um CTkComboBox.

        Parâmetros:
            combo: Instância de CTkComboBox a ser estilizada.
        """
        combo.configure(
            fg_color=self.palette["surface_input"],
            border_color=self.palette["border_input"],
            button_color=self.palette["surface_input"],
            button_hover_color=self.palette["border_input"],
            text_color=self.palette["text"],
            dropdown_fg_color=self.palette["surface"],
            dropdown_text_color=self.palette["text"],
        )

    def _render_list(self):
        """
        Renderiza a lista de categorias no scrollable frame.

        Cada categoria é exibida como uma linha com:
            - Ponto colorido (●) com a cor da categoria.
            - Nome e tipo (ex: "Salário · Receita").
            - Botões "Editar" e "Remover".

        Se uma categoria está sendo editada (self.edit_id corresponde),
        a linha é destacada com cores invertidas (fundo de acento, texto branco).
        """
        # Limpa widgets existentes antes de re-renderizar
        for child in self.list_frame.winfo_children():
            child.destroy()

        for category in self.service.categories(active_only=False):
            state = "" if category.active else f" · {t('financial.dialog.state.archived')}"
            is_editing = self.edit_id == category.id

            if is_editing:
                # Linha em edição: cores invertidas para contraste (fundo escuro, texto branco)
                row = ctk.CTkFrame(
                    self.list_frame,
                    fg_color=self.palette["accent"],
                    corner_radius=10,
                    border_width=1,
                    border_color=self.palette["accent_text"]
                )
                row.pack(fill="x", pady=3)
                ctk.CTkLabel(
                    row, text="●", text_color="#FFFFFF", font=("Segoe UI", 18)
                ).pack(side="left", padx=(10, 4))
                ctk.CTkLabel(
                    row,
                    text=f"{category.name}{state}\n{category.transaction_type.label}",
                    justify="left", anchor="w",
                    text_color="#FFFFFF", font=("Segoe UI", 12)
                ).pack(side="left", fill="x", expand=True, pady=7)
                ctk.CTkButton(
                    row, text=t("financial.dialog.edit"), width=54, height=28, corner_radius=9,
                    fg_color=self.palette["accent_text"],
                    hover_color=self.palette["accent_bg"],
                    text_color="#FFFFFF",
                    command=lambda item=category: self._edit(item)
                ).pack(side="right", padx=3)
                ctk.CTkButton(
                    row, text=t("financial.dialog.remove"), width=72, height=28, corner_radius=9,
                    fg_color="#D9534F", hover_color="#B94440",
                    text_color="#FFFFFF",
                    command=lambda item=category: self._delete(item)
                ).pack(side="right", padx=(3, 9))
            else:
                # Linha normal: cores padrão do tema
                row = ctk.CTkFrame(
                    self.list_frame,
                    fg_color=self.palette["surface"],
                    corner_radius=10,
                    border_width=1,
                    border_color=self.palette["border"]
                )
                row.pack(fill="x", pady=3)
                ctk.CTkLabel(
                    row, text="●", text_color=category.color, font=("Segoe UI", 18)
                ).pack(side="left", padx=(10, 4))
                ctk.CTkLabel(
                    row,
                    text=f"{category.name}{state}\n{category.transaction_type.label}",
                    justify="left", anchor="w",
                    text_color=self.palette["text"], font=("Segoe UI", 12)
                ).pack(side="left", fill="x", expand=True, pady=7)
                ctk.CTkButton(
                    row, text=t("financial.dialog.edit"), width=54, height=28, corner_radius=9,
                    fg_color=self.palette["surface_input"],
                    hover_color=self.palette["border_input"],
                    text_color=self.palette["text"],
                    command=lambda item=category: self._edit(item)
                ).pack(side="right", padx=3)
                ctk.CTkButton(
                    row, text=t("financial.dialog.remove"), width=72, height=28, corner_radius=9,
                    fg_color="#D9534F", hover_color="#B94440",
                    command=lambda item=category: self._delete(item)
                ).pack(side="right", padx=(3, 9))

    def _edit(self, category):
        """
        Preenche o formulário com os dados da categoria para edição.

        Define self.edit_id e chama _render_list() para destacar a linha
        selecionada na lista.

        Parâmetros:
            category (FinancialCategory): Categoria a ser editada.
        """
        self.edit_id = category.id
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, category.name)
        self.type_combo.set(category.transaction_type.label)

        # Seleciona a cor correspondente no combobox de cores
        for name, hex_color in CATEGORY_COLORS:
            if hex_color == category.color:
                self.color_combo.set(name)
                break

        self.save_button.configure(text="Salvar")
        self._render_list()

    def _save(self):
        """
        Salva a categoria (cria nova ou atualiza existente).

        Valida os dados através do FinancialService e exibe mensagem de erro
        caso haja problema (ex: nome duplicado).

        Após salvar, limpa o formulário, re-renderiza a lista e atualiza o
        dashboard pai.
        """
        try:
            # Mapeia o nome da cor selecionada de volta para o código hex
            selected_color_name = self.color_combo.get()
            selected_color_hex = next(
                (hex_color for name, hex_color in CATEGORY_COLORS if name == selected_color_name),
                CATEGORY_COLORS[0][1]
            )

            if self.edit_id:
                self.service.update_category(
                    self.edit_id,
                    self.name_entry.get(),
                    TYPE_LABELS[self.type_combo.get()],
                    selected_color_hex
                )
            else:
                self.service.create_category(
                    self.name_entry.get(),
                    TYPE_LABELS[self.type_combo.get()],
                    selected_color_hex
                )

            # Limpa formulário e re-renderiza
            self.edit_id = None
            self.name_entry.delete(0, "end")
            self.color_combo.set(CATEGORY_COLORS[0][0])
            self.save_button.configure(text=t("financial.dialog.add"))
            self._render_list()
            self.dashboard.refresh()
        except ValueError as exc:
            messagebox.showerror(t("financial.dialog.title"), str(exc), parent=self)

    def _delete(self, category):
        """
        Exclui ou arquiva uma categoria.

        Se a categoria tiver lançamentos associados, solicita confirmação
        para arquivamento (preserva o histórico). Caso contrário, exclui
        diretamente.

        Parâmetros:
            category (FinancialCategory): Categoria a ser removida.
        """
        if not messagebox.askyesno(
            t("financial.dialog.remove_confirm_title"),
            t("financial.dialog.remove_confirm_msg", name=category.name),
            parent=self
        ):
            return
        try:
            result = self.service.delete_or_archive_category(category.id)
            if result == "archived":
                messagebox.showinfo(
                    t("financial.dialog.archived_title"),
                    t("financial.dialog.archived_msg"),
                    parent=self
                )
            self._render_list()
            self.dashboard.refresh()
        except ValueError as exc:
            messagebox.showerror(t("financial.dialog.title"), str(exc), parent=self)


# =============================================================================
# Classe FinancialDashboard
# =============================================================================

class FinancialDashboard(ctk.CTkFrame):
    """
    Painel principal do Controle Financeiro.

    Contém:
        - Filtros (período, tipo, categoria).
        - Cards de métrica (Receitas, Despesas, Investimentos, Saldo, Taxa investida).
        - Formulário de novo lançamento.
        - Gráficos (donut e barras).
        - Histórico detalhado de transações.
        - Botões de backup e restauração.

    Atributos:
        service (FinancialService): Serviço de controle financeiro.
        palette (dict): Paleta de cores do tema atual.
        editing_id (int | None): ID da transação sendo editada.
        _history_rows (list): Referências aos widgets de linha do histórico
                              (reutilização para evitar recriação).
        _category_dialog (CategoryDialog | None): Referência ao diálogo de
                                                  categorias (singleton).
        _editing_transaction_id (int | None): ID da transação em edição no
                                              histórico (para destaque visual).

    Exemplo de uso:
        dashboard = FinancialDashboard(master, service, palette)
        dashboard.pack(fill="both", expand=True)
        dashboard.refresh()
    """

    def __init__(self, master, service: FinancialService, palette: dict):
        """
        Inicializa o dashboard e constrói toda a interface.

        Parâmetros:
            master: Widget pai.
            service (FinancialService): Instância do serviço financeiro.
            palette (dict): Paleta de cores do tema atual.
        """
        super().__init__(master, fg_color="transparent")
        self.service, self.palette = service, palette
        self.editing_id: int | None = None
        self._form_categories = {}
        self._filter_categories = {"Todas as categorias": None}
        self._history_rows: list = []
        self._category_dialog: Optional[CategoryDialog] = None
        self._editing_transaction_id: Optional[int] = None
        self._build()
        self.refresh()

    def _entry(self, master, placeholder="", **kwargs):
        """Cria um CTkEntry com estilo padronizado do tema."""
        return ctk.CTkEntry(
            master, placeholder_text=placeholder, height=38, corner_radius=10,
            fg_color=self.palette["surface_input"],
            border_color=self.palette["border_input"],
            text_color=self.palette["text"], **kwargs
        )

    def _combo(self, master, values, command=None, width=None):
        """Cria um CTkComboBox com estilo padronizado do tema."""
        kwargs = {
            "values": values, "height": 38, "corner_radius": 10, "command": command,
            "fg_color": self.palette["surface_input"],
            "border_color": self.palette["border_input"],
            "button_color": self.palette["surface_input"],
            "button_hover_color": self.palette["border_input"],
            "text_color": self.palette["text"],
            "dropdown_fg_color": self.palette["surface"],
            "dropdown_text_color": self.palette["text"],
        }
        if width:
            kwargs["width"] = width
        return ctk.CTkComboBox(master, **kwargs)

    def _card(self, master):
        """Cria um CTkFrame com estilo de card (superfície + borda)."""
        return ctk.CTkFrame(
            master,
            fg_color=self.palette["surface"],
            corner_radius=16,
            border_width=1,
            border_color=self.palette["border"]
        )

    def _build(self):
        """
        Constrói toda a interface do dashboard:

            1. Cabeçalho com título e botões (Backup, Restaurar, Gerenciar categorias).
            2. Filtros (período, tipo, categoria, botão Aplicar).
            3. Cards de métrica (5 cards em grid responsivo).
            4. Formulário de novo lançamento.
            5. Gráficos (donut e barras).
            6. Histórico de transações (lista rolável).
        """
        # Cabeçalho superior
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            top, text=t("financial.title"),
            font=("Segoe UI", 21, "bold"),
            text_color=self.palette["text"]
        ).pack(side="left")

        botoes = ctk.CTkFrame(top, fg_color="transparent")
        botoes.pack(side="right")

        self.backup_button = PillButton(
            botoes, text=t("financial.button.backup"),
            command=self._backup_database, variant="secondary", width=100
        )
        self.backup_button.pack(side="left", padx=(0, 6))
        self.backup_button.apply_theme(self.palette)

        self.restore_button = PillButton(
            botoes, text=t("financial.button.restore"),
            command=self._restore_database, variant="secondary", width=110
        )
        self.restore_button.pack(side="left", padx=(0, 6))
        self.restore_button.apply_theme(self.palette)

        self.manage_button = PillButton(
            top, text=t("financial.button.manage"),
            command=self._open_category_dialog, variant="secondary", width=185
        )
        self.manage_button.pack(side="right")
        self.manage_button.apply_theme(self.palette)

        ctk.CTkLabel(
            self, text=t("financial.subtitle"),
            font=("Segoe UI", 12), text_color=self.palette["text_muted"]
        ).pack(anchor="w", pady=(0, 12))

        # Filtros
        filters = self._card(self)
        self.filter_card = filters
        filters.pack(fill="x", pady=(0, 10))
        filters.grid_columnconfigure(4, weight=1)

        ctk.CTkLabel(
            filters, text=t("financial.filter.period"),
            font=("Segoe UI", 10, "bold"),
            text_color=self.palette["text_muted"]
        ).grid(row=0, column=0, padx=(12, 4), pady=10)

        self.period_combo = self._combo(
            filters, PERIODS, self._on_period_change, width=165
        )
        self.period_combo.set("Mês atual")
        self.period_combo.grid(row=0, column=1, padx=4, pady=10)

        self.custom_start = self._entry(filters, "Início DD/MM/AAAA", width=135)
        self.custom_end = self._entry(filters, "Fim DD/MM/AAAA", width=135)

        ctk.CTkLabel(
            filters, text=t("financial.filter.type"),
            font=("Segoe UI", 10, "bold"),
            text_color=self.palette["text_muted"]
        ).grid(row=0, column=2, padx=(12, 4), pady=10)

        self.filter_type = self._combo(
            filters, ["Todos", *TYPE_LABELS], self._on_filter_type, width=130
        )
        self.filter_type.set("Todos")
        self.filter_type.grid(row=0, column=3, padx=4, pady=10)

        self.filter_category = self._combo(
            filters, ["Todas as categorias"], lambda _: self.refresh(), width=180
        )
        self.filter_category.set("Todas as categorias")
        self.filter_category.grid(row=0, column=4, padx=4, pady=10, sticky="w")

        self.filter_button = PillButton(
            filters, text=t("financial.filter.apply"),
            command=self.refresh, variant="secondary", width=78
        )
        self.filter_button.grid(row=0, column=5, padx=(4, 12), pady=10)
        self.filter_button.apply_theme(self.palette)

        # Cards de métrica
        self.metrics = ctk.CTkFrame(self, fg_color="transparent")
        self.metrics.pack(fill="x", pady=(0, 10))
        self.cards = [
            MetricCard(self.metrics, t("financial.card.income"), "R$ 0,00"),
            MetricCard(self.metrics, t("financial.card.expense"), "R$ 0,00"),
            MetricCard(self.metrics, t("financial.card.investment"), "R$ 0,00"),
            MetricCard(self.metrics, t("financial.card.balance"), "R$ 0,00", is_highlight=True),
            MetricCard(self.metrics, t("financial.card.rate"), "0,0%"),
        ]

        # Formulário de novo lançamento
        self.form_card = self._card(self)
        self.form_card.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            self.form_card, text=t("financial.form.new"),
            font=("Segoe UI", 15, "bold"),
            text_color=self.palette["text"]
        ).grid(row=0, column=0, columnspan=6, sticky="w", padx=14, pady=(12, 8))

        self.transaction_type = self._combo(
            self.form_card, list(TYPE_LABELS), self._on_form_type, width=130
        )
        self.transaction_type.set("Despesa")
        self.description = self._entry(self.form_card, "Descrição")
        self.amount = self._entry(self.form_card, "Valor (R$)", width=125)
        self.category = self._combo(self.form_card, [""], None, width=160)
        self.occurred_on = self._entry(self.form_card, "DD/MM/AAAA", width=118)
        self.notes = self._entry(self.form_card, "Observação (opcional)")

        self.save_transaction = PillButton(
            self.form_card, text="Adicionar",
            command=self._save_transaction, variant="primary", width=110
        )
        self.cancel_edit = PillButton(
            self.form_card, text="Cancelar",
            command=self._clear_form, variant="secondary", width=90
        )

        for column, widget in enumerate((
            self.transaction_type, self.description, self.amount,
            self.category, self.occurred_on, self.notes,
            self.save_transaction, self.cancel_edit
        )):
            widget.grid(
                row=1, column=column,
                padx=(14 if column == 0 else 4, 14 if column == 7 else 4),
                pady=(0, 14), sticky="ew"
            )
        for column in (1, 5):
            self.form_card.grid_columnconfigure(column, weight=1)

        self.save_transaction.apply_theme(self.palette)
        self.cancel_edit.apply_theme(self.palette)
        self.cancel_edit.grid_remove()

        self.occurred_on.insert(0, date.today().strftime("%d/%m/%Y"))
        self._refresh_form_categories()

        # Gráficos
        self.charts = ctk.CTkFrame(self, fg_color="transparent")
        self.charts.pack(fill="both", expand=False, pady=(0, 10))
        self.donut_card = self._card(self.charts)
        self.bar_card = self._card(self.charts)

        ctk.CTkLabel(
            self.donut_card, text=t("financial.chart.donut.title"),
            font=("Segoe UI", 14, "bold"),
            text_color=self.palette["text"]
        ).pack(anchor="w", padx=14, pady=(12, 0))

        bar_head = ctk.CTkFrame(self.bar_card, fg_color="transparent")
        bar_head.pack(fill="x", padx=14, pady=(12, 0))

        self.chart_mode = self._combo(
            bar_head, [t("financial.chart.mode.category"), t("financial.chart.mode.monthly")],
            lambda _: self.refresh(), width=155
        )
        self.chart_mode.set(t("financial.chart.mode.category"))
        self.chart_mode.pack(side="right")

        self.fin_charts = FinancialCharts(self.donut_card, self.bar_card, self.palette)

        # Histórico de transações
        self.history_card = self._card(self)
        self.history_card.pack(fill="both", expand=True)
        ctk.CTkLabel(
            self.history_card, text=t("financial.history.title"),
            font=("Segoe UI", 15, "bold"),
            text_color=self.palette["text"]
        ).pack(anchor="w", padx=14, pady=(12, 6))

        self.history = ctk.CTkScrollableFrame(
            self.history_card, fg_color="transparent", height=240
        )
        self.history.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.apply_layout(1200)

    def _open_category_dialog(self):
        """
        Abre o diálogo de gerenciamento de categorias (singleton).

        Se o diálogo já estiver aberto, apenas dá foco a ele em vez de
        criar uma nova instância.
        """
        if self._category_dialog is not None and self._category_dialog.winfo_exists():
            self._category_dialog.focus()
            return
        self._category_dialog = CategoryDialog(self)
        self._category_dialog.bind(
            "<Destroy>", lambda _: self._clear_category_dialog_ref()
        )

    def _clear_category_dialog_ref(self):
        """Limpa a referência do diálogo quando ele é fechado."""
        self._category_dialog = None

    def _backup_database(self):
        """
        Faz backup dos arquivos criptografados (.enc + .db_key).

        Copia financial.sqlite3.enc e .db_key da pasta do usuário
        para uma pasta escolhida pelo usuário.

        Importante: O arquivo .db_key é essencial para restaurar os dados.
        Sem ele, não é possível descriptografar o banco.
        """
        from tkinter import filedialog
        from pathlib import Path
        import shutil

        db_dir = Path.home() / ".cdb_simulator"
        enc_file = db_dir / "financial.sqlite3.enc"
        key_file = db_dir / ".db_key"

        if not enc_file.exists():
            messagebox.showwarning(
                t("financial.backup.title"),
                t("financial.backup.no_db"),
                parent=self.winfo_toplevel()
            )
            return

        destino = filedialog.askdirectory(
            title=t("financial.backup.select_title"),
            parent=self.winfo_toplevel()
        )
        if not destino:
            return

        try:
            destino_path = Path(destino)
            shutil.copy2(enc_file, destino_path / "financial.sqlite3.enc")
            if key_file.exists():
                shutil.copy2(key_file, destino_path / ".db_key")
            messagebox.showinfo(
                t("financial.backup.title"),
                t("financial.backup.success"),
                parent=self.winfo_toplevel()
            )
        except Exception as exc:
            messagebox.showerror(
                t("financial.backup.error_title"),
                t("financial.backup.error_msg", error=exc),
                parent=self.winfo_toplevel()
            )

    def _restore_database(self):
        """
        Restaura o banco de dados a partir de um backup.

        Copia financial.sqlite3.enc e .db_key de uma pasta escolhida
        de volta para a pasta do usuário.

        Após a restauração, recomenda-se reiniciar a aplicação.
        """
        from tkinter import filedialog
        from pathlib import Path
        import shutil

        db_dir = Path.home() / ".cdb_simulator"
        db_dir.mkdir(parents=True, exist_ok=True)

        origem = filedialog.askdirectory(
            title="Escolha a pasta contendo o backup",
            parent=self.winfo_toplevel()
        )
        if not origem:
            return

        enc_file = Path(origem) / "financial.sqlite3.enc"
        key_file = Path(origem) / ".db_key"

        if not enc_file.exists():
            messagebox.showerror(
                t("financial.restore.error_title"),
                t("financial.restore.no_file"),
                parent=self.winfo_toplevel()
            )
            return

        try:
            shutil.copy2(enc_file, db_dir / "financial.sqlite3.enc")
            if key_file.exists():
                shutil.copy2(key_file, db_dir / ".db_key")
            messagebox.showinfo(
                t("financial.restore.title"),
                t("financial.restore.success"),
                parent=self.winfo_toplevel()
            )
        except Exception as exc:
            messagebox.showerror(
                t("financial.restore.error_title"),
                t("financial.restore.error_msg", error=exc),
                parent=self.winfo_toplevel()
            )

    def _on_period_change(self, value):
        """
        Mostra/esconde campos de data personalizada quando o período muda.

        Se o usuário selecionar "Período personalizado", exibe campos
        de início e fim. Caso contrário, esconde-os.
        """
        if value == t("financial.filter.period.custom"):
            self.custom_start.grid(row=1, column=1, padx=4, pady=(0, 10))
            self.custom_end.grid(row=1, column=2, padx=4, pady=(0, 10))
        else:
            self.custom_start.grid_remove()
            self.custom_end.grid_remove()
        self.refresh()

    def _on_filter_type(self, _):
        """Atualiza categorias do filtro quando o tipo muda."""
        self._refresh_filter_categories()
        self.refresh()

    def _refresh_form_categories(self):
        """Atualiza o combo de categorias do formulário com base no tipo selecionado."""
        kind = TYPE_LABELS[self.transaction_type.get()]
        items = self.service.categories(kind)
        self._form_categories = {item.name: item.id for item in items}
        values = list(self._form_categories) or ["Sem categorias"]
        self.category.configure(values=values)
        self.category.set(values[0])

    def _on_form_type(self, _):
        """Chamado quando o tipo do formulário muda."""
        self._refresh_form_categories()

    def _refresh_filter_categories(self):
        """Atualiza o combo de categorias do filtro com base no tipo selecionado."""
        current = self.filter_category.get()
        selected_type = self.filter_type.get()
        kind = TYPE_LABELS.get(selected_type)
        items = self.service.categories(kind) if kind else self.service.categories()
        self._filter_categories = {"Todas as categorias": None}
        for item in items:
            self._filter_categories[
                f"{item.name} · {item.transaction_type.label}"
            ] = item.id
        values = list(self._filter_categories)
        self.filter_category.configure(values=values)
        self.filter_category.set(
            current if current in self._filter_categories else values[0]
        )

    def _filters(self):
        """
        Constrói dicionário de filtros a partir dos controles da UI.

        Retorna:
            dict: Parâmetros para consulta ao serviço (period, transaction_type,
                  category_id, custom_start, custom_end).
        """
        custom_start = custom_end = None
        if self.period_combo.get() == "Período personalizado":
            custom_start, custom_end = (
                parse_br_date(self.custom_start.get()),
                parse_br_date(self.custom_end.get())
            )
        kind = TYPE_LABELS.get(self.filter_type.get())
        return {
            "period": self.period_combo.get(),
            "transaction_type": kind,
            "category_id": self._filter_categories.get(self.filter_category.get()),
            "custom_start": custom_start,
            "custom_end": custom_end,
        }

    def refresh(self):
        """
        Atualiza toda a interface do dashboard.

        Fluxo:
            1. Atualiza categorias do filtro.
            2. Consulta agregações via SQL (resumo, alocação, despesas por categoria,
               despesas mensais) - mais eficiente que carregar todas as transações.
            3. Carrega transações apenas para o histórico detalhado.
            4. Atualiza cards, gráficos e histórico.

        Se houver erro de validação (ex: data inválida), exibe messagebox e retorna.
        """
        try:
            self._refresh_filter_categories()
            filters = self._filters()

            # Consulta agregações diretamente via SQL (evita carregar todas as
            # transações para o Python - muito mais eficiente)
            summary = self.service.summary_sql(**filters)

            # Métodos de despesa já filtram por EXPENSE internamente,
            # então removemos transaction_type dos filtros para esses métodos
            expense_filters = {k: v for k, v in filters.items() if k != "transaction_type"}
            allocation = self.service.allocation_sql(**expense_filters)
            expense_by_category = self.service.expense_by_category_sql(**expense_filters)
            monthly_expenses = self.service.monthly_expenses_sql(**expense_filters)

            # Carrega transações apenas para o histórico detalhado
            transactions = self.service.transactions(**filters)
        except ValueError as exc:
            messagebox.showerror(t("financial.error.filters_title"), str(exc), parent=self.winfo_toplevel())
            return

        # Atualiza cards de métrica
        values = [
            format_cents(summary.income_cents),
            format_cents(summary.expense_cents),
            format_cents(summary.investment_cents),
            format_cents(summary.available_balance_cents),
            f"{summary.investment_rate:.1f}%".replace(".", ","),
        ]
        for card, value in zip(self.cards, values):
            card.update_value(value)

        # Atualiza gráficos
        self.fin_charts.plot_donut(allocation)
        self.fin_charts.plot_bars(
            expense_by_category, monthly_expenses, self.chart_mode.get()
        )

        # Atualiza histórico
        self._render_history(transactions)

    def _render_history(self, transactions: list[FinancialTransaction]):
        """
        Renderiza a lista de transações no histórico.

        Usa reutilização de widgets: em vez de destruir e recriar todas as
        linhas a cada refresh, verifica se já existem widgets suficientes e
        apenas atualiza seus textos e comandos. Isso é muito mais eficiente
        para listas longas.

        Quando uma transação está em edição (self._editing_transaction_id),
        sua linha é destacada com fundo de acento e texto branco.

        Parâmetros:
            transactions (list[FinancialTransaction]): Transações a exibir.
        """
        # Reutiliza widgets de linha existentes
        existing = getattr(self, "_history_rows", [])
        needed = len(transactions)

        # Cria widgets extras se não houver suficientes
        while len(existing) < needed:
            row = ctk.CTkFrame(
                self.history, fg_color=self.palette["surface_input"],
                corner_radius=10
            )
            row.pack(fill="x", padx=3, pady=3)

            dot = ctk.CTkLabel(row, text="●", font=("Segoe UI", 17))
            dot.pack(side="left", padx=(9, 4))

            info = ctk.CTkLabel(
                row, anchor="w", justify="left",
                text_color=self.palette["text"], font=("Segoe UI", 12)
            )
            info.pack(side="left", fill="x", expand=True, pady=7)

            amount = ctk.CTkLabel(row, font=("Segoe UI", 12, "bold"))
            amount.pack(side="left", padx=8)

            edit_indicator = ctk.CTkLabel(
                row, text="✏️ Editando", font=("Segoe UI", 10),
                text_color=self.palette["accent"]
            )
            edit_indicator.pack(side="right", padx=8)
            edit_indicator.pack_forget()  # começa escondido

            btn_edit = ctk.CTkButton(
                row, text="Editar", width=52, height=27, corner_radius=8,
                fg_color=self.palette["surface_input"],
                hover_color=self.palette["border_input"],
                text_color=self.palette["text"],
            )
            btn_edit.pack(side="left", padx=2)

            btn_del = ctk.CTkButton(
                row, text="×", width=27, height=27, corner_radius=8,
                fg_color="transparent", hover_color="#B94440",
                text_color=self.palette["text_muted"],
            )
            btn_del.pack(side="left", padx=(2, 8))

            existing.append({
                "row": row, "dot": dot, "info": info, "amount": amount,
                "btn_edit": btn_edit, "btn_del": btn_del,
                "edit_indicator": edit_indicator,
            })

        # Oculta sobrantes quando há menos transações que widgets
        for extra in existing[needed:]:
            extra["row"].pack_forget()

        if not transactions:
            if not existing:
                ctk.CTkLabel(
                    self.history,
                    text=t("financial.history.empty"),
                    text_color=self.palette["text_muted"]
                ).pack(pady=22)
            return

        # Atualiza apenas as linhas necessárias
        for index, item in enumerate(existing[:needed]):
            tx = transactions[index]
            is_editing = self._editing_transaction_id == tx.id
            sign = "+" if tx.transaction_type == TransactionType.INCOME else "−"
            amount_color = (
                self.palette["accent"]
                if tx.transaction_type == TransactionType.INCOME
                else self.palette["text"]
            )
            item["row"].pack(fill="x", padx=3, pady=3)

            # Destaque visual na linha que está sendo editada
            if is_editing:
                item["row"].configure(
                    fg_color=self.palette["accent"]  # fundo verde/acento
                )
                item["row"].configure(
                    border_width=2,
                    border_color=self.palette["accent_text"]
                )
                item["edit_indicator"].configure(
                    text="✏️ Editando",
                    text_color=self.palette["accent_text"]
                )
                item["edit_indicator"].pack(side="right", padx=8)
                # Inverte cores do texto para ficar legível sobre fundo escuro
                item["dot"].configure(text_color="#FFFFFF")
                item["info"].configure(
                    text=f"{tx.description}\n{tx.category_name} · "
                         f"{tx.occurred_on.strftime('%d/%m/%Y')}",
                    text_color="#FFFFFF"
                )
                item["amount"].configure(
                    text=f"{sign} {format_cents(tx.amount_cents)}",
                    text_color="#FFFFFF"
                )
                # Botão Editar com cores invertidas no modo edição
                item["btn_edit"].configure(
                    fg_color=self.palette["accent_text"],
                    text_color="#FFFFFF"
                )
            else:
                item["row"].configure(fg_color=self.palette["surface_input"])
                item["row"].configure(border_width=0)
                item["edit_indicator"].pack_forget()
                item["dot"].configure(
                    text_color=tx.category_color or self.palette["text_muted"]
                )
                item["info"].configure(
                    text=f"{tx.description}\n{tx.category_name} · "
                         f"{tx.occurred_on.strftime('%d/%m/%Y')}",
                    text_color=self.palette["text"]
                )
                item["amount"].configure(
                    text=f"{sign} {format_cents(tx.amount_cents)}",
                    text_color=amount_color
                )
                # Botão Editar com cores normais
                item["btn_edit"].configure(
                    fg_color=self.palette["surface_input"],
                    text_color=self.palette["text"]
                )

            item["btn_edit"].configure(
                command=lambda record=tx: self._start_edit(record)
            )
            item["btn_del"].configure(
                command=lambda record=tx: self._delete_transaction(record)
            )

        self._history_rows = existing

    def _save_transaction(self):
        """
        Salva uma nova transação ou atualiza uma existente.

        Valida que uma categoria foi selecionada, chama o serviço apropriado
        (create_transaction ou update_transaction) e atualiza a interface.
        """
        try:
            category_id = self._form_categories.get(self.category.get())
            if not category_id:
                raise ValueError("Crie ou selecione uma categoria para este tipo.")
            data = (
                TYPE_LABELS[self.transaction_type.get()],
                self.description.get(),
                self.amount.get(),
                category_id,
                self.occurred_on.get(),
                self.notes.get()
            )
            if self.editing_id:
                self.service.update_transaction(self.editing_id, *data)
            else:
                self.service.create_transaction(*data)
            self._clear_form()
            self.refresh()
        except ValueError as exc:
            messagebox.showerror(t("financial.error.transaction_title"), str(exc), parent=self.winfo_toplevel())

    def _start_edit(self, item: FinancialTransaction):
        """
        Preenche o formulário com os dados da transação para edição.

        Define self.editing_id e self._editing_transaction_id (para destaque
        visual no histórico), preenche todos os campos e muda o botão para
        "Salvar".

        Parâmetros:
            item (FinancialTransaction): Transação a ser editada.
        """
        self.editing_id = item.id
        self._editing_transaction_id = item.id
        self.transaction_type.set(item.transaction_type.label)
        self._refresh_form_categories()
        for entry, value in (
            (self.description, item.description),
            (
                self.amount,
                f"{item.amount_cents / 100:.2f}".replace(".", ",")
            ),
            (self.occurred_on, item.occurred_on.strftime("%d/%m/%Y")),
            (self.notes, item.notes),
        ):
            entry.delete(0, "end")
            entry.insert(0, value)
        self.category.set(item.category_name)
        self.save_transaction.configure(text="Salvar")
        self.cancel_edit.grid()
        self.form_card.focus_set()
        self.refresh()  # Re-renderiza o histórico para mostrar o destaque

    def _clear_form(self):
        """
        Limpa o formulário de transação e cancela a edição.

        Reseta editing_id, limpa campos de texto, define data como hoje,
        esconde o botão Cancelar e re-renderiza o histórico para remover
        o destaque de edição.
        """
        self.editing_id = None
        self._editing_transaction_id = None
        for entry in (self.description, self.amount, self.notes):
            entry.delete(0, "end")
        self.occurred_on.delete(0, "end")
        self.occurred_on.insert(0, date.today().strftime("%d/%m/%Y"))
        self._refresh_form_categories()
        self.save_transaction.configure(text=t("financial.form.add"))
        self.cancel_edit.grid_remove()
        self.refresh()

    def _delete_transaction(self, item):
        """
        Exclui uma transação após confirmação do usuário.

        Exibe uma caixa de diálogo de confirmação antes de excluir.

        Parâmetros:
            item (FinancialTransaction): Transação a ser excluída.
        """
        if messagebox.askyesno(
            t("financial.transaction.delete_confirm_title"),
            t("financial.transaction.delete_confirm_msg", description=item.description),
            parent=self.winfo_toplevel()
        ):
            try:
                self.service.delete_transaction(item.id)
                self.refresh()
            except ValueError as exc:
                messagebox.showerror(
                    t("financial.error.transaction_title"), str(exc), parent=self.winfo_toplevel()
                )

    def apply_layout(self, width: int):
        """
        Aplica layout responsivo aos cards de métrica e gráficos.

        Mobile (< 860px): cards em 2 colunas, gráficos empilhados verticalmente.
        Desktop (>= 860px): cards em 5 colunas, gráficos lado a lado.

        Parâmetros:
            width (int): Largura da janela em pixels.
        """
        cols = 2 if width < 860 else 5
        for card in self.cards:
            card.grid_forget()
        for index, card in enumerate(self.cards):
            if cols == 2 and index == 4:
                card.grid(
                    row=2, column=0, columnspan=2,
                    padx=4, pady=3, sticky="nsew"
                )
            else:
                card.grid(
                    row=index // cols, column=index % cols,
                    padx=4, pady=3, sticky="nsew"
                )
        for col in range(5):
            self.metrics.grid_columnconfigure(
                col, weight=1 if col < cols else 0
            )

        self.donut_card.grid_forget()
        self.bar_card.grid_forget()
        if width < 860:
            self.charts.grid_columnconfigure(0, weight=1)
            self.donut_card.grid(
                row=0, column=0, sticky="nsew", pady=(0, 8)
            )
            self.bar_card.grid(
                row=1, column=0, sticky="nsew"
            )
        else:
            self.charts.grid_columnconfigure(0, weight=1)
            self.charts.grid_columnconfigure(1, weight=1)
            self.donut_card.grid(
                row=0, column=0, sticky="nsew", padx=(0, 5)
            )
            self.bar_card.grid(
                row=0, column=1, sticky="nsew", padx=(5, 0)
            )

    def apply_theme(self, palette: dict):
        """
        Reaplica as cores do tema em todos os widgets do dashboard.

        Parâmetros:
            palette (dict): Dicionário de cores da paleta selecionada.
        """
        self.palette = palette
        self.configure(fg_color="transparent")
        for card in self.cards:
            card.apply_theme(palette)
        for frame in (
            self.filter_card, self.form_card,
            self.donut_card, self.bar_card, self.history_card
        ):
            frame.configure(
                fg_color=palette["surface"],
                border_color=palette["border"]
            )
        self._apply_widget_theme(self)
        self.manage_button.apply_theme(palette)
        self.filter_button.apply_theme(palette)
        self.save_transaction.apply_theme(palette)
        self.cancel_edit.apply_theme(palette)
        self.fin_charts.apply_theme(palette)
        self.refresh()

    def _apply_widget_theme(self, parent):
        """
        Propaga cores do tema para controles simples (Entry, ComboBox, Label, Frame).

        Percorre recursivamente todos os widgets filhos e aplica as cores
        da paleta atual, sem recriar os widgets.

        Parâmetros:
            parent: Widget pai cujos filhos serão estilizados.
        """
        for widget in parent.winfo_children():
            if isinstance(widget, ctk.CTkEntry):
                widget.configure(
                    fg_color=self.palette["surface_input"],
                    border_color=self.palette["border_input"],
                    text_color=self.palette["text"],
                    placeholder_text_color=self.palette["text_muted"]
                )
            elif isinstance(widget, ctk.CTkComboBox):
                widget.configure(
                    fg_color=self.palette["surface_input"],
                    border_color=self.palette["border_input"],
                    button_color=self.palette["surface_input"],
                    button_hover_color=self.palette["border_input"],
                    text_color=self.palette["text"],
                    dropdown_fg_color=self.palette["surface"],
                    dropdown_text_color=self.palette["text"]
                )
            elif isinstance(widget, ctk.CTkLabel):
                widget.configure(text_color=self.palette["text"])
            elif isinstance(widget, ctk.CTkFrame) and widget not in self.cards:
                if widget.cget("fg_color") != "transparent":
                    try:
                        widget.configure(fg_color=self.palette["surface"])
                    except Exception:
                        pass
            self._apply_widget_theme(widget)