"""
Testes de Interface (UI) para o CDB Simulator.
==============================================

Este módulo testa a camada de apresentação (ModernAppGUI e FinancialDashboard)
usando o modo offscreen do Tkinter (janela oculta), sem exigir display gráfico.

Os testes validam:
    - Criação da janela principal e seus widgets
    - Alternância de tema claro/escuro
    - Navegação entre seções (Simulador / Controle Financeiro)
    - Execução de simulação via caso de uso
    - Criação do dashboard financeiro e seus componentes
    - Tratamento de exceções de validação na UI

Execução:
    QT_QPA_PLATFORM=offscreen pytest tests/test_ui.py -v
    ou simplesmente:
    pytest tests/test_ui.py -v
"""

import os
import sys
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

# Garante que o modo offscreen seja usado se houver suporte
os.environ.setdefault("TK_INTERACTIVE", "0")

import customtkinter as ctk  # noqa: E402  (precisa ser importado após definir env)
from tkinter import messagebox  # noqa: E402

from src.use_cases.simulate_investment import (
    SimulateInvestmentUseCase,
    SimulationInput,
)
from src.use_cases.financial_use_cases import FinancialUseCases
from src.ui.gui.app import ModernAppGUI


# -------------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app_root():
    """
    Cria uma instância raiz do Tkinter para a sessão de testes.

    Usada como pai para janelas Toplevel e para inicializar o CustomTkinter.
    A janela fica oculta (withdraw) para não aparecer na tela.
    """
    root = ctk.CTk()
    root.withdraw()  # Oculta a janela (modo offscreen)
    yield root
    try:
        root.destroy()
    except Exception:
        pass


@pytest.fixture(scope="session")
def gui_app(app_root):
    """
    Cria uma instância da ModernAppGUI para testes.

    Injeta casos de uso reais (não mockados) para testar integração.
    Reutiliza a instância raiz da sessão para evitar múltiplas instâncias Tk.
    A janela fica oculta durante os testes.
    """
    simulator_uc = SimulateInvestmentUseCase()
    financial_uc = FinancialUseCases(
        database_path=Path(tempfile.mkdtemp()) / "test_ui.sqlite3"
    )
    app = ModernAppGUI(
        simulator_use_case=simulator_uc,
        financial_use_cases=financial_uc,
    )
    app.withdraw()  # Oculta a janela
    yield app
    try:
        app.destroy()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def reset_gui_state(gui_app):
    """
    Reseta o estado da GUI antes de cada teste.

    Como a fixture gui_app tem escopo session (necessário por causa do Tkinter),
    precisamos resetar o estado entre testes para evitar interferência.
    """
    # Reseta seção ativa
    gui_app.active_section = "simulator"
    gui_app.is_mobile_layout = None

    # Reseta tema
    gui_app.theme_mode = "Light"
    gui_app._apply_theme("Light")

    # Reseta campos de entrada para valores padrão
    gui_app.entry_inicial.delete(0, "end")
    gui_app.entry_inicial.insert(0, "5000")
    gui_app.entry_mensal.delete(0, "end")
    gui_app.entry_mensal.insert(0, "500")
    gui_app.entry_taxa.delete(0, "end")
    gui_app.entry_taxa.insert(0, "12.0")
    gui_app.entry_periodo.delete(0, "end")
    gui_app.entry_periodo.insert(0, "5")
    gui_app.entry_meta.delete(0, "end")
    gui_app.entry_meta.insert(0, "1000000")
    gui_app.entry_cdi_base.delete(0, "end")
    gui_app.entry_cdi_base.insert(0, "10.75")

    # Reseta combos
    gui_app.combo_estrategia.set("Taxa Prefixada (% a.a. / a.m.)")
    gui_app.combo_periodo_taxa.set("% ao ano")
    gui_app.combo_tipo_periodo.set("Anos")

    # Reseta cards
    gui_app.card_investido.update_value("R$ 0,00")
    gui_app.card_juros.update_value("R$ 0,00", badge_text="+0.0%")
    gui_app.card_total.update_value("R$ 0,00")
    gui_app.card_liquido.update_value("R$ 0,00", badge_text="IR 15%")
    gui_app.card_meta.update_value("-")

    # Garante que está na seção simulador
    gui_app._show_section("simulator")

    yield


@pytest.fixture
def mock_messagebox():
    """Faz mock do messagebox para não travar em modo offscreen."""
    with patch.object(messagebox, "showerror"), patch.object(
        messagebox, "showwarning"
    ), patch.object(messagebox, "showinfo"), patch.object(
        messagebox, "askyesno", return_value=True
    ):
        yield


# -------------------------------------------------------------------------
# Testes de Criação e Estrutura da UI
# -------------------------------------------------------------------------

def test_modern_app_gui_creation(gui_app):
    """Verifica que a janela principal é criada com os atributos esperados."""
    assert gui_app is not None
    assert isinstance(gui_app, ctk.CTk)
    assert gui_app.active_section == "simulator"
    assert gui_app.theme_mode in ("Light", "Dark")
    assert hasattr(gui_app, "simulator_use_case")
    assert hasattr(gui_app, "financial_use_cases")


def test_gui_has_sidebar_widgets(gui_app):
    """Verifica que os widgets da barra lateral existem."""
    assert hasattr(gui_app, "entry_inicial")
    assert hasattr(gui_app, "entry_mensal")
    assert hasattr(gui_app, "entry_taxa")
    assert hasattr(gui_app, "entry_periodo")
    assert hasattr(gui_app, "entry_meta")
    assert hasattr(gui_app, "entry_cdi_base")
    assert hasattr(gui_app, "combo_estrategia")
    assert hasattr(gui_app, "combo_periodo_taxa")
    assert hasattr(gui_app, "combo_tipo_periodo")
    assert hasattr(gui_app, "btn_simular")
    assert hasattr(gui_app, "btn_tema")


def test_gui_has_metric_cards(gui_app):
    """Verifica que os 5 cards de métrica existem."""
    assert hasattr(gui_app, "card_investido")
    assert hasattr(gui_app, "card_juros")
    assert hasattr(gui_app, "card_total")
    assert hasattr(gui_app, "card_liquido")
    assert hasattr(gui_app, "card_meta")
    assert len(gui_app.cards_list) == 5


def test_gui_has_chart_controller(gui_app):
    """Verifica que o controlador de gráficos foi inicializado."""
    assert hasattr(gui_app, "chart_controller")
    assert gui_app.chart_controller is not None


def test_gui_has_financial_dashboard(gui_app):
    """Verifica que o dashboard financeiro existe."""
    assert hasattr(gui_app, "financial_dashboard")
    assert gui_app.financial_dashboard is not None


# -------------------------------------------------------------------------
# Testes de Tema
# -------------------------------------------------------------------------

def test_theme_toggle_changes_mode(gui_app):
    """Verifica que alternar o tema muda o modo atual."""
    modo_inicial = gui_app.theme_mode
    gui_app._toggle_theme()
    novo_modo = gui_app.theme_mode
    assert novo_modo != modo_inicial
    assert novo_modo in ("Light", "Dark")


def test_theme_persistence(gui_app, tmp_path):
    """Verifica que o tema pode ser salvo e carregado de arquivo JSON."""
    import json

    theme_file = tmp_path / "test_theme.json"
    gui_app.THEME_FILE = theme_file

    # Salva tema Dark
    gui_app.theme_mode = "Dark"
    gui_app._save_theme()
    conteudo = json.loads(theme_file.read_text(encoding="utf-8"))
    assert conteudo["mode"] == "Dark"

    # Carrega de volta
    gui_app.theme_mode = "Light"  # reseta
    modo_carregado = gui_app._load_theme()
    assert modo_carregado == "Dark"


def test_apply_theme_updates_widgets(gui_app):
    """Verifica que aplicar um tema atualiza os widgets sem erro."""
    gui_app._apply_theme("Dark")
    assert gui_app.theme_mode == "Dark"
    gui_app._apply_theme("Light")
    assert gui_app.theme_mode == "Light"


# -------------------------------------------------------------------------
# Testes de Navegação
# -------------------------------------------------------------------------

def test_show_section_simulator(gui_app):
    """Verifica que a seção do simulador pode ser exibida."""
    gui_app._show_section("simulator")
    assert gui_app.active_section == "simulator"


def test_show_section_financial(gui_app):
    """Verifica que a seção financeira pode ser exibida."""
    gui_app._show_section("financial")
    assert gui_app.active_section == "financial"


def test_navigation_buttons_state(gui_app):
    """Verifica que os botões de navegação refletem a seção ativa."""
    gui_app._show_section("simulator")
    gui_app._update_navigation()
    assert gui_app.nav_simulator._variant == "primary"
    assert gui_app.nav_financial._variant == "secondary"

    gui_app._show_section("financial")
    gui_app._update_navigation()
    assert gui_app.nav_simulator._variant == "secondary"
    assert gui_app.nav_financial._variant == "primary"


# -------------------------------------------------------------------------
# Testes de Simulação via UI
# -------------------------------------------------------------------------

def test_on_simulate_click_prefixado_valido(gui_app, mock_messagebox):
    """
    Teste de simulação válida via UI.

    Preenche os campos com valores válidos e verifica que o resultado
    é exibido nos cards.
    """
    # Preenche campos
    gui_app.entry_inicial.delete(0, "end")
    gui_app.entry_inicial.insert(0, "1.000,00")
    gui_app.entry_mensal.delete(0, "end")
    gui_app.entry_mensal.insert(0, "100,00")
    gui_app.entry_taxa.delete(0, "end")
    gui_app.entry_taxa.insert(0, "1,0")  # 1% ao mês
    gui_app.entry_periodo.delete(0, "end")
    gui_app.entry_periodo.insert(0, "2")
    gui_app.combo_tipo_periodo.set("Meses")
    gui_app.entry_meta.delete(0, "end")
    gui_app.entry_meta.insert(0, "10.000,00")
    gui_app.combo_estrategia.set("Taxa Prefixada (% a.a. / a.m.)")
    gui_app.combo_periodo_taxa.set("% ao mês")

    # Executa simulação
    gui_app.on_simulate_click()

    # Verifica que os cards foram atualizados (não estão mais com valor zero)
    valor_investido = gui_app.card_investido.lbl_valor.cget("text")
    assert valor_investido != "R$ 0,00"
    assert "1.200,00" in valor_investido  # 1000 + 2*100


def test_on_simulate_click_valor_invalido(gui_app, mock_messagebox):
    """
    Teste que valor inválido exibe mensagem de erro.

    Preenche com texto não numérico e verifica que não trava a aplicação.
    """
    gui_app.entry_inicial.delete(0, "end")
    gui_app.entry_inicial.insert(0, "abc")  # inválido
    gui_app.entry_mensal.delete(0, "end")
    gui_app.entry_mensal.insert(0, "100,00")
    gui_app.entry_taxa.delete(0, "end")
    gui_app.entry_taxa.insert(0, "12,0")
    gui_app.entry_periodo.delete(0, "end")
    gui_app.entry_periodo.insert(0, "12")
    gui_app.combo_tipo_periodo.set("Meses")
    gui_app.entry_meta.delete(0, "end")
    gui_app.entry_meta.insert(0, "10.000,00")
    gui_app.combo_estrategia.set("Taxa Prefixada (% a.a. / a.m.)")

    # Não deve levantar exceção não tratada
    gui_app.on_simulate_click()

    # Os cards devem continuar com valores iniciais (simulação não executada)
    assert gui_app.card_investido.lbl_valor.cget("text") == "R$ 0,00"


def test_on_simulate_click_taxa_acima_limite(gui_app, mock_messagebox):
    """
    Teste que taxa acima do limite exibe erro de validação.

    Taxa de 150% para prefixado deve ser rejeitada (limite é 100%).
    """
    gui_app.entry_inicial.delete(0, "end")
    gui_app.entry_inicial.insert(0, "1.000,00")
    gui_app.entry_mensal.delete(0, "end")
    gui_app.entry_mensal.insert(0, "100,00")
    gui_app.entry_taxa.delete(0, "end")
    gui_app.entry_taxa.insert(0, "150,0")  # acima de 100%
    gui_app.entry_periodo.delete(0, "end")
    gui_app.entry_periodo.insert(0, "12")
    gui_app.combo_tipo_periodo.set("Meses")
    gui_app.entry_meta.delete(0, "end")
    gui_app.entry_meta.insert(0, "10.000,00")
    gui_app.combo_estrategia.set("Taxa Prefixada (% a.a. / a.m.)")

    gui_app.on_simulate_click()

    # Simulação não deve ter sido executada (cards continuam zerados)
    assert gui_app.card_investido.lbl_valor.cget("text") == "R$ 0,00"


def test_on_simulate_click_cdi_valido(gui_app, mock_messagebox):
    """
    Teste de simulação com CDI válido.

    Preenche campos para estratégia CDI e verifica execução.
    """
    gui_app.entry_inicial.delete(0, "end")
    gui_app.entry_inicial.insert(0, "5.000,00")
    gui_app.entry_mensal.delete(0, "end")
    gui_app.entry_mensal.insert(0, "500,00")
    gui_app.entry_taxa.delete(0, "end")
    gui_app.entry_taxa.insert(0, "110")  # 110% do CDI
    gui_app.entry_periodo.delete(0, "end")
    gui_app.entry_periodo.insert(0, "60")
    gui_app.combo_tipo_periodo.set("Meses")
    gui_app.entry_meta.delete(0, "end")
    gui_app.entry_meta.insert(0, "100.000,00")
    gui_app.combo_estrategia.set("Pós-fixado (% do CDI)")
    gui_app.entry_cdi_base.delete(0, "end")
    gui_app.entry_cdi_base.insert(0, "10.75")

    gui_app.on_simulate_click()

    valor_investido = gui_app.card_investido.lbl_valor.cget("text")
    assert valor_investido != "R$ 0,00"
    assert "35.000,00" in valor_investido  # 5000 + 60*500


def test_strategy_change_shows_hides_cdi_base(gui_app):
    """
    Verifica que mudar estratégia mostra/esconde campo CDI base.

    Como a janela está oculta (modo offscreen), winfo_ismapped() sempre
    retorna 0. Em vez disso, verificamos que o método não levanta exceção
    e que o campo de taxa é atualizado corretamente.
    """
    # Inicialmente prefixada
    gui_app._on_strategy_change("Taxa Prefixada (% a.a. / a.m.)")
    assert gui_app.lbl_taxa.cget("text") == "TAXA DE RENDIMENTO (%):"

    # Muda para CDI
    gui_app._on_strategy_change("Pós-fixado (% do CDI)")
    assert gui_app.lbl_taxa.cget("text") == "% DO CDI (ex: 110%):"
    assert gui_app.entry_taxa.get() == "110"

    # Volta para prefixada
    gui_app._on_strategy_change("Taxa Prefixada (% a.a. / a.m.)")
    assert gui_app.lbl_taxa.cget("text") == "TAXA DE RENDIMENTO (%):"
    assert gui_app.entry_taxa.get() == "12.0"


# -------------------------------------------------------------------------
# Testes de Layout Responsivo
# -------------------------------------------------------------------------

def test_responsive_layout_mobile(gui_app):
    """Verifica que layout mobile (< 860px) é aplicado."""
    gui_app._apply_responsive_layout(500)
    assert gui_app.is_mobile_layout is True


def test_responsive_layout_desktop(gui_app):
    """Verifica que layout desktop (>= 860px) é aplicado."""
    gui_app._apply_responsive_layout(1200)
    assert gui_app.is_mobile_layout is False


def test_cards_grid_reconfiguration(gui_app):
    """Verifica que o grid dos cards é reconfigurado conforme colunas."""
    gui_app._configure_cards_grid(columns=2)
    gui_app._configure_cards_grid(columns=5)
    # Não deve levantar exceção


# -------------------------------------------------------------------------
# Testes de Caso de Uso Integrado à UI
# -------------------------------------------------------------------------

def test_use_case_injecao_na_ui(gui_app):
    """Verifica que a UI recebeu os casos de uso injetados."""
    assert isinstance(gui_app.simulator_use_case, SimulateInvestmentUseCase)
    assert isinstance(gui_app.financial_use_cases, FinancialUseCases)


def test_simulation_output_tem_campos_obrigatorios(gui_app):
    """
    Verifica que o output do caso de uso tem todos os campos obrigatórios.

    Integra UI -> caso de uso -> serviço.
    """
    input_data = SimulationInput(
        inicial="1.000,00",
        mensal="100,00",
        taxa="1,0",
        periodo="2",
        tipo_periodo="Meses",
        meta="10.000,00",
        estrategia="Taxa Prefixada (% a.a. / a.m.)",
    )
    output = gui_app.simulator_use_case.execute(input_data)

    assert isinstance(output.total_invested, float)
    assert isinstance(output.total_interest, float)
    assert isinstance(output.final_balance, float)
    assert isinstance(output.total_months, int)
    assert output.months_to_target is None or isinstance(output.months_to_target, int)
    assert isinstance(output.ir_aliquota, float)
    assert isinstance(output.net_balance, float)
    assert isinstance(output.timeline, list)
    assert isinstance(output.truncado, bool)
    assert isinstance(output.estrategia_descricao, str)


# -------------------------------------------------------------------------
# Testes de Dashboard Financeiro (via UI)
# -------------------------------------------------------------------------

def test_financial_dashboard_criacao(gui_app):
    """Verifica que o dashboard financeiro foi criado corretamente."""
    dashboard = gui_app.financial_dashboard
    assert dashboard is not None
    assert hasattr(dashboard, "service")
    assert hasattr(dashboard, "palette")
    assert hasattr(dashboard, "cards")
    assert len(dashboard.cards) == 5  # Receitas, Despesas, Investimentos, Saldo, Taxa


def test_financial_dashboard_refresh(gui_app):
    """Verifica que o refresh do dashboard não levanta exceção."""
    dashboard = gui_app.financial_dashboard
    # Não deve levantar exceção mesmo sem dados
    dashboard.refresh()


def test_financial_dashboard_apply_theme(gui_app):
    """Verifica que aplicar tema no dashboard não levanta exceção."""
    dashboard = gui_app.financial_dashboard
    dashboard.apply_theme(gui_app.PALETTES["Dark"])
    dashboard.apply_theme(gui_app.PALETTES["Light"])


def test_financial_dashboard_apply_layout(gui_app):
    """Verifica que aplicar layout no dashboard não levanta exceção."""
    dashboard = gui_app.financial_dashboard
    dashboard.apply_layout(1200)  # desktop
    dashboard.apply_layout(500)   # mobile


# -------------------------------------------------------------------------
# Testes de Tratamento de Exceções
# -------------------------------------------------------------------------

def test_gui_fecha_sem_erro(gui_app):
    """Verifica que fechar a GUI não levanta exceção."""
    gui_app._on_close()
