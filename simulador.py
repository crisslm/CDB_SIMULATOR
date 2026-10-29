# ==============================================================================
# SIMULADOR DE JUROS COMPOSTOS
# ==============================================================================

def ler_numero(mensagem):
    """
    Garante que o utilizador digite um número válido e positivo.
    Trata erros de digitação de texto.
    """
    while True:
        try:
            valor = float(input(mensagem))
            if valor >= 0:
                return valor
            print("Por favor, insira um valor maior ou igual a zero.")
        except ValueError:
            print("Entrada inválida! Por favor, digite apenas números.")


def calcular_tempo_ate_meta(inicial, aporte_mensal, taxa_mensal, meta=1_000_000.0):
    """
    Calcula quantos meses levaria para atingir a meta estipulada
    com base no valor inicial, aporte mensal e taxa mensal (em %).
    Retorna o número de meses ou None se for inatingível.
    """
    if inicial >= meta:
        return 0

    r = taxa_mensal / 100.0

    # Se não há juros nem aporte, nunca atinge
    if r == 0 and aporte_mensal == 0:
        return None

    # Se não há juros, cálculo linear simples
    if r == 0:
        import math
        return math.ceil((meta - inicial) / aporte_mensal)

    # Simulação mês a mês para seguir a mesma regra de capitalização da simulação
    saldo = inicial
    meses_necessarios = 0
    # Limite razoável para evitar loop infinito (ex: 1200 meses = 100 anos)
    limite_meses = 1200

    while saldo < meta and meses_necessarios < limite_meses:
        saldo += aporte_mensal
        rendimento = saldo * r
        saldo += rendimento
        meses_necessarios += 1

    if saldo >= meta:
        return meses_necessarios
    return None


def formatar_tempo(meses):
    """
    Formata o tempo em anos e meses de forma legível.
    """
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


def executar_simulador():
    print("==========================================")
    print("      SIMULADOR DE JUROS COMPOSTOS        ")
    print("==========================================\n")

    while True:
        #Coleta do Capital Inicial e Aporte Mensal
        inicial = ler_numero("Insira o valor inicial guardado (R$): ")
        valor_mensal = ler_numero("Insira o valor do aporte mensal (R$): ")

        #Definição da Taxa de Juros (Mês ou Ano)
        while True:
            resp_juros = input("Deseja calcular os juros ao [m]ês ou ao [a]no? ").strip().lower()
            if resp_juros in ['m', 'mes', 'mês', 'meses']:
                taxa_mensal = ler_numero("Insira a taxa de juros ao mês (%): ")
                break
            elif resp_juros in ['a', 'ano', 'anos']:
                taxa_anual = ler_numero("Insira a taxa de juros ao ano (%): ")
                taxa_mensal = taxa_anual / 12  # Conversão nominal para taxa mensal
                break
            else:
                print("Opção inválida! Digite 'm' para mês ou 'a' para ano.")

        #Definição do Tempo de Investimento
        while True:
            resp_tempo = input("\nDeseja calcular em [m]eses ou [a]nos? ").strip().lower()
            if resp_tempo in ['m', 'mes', 'mês', 'meses']:
                meses = int(ler_numero("Insira o número de meses: "))
                anos = meses / 12
                break
            elif resp_tempo in ['a', 'ano', 'anos']:
                anos = ler_numero("Insira o número de anos: ")
                meses = int(anos * 12)
                break
            else:
                print("Opção inválida! Digite 'm' para meses ou 'a' para anos.")

        # 4. Cálculo dos Juros Compostos
        saldo_total = inicial
        total_investido = inicial

        for _ in range(meses):
            saldo_total += valor_mensal
            total_investido += valor_mensal
            rendimento_do_mes = saldo_total * (taxa_mensal / 100)
            saldo_total += rendimento_do_mes

        total_juros = saldo_total - total_investido

        # Cálculo do tempo até 1 milhão
        meses_ate_milhao = calcular_tempo_ate_meta(inicial, valor_mensal, taxa_mensal, meta=1_000_000.0)
        tempo_milhao_texto = formatar_tempo(meses_ate_milhao) if meses_ate_milhao is not None else "Inatingível / Superior a 100 anos"

        # 5. Apresentação Clara dos Resultados
        print("\n" + "=" * 40)
        print("          RESUMO DO INVESTIMENTO          ")
        print("=" * 40)
        print(f"Período total:      {meses} meses ({anos:.1f} anos)")
        print(f"Total investido:    R$ {total_investido:,.2f}")
        print(f"Total em juros:     R$ {total_juros:,.2f}")
        print(f"VALOR FINAL TOTAL:  R$ {saldo_total:,.2f}")
        print("-" * 40)
        print(f"Tempo até R$ 1 Mi:  {tempo_milhao_texto}")
        print("=" * 40)

        # 6. Opção para Novo Cálculo
        opcao = input("\nDeseja realizar outro cálculo? (s/n): ").strip().lower()
        if opcao != 's':
            print("\nSimulação encerrada com sucesso!")
            break


# Ponto de entrada do programa
if __name__ == "__main__":
    executar_simulador()