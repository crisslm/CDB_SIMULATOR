"""
Camada de Domínio - Entidades e Modelos de Dados
================================================

Este módulo contém as classes puras de dados (dataclasses) usadas para entrada
e saída das simulações financeiras, além da função de cálculo de Imposto de Renda.

Princípio SOLID aplicado: Single Responsibility Principle (SRP)
- Cada classe tem uma única responsabilidade bem definida.
- Este módulo NÃO depende de UI, banco de dados ou serviços externos.
- Pode ser testado e mantido isoladamente.

Autor: CDB Simulator
Versão: 1.0.0
"""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


def calcular_aliquota_ir(dias: int) -> float:
    """
    Calcula a alíquota regressiva do Imposto de Renda (IR) para aplicações
    de renda fixa (CDB, LCI, LCA, Tesouro Direto, etc.) no Brasil.

    A tabela regressiva funciona da seguinte forma:
      - Quanto maior o prazo, menor a alíquota (incentivo ao investimento longo).

    Regras (conforme Receita Federal):
      - Até 180 dias:      22,5%
      - De 181 a 360 dias: 20,0%
      - De 361 a 720 dias: 17,5%
      - Acima de 720 dias: 15,0%

    Parâmetros:
        dias (int): Número de dias corridos da aplicação.
                    Deve ser um inteiro não negativo.

    Retorna:
        float: Alíquota em formato decimal (ex: 0.225 = 22,5%).

    Exemplo de uso:
        >>> calcular_aliquota_ir(100)
        0.225
        >>> calcular_aliquota_ir(200)
        0.2
        >>> calcular_aliquota_ir(800)
        0.15

    Observação de manutenção:
        Se a tabela de IR mudar no futuro, é aqui que deve ser alterado.
        Não esqueça de atualizar também os testes em tests/test_domain.py.
    """
    if dias <= 180:
        return 0.225
    elif dias <= 360:
        return 0.20
    elif dias <= 720:
        return 0.175
    else:
        return 0.15


@dataclass(frozen=True)
class MonthlyRecord:
    """
    Representa o 'foto' financeiro de um único mês da simulação.

    É um registro imutável (frozen=True) que armazena os valores de um mês
    específico dentro da timeline de simulação. Usado para exibição no gráfico
    e para rastrear a evolução do patrimônio ao longo do tempo.

    Atributos:
        month (int): Número do mês na simulação (começa em 1).
        invested_to_date (float): Total aportado até este mês (inicial + aportes).
        interest_earned_month (float): Rendimento bruto gerado apenas neste mês.
        total_balance (float): Saldo total acumulado até este mês (aportes + rendimentos).

    Exemplo:
        MonthlyRecord(month=3, invested_to_date=1500.00, interest_earned_month=45.00, total_balance=1545.00)
    """
    month: int
    invested_to_date: float
    interest_earned_month: float
    total_balance: float


@dataclass(frozen=True)
class SimulationParams:
    """
    Parâmetros imutáveis de entrada necessários para executar uma simulação de investimento.

    Esta classe é imutável (frozen=True) para garantir que, uma vez criados,
    os parâmetros não sejam alterados acidentalmente durante a execução da
    simulação. Isso previne bugs difíceis de rastrear.

    Atributos:
        initial_amount (float): Valor inicial investido (R$).
                                Ex: 5000.00
        monthly_contribution (float): Aporte mensal recorrente (R$).
                                      Ex: 500.00. Pode ser 0 se não houver aporte.
        total_months (int): Período total da simulação em meses.
                            Ex: 60 para 5 anos.
        target_amount (float): Meta financeira desejada (R$).
                               Padrão: 1.000.000,00.
                               Se o saldo atingir este valor, a simulação ainda
                               continua até total_months, mas o cálculo de
                               "tempo até a meta" para quando atingir.
        start_date (Optional[date]): Data inicial da aplicação (opcional).
                                     Se fornecido, é usado para calcular dias
                                     reais para o IR (em vez de meses * 30).
        end_date (Optional[date]): Data final da aplicação (opcional).
                                   Usada em conjunto com start_date para o IR.

    Exemplo de criação:
        params = SimulationParams(
            initial_amount=5000.0,
            monthly_contribution=500.0,
            total_months=60,
            target_amount=100000.0
        )

    Observação de manutenção:
        Se adicionar novos parâmetros, lembre-se de atualizar:
        1. src/ui/gui/app.py (campos da GUI)
        2. tests/test_domain.py e tests/test_services.py (testes)
    """
    initial_amount: float
    monthly_contribution: float
    total_months: int
    target_amount: float = 1_000_000.0
    start_date: Optional[date] = None
    end_date: Optional[date] = None


@dataclass(frozen=True)
class SimulationResult:
    """
    Resultado consolidado de uma simulação de investimento.

    Contém todos os valores calculados após a execução da simulação,
    tanto brutos (antes do IR) quanto líquidos (após o IR).

    Atributos:
        total_invested (float): Total de capital próprio investido
                                (valor inicial + somatória dos aportes).
        total_interest (float): Total de rendimentos brutos gerados
                                (antes do Imposto de Renda).
        final_balance (float): Montante bruto final (investido + rendimentos).
        total_months (int): Número de meses efetivamente simulados.
                            Pode ser menor que o solicitado se houver truncamento
                            pelo limite de segurança (1200 meses).
        months_to_target (Optional[int]): Meses necessários para atingir a meta.
                                          None se a meta for inalcançável no período.
        ir_aliquota (float): Alíquota de IR aplicada (ex: 0.15 = 15%).
        ir_total (float): Valor total do Imposto de Renda retido.
        net_interest (float): Rendimentos líquidos (após desconto do IR).
        net_balance (float): Montante líquido final (o que o investidor recebe).
        timeline (List[MonthlyRecord]): Lista de registros mensais para o gráfico.
        truncado (bool): True se o período foi limitado pelo teto de segurança.

    Exemplo:
        result = SimulationResult(
            total_invested=35000.0,
            total_interest=5000.0,
            final_balance=40000.0,
            total_months=60,
            months_to_target=45,
            ir_aliquota=0.175,
            ir_total=875.0,
            net_interest=4125.0,
            net_balance=39125.0,
            timeline=[...],
            truncado=False
        )

    Observação de manutenção:
        Este é um DTO (Data Transfer Object) - não contém lógica de negócio,
        apenas transporta dados entre a camada de serviços e a UI.
    """
    total_invested: float
    total_interest: float
    final_balance: float
    total_months: int
    months_to_target: Optional[int]
    ir_aliquota: float = 0.15
    ir_total: float = 0.0
    net_interest: float = 0.0
    net_balance: float = 0.0
    timeline: List[MonthlyRecord] = field(default_factory=list)
    truncado: bool = False