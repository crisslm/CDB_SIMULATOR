# CDB Simulator • Planejamento e Simulação de Renda Fixa

[![Python Version](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/)
[![UI](https://img.shields.io/badge/GUI-CustomTkinter-emerald.svg)](https://github.com/TomSchimansky/CustomTkinter)
[![Tests](https://img.shields.io/badge/tests-pytest-green.svg)](https://docs.pytest.org/)
[![Architecture](https://img.shields.io/badge/architecture-Clean%20%2F%20Layered-orange.svg)]()

> Aplicação desktop e de linha de comando para simulação de rendimentos de CDB e investimentos em juros compostos com aportes mensais recorrentes, projeção temporal analítica de metas patrimoniais, cálculo de Imposto de Renda regressivo, interface adaptativa **Mobile-Friendly / Desktop** e visualização gráfica de alta performance.

---

## Sumário

- [1. Visão Geral](#1-visão-geral)
- [2. Funcionalidades](#2-funcionalidades)
- [3. Stack Tecnológica e Justificativas](#3-stack-tecnológica-e-justificativas)
- [4. Arquitetura e Princípios de Design](#4-arquitetura-e-princípios-de-design)
  - [4.1 Estrutura de Diretórios](#41-estrutura-de-diretórios)
  - [4.2 Princípios SOLID Aplicados](#42-princípios-solid-aplicados)
- [5. Componentes e Responsabilidades do Código](#5-componentes-e-responsabilidades-do-código)
  - [5.1 Camada de Domínio (`src/domain/`)](#51-camada-de-domínio-srcdomain)
  - [5.2 Camada de Serviços (`src/services/`)](#52-camada-de-serviços-srcservices)
  - [5.3 Camada de Apresentação (`src/ui/`)](#53-camada-de-apresentação-srcui)
- [6. Regras de Negócio e Ciclo de Cálculo](#6-regras-de-negócio-e-ciclo-de-cálculo)
  - [6.1 Capitalização e Juros Compostos](#61-capitalização-e-juros-compostos)
  - [6.2 Tabela Regressiva de Imposto de Renda (IR)](#62-tabela-regressiva-de-imposto-de-renda-ir)
  - [6.3 Projeção Analítica de Metas em $O(1)$](#63-projeção-analítica-de-metas-em-o1)
- [7. Design System e Interface Mobile-Friendly (UI/UX)](#7-design-system-e-interface-mobile-friendly-uiux)
  - [7.1 Breakpoints e Comportamento Responsivo](#71-breakpoints-e-comportamento-responsivo)
  - [7.2 Grid Fluido de Cards de Métricas](#72-grid-fluido-de-cards-de-métricas)
  - [7.3 Paleta de Cores e Tipografia](#73-paleta-de-cores-e-tipografia)
- [8. Configuração do Ambiente e Instalação](#8-configuração-do-ambiente-e-instalação)
- [9. Execução da Aplicação](#9-execução-da-aplicação)
  - [9.1 Modo Gráfico (GUI)](#91-modo-gráfico-gui)
  - [9.2 Modo Terminal (CLI)](#92-modo-terminal-cli)
  - [9.3 Scripts de Automação (`project`)](#93-scripts-de-automação-project)
- [10. Testes Automatizados e Qualidade](#10-testes-automatizados-e-qualidade)
- [11. Build e Distribuição (.EXE)](#11-build-e-distribuição-exe)
- [12. Histórico de Melhorias e Correções](#12-histórico-de-melhorias-e-correções)

---

## 1. Visão Geral

O **CDB Simulator** foi desenvolvido para auxiliar investidores e pessoas físicas no planejamento e na visualização clara do impacto dos juros compostos ao longo do tempo. O projeto contempla tanto aplicações com taxa fixa (prefixadas em base anual ou mensal) quanto simulações de títulos pós-fixados atrelados ao CDI (ex.: 100%, 110% ou 120% do CDI com taxa anual parametrizável).

A aplicação conta com arquitetura responsiva que se molda dinamicamente ao tamanho da tela (de telas mobile compactas de 360px a monitores ultrawide), além de calcular deduções de **Imposto de Renda regressivo** e fornecer resoluções analíticas instantâneas de metas patrimoniais.

---

## 2. Funcionalidades

- **Interface Mobile-Friendly & Desktop Adaptativa:**
  - Redimensionamento inteligente em tempo real com breakpoint em 860px.
  - Empilhamento vertical com scroll fluido em janelas estreitas/mobile.
  - Disposição lado a lado em duas colunas em telas médias e desktop.
  - Suporte a resoluções compactas a partir de 360x520.
- **Simulação com Aportes Recorrentes:** Suporte a montante inicial guardado e contribuições mensais programadas.
- **Múltiplas Modalidades de Rendimento:**
  - Taxa prefixada com conversão equivalente composta: $i_{\text{mensal}} = (1 + i_{\text{anual}})^{1/12} - 1$ (ou taxa direta ao mês).
  - CDB pós-fixado em percentual do CDI (% do CDI) com **taxa CDI base anual configurável pelo usuário**.
- **Cálculo Automático de Imposto de Renda (IR Regressivo):** Dedução fiel da tabela de Renda Fixa brasileira (22,5% a 15,0%), exibindo tanto o valor bruto quanto o valor líquido resgatável.
- **Projeção Analítica de Metas Financeiras:** Algoritmo fechado em $O(1)$ baseado na fórmula logarítmica de anuidade com aportes antecipados, sem dependência de loops lentos.
- **Gráfico de Área de Alta Performance:** Renderização via `matplotlib` reutilizando instâncias de `FigureCanvasTkAgg` com atualização suave (`draw_idle`), evitando recriação de widgets ou vazamentos de memória.
- **Proteção Contra Sobrecarga (Anti-DoS):** Validação de valores nulos, negativos e teto máximo de prazo (100 anos / 1.200 meses) para proteger a aplicação contra travamento por consumo excessivo de memória.
- **Duas Interfaces de Acesso:**
  - **GUI Moderna:** Interface desktop com tema **Clean Light / Fintech** e suporte completo a **Modo Escuro** (Dark Mode), com alternância via botão no cabeçalho da barra lateral e persistência da preferência entre reinicializações (`~/.cdb_simulator_theme.json`). Toda a paleta (fundo, superfícies, inputs, cards, badges, botões, gráficos e legendas) se adapta dinamicamente ao tema escolhido.
  - **CLI (Terminal):** Modo console direto com validação de limites e suporte completo a Prefixado e CDI.
- **Automação Completa:** Scripts unificados (`.bat`, `.ps1`, `.sh`) com pipeline que só permite recompilar ou rodar o software se todos os testes unitários passarem.

---

## 3. Stack Tecnológica e Justificativas

| Tecnologia | Versão Mínima | Função no Projeto | Justificativa Técnica |
| :--- | :--- | :--- | :--- |
| **Python** | 3.13+ | Linguagem Base | Tipagem estática (`typing`), dataclasses imutáveis e ecossistema maduro para finanças e GUI desktop. |
| **CustomTkinter** | >= 6.0.0 | Toolkit de GUI Desktop | Extensão moderna sobre o Tkinter nativo. Fornece widgets modernos, cantos arredondados, paletas consistentes e suporte a High-DPI sem o overhead de Chromium/Electron. |
| **Matplotlib** | >= 3.8.0 | Motor Gráfico | Renderizador visual integrado à janela via `FigureCanvasTkAgg`. Reutilização de canvas para máxima fluidez e limpeza visual sem molduras pesadas (*despined*). |
| **Pytest** | >= 8.0.0 | Testes Unitários | Framework de testes rápido e conciso. Configurado via `pytest.ini` para execução direta. |
| **PyInstaller** | >= 6.0.0 | Empacotamento | Gera executáveis nativos independentes (`.exe` no Windows) sem exigir Python instalado na máquina final. |

---

## 4. Arquitetura e Princípios de Design

O projeto adota uma arquitetura em camadas (**Clean / Layered Architecture**), desacoplando inteiramente o motor de cálculo financeiro de qualquer dependência visual ou de infraestrutura externa.

```
                      ┌─────────────────────────┐
                      │    Camada de UI / Apres. │
                      │  (main_gui.py, CLI, GUI)│
                      └────────────┬────────────┘
                                   │  (Usa)
                                   ▼
                      ┌─────────────────────────┐
                      │   Camada de Serviços    │
                      │(InvestmentSimulatorServ)│
                      └────────────┬────────────┘
                                   │  (Injeta / Consome)
                                   ▼
                      ┌─────────────────────────┐
                      │    Camada de Domínio    │
                      │(YieldStrategy, Models)  │
                      └─────────────────────────┘
```

### 4.1 Estrutura de Diretórios

```text
CDB Simulator/
│
├── src/                                  # Código-fonte principal modularizado
│   ├── domain/                           # Regras de negócio puras (sem dependências de UI)
│   │   ├── __init__.py                   # Exportação explícita de símbolos do domínio
│   │   ├── models.py                     # Dataclasses de dados, DTOs e cálculo de IR
│   │   └── strategies.py                 # Contrato YieldStrategy, Prefixado e CDI
│   │
│   ├── services/                         # Casos de uso e orquestração financeira
│   │   ├── __init__.py
│   │   └── simulator_service.py          # Lógica de simulação, IR e metas analíticas
│   │
│   └── ui/                               # Camada de apresentação
│       ├── __init__.py
│       ├── cli.py                        # Interface de linha de comando
│       └── gui/                          # Interface gráfica desktop
│           ├── __init__.py
│           ├── app.py                    # Janela principal responsiva (Mobile/Desktop)
│           ├── components.py             # Cards de métricas, botões Pill e formatadores
│           └── chart.py                  # Canvas Matplotlib performático
│
├── tests/                                # Testes automatizados (pytest)
│   ├── test_domain.py                    # Testes de estratégias, CDI e IR regressivo
│   ├── test_publish.py                   # Testes da publicação do .exe (substituição e hash)
│   └── test_services.py                  # Testes do serviço, metas analíticas e limites
│
├── .gitignore                            # Exclusão de caches, executáveis e arquivos temporários
├── pytest.ini                            # Configuração global de execução do pytest
├── main_gui.py                           # Ponto de entrada oficial para a Interface Gráfica
├── main_cli.py                           # Ponto de entrada oficial para a Interface Terminal
├── preview.py                            # Utilitário de Live-Reload para desenvolvimento
├── publish.py                            # Copia o .exe compilado para a Área de Trabalho (substituição segura)
├── project.bat                           # Script utilitário para Windows CMD
├── project.ps1                           # Script utilitário para Windows PowerShell
├── project.sh                            # Script utilitário para Bash (Linux / Git Bash / WSL)
├── requirements.txt                      # Declaração formal de dependências do Python
└── update.txt                            # Guia rápido de compilação
```

### 4.2 Princípios SOLID Aplicados

1. **S — Single Responsibility Principle (SRP):** Cada módulo tem uma responsabilidade estrita (`models` para estruturas e IR, `strategies` para taxas, `chart` para visualização gráfica, `simulator_service` para evolução patrimonial).
2. **O — Open/Closed Principle (OCP):** A classe abstrata `YieldStrategy` define o contrato `get_monthly_rate()`. Para criar novas modalidades de investimento (ex.: *IPCA+*, *LCI/LCA com isenção*), basta estender a classe base sem modificar o serviço.
3. **L — Liskov Substitution Principle (LSP):** `CompoundInterestStrategy` e `CDIStrategy` implementam integralmente o contrato e são utilizadas intercambiavelmente.
4. **I — Interface Segregation Principle (ISP):** O contrato `YieldStrategy` é conciso e focado (`get_monthly_rate()` e `get_description()`).
5. **D — Dependency Inversion Principle (DIP):** O orquestrador depende da abstração `YieldStrategy`, permitindo injeção de dependência flexível e facilidade nos testes unitários.

---

## 5. Componentes e Responsabilidades do Código

### 5.1 Camada de Domínio (`src/domain/`)

- **[models.py](file:///C:/Users/crist/OneDrive/Área%20de%20Trabalho/CDB%20Simulator/src/domain/models.py):**
  - `calcular_aliquota_ir(meses: int) -> float`: Retorna a alíquota de IR de acordo com o prazo.
  - `MonthlyRecord`: Registro individual de cada mês.
  - `SimulationParams`: Parâmetros imutáveis de entrada.
  - `SimulationResult`: DTO completo com montante investido, juros brutos, saldo bruto, alíquota de IR, total de IR retido, juros líquidos e saldo líquido final.
- **[strategies.py](file:///C:/Users/crist/OneDrive/Área%20de%20Trabalho/CDB%20Simulator/src/domain/strategies.py):**
  - `CompoundInterestStrategy`: Suporte à taxa equivalente composta $((1 + i)^{1/12} - 1)$ ou nominal.
  - `CDIStrategy`: Aplica o percentual contratado sobre a taxa CDI base anual informada pelo usuário.

### 5.2 Camada de Serviços (`src/services/`)

- **[simulator_service.py](file:///C:/Users/crist/OneDrive/Área%20de%20Trabalho/CDB%20Simulator/src/services/simulator_service.py):**
  - `simulate`: Executa o avanço mensal respeitando o teto de segurança `MAX_SIMULATION_MONTHS` e computa o resumo bruto e líquido pós-IR.
  - `calculate_months_to_target`: Resolve matematicamente em $O(1)$ o número de meses necessários para atingir qualquer meta patrimonial positiva.

### 5.3 Camada de Apresentação (`src/ui/`)

- **[app.py](file:///C:/Users/crist/OneDrive/Área%20de%20Trabalho/CDB%20Simulator/src/ui/gui/app.py):**
  - Janela principal responsiva equipada com container `CTkScrollableFrame`.
  - Mecanismo dinâmico `_apply_responsive_layout(width)` disparado pelo evento `<Configure>`.
  - Reorganização automática dos cards de métricas entre 2 e 5 colunas.
  - Alternância dinâmica de campos: ao selecionar CDB pós-fixado, abre o campo de **Taxa CDI Base (% a.a.)**.
  - **Botão de Alternância de Tema:** Permite alternar entre Modo Claro e Modo Escuro com persistência da preferência em arquivo JSON local (`~/.cdb_simulator_theme.json`). A reaplicação de cores é aplicada em toda a interface (fundo, superfícies, inputs, cards, badges, botões e gráficos Matplotlib).
  - Validações completas para valores negativos, metas inválidas e prazos fracionários.
- **[chart.py](file:///C:/Users/crist/OneDrive/Área%20de%20Trabalho/CDB%20Simulator/src/ui/gui/chart.py):**
  - Controlador gráfico de alta eficiência que reutiliza a mesma `Figure` e `Canvas`, limpando apenas os eixos (`ax.clear()`) e desenhando de forma assíncrona (`draw_idle()`).
- **[cli.py](file:///C:/Users/crist/OneDrive/Área%20de%20Trabalho/CDB%20Simulator/src/ui/cli.py):**
  - Interface via terminal com suporte a CDI customizado, metas e apresentação detalhada de IR.

---

## 6. Regras de Negócio e Ciclo de Cálculo

### 6.1 Capitalização e Juros Compostos

Para taxas anuais, a taxa mensal equivalente utilizada é:
$$i_{\text{mensal}} = (1 + i_{\text{anual}})^{\frac{1}{12}} - 1$$

O saldo evolui mês a mês com aportes antecipados:
$$\text{Saldo Provisório} = \text{Saldo Anterior} + \text{Aporte}$$
$$\text{Rendimento do Mês} = \text{Saldo Provisório} \times i_{\text{mensal}}$$
$$\text{Saldo Final} = \text{Saldo Provisório} + \text{Rendimento do Mês}$$

### 6.2 Tabela Regressiva de Imposto de Renda (IR)

| Prazo da Aplicação | Alíquota de IR |
| :--- | :--- |
| Até 6 meses (180 dias) | **22,5%** sobre o rendimento |
| De 7 a 12 meses (181 a 360 dias) | **20,0%** sobre o rendimento |
| De 13 a 24 meses (361 a 720 dias) | **17,5%** sobre o rendimento |
| Acima de 24 meses (mais de 720 dias) | **15,0%** sobre o rendimento |

$$\text{IR Retido} = \text{Total em Juros Brutos} \times \text{Alíquota}$$
$$\text{Saldo Líquido} = \text{Total Investido} + (\text{Total em Juros Brutos} - \text{IR Retido})$$

### 6.3 Projeção Analítica de Metas em $O(1)$

A quantidade de meses $n$ para atingir o valor futuro $FV$ com aporte antecipado $PMT$ e valor inicial $PV$ é obtida diretamente por:
$$n = \left\lceil \frac{\ln\left(\frac{FV + k}{PV + k}\right)}{\ln(1 + r)} \right\rceil \quad \text{onde } k = \frac{PMT \cdot (1 + r)}{r}$$

---

## 7. Design System e Interface Mobile-Friendly (UI/UX)

A interface gráfica foi concebida para oferecer uma experiência consistente em qualquer formato de tela, seja em monitores desktop de alta resolução ou janelas estreitas estilo mobile.

### 7.1 Breakpoints e Comportamento Responsivo

```
  Largura da Janela >= 860px (Desktop):
  ┌───────────────────────┬────────────────────────────────────────┐
  │ Sidebar de Parâmetros │ Área Principal (Cards + Gráfico Amplo) │
  │ (Coluna Fixa 340px)   │ (Coluna Flexível com peso 1)           │
  └───────────────────────┴────────────────────────────────────────┘

  Largura da Janela < 860px (Mobile / Telas Estreitas):
  ┌────────────────────────────────────────────────────────┐
  │ Sidebar de Configuração (Largura Total 100%)           │
  ├────────────────────────────────────────────────────────┤
  │ Cards de Métricas (Grade em 2 Colunas)                 │
  ├────────────────────────────────────────────────────────┤
  │ Gráfico de Rendimento Responsivo                       │
  └────────────────────────────────────────────────────────┘
```

- **Scroll Global:** A janela possui container de rolagem suave (`CTkScrollableFrame`), permitindo que formulários e gráficos sejam acessados mesmo em resoluções verticais reduzidas sem truncamento.
- **Tamanho Mínimo Reduzido:** Suporte nativo para janelas a partir de **360x520 pixels**.

### 7.2 Grid Fluido de Cards de Métricas

- **Modo Desktop (≥ 860px):** 5 cards alinhados horizontalmente (1 linha x 5 colunas).
- **Modo Mobile (< 860px):** 5 cards distribuídos em grade de 2 colunas:
  - Linha 1: *Total Aportado* e *Lucro Bruto*.
  - Linha 2: *Montante Bruto* e *Líquido (Pós-IR)*.
  - Linha 3: *Tempo p/ Meta* (expandido ocupando as duas colunas).

### 7.3 Paleta de Cores e Tipografia

- **Paleta de Cores:**
  - Fundo da Aplicação: `#F9F9FB` (Off-white).
  - Superfícies dos Cards: `#FFFFFF` com bordas sutis `#EBEBEB`.
  - Acentos de Ganho / Lucro: `#24C270` (Verde menta vibrante).
  - Card de Destaque Líquido: Fundo `#EBF7EE` com borda `#BCE8CB`.
  - Botão Primário: `#1C1C1E` com curvatura estilo Pílula (`corner_radius=22`).
- **Cards de Métricas:**
  1. *Total Aportado:* Somatório do capital próprio do investidor.
  2. *Lucro Bruto:* Total gerado exclusivamente por juros com badge percentual (`+X.X%`).
  3. *Montante Bruto:* Saldo acumulado antes dos tributos.
  4. *Líquido (Pós-IR):* Valor real no bolso do investidor com badge da alíquota aplicada (`IR 15.0%`).
  5. *Tempo p/ Meta:* Estimativa formatada em anos e meses para alcance do objetivo.

- **Modo Claro / Modo Escuro (Tema Dinâmico):**
  - O tema padrão é **Claro**, com paleta *Clean Warm Light* (#F9F9FB, superfícies #FFFFFF, acentos em verde menta #24C270).
  - O **Modo Escuro** usa paleta própria (#121214 fundo, #1C1C1E superfícies, textos em tons claros, acentos verdes mais suaves #6FE29F) para reduzir cansaço visual em ambientes com pouca luz.
  - A alternância é feita pelo botão "🌙 Escuro" / "☀️ Claro" no cabeçalho da barra lateral e a escolha é persistida automaticamente entre reinicializações.

---

## 8. Configuração do Ambiente e Instalação

### Pré-requisitos
- **Python 3.13 ou superior** configurado no `PATH`.
- Gerenciador de pacotes `pip`.

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Executar os testes automatizados
pytest
```

---

## 9. Execução da Aplicação

### 9.1 Modo Gráfico (GUI)
```bash
python main_gui.py
```

### 9.2 Modo Terminal (CLI)
```bash
python main_cli.py
```

### 9.3 Scripts de Automação (`project`)

| Ação | Windows CMD | Windows PowerShell | Git Bash / Linux |
| :--- | :--- | :--- | :--- |
| **Live-Reload (Preview)** | `project preview` | `.\project.ps1 preview` | `./project.sh preview` |
| **Rodar GUI (com validação prévia)** | `project run` | `.\project.ps1 run` | `./project.sh run` |
| **Rodar CLI (com validação prévia)** | `project run cli` | `.\project.ps1 run cli` | `./project.sh run cli` |
| **Executar Testes Unitários** | `project test` | `.\project.ps1 test` | `./project.sh test` |
| **Testar, Compilar e Publicar o .exe** | `project update` | `.\project.ps1 update` | `./project.sh update` |

---

## 10. Testes Automatizados e Qualidade

O projeto conta com uma suíte de testes unitários que valida 100% das regras críticas de negócio antes de qualquer execução ou empacotamento:

```bash
pytest
```

### Cobertura de Testes
- **Taxas de Juros (`test_domain.py`):**
  - Taxa direta ao mês.
  - Taxa anual nominal vs. taxa equivalente composta.
  - Estratégia de CDI com taxas base customizadas.
  - Tabela regressiva completa de Imposto de Renda (todas as 4 faixas).
- **Serviço e Simulações (`test_services.py`):**
  - Simulação precisa com aporte e rentabilidade mês a mês.
  - Apuração exata de IR retido e saldo líquido.
  - Cálculo analítico de tempo até a meta ($O(1)$).
  - Tratamento de metas já atingidas ou inalcançáveis.
  - Proteção contra limites abusivos de prazo (limite de 100 anos anti-DoS).
- **Publicação do Executável (`test_publish.py`):**
  - Substituição do `.exe` na Área de Trabalho pela versão nova.
  - Bloqueio quando o executável está em execução.
  - Detecção de versão já publicada (no-op) e modo `--dry-run`.

---

## 11. Build e Distribuição (.EXE)

A compilação do executável é gerenciada pelo comando `project update`:
1. Executa a suíte de testes unitários automatizados com `pytest`.
2. Em caso de falha, o build é **imediatamente bloqueado**.
3. Se todos os testes passarem, o PyInstaller compila um novo executável otimizado em:
   ```text
   dist/CDB_Simulator.exe
   ```
4. Por fim, o `publish.py` copia o novo executável para a **Área de Trabalho**,
   substituindo a versão anterior (sem manter backup) e conferindo o SHA-256
   dos dois arquivos.

### 11.1 Por que existe o `publish.py`?

A Área de Trabalho deste projeto está dentro do OneDrive. Arquivos `.exe`
sincronizados (*Files On-Demand*) são **reparse points**, e o Windows Explorer
costuma falhar ao substituir/excluir esses arquivos com erros de sincronização
("não foi possível excluir o arquivo", "arquivo em uso", `0x800701AA`, etc.).

O `publish.py` faz a troca na ordem que funciona de forma confiável, sem passar
pela camada de sincronização do Explorer: copia o novo `.exe` preservando a data
da compilação (removendo o antigo apenas se a sobrescrita direta falhar) e
valida o hash. Ele também **aborta** se o simulador estiver aberto (arquivo travado).

Comandos úteis:

```bash
python publish.py              # publica dist/CDB_Simulator.exe na Área de Trabalho
python publish.py --dry-run    # apenas mostra o que seria feito
python publish.py --dest PATH  # publica em outra pasta
```

---

## 12. Histórico de Melhorias e Correções

- **Interface Mobile-Friendly e Layout Responsivo (UX):**
  - Implementado sistema reativo com detecção de redimensionamento em tempo real.
  - Breakpoint dinâmico em 860px alternando entre visualização empilhada vertical (mobile) e painel duplo lateral (desktop).
  - Grid flexível de cards (2 colunas em mobile e 5 colunas em desktop).
  - Janela mínima ajustada para 360x520 com suporte a rolagem integral via `CTkScrollableFrame`.
- **Matemática Financeira:** Substituída a conversão linear simples por taxa equivalente mensal exponencial composta.
- **Tributação (IR):** Incorporado o cálculo oficial do Imposto de Renda regressivo para CDBs e Renda Fixa, apresentando montantes brutos e líquidos.
- **CDI Parametrizável:** Adicionado campo dinâmico na interface gráfica e na CLI para alteração da taxa anual base do CDI.
- **Otimização de Desempenho:**
  - Resolução da meta patrimonial migrada de loop iterativo para fórmula fechada analítica em $O(1)$.
  - Canvas do Matplotlib refatorado para reuso de instância com `ax.clear()` e `draw_idle()`, eliminando flickering e vazamento de memória.
- **Resiliência e Segurança:**
  - Limite de segurança anti-DoS para prazos longos (`MAX_SIMULATION_MONTHS = 1200`).
  - Validação estrita de metas financeiras positivas e prazos não nulos.
  - Adicionado `.gitignore` completo e configuração oficial `pytest.ini`.
- **Tema Claro / Escuro:**
  - Implementado botão de alternância de tema na barra lateral da GUI com persistência da preferência entre sessões.
  - Criação de paletas de cores dedicadas para Modo Claro e Modo Escuro, aplicadas dinamicamente a inputs, cards, badges, botões e gráficos Matplotlib.
  - Quebra de ciclo de importação entre pacotes `ui` e `ui.gui` via importação preguiçosa (PEP 562), permitindo inicialização estável do executável `.exe`.

---
# CDB_SIMULATOR
