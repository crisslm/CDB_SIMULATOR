"""
Camada de Apresentação - Interface de Linha de Comando (CLI)
Princípios SOLID:
 - Single Responsibility Principle (SRP): Focado na interação via terminal.
 - Dependency Inversion Principle (DIP): Utiliza o serviço InvestmentSimulatorService.
"""

from src.services.simulator_service import InvestmentSimulatorService, MAX_SIMULATION_MONTHS
from src.domain.models import SimulationParams
from src.domain.strategies import CompoundInterestStrategy, CDIStrategy
from src.ui.gui.components import formatar_tempo, formatar_moeda


def ler_numero(mensagem: str, max_valor: float = float("inf"), permitir_zero: bool = True) -> float:
    while True:
        try:
            valor = float(input(mensagem).replace(",", "."))
            if (valor > 0) or (permitir_zero and valor == 0):
                if valor <= max_valor:
                    return valor
                print(f"Por favor, insira um valor menor ou igual a {max_valor}.")
            else:
                print("Por favor, insira um valor maior que zero.")
        except ValueError:
            print("Entrada inválida! Por favor, digite apenas números.")


def executar_cli():
    service = InvestmentSimulatorService()

    print("==========================================")
    print("      SIMULADOR DE INVESTIMENTOS (CLI)    ")
    print("==========================================\n")

    while True:
        inicial = ler_numero("Insira o valor inicial guardado (R$): ")
        valor_mensal = ler_numero("Insira o valor do aporte mensal (R$): ")

        while True:
            resp_tipo = input("Tipo de investimento: [1] Prefixado ou [2] CDB (% CDI)? ").strip()
            if resp_tipo == "1":
                resp_juros = input("Deseja calcular os juros ao [m]ês ou ao [a]no? ").strip().lower()
                if resp_juros in ['m', 'mes', 'mês']:
                    taxa = ler_numero("Insira a taxa de juros ao mês (%): ")
                    strategy = CompoundInterestStrategy(rate_percent=taxa, is_annual=False)
                    break
                elif resp_juros in ['a', 'ano']:
                    taxa = ler_numero("Insira a taxa de juros ao ano (%): ")
                    strategy = CompoundInterestStrategy(rate_percent=taxa, is_annual=True, use_effective_rate=True)
                    break
                else:
                    print("Opção inválida! Digite 'm' para mês ou 'a' para ano.")
            elif resp_tipo == "2":
                pct_cdi = ler_numero("Insira o percentual do CDI (ex: 110 para 110%): ")
                cdi_anual = ler_numero("Insira a taxa anual do CDI (ex: 10.75): ")
                strategy = CDIStrategy(cdi_percentage=pct_cdi, cdi_annual_rate=cdi_anual, use_effective_rate=True)
                break
            else:
                print("Opção inválida! Digite 1 ou 2.")

        while True:
            resp_tempo = input("\nDeseja calcular em [m]eses ou [a]nos? ").strip().lower()
            if resp_tempo in ['m', 'mes', 'mês']:
                meses = int(ler_numero("Insira o número de meses (máx 1200): ", max_valor=MAX_SIMULATION_MONTHS, permitir_zero=False))
                break
            elif resp_tempo in ['a', 'ano']:
                anos = ler_numero("Insira o número de anos (máx 100): ", max_valor=100, permitir_zero=False)
                meses = min(int(anos * 12), MAX_SIMULATION_MONTHS)
                break
            else:
                print("Opção inválida! Digite 'm' para meses ou 'a' para anos.")

        meta_input = ler_numero("Insira o objetivo / meta financeira (R$, padrão 1.000.000): ", permitir_zero=False)

        params = SimulationParams(
            initial_amount=inicial,
            monthly_contribution=valor_mensal,
            total_months=meses,
            target_amount=meta_input
        )

        resultado = service.simulate(params, strategy)

        print("\n" + "=" * 45)
        print("          RESUMO DO INVESTIMENTO          ")
        print("=" * 45)
        print(f"Estratégia:         {strategy.get_description()}")
        print(f"Período total:      {meses} meses ({meses / 12:.1f} anos)")
        print(f"Total investido:    {formatar_moeda(resultado.total_invested)}")
        print(f"Total juros bruto:  {formatar_moeda(resultado.total_interest)}")
        print(f"VALOR BRUTO TOTAL:  {formatar_moeda(resultado.final_balance)}")
        print("-" * 45)
        print(f"Alíquota IR (CDB):  {resultado.ir_aliquota * 100:.1f}%")
        print(f"Total em IR retido: {formatar_moeda(resultado.ir_total)}")
        print(f"VALOR LÍQUIDO:      {formatar_moeda(resultado.net_balance)}")
        print("-" * 45)
        print(f"Tempo até meta:     {formatar_tempo(resultado.months_to_target)}")
        print("=" * 45)

        opcao = input("\nDeseja realizar outro cálculo? (s/n): ").strip().lower()
        if opcao != 's':
            print("\nSimulação encerrada!")
            break


if __name__ == "__main__":
    executar_cli()
