"""Tela completa e responsiva do Controle Financeiro."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from src.domain.financial_models import FinancialTransaction, TransactionType
from src.services.financial_service import FinancialService, format_cents, parse_br_date
from src.ui.gui.components import MetricCard, PillButton
from src.ui.gui.financial.financial_charts import FinancialCharts


TYPE_LABELS = {"Receita": TransactionType.INCOME, "Despesa": TransactionType.EXPENSE, "Investimento": TransactionType.INVESTMENT}
TYPE_BY_VALUE = {item.value: label for label, item in TYPE_LABELS.items()}
PERIODS = ["Mês atual", "Mês anterior", "Últimos 3 meses", "Últimos 6 meses", "Últimos 12 meses", "Todo o período", "Período personalizado"]

# Cores pré-definidas para categorias (nome amigável -> código hex)
CATEGORY_COLORS = [
    ("Verde", "#24C270"),
    ("Azul", "#4F8CFF"),
    ("Laranja", "#FF9F43"),
    ("Vermelho", "#FF6B6B"),
    ("Roxo", "#A970FF"),
    ("Ciano", "#32B8C6"),
    ("Rosa", "#F368E0"),
    ("Cinza", "#8395A7"),
    ("Amarelo", "#F9CA24"),
    ("Azul Escuro", "#1C1C1E"),
    ("Verde Escuro", "#107C41"),
    ("Laranja Escuro", "#D9534F"),
]


class CategoryDialog(ctk.CTkToplevel):
    def __init__(self, dashboard: "FinancialDashboard"):
        super().__init__(dashboard.winfo_toplevel())
        self.dashboard, self.service, self.palette = dashboard, dashboard.service, dashboard.palette
        self.edit_id = None
        self.title("Gerenciar categorias")
        self.geometry("580x620"); self.minsize(440, 480)
        self.configure(fg_color=self.palette["bg_root"])
        self.transient(dashboard.winfo_toplevel()); self.grab_set()
        self._build()

    def _input(self, master, placeholder=""):
        return ctk.CTkEntry(master, placeholder_text=placeholder, height=36, corner_radius=10,
            fg_color=self.palette["surface_input"], border_color=self.palette["border_input"], text_color=self.palette["text"])

    def _build(self):
        header = ctk.CTkLabel(self, text="Categorias", font=("Segoe UI", 18, "bold"), text_color=self.palette["text"])
        header.pack(anchor="w", padx=18, pady=(18, 8))
        form = ctk.CTkFrame(self, fg_color=self.palette["surface"], corner_radius=14, border_width=1, border_color=self.palette["border"])
        form.pack(fill="x", padx=18, pady=(0, 10))
        self.name_entry = self._input(form, "Nome da categoria")
        self.type_combo = ctk.CTkComboBox(form, values=list(TYPE_LABELS), height=36, corner_radius=10, command=lambda _: None)
        self.color_combo = ctk.CTkComboBox(form, values=[name for name, _ in CATEGORY_COLORS], height=36, corner_radius=10, command=lambda _: None)
        self.color_combo.set(CATEGORY_COLORS[0][0])
        self.name_entry.grid(row=0, column=0, sticky="ew", padx=12, pady=12); self.type_combo.grid(row=0, column=1, padx=5, pady=12)
        self.color_combo.grid(row=0, column=2, padx=5, pady=12); form.grid_columnconfigure(0, weight=1)
        self.type_combo.set("Despesa")
        self.save_button = PillButton(form, text="Adicionar", command=self._save, variant="primary", width=110)
        self.save_button.grid(row=0, column=3, padx=(5, 12), pady=12); self.save_button.apply_theme(self.palette)
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        self._style_combo(self.type_combo); self._style_combo(self.color_combo); self._render_list()

    def _style_combo(self, combo):
        combo.configure(fg_color=self.palette["surface_input"], border_color=self.palette["border_input"], button_color=self.palette["surface_input"], button_hover_color=self.palette["border_input"], text_color=self.palette["text"], dropdown_fg_color=self.palette["surface"], dropdown_text_color=self.palette["text"])

    def _render_list(self):
        for child in self.list_frame.winfo_children(): child.destroy()
        for category in self.service.categories(active_only=False):
            state = "" if category.active else " · arquivada"
            row = ctk.CTkFrame(self.list_frame, fg_color=self.palette["surface"], corner_radius=10, border_width=1, border_color=self.palette["border"])
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text="●", text_color=category.color, font=("Segoe UI", 18)).pack(side="left", padx=(10, 4))
            ctk.CTkLabel(row, text=f"{category.name}{state}\n{category.transaction_type.label}", justify="left", anchor="w", text_color=self.palette["text"], font=("Segoe UI", 12)).pack(side="left", fill="x", expand=True, pady=7)
            ctk.CTkButton(row, text="Editar", width=54, height=28, corner_radius=9, fg_color=self.palette["surface_input"], hover_color=self.palette["border_input"], text_color=self.palette["text"], command=lambda item=category: self._edit(item)).pack(side="right", padx=3)
            ctk.CTkButton(row, text="Remover", width=72, height=28, corner_radius=9, fg_color="#D9534F", hover_color="#B94440", command=lambda item=category: self._delete(item)).pack(side="right", padx=(3, 9))

    def _edit(self, category):
        self.edit_id = category.id; self.name_entry.delete(0, "end"); self.name_entry.insert(0, category.name)
        self.type_combo.set(category.transaction_type.label)
        # Seleciona a cor correspondente no combobox
        for name, hex_color in CATEGORY_COLORS:
            if hex_color == category.color:
                self.color_combo.set(name)
                break
        self.save_button.configure(text="Salvar")

    def _save(self):
        try:
            # Mapeia o nome da cor selecionada de volta para o código hex
            selected_color_name = self.color_combo.get()
            selected_color_hex = next((hex_color for name, hex_color in CATEGORY_COLORS if name == selected_color_name), CATEGORY_COLORS[0][1])

            if self.edit_id:
                self.service.update_category(self.edit_id, self.name_entry.get(), TYPE_LABELS[self.type_combo.get()], selected_color_hex)
            else:
                self.service.create_category(self.name_entry.get(), TYPE_LABELS[self.type_combo.get()], selected_color_hex)
            self.edit_id = None; self.name_entry.delete(0, "end"); self.color_combo.set(CATEGORY_COLORS[0][0])
            self.save_button.configure(text="Adicionar"); self._render_list(); self.dashboard.refresh()
        except ValueError as exc: messagebox.showerror("Categoria", str(exc), parent=self)

    def _delete(self, category):
        if not messagebox.askyesno("Remover categoria", f"Remover '{category.name}'?\nSe ela possuir lançamentos, será arquivada para preservar o histórico.", parent=self): return
        try:
            result = self.service.delete_or_archive_category(category.id)
            if result == "archived": messagebox.showinfo("Categoria arquivada", "A categoria possui lançamentos e foi arquivada com segurança.", parent=self)
            self._render_list(); self.dashboard.refresh()
        except ValueError as exc: messagebox.showerror("Categoria", str(exc), parent=self)


class FinancialDashboard(ctk.CTkFrame):
    def __init__(self, master, service: FinancialService, palette: dict):
        super().__init__(master, fg_color="transparent")
        self.service, self.palette = service, palette
        self.editing_id: int | None = None
        self._form_categories = {}; self._filter_categories = {"Todas as categorias": None}
        self._build(); self.refresh()

    def _entry(self, master, placeholder="", **kwargs):
        return ctk.CTkEntry(master, placeholder_text=placeholder, height=38, corner_radius=10,
            fg_color=self.palette["surface_input"], border_color=self.palette["border_input"], text_color=self.palette["text"], **kwargs)

    def _combo(self, master, values, command=None, width=None):
        kwargs = {"values": values, "height": 38, "corner_radius": 10, "command": command,
            "fg_color": self.palette["surface_input"], "border_color": self.palette["border_input"], "button_color": self.palette["surface_input"], "button_hover_color": self.palette["border_input"], "text_color": self.palette["text"], "dropdown_fg_color": self.palette["surface"], "dropdown_text_color": self.palette["text"]}
        if width: kwargs["width"] = width
        return ctk.CTkComboBox(master, **kwargs)

    def _card(self, master):
        return ctk.CTkFrame(master, fg_color=self.palette["surface"], corner_radius=16, border_width=1, border_color=self.palette["border"])

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent"); top.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(top, text="Controle Financeiro", font=("Segoe UI", 21, "bold"), text_color=self.palette["text"]).pack(side="left")

        botoes = ctk.CTkFrame(top, fg_color="transparent")
        botoes.pack(side="right")

        self.backup_button = PillButton(botoes, text="Backup", command=self._backup_database, variant="secondary", width=100)
        self.backup_button.pack(side="left", padx=(0, 6)); self.backup_button.apply_theme(self.palette)

        self.restore_button = PillButton(botoes, text="Restaurar", command=self._restore_database, variant="secondary", width=110)
        self.restore_button.pack(side="left", padx=(0, 6)); self.restore_button.apply_theme(self.palette)

        self.manage_button = PillButton(top, text="Gerenciar categorias", command=lambda: CategoryDialog(self), variant="secondary", width=185)
        self.manage_button.pack(side="right"); self.manage_button.apply_theme(self.palette)
        ctk.CTkLabel(self, text="Acompanhe receitas, despesas e aportes em um só lugar.", font=("Segoe UI", 12), text_color=self.palette["text_muted"]).pack(anchor="w", pady=(0, 12))

        filters = self._card(self); self.filter_card = filters; filters.pack(fill="x", pady=(0, 10)); filters.grid_columnconfigure(4, weight=1)
        ctk.CTkLabel(filters, text="PERÍODO", font=("Segoe UI", 10, "bold"), text_color=self.palette["text_muted"]).grid(row=0, column=0, padx=(12, 4), pady=10)
        self.period_combo = self._combo(filters, PERIODS, self._on_period_change, width=165); self.period_combo.set("Mês atual"); self.period_combo.grid(row=0, column=1, padx=4, pady=10)
        self.custom_start = self._entry(filters, "Início DD/MM/AAAA", width=135); self.custom_end = self._entry(filters, "Fim DD/MM/AAAA", width=135)
        ctk.CTkLabel(filters, text="TIPO", font=("Segoe UI", 10, "bold"), text_color=self.palette["text_muted"]).grid(row=0, column=2, padx=(12, 4), pady=10)
        self.filter_type = self._combo(filters, ["Todos", *TYPE_LABELS], self._on_filter_type, width=130); self.filter_type.set("Todos"); self.filter_type.grid(row=0, column=3, padx=4, pady=10)
        self.filter_category = self._combo(filters, ["Todas as categorias"], lambda _: self.refresh(), width=180); self.filter_category.set("Todas as categorias"); self.filter_category.grid(row=0, column=4, padx=4, pady=10, sticky="w")
        self.filter_button = PillButton(filters, text="Aplicar", command=self.refresh, variant="secondary", width=78); self.filter_button.grid(row=0, column=5, padx=(4, 12), pady=10); self.filter_button.apply_theme(self.palette)

        self.metrics = ctk.CTkFrame(self, fg_color="transparent"); self.metrics.pack(fill="x", pady=(0, 10))
        self.cards = [MetricCard(self.metrics, "Receitas", "R$ 0,00"), MetricCard(self.metrics, "Despesas", "R$ 0,00"), MetricCard(self.metrics, "Investimentos", "R$ 0,00"), MetricCard(self.metrics, "Saldo disponível", "R$ 0,00", is_highlight=True), MetricCard(self.metrics, "Taxa investida", "0,0%")]

        self.form_card = self._card(self); self.form_card.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(self.form_card, text="Novo lançamento", font=("Segoe UI", 15, "bold"), text_color=self.palette["text"]).grid(row=0, column=0, columnspan=6, sticky="w", padx=14, pady=(12, 8))
        self.transaction_type = self._combo(self.form_card, list(TYPE_LABELS), self._on_form_type, width=130); self.transaction_type.set("Despesa")
        self.description = self._entry(self.form_card, "Descrição"); self.amount = self._entry(self.form_card, "Valor (R$)", width=125)
        self.category = self._combo(self.form_card, [""], None, width=160); self.occurred_on = self._entry(self.form_card, "DD/MM/AAAA", width=118); self.notes = self._entry(self.form_card, "Observação (opcional)")
        self.save_transaction = PillButton(self.form_card, text="Adicionar", command=self._save_transaction, variant="primary", width=110); self.cancel_edit = PillButton(self.form_card, text="Cancelar", command=self._clear_form, variant="secondary", width=90)
        for column, widget in enumerate((self.transaction_type, self.description, self.amount, self.category, self.occurred_on, self.notes, self.save_transaction, self.cancel_edit)):
            widget.grid(row=1, column=column, padx=(14 if column == 0 else 4, 14 if column == 7 else 4), pady=(0, 14), sticky="ew")
        for column in (1, 5): self.form_card.grid_columnconfigure(column, weight=1)
        self.save_transaction.apply_theme(self.palette); self.cancel_edit.apply_theme(self.palette); self.cancel_edit.grid_remove()
        self.occurred_on.insert(0, date.today().strftime("%d/%m/%Y")); self._refresh_form_categories()

        self.charts = ctk.CTkFrame(self, fg_color="transparent"); self.charts.pack(fill="both", expand=False, pady=(0, 10))
        self.donut_card = self._card(self.charts); self.bar_card = self._card(self.charts)
        ctk.CTkLabel(self.donut_card, text="Destino do dinheiro", font=("Segoe UI", 14, "bold"), text_color=self.palette["text"]).pack(anchor="w", padx=14, pady=(12, 0))
        bar_head = ctk.CTkFrame(self.bar_card, fg_color="transparent"); bar_head.pack(fill="x", padx=14, pady=(12, 0))
        self.chart_mode = self._combo(bar_head, ["Por categoria", "Evolução mensal"], lambda _: self.refresh(), width=155); self.chart_mode.set("Por categoria"); self.chart_mode.pack(side="right")
        self.fin_charts = FinancialCharts(self.donut_card, self.bar_card, self.palette)

        self.history_card = self._card(self); self.history_card.pack(fill="both", expand=True)
        ctk.CTkLabel(self.history_card, text="Histórico de movimentações", font=("Segoe UI", 15, "bold"), text_color=self.palette["text"]).pack(anchor="w", padx=14, pady=(12, 6))
        self.history = ctk.CTkScrollableFrame(self.history_card, fg_color="transparent", height=240); self.history.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.apply_layout(1200)

    def _backup_database(self):
        """Copia os arquivos criptografados (.enc + .db_key) para uma pasta escolhida pelo usuário."""
        from tkinter import filedialog
        from pathlib import Path
        import shutil

        db_dir = Path.home() / ".cdb_simulator"
        enc_file = db_dir / "financial.sqlite3.enc"
        key_file = db_dir / ".db_key"

        if not enc_file.exists():
            messagebox.showwarning("Backup", "Nenhum banco de dados criptografado encontrado para fazer backup.", parent=self.winfo_toplevel())
            return

        destino = filedialog.askdirectory(title="Escolha a pasta para salvar o backup", parent=self.winfo_toplevel())
        if not destino:
            return

        try:
            destino_path = Path(destino)
            shutil.copy2(enc_file, destino_path / "financial.sqlite3.enc")
            if key_file.exists():
                shutil.copy2(key_file, destino_path / ".db_key")
            messagebox.showinfo("Backup", "Backup concluído com sucesso!\n\nArquivos salvos:\n- financial.sqlite3.enc\n- .db_key\n\nGuarde o arquivo .db_key em local seguro: sem ele, não é possível restaurar os dados.", parent=self.winfo_toplevel())
        except Exception as exc:
            messagebox.showerror("Erro no Backup", f"Não foi possível fazer o backup: {exc}", parent=self.winfo_toplevel())

    def _restore_database(self):
        """Restaura os arquivos criptografados (.enc + .db_key) de uma pasta escolhida pelo usuário."""
        from tkinter import filedialog
        from pathlib import Path
        import shutil

        db_dir = Path.home() / ".cdb_simulator"
        db_dir.mkdir(parents=True, exist_ok=True)

        origem = filedialog.askdirectory(title="Escolha a pasta contendo o backup", parent=self.winfo_toplevel())
        if not origem:
            return

        enc_file = Path(origem) / "financial.sqlite3.enc"
        key_file = Path(origem) / ".db_key"

        if not enc_file.exists():
            messagebox.showerror("Erro na Restauração", "Arquivo financial.sqlite3.enc não encontrado na pasta selecionada.", parent=self.winfo_toplevel())
            return

        try:
            shutil.copy2(enc_file, db_dir / "financial.sqlite3.enc")
            if key_file.exists():
                shutil.copy2(key_file, db_dir / ".db_key")
            messagebox.showinfo("Restauração", "Banco de dados restaurado com sucesso!\n\nReinicie a aplicação para aplicar as alterações.", parent=self.winfo_toplevel())
        except Exception as exc:
            messagebox.showerror("Erro na Restauração", f"Não foi possível restaurar o backup: {exc}", parent=self.winfo_toplevel())

    def _on_period_change(self, value):
        if value == "Período personalizado":
            self.custom_start.grid(row=1, column=1, padx=4, pady=(0, 10)); self.custom_end.grid(row=1, column=2, padx=4, pady=(0, 10))
        else:
            self.custom_start.grid_remove(); self.custom_end.grid_remove()
        self.refresh()

    def _on_filter_type(self, _): self._refresh_filter_categories(); self.refresh()

    def _refresh_form_categories(self):
        kind = TYPE_LABELS[self.transaction_type.get()]
        items = self.service.categories(kind); self._form_categories = {item.name: item.id for item in items}
        values = list(self._form_categories) or ["Sem categorias"]
        self.category.configure(values=values); self.category.set(values[0])

    def _on_form_type(self, _): self._refresh_form_categories()

    def _refresh_filter_categories(self):
        current = self.filter_category.get(); selected_type = self.filter_type.get()
        kind = TYPE_LABELS.get(selected_type)
        items = self.service.categories(kind) if kind else self.service.categories()
        self._filter_categories = {"Todas as categorias": None}
        for item in items: self._filter_categories[f"{item.name} · {item.transaction_type.label}"] = item.id
        values = list(self._filter_categories); self.filter_category.configure(values=values)
        self.filter_category.set(current if current in self._filter_categories else values[0])

    def _filters(self):
        custom_start = custom_end = None
        if self.period_combo.get() == "Período personalizado":
            custom_start, custom_end = parse_br_date(self.custom_start.get()), parse_br_date(self.custom_end.get())
        kind = TYPE_LABELS.get(self.filter_type.get())
        return {"period": self.period_combo.get(), "transaction_type": kind, "category_id": self._filter_categories.get(self.filter_category.get()), "custom_start": custom_start, "custom_end": custom_end}

    def refresh(self):
        try:
            self._refresh_filter_categories()
            transactions = self.service.transactions(**self._filters())
        except ValueError as exc:
            messagebox.showerror("Filtros", str(exc), parent=self.winfo_toplevel()); return
        summary = self.service.summary_for(transactions)
        values = [format_cents(summary.income_cents), format_cents(summary.expense_cents), format_cents(summary.investment_cents), format_cents(summary.available_balance_cents), f"{summary.investment_rate:.1f}%".replace(".", ",")]
        for card, value in zip(self.cards, values): card.update_value(value)
        self.fin_charts.plot_donut(self.service.allocation(transactions))
        self.fin_charts.plot_bars(self.service.expense_by_category(transactions), self.service.monthly_expenses(transactions), self.chart_mode.get())
        self._render_history(transactions)

    def _render_history(self, transactions: list[FinancialTransaction]):
        for child in self.history.winfo_children(): child.destroy()
        if not transactions:
            ctk.CTkLabel(self.history, text="Nenhuma movimentação encontrada neste período.", text_color=self.palette["text_muted"]).pack(pady=22)
            return
        for item in transactions:
            row = ctk.CTkFrame(self.history, fg_color=self.palette["surface_input"], corner_radius=10)
            row.pack(fill="x", padx=3, pady=3)
            sign = "+" if item.transaction_type == TransactionType.INCOME else "−"
            amount_color = self.palette["accent"] if item.transaction_type == TransactionType.INCOME else self.palette["text"]
            ctk.CTkLabel(row, text="●", text_color=item.category_color or self.palette["text_muted"], font=("Segoe UI", 17)).pack(side="left", padx=(9, 4))
            ctk.CTkLabel(row, text=f"{item.description}\n{item.category_name} · {item.occurred_on.strftime('%d/%m/%Y')}", anchor="w", justify="left", text_color=self.palette["text"], font=("Segoe UI", 12)).pack(side="left", fill="x", expand=True, pady=7)
            ctk.CTkLabel(row, text=f"{sign} {format_cents(item.amount_cents)}", text_color=amount_color, font=("Segoe UI", 12, "bold")).pack(side="left", padx=8)
            ctk.CTkButton(row, text="Editar", width=52, height=27, corner_radius=8, fg_color="transparent", hover_color=self.palette["border_input"], text_color=self.palette["text"], command=lambda record=item: self._start_edit(record)).pack(side="left", padx=2)
            ctk.CTkButton(row, text="×", width=27, height=27, corner_radius=8, fg_color="transparent", hover_color="#B94440", text_color=self.palette["text_muted"], command=lambda record=item: self._delete_transaction(record)).pack(side="left", padx=(2, 8))

    def _save_transaction(self):
        try:
            category_id = self._form_categories.get(self.category.get())
            if not category_id: raise ValueError("Crie ou selecione uma categoria para este tipo.")
            data = (TYPE_LABELS[self.transaction_type.get()], self.description.get(), self.amount.get(), category_id, self.occurred_on.get(), self.notes.get())
            if self.editing_id: self.service.update_transaction(self.editing_id, *data)
            else: self.service.create_transaction(*data)
            self._clear_form(); self.refresh()
        except ValueError as exc: messagebox.showerror("Lançamento", str(exc), parent=self.winfo_toplevel())

    def _start_edit(self, item: FinancialTransaction):
        self.editing_id = item.id; self.transaction_type.set(item.transaction_type.label); self._refresh_form_categories()
        for entry, value in ((self.description, item.description), (self.amount, f"{item.amount_cents / 100:.2f}".replace(".", ",")), (self.occurred_on, item.occurred_on.strftime("%d/%m/%Y")), (self.notes, item.notes)):
            entry.delete(0, "end"); entry.insert(0, value)
        self.category.set(item.category_name); self.save_transaction.configure(text="Salvar"); self.cancel_edit.grid(); self.form_card.focus_set()

    def _clear_form(self):
        self.editing_id = None
        for entry in (self.description, self.amount, self.notes): entry.delete(0, "end")
        self.occurred_on.delete(0, "end"); self.occurred_on.insert(0, date.today().strftime("%d/%m/%Y"))
        self._refresh_form_categories(); self.save_transaction.configure(text="Adicionar"); self.cancel_edit.grid_remove()

    def _delete_transaction(self, item):
        if messagebox.askyesno("Excluir lançamento", f"Excluir '{item.description}'? Esta ação não pode ser desfeita.", parent=self.winfo_toplevel()):
            try: self.service.delete_transaction(item.id); self.refresh()
            except ValueError as exc: messagebox.showerror("Lançamento", str(exc), parent=self.winfo_toplevel())

    def apply_layout(self, width: int):
        cols = 2 if width < 860 else 5
        for card in self.cards: card.grid_forget()
        for index, card in enumerate(self.cards):
            if cols == 2 and index == 4: card.grid(row=2, column=0, columnspan=2, padx=4, pady=3, sticky="nsew")
            else: card.grid(row=index // cols, column=index % cols, padx=4, pady=3, sticky="nsew")
        for col in range(5): self.metrics.grid_columnconfigure(col, weight=1 if col < cols else 0)
        self.donut_card.grid_forget(); self.bar_card.grid_forget()
        if width < 860:
            self.charts.grid_columnconfigure(0, weight=1); self.donut_card.grid(row=0, column=0, sticky="nsew", pady=(0, 8)); self.bar_card.grid(row=1, column=0, sticky="nsew")
        else:
            self.charts.grid_columnconfigure(0, weight=1); self.charts.grid_columnconfigure(1, weight=1); self.donut_card.grid(row=0, column=0, sticky="nsew", padx=(0, 5)); self.bar_card.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

    def apply_theme(self, palette: dict):
        self.palette = palette; self.configure(fg_color="transparent")
        for card in self.cards: card.apply_theme(palette)
        for frame in (self.filter_card, self.form_card, self.donut_card, self.bar_card, self.history_card): frame.configure(fg_color=palette["surface"], border_color=palette["border"])
        self._apply_widget_theme(self)
        self.manage_button.apply_theme(palette); self.filter_button.apply_theme(palette); self.save_transaction.apply_theme(palette); self.cancel_edit.apply_theme(palette)
        self.fin_charts.apply_theme(palette); self.refresh()

    def _apply_widget_theme(self, parent):
        """Propaga cores para os controles simples sem recriar widgets."""
        for widget in parent.winfo_children():
            if isinstance(widget, ctk.CTkEntry):
                widget.configure(fg_color=self.palette["surface_input"], border_color=self.palette["border_input"], text_color=self.palette["text"], placeholder_text_color=self.palette["text_muted"])
            elif isinstance(widget, ctk.CTkComboBox):
                widget.configure(fg_color=self.palette["surface_input"], border_color=self.palette["border_input"], button_color=self.palette["surface_input"], button_hover_color=self.palette["border_input"], text_color=self.palette["text"], dropdown_fg_color=self.palette["surface"], dropdown_text_color=self.palette["text"])
            elif isinstance(widget, ctk.CTkLabel):
                widget.configure(text_color=self.palette["text"])
            elif isinstance(widget, ctk.CTkFrame) and widget not in self.cards:
                # Frames transparentes permanecem transparentes; superfícies recebem a paleta.
                if widget.cget("fg_color") != "transparent":
                    try: widget.configure(fg_color=self.palette["surface"])
                    except Exception: pass
            self._apply_widget_theme(widget)
