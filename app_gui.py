"""
==============================================================================
SIMULADOR DE INVESTIMENTOS / CDB COM INTERFACE GRÁFICA MODERNA
==============================================================================
Este script utiliza 'customtkinter' para fornecer um visual moderno (dark/light),
com suporte a gráficos dinâmicos incorporados via 'matplotlib'.

Para compilar para executável com o PyInstaller posteriormente:
    pyinstaller --noconsole --onefile app_gui.py
"""

import math
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import messagebox

# ==============================================================================
# CONFIGURAÇÃO VISUAL GLOBAL
# ==============================================================================
# Modos disponíveis: "System" (padrão do SO), "Dark" (escuro) ou "Light" (claro)
ctk.set_appearance_mode("Dark")

# Temas de cores disponíveis: "blue" (padrão), "green", "dark-blue"
ctk.set_default_color_theme("blue")


# ==============================================================================
# FUNÇÕES DE CÁLCULO E LÓGICA FINANCEIRA
# ==============================================================================

def calcular_tempo_ate_meta(inicial: float, aporte_mensal: float, taxa_mensal: float, meta: float = 1_000_000.0):
    """
    Calcula quantos meses levaria para atingir a meta estipulada.
    Retorna o número de meses (int) ou None se for inatingível.
    """
    if inicial >= meta:
        return 0

    r = taxa_mensal / 100.0

    # Sem rendimento e sem aportes
    if r == 0 and aporte_mensal == 0:
        return None

    # Sem juros: apenas acumulação linear de aportes
    if r == 0:
        return math.ceil((meta - inicial) / aporte_mensal)

    # Simulação iterativa mês a mês
    saldo = inicial
    meses_necessarios = 0
    limite_meses = 1200  # Máximo de 100 anos para evitar loops infinitos

    while saldo < meta and meses_necessarios < limite_meses:
        saldo += aporte_mensal
        saldo += saldo * r
        meses_necessarios += 1

    if saldo >= meta:
        return meses_necessarios
    return None


def formatar_tempo(meses):
    """Formata meses em texto legível com anos e meses."""
    if meses is None:
        return "Superior a 100 anos"
    if meses == 0:
        return "Já atingido com o valor inicial!"
    
    anos = meses // 12
    meses_restantes = meses % 12
    partes = []
    if anos > 0:
        partes.append(f"{anos} {'ano' if anos == 1 else 'anos'}")
    if meses_restantes > 0:
        partes.append(f"{meses_restantes} {'mês' if meses_restantes == 1 else 'meses'}")

    return f"{meses} meses ({', '.join(partes)})"


def formatar_moeda(valor: float) -> str:
    """Formata um número float no padrão de moeda brasileira (R$ 1.234,56)."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ==============================================================================
# CLASSE PRINCIPAL DA INTERFACE GRÁFICA (APP)
# ==============================================================================

class AppSimulador(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Configurações da Janela Principal ---
        self.title("Simulador de CDB & Juros Compostos")
        self.geometry("1100x720")
        self.minsize(980, 650)

        # Matplotlib Canvas referência
        self.canvas = None
        self.tema_escuro = True  # Começa no modo escuro

        # --- Grid Layout (3 linhas: cabeçalho, formulário e resultados) ---
        self.grid_columnconfigure(0, weight=0, minsize=380)  # Barra lateral fixa
        self.grid_columnconfigure(1, weight=1)               # Área de resultados expansível
        self.grid_rowconfigure(0, weight=0)                  # Cabeçalho com título e botão de tema
        self.grid_rowconfigure(1, weight=1)                  # Conteúdo principal

        self._criar_header()
        self._criar_painel_formulario()
        self._criar_painel_resultados()

        # Executa uma simulação inicial com valores padrão
        self.executar_calculo()

    # --------------------------------------------------------------------------
    # PAINEL DA ESQUERDA: ENTRADAS DE DADOS
    # --------------------------------------------------------------------------
    def _criar_painel_formulario(self):
        # Frame do formulário lateral
        self.frame_form = ctk.CTkScrollableFrame(self, label_text="Parâmetros da Simulação", label_font=("Segoe UI", 16, "bold"))
        self.frame_form.grid(row=1, column=0, padx=15, pady=15, sticky="nsew")

        # 1. Valor Inicial
        self.lbl_inicial = ctk.CTkLabel(self.frame_form, text="Valor Inicial Guardado (R$):", anchor="w")
        self.lbl_inicial.pack(fill="x", padx=10, pady=(10, 2))
        self.entry_inicial = ctk.CTkEntry(self.frame_form, placeholder_text="Ex: 5000.00")
        self.entry_inicial.insert(0, "5000")
        self.entry_inicial.pack(fill="x", padx=10, pady=(0, 10))

        # 2. Aporte Mensal
        self.lbl_mensal = ctk.CTkLabel(self.frame_form, text="Aporte Mensal (R$):", anchor="w")
        self.lbl_mensal.pack(fill="x", padx=10, pady=(5, 2))
        self.entry_mensal = ctk.CTkEntry(self.frame_form, placeholder_text="Ex: 500.00")
        self.entry_mensal.insert(0, "500")
        self.entry_mensal.pack(fill="x", padx=10, pady=(0, 10))

        # 3. Taxa de Juros e Tipo (Ao mês ou Ao ano)
        self.lbl_taxa = ctk.CTkLabel(self.frame_form, text="Taxa de Rendimento (%):", anchor="w")
        self.lbl_taxa.pack(fill="x", padx=10, pady=(5, 2))
        
        self.frame_taxa = ctk.CTkFrame(self.frame_form, fg_color="transparent")
        self.frame_taxa.pack(fill="x", padx=10, pady=(0, 10))

        self.entry_taxa = ctk.CTkEntry(self.frame_taxa, placeholder_text="Ex: 12.0")
        self.entry_taxa.insert(0, "12.0")
        self.entry_taxa.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.combo_periodo_taxa = ctk.CTkComboBox(self.frame_taxa, values=["% ao ano", "% ao mês"], width=110)
        self.combo_periodo_taxa.set("% ao ano")
        self.combo_periodo_taxa.pack(side="right")

        # 4. Período / Tempo de Aplicação
        self.lbl_periodo = ctk.CTkLabel(self.frame_form, text="Período do Investimento:", anchor="w")
        self.lbl_periodo.pack(fill="x", padx=10, pady=(5, 2))

        self.frame_periodo = ctk.CTkFrame(self.frame_form, fg_color="transparent")
        self.frame_periodo.pack(fill="x", padx=10, pady=(0, 10))

        self.entry_periodo = ctk.CTkEntry(self.frame_periodo, placeholder_text="Ex: 5")
        self.entry_periodo.insert(0, "5")
        self.entry_periodo.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.combo_tipo_periodo = ctk.CTkComboBox(self.frame_periodo, values=["Anos", "Meses"], width=110)
        self.combo_tipo_periodo.set("Anos")
        self.combo_tipo_periodo.pack(side="right")

        # 5. Meta Personalizada (Opcional)
        self.lbl_meta = ctk.CTkLabel(self.frame_form, text="Meta Desejada (R$):", anchor="w")
        self.lbl_meta.pack(fill="x", padx=10, pady=(5, 2))
        self.entry_meta = ctk.CTkEntry(self.frame_form, placeholder_text="Ex: 1000000")
        self.entry_meta.insert(0, "1000000")
        self.entry_meta.pack(fill="x", padx=10, pady=(0, 15))

        # Botão Principal de Calcular
        self.btn_calcular = ctk.CTkButton(
            self.frame_form, 
            text="Simular Rendimento", 
            command=self.executar_calculo,
            height=40,
            font=("Segoe UI", 14, "bold")
        )
        self.btn_calcular.pack(fill="x", padx=10, pady=(10, 15))

        # Botão para Limpar Campos
        self.btn_limpar = ctk.CTkButton(
            self.frame_form, 
            text="Limpar Campos", 
            command=self.limpar_entradas,
            fg_color="transparent",
            border_width=1,
            hover_color=("#e0e0e0", "#2c2c2c")
        )
        self.btn_limpar.pack(fill="x", padx=10, pady=(0, 10))

    # --------------------------------------------------------------------------
    # PAINEL DA DIREITA: RESULTADOS EM CARDS E GRÁFICO
    # --------------------------------------------------------------------------
    def _criar_painel_resultados(self):
        self.frame_resultados = ctk.CTkFrame(self)
        self.frame_resultados.grid(row=1, column=1, padx=15, pady=15, sticky="nsew")
        self.frame_resultados.grid_rowconfigure(1, weight=1)
        self.frame_resultados.grid_columnconfigure(0, weight=1)

        # 1. Cards com métricas principais (Topo)
        self.frame_cards = ctk.CTkFrame(self.frame_resultados, fg_color="transparent")
        self.frame_cards.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.frame_cards.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Card: Total Investido
        self.card_investido = self._criar_card(self.frame_cards, 0, "Total Investido", "R$ 0,00", "#3a3a3c")
        # Card: Total em Juros
        self.card_juros = self._criar_card(self.frame_cards, 1, "Total em Juros", "R$ 0,00", "#1b5e20")
        # Card: Valor Final Total
        self.card_total = self._criar_card(self.frame_cards, 2, "Montante Final", "R$ 0,00", "#0d47a1")
        # Card: Tempo até a Meta
        self.card_meta = self._criar_card(self.frame_cards, 3, "Tempo até a Meta", "-", "#424242")

        # 2. Área do Gráfico Matplotlib
        self.frame_grafico = ctk.CTkFrame(self.frame_resultados)
        self.frame_grafico.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

    def _criar_card(self, parent, coluna, titulo, valor_inicial, cor_destaque):
        card = ctk.CTkFrame(parent, corner_radius=8)
        card.grid(row=0, column=coluna, padx=6, pady=5, sticky="nsew")

        lbl_tit = ctk.CTkLabel(card, text=titulo, font=("Segoe UI", 12), text_color="gray")
        lbl_tit.pack(padx=10, pady=(8, 0))

        lbl_val = ctk.CTkLabel(card, text=valor_inicial, font=("Segoe UI", 15, "bold"))
        lbl_val.pack(padx=10, pady=(2, 8))

        return {"frame": card, "label_valor": lbl_val}

    # --------------------------------------------------------------------------
    # CABEÇALHO E TEMA (CLARO / ESCURO)
    # --------------------------------------------------------------------------
    def _criar_header(self):
        """Cria o cabeçalho superior com o título do app e o botão de tema sol/lua."""
        self.frame_header = ctk.CTkFrame(self, fg_color="transparent", height=50)
        self.frame_header.grid(row=0, column=0, columnspan=2, padx=15, pady=(10, 0), sticky="ew")
        self.frame_header.grid_columnconfigure(0, weight=1)

        self.lbl_titulo = ctk.CTkLabel(
            self.frame_header,
            text="Simulador de CDB & Juros Compostos",
            font=("Segoe UI", 18, "bold"),
        )
        self.lbl_titulo.grid(row=0, column=0, sticky="w")

        texto_botao = "☀️ Modo Claro" if self.tema_escuro else "🌙 Modo Escuro"
        self.btn_tema = ctk.CTkButton(
            self.frame_header,
            text=texto_botao,
            command=self.alternar_tema,
            width=140,
            height=32,
            font=("Segoe UI", 12, "bold"),
        )
        self.btn_tema.grid(row=0, column=1, sticky="e")

    def alternar_tema(self):
        """Alterna entre o modo escuro e o modo claro da interface."""
        if self.tema_escuro:
            ctk.set_appearance_mode("Light")
            self.btn_tema.configure(text="🌙 Modo Escuro")
            self.tema_escuro = False
        else:
            ctk.set_appearance_mode("Dark")
            self.btn_tema.configure(text="☀️ Modo Claro")
            self.tema_escuro = True

        # Redesenha o gráfico para adequar as cores ao novo tema
        if self.canvas is not None:
            self.executar_calculo()

    # --------------------------------------------------------------------------
    # EVENTOS E CÁLCULOS
    # --------------------------------------------------------------------------
    def limpar_entradas(self):
        """Restaura valores padrão nos campos."""
        self.entry_inicial.delete(0, "end")
        self.entry_mensal.delete(0, "end")
        self.entry_taxa.delete(0, "end")
        self.entry_periodo.delete(0, "end")
        self.entry_meta.delete(0, "end")

    def executar_calculo(self):
        """Lê os dados da tela, valida e atualiza os cards e gráfico."""
        try:
            # Leitura e conversão dos dados
            inicial = float(self.entry_inicial.get().replace(",", "."))
            mensal = float(self.entry_mensal.get().replace(",", "."))
            taxa_raw = float(self.entry_taxa.get().replace(",", "."))
            periodo_raw = float(self.entry_periodo.get().replace(",", "."))
            meta = float(self.entry_meta.get().replace(",", ".")) if self.entry_meta.get() else 1_000_000.0

            if inicial < 0 or mensal < 0 or taxa_raw < 0 or periodo_raw <= 0:
                messagebox.showerror("Erro de Validação", "Por favor, digite valores positivos.")
                return

        except ValueError:
            messagebox.showerror("Erro de Formato", "Insira números válidos nos campos.")
            return

        # Ajuste da taxa mensal
        if self.combo_periodo_taxa.get() == "% ao ano":
            taxa_mensal = taxa_raw / 12.0
        else:
            taxa_mensal = taxa_raw

        # Ajuste do total de meses
        if self.combo_tipo_periodo.get() == "Anos":
            meses_totais = int(periodo_raw * 12)
        else:
            meses_totais = int(periodo_raw)

        # Simulação mês a mês para acumular histórico para o gráfico
        meses_eixo = [0]
        investido_eixo = [inicial]
        total_eixo = [inicial]

        saldo_atual = inicial
        investido_atual = inicial

        for mes in range(1, meses_totais + 1):
            saldo_atual += mensal
            investido_atual += mensal
            rendimento = saldo_atual * (taxa_mensal / 100.0)
            saldo_atual += rendimento

            meses_eixo.append(mes)
            investido_eixo.append(investido_atual)
            total_eixo.append(saldo_atual)

        total_juros = saldo_atual - investido_atual

        # Cálculo do tempo até a meta
        meses_meta = calcular_tempo_ate_meta(inicial, mensal, taxa_mensal, meta=meta)
        texto_meta = formatar_tempo(meses_meta)

        # Atualização dos Cards
        self.card_investido["label_valor"].configure(text=formatar_moeda(investido_atual))
        self.card_juros["label_valor"].configure(text=formatar_moeda(total_juros))
        self.card_total["label_valor"].configure(text=formatar_moeda(saldo_atual))
        self.card_meta["label_valor"].configure(text=texto_meta)

        # Atualizar gráfico
        self._desenhar_grafico(meses_eixo, investido_eixo, total_eixo)

    def _desenhar_grafico(self, meses, investido, total):
        """Renderiza ou atualiza a visualização do gráfico de evolução patrimonial."""
        # Se já existir um canvas antigo, destrói para desenhar o novo
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()

        # Cores adaptadas ao tema atual (escuro ou claro)
        if self.tema_escuro:
            cor_fundo_fig = "#2b2b2b"
            cor_fundo_ax = "#1e1e1e"
            cor_texto_titulo = "white"
            cor_texto_eixo = "lightgray"
            cor_grid = "gray"
            cor_legenda_fundo = "#2b2b2b"
            cor_legenda_texto = "white"
        else:
            cor_fundo_fig = "#f5f5f5"
            cor_fundo_ax = "#ffffff"
            cor_texto_titulo = "#1a1a1a"
            cor_texto_eixo = "#4a4a4a"
            cor_grid = "#cccccc"
            cor_legenda_fundo = "#f5f5f5"
            cor_legenda_texto = "#1a1a1a"

        # Configuração do gráfico estilizado de acordo com o tema
        fig, ax = plt.subplots(figsize=(7, 4), dpi=100)
        fig.patch.set_facecolor(cor_fundo_fig)
        ax.set_facecolor(cor_fundo_ax)

        # Linhas de Total Acumulado vs Aportado
        ax.plot(meses, total, label="Montante Total (com juros)", color="#1f77b4", linewidth=2.5)
        ax.plot(meses, investido, label="Total Aportado (do seu bolso)", color="#2ca02c", linestyle="--", linewidth=1.8)

        # Preenchimento entre as linhas para destacar o efeito dos juros compostos
        ax.fill_between(meses, investido, total, color="#1f77b4", alpha=0.15, label="Ganho em Juros")

        # Customizações dos Eixos e Títulos
        ax.set_title("Evolução Patrimonial ao Longo do Tempo", color=cor_texto_titulo, fontsize=12, pad=12)
        ax.set_xlabel("Meses Decorridos", color=cor_texto_eixo, fontsize=10)
        ax.set_ylabel("Valor (R$)", color=cor_texto_eixo, fontsize=10)

        ax.tick_params(colors=cor_texto_eixo, which="both")
        ax.grid(True, linestyle=":", alpha=0.3, color=cor_grid)

        # Formatador simples para valores no eixo Y em milhares (k) ou milhões (M)
        def formato_moeda_eixo(x, pos):
            if x >= 1_000_000:
                return f"R$ {x*1e-6:.1f}M"
            elif x >= 1_000:
                return f"R$ {x*1e-3:.0f}k"
            return f"R$ {x:.0f}"

        from matplotlib.ticker import FuncFormatter
        ax.yaxis.set_major_formatter(FuncFormatter(formato_moeda_eixo))

        # Legenda com fundo adequado ao tema
        legend = ax.legend(facecolor=cor_legenda_fundo, edgecolor="none")
        for text in legend.get_texts():
            text.set_color(cor_legenda_texto)

        plt.tight_layout()

        # Vincula o canvas ao Tkinter
        self.canvas = FigureCanvasTkAgg(fig, master=self.frame_grafico)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)


# ==============================================================================
# PONTO DE ENTRADA DO PROGRAMA
# ==============================================================================
if __name__ == "__main__":
    app = AppSimulador()
    app.mainloop()
