# CDB Simulator • Planejamento e Simulação de Renda Fixa

[![Python Version](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/)
[![UI](https://img.shields.io/badge/GUI-CustomTkinter-emerald.svg)](https://github.com/TomSchimansky/CustomTkinter)
[![Tests](https://img.shields.io/badge/tests-pytest-green.svg)](https://docs.pytest.org/)
[![Architecture](https://img.shields.io/badge/architecture-Clean%20%2F%20Layered-orange.svg)]()

> Aplicação desktop (GUI) para simulação de rendimentos de CDB e investimentos em juros compostos com aportes mensais recorrentes, projeção temporal analítica de metas patrimoniais, cálculo de Imposto de Renda regressivo, interface adaptativa **Mobile-Friendly / Desktop** e visualização gráfica de alta performance.

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
  - [5.2 Camada de Casos de Uso (`src/use_cases/`)](#52-camada-de-casos-de-uso-srcuse_cases)
  - [5.3 Camada de Serviços (`src/services/`)](#53-camada-de-serviços-srcservices)
  - [5.4 Camada de Repositórios (`src/repositories/`)](#54-camada-de-repositórios-srcrepositories)
  - [5.5 Camada de Apresentação (`src/ui/`)](#55-camada-de-apresentação-srcui)
  - [5.6 Configuração (`src/config.py`)](#56-configuração-srcconfigpy)
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
- [12. Variáveis de Ambiente (`.env`)](#12-variáveis-de-ambiente-env)
- [13. Histórico de Melhorias e Correções](#13-histórico-de-melhorias-e-correções)

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
- **Interface Gráfica (GUI):** Interface desktop com tema **Clean Light / Fintech** e suporte completo a **Modo Escuro** (Dark Mode), com alternância via botão no cabeçalho da barra lateral e persistência da preferência entre reinicializações (`~/.cdb_simulator_theme.json`). Toda a paleta (fundo, superfícies, inputs, cards, badges, botões, gráficos e legendas) se adapta dinamicamente ao tema escolhido.
- **Controle Financeiro persistente:** Nova seção da GUI para registrar receitas, despesas e aportes, com categorias personalizáveis, filtros temporais, histórico editável e gráficos dinâmicos. Os dados ficam em SQLite local, criptografados em repouso, fora do repositório.
- **Camada de Casos de Uso (Use Cases):** Orquestração de regras de negócio separada da UI, permitindo reutilização da lógica em outras interfaces (CLI, API, etc.) e facilitando testes.
- **Automação Completa:** Scripts unificados (`.bat`, `.ps1`, `.sh`) com pipeline que só permite rodar o software se todos os testes unitários passarem.

---

## 3. Stack Tecnológica e Justificativas

| Tecnologia | Versão Mínima | Função no Projeto | Justificativa Técnica |
| :--- | :--- | :--- | :--- |
| **Python** | 3.13+ | Linguagem Base | Tipagem estática (`typing`), dataclasses imutáveis e ecossistema maduro para finanças e GUI desktop. |
| **CustomTkinter** | == 6.0.0 | Toolkit de GUI Desktop | Extensão moderna sobre o Tkinter nativo. Fornece widgets modernos, cantos arredondados, paletas consistentes e suporte a High-DPI sem o overhead de Chromium/Electron. |
| **Matplotlib** | == 3.8.0 | Motor Gráfico | Renderizador visual integrado à janela via `FigureCanvasTkAgg`. Reutilização de canvas para máxima fluidez e limpeza visual sem molduras pesadas (*despined*). |
| **Pytest** | == 8.0.0 | Testes Unitários | Framework de testes rápido e conciso. Configurado via `pytest.ini` para execução direta. |
| **PyInstaller** | == 6.10.0 | Empacotamento | Gera executáveis nativos independentes (`.exe` no Windows) sem exigir Python instalado na máquina final. |
| **cryptography** | == 42.0.8 | Criptografia | Criptografia de arquivo (Fernet/AES-128 + HMAC-SHA256) para o banco de dados do Controle Financeiro em repouso. |
| **python-dotenv** | == 1.0.0 | Configuração | Carrega variáveis de ambiente do arquivo `.env` para configuração externa tipada. |

---

## 4. Arquitetura e Princípios de Design

O projeto adota uma arquitetura em camadas (**Clean / Layered Architecture**), desacoplando inteiramente o motor de cálculo financeiro de qualquer dependência visual ou de infraestrutura externa.

```
                      ┌─────────────────────────┐
                      │    Camada de UI / Apres. │
                      │  (main_gui.py, GUI)      │
                      └────────────┬────────────┘
                                   │  (Usa)
                                   ▼
                      ┌─────────────────────────┐
                      │   Camada de Casos de Uso │
                      │   (src/use_cases/)       │
                      └────────────┬────────────┘
                                   │  (Orquestra)
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
                      └────────────┬────────────┘
                                   │  (Persiste)
                                   ▼
                      ┌─────────────────────────┐
                      │   Camada de Repositórios │
                      │(SQLite criptografado)   │
                      └─────────────────────────┘
```

### 4.1 Estrutura de Diretórios

```text
CDB Simulator/
│
├── src/                                  # Código-fonte principal modularizado
│   ├── config.py                         # Configuração via .env (NOVO)
│   ├── domain/                           # Regras de negócio puras (sem dependências de UI)
│   │   ├── __init__.py                   # Exportação explícita de símbolos do domínio
│   │   ├── constants.py                  # Constantes centralizadas de negócio (NOVO)
│   │   ├── financial_models.py           # Entidades do controle financeiro
│   │   ├── financial_utils.py            # Utilitários financeiros puros (NOVO)
│   │   ├── models.py                     # Dataclasses de dados, DTOs e cálculo de IR
│   │   └── strategies.py                 # Contrato YieldStrategy, Prefixado e CDI
│   │
│   ├── services/                         # Lógica de negócio e orquestração
│   │   ├── __init__.py
│   │   ├── simulator_service.py          # Motor de simulação, IR e metas analíticas
│   │   └── financial_service.py          # Casos de uso, filtros e agregações financeiras
│   │
│   ├── repositories/                     # Adaptadores de persistência
│   │   ├── __init__.py
│   │   ├── financial_repository.py       # Banco SQLite versionado do Controle Financeiro
│   │   ├── db_encryption.py              # Criptografia do banco SQLite (Fernet/AES-128)
│   │   └── interfaces.py                 # Protocolo abstrato para repositório (NOVO)
│   │
│   ├── use_cases/                        # Camada de Casos de Uso (NOVO)
│   │   ├── __init__.py
│   │   ├── simulate_investment.py        # Caso de uso de simulação de investimento
│   │   └── financial_use_cases.py        # Casos de uso do controle financeiro
│   │
│   └── ui/                               # Camada de apresentação
│       ├── __init__.py
│       └── gui/                          # Interface gráfica desktop
│           ├── __init__.py
│           ├── app.py                    # Janela principal responsiva (Mobile/Desktop)
│           ├── components.py             # Cards de métricas, botões Pill e formatadores
│           ├── chart.py                  # Canvas Matplotlib performático
│           ├── theme.py                  # Paletas de cores (Claro/Escuro) — módulo independente
│           └── financial/                # Módulo do Controle Financeiro
│               ├── __init__.py
│               ├── dashboard.py          # Tela do Controle Financeiro
│               └── financial_charts.py   # Gráficos financeiros (donut e barras)
│
├── tests/                                # Testes automatizados (pytest)
│   ├── test_domain.py                    # Testes de estratégias, CDI e IR regressivo
│   ├── test_financial.py                 # Testes do Controle Financeiro
│   ├── test_security_and_validations.py  # Testes de segurança e validações
│   ├── test_services.py                  # Testes do serviço, metas analíticas e limites
│   └── test_use_cases.py                 # Testes de casos de uso (NOVO)
│
├── .gitignore                            # Exclusão de caches, executáveis e arquivos temporários
├── pytest.ini                            # Configuração global de execução do pytest
├── main_gui.py                           # Ponto de entrada oficial para a Interface Gráfica
├── project.bat                           # Script utilitário para Windows CMD
├── project.ps1                           # Script utilitário para Windows PowerShell
├── project.sh                            # Script utilitário para Bash (Linux / Git Bash / WSL)
├── requirements.txt                      # Declaração formal de dependências do Python
├── update.txt                            # Guia rápido de compilação
├── CDB_Simulator.spec                    # Spec do PyInstaller para build do executável
└── CDB_Simulator.iss                     # Script Inno Setup para instalador Windows
```

### 4.2 Princípios SOLID Aplicados

1. **S — Single Responsibility Principle (SRP):** Cada módulo tem uma responsabilidade estrita (`models` para estruturas e IR, `strategies` para taxas, `chart` para visualização gráfica, `simulator_service` para evolução patrimonial, `use_cases` para orquestração de regras de negócio).

2. **O — Open/Closed Principle (OCP):** A classe abstrata `YieldStrategy` define o contrato `get_monthly_rate()`. Para criar novas modalidades de investimento (ex.: *IPCA+*, *LCI/LCA com isenção*), basta estender a classe base sem modificar o código existente.

3. **L — Liskov Substitution Principle (LSP):** `CompoundInterestStrategy` e `CDIStrategy` implementam integralmente o contrato e são utilizadas intercambiavelmente.

4. **I — Interface Segregation Principle (ISP):** O contrato `YieldStrategy` é conciso e focado (`get_monthly_rate()` e `get_description()`). O `FinancialRepositoryProtocol` define apenas os métodos necessários de persistência.

5. **D — Dependency Inversion Principle (DIP):** Os serviços e casos de uso dependem de abstrações (`YieldStrategy`, `FinancialRepositoryProtocol`), permitindo injeção de dependência flexível e facilidade nos testes unitários.

---

## 5. Componentes e Responsabilidades do Código

### 5.1 Camada de Domínio (`src/domain/`)

- **[models.py]:** `calcular_aliquota_ir(meses: int) -> float`, `MonthlyRecord`, `SimulationParams`, `SimulationResult`.
- **[strategies.py]:** `CompoundInterestStrategy` (taxa prefixada), `CDIStrategy` (CDB pós-fixado % do CDI), `YieldStrategy` (contrato abstrato).
- **[financial_models.py]:** `TransactionType`, `FinancialCategory`, `FinancialTransaction`, `FinancialSummary`.
- **[constants.py]:** Constantes centralizadas de negócio e segurança (`MAX_SIMULATION_MONTHS`, `ZERO_TOLERANCE`, `LIMITE_MONETARIO`, limites de taxa, faixas de IR).
- **[financial_utils.py]:** Utilitários financeiros puros (`parse_amount_to_cents`, `format_cents`, `parse_br_date`, `period_range`, agregações).

### 5.2 Camada de Casos de Uso (`src/use_cases/`) — NOVA CAMADA

- **[simulate_investment.py]:** `SimulateInvestmentUseCase` com DTOs `SimulationInput` e `SimulationOutput`. Orquestra conversão de valores, validação de limites, criação de estratégia, chamada ao serviço e retorno de resultado para a UI.
- **[financial_use_cases.py]:** `FinancialUseCases`. CRUD de categorias e transações, consultas agregadas.

### 5.3 Camada de Serviços (`src/services/`)

- **[simulator_service.py]:** `InvestmentSimulatorService.simulate()`, `calculate_months_to_target()`, constantes de segurança (`MAX_SIMULATION_MONTHS`, `ZERO_TOLERANCE`, `MAX_SIMULATION_BALANCE`).
- **[financial_service.py]:** `FinancialService` — gerencia categorias, transações, resumos, filtros e agregações. Delega métodos estáticos para `financial_utils`.

### 5.4 Camada de Repositórios (`src/repositories/`)

- **[financial_repository.py]:** `FinancialRepository` implementa `FinancialRepositoryProtocol`. CRUD completo, criptografia opcional, tabela de auditoria (`audit_log`), consultas SQL agregadas.
- **[db_encryption.py]:** `DatabaseEncryption` — Fernet/AES-128 + HMAC-SHA256, gerenciamento de chave via variável de ambiente ou arquivo `.db_key`.
- **[interfaces.py]:** `FinancialRepositoryProtocol` — protocolo abstrato para repositórios, permite injeção de dependência e mock em testes.

### 5.5 Camada de Apresentação (`src/ui/`)

- **[app.py]:** `ModernAppGUI` — janela principal responsiva, usa casos de uso para lógica de negócio, imports relativos, tratamento de exceções específico.
- **[components.py]:** `MetricCard`, `PillButton`, `formatar_moeda()`, `formatar_tempo()`.
- **[theme.py]:** `PALETTES`, `THEME_MODES` — módulo independente para evitar ciclos de importação.
- **[chart.py]:** `InvestmentChart` — gráficos Matplotlib reutilizáveis com `draw_idle()`.
- **[financial/dashboard.py]:** `FinancialDashboard` — tela completa do Controle Financeiro.
- **[financial/financial_charts.py]:** Gráficos de donut e barras.

### 5.6 Configuração (`src/config.py`) — NOVO

Carrega variáveis de ambiente do arquivo `.env` (se existir) via `python-dotenv` e expõe configurações tipadas para toda a aplicação.

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

A alíquota regressiva segue a tabela oficial brasileira baseada em **dias corridos**:

| Prazo da Aplicação | Alíquota de IR |
| :--- | :--- |
| Até 180 dias | **22,5%** sobre o rendimento |
| De 181 a 360 dias | **20,0%** sobre o rendimento |
| De 361 a 720 dias | **17,5%** sobre o rendimento |
| Acima de 720 dias | **15,0%** sobre o rendimento |

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

### Configuração externa (`.env`)

Crie um arquivo `.env` na raiz do projeto (copiando `.env.example`) para configurar a aplicação externamente:

```env
CDB_DB_ENCRYPTION_KEY=sua_chave_fernet_aqui
CDB_APP_THEME=Light
CDB_MAX_SIMULATION_MONTHS=1200
CDB_LIMITE_MONETARIO=1000000000000.0
```

---

## 9. Execução da Aplicação

### 9.1 Modo Gráfico (GUI)
```bash
python main_gui.py
```

### 9.2 Scripts de Automação (`project`)

| Ação | Windows CMD | Windows PowerShell | Git Bash / Linux |
| :--- | :--- | :--- | :--- |
| **Rodar GUI (com validação prévia)** | `project run` | `.\project.ps1 run` | `./project.sh run` |
| **Executar Testes Unitários** | `project test` | `.\project.ps1 test` | `./project.sh test` |

### 9.3 Gerar o Executável (.EXE) para Desktop

O CDB Simulator pode ser empacotado em um único arquivo `.exe` que roda em qualquer Windows sem precisar de Python instalado.

```bash
# Windows CMD
project update

# Windows PowerShell
.\project.ps1 update

# Git Bash / Linux / WSL
./project.sh update
```

O que o comando `update` faz:
1. Executa a suíte de testes com `pytest`. Se algum falhar, o build é **bloqueado**.
2. Gera o executável com PyInstaller usando o arquivo `CDB_Simulator.spec`.
3. O resultado fica em: `dist/CDB_Simulator.exe`

#### Onde os dados ficam salvos?

O banco de dados financeiro (criptografado) é salvo em:
```
%USERPROFILE%\.cdb_simulator\
```
Exemplo: `C:\Users\SeuNome\.cdb_simulator\financial.sqlite3.enc`

> ⚠️ **Importante:** Atualizar o `.exe` **não apaga** seus dados. O banco fica fora da pasta do programa. Porém, se você formatar o PC ou excluir essa pasta, os dados serão perdidos. Use o botão **Backup** na tela do Controle Financeiro para salvar uma cópia segura (`.enc` + `.db_key`) em outro local (OneDrive, pendrive, etc.).

#### Instalador opcional

Se preferir um instalador com atalho no Iniciar e desinstalador, você pode empacotar o `dist/CDB_Simulator.exe` com o [Inno Setup](https://jrsoftware.org/isinfo.php) (gratuito) ou [NSIS](https://nsis.sourceforge.net/). O instalador **não deve remover** a pasta `~/.cdb_simulator/` durante a desinstalação.

---

## 10. Segurança e Criptografia em Repouso

### 10.1 Banco de Dados do Controle Financeiro

O banco de dados SQLite do **Controle Financeiro** (`~/.cdb_simulator/financial.sqlite3`) é armazenado **criptografado em repouso** utilizando **Fernet (AES-128 CBC + HMAC-SHA256)** da biblioteca [`cryptography`](https://cryptography.io/).

- O arquivo real mantido em disco é `financial.sqlite3.enc` (criptografado).
- Enquanto a aplicação está em execução, o banco é descriptografado para um **arquivo temporário** protegido.
- Ao encerrar a aplicação, o banco é recriptografado de volta para o `.enc` e o temporário é removido.
- Uma chave simétrica é gerada automaticamente na primeira execução e armazenada em `~/.cdb_simulator/.db_key` com permissões restritas (`0600` em sistemas Unix).

> ⚠️ **Importante:** Faça backup do arquivo `.db_key` junto com o banco `.enc`. Sem a chave, não é possível recuperar os dados financeiros criptografados.

### 10.2 Correções de Bugs e Vulnerabilidades

A seguir, todas as correções aplicadas nas versões recentes:

| # | Problema | Severidade | Correção |
|---|----------|------------|----------|
| 1 | **IR regressivo por meses** (deveria ser dias) | Alta | `calcular_aliquota_ir` agora recebe `dias` (faixas: ≤180, 181–360, 361–720, >720), alinhado com a documentação de negócio. |
| 2 | **Uso de `float` em cálculos monetários** | Alta | O `InvestmentSimulatorService` agora usa `decimal.Decimal` internamente, arredondando a cada mês com `ROUND_HALF_UP`, eliminando erros de ponto flutuante. |
| 3 | **Banco SQLite não criptografado** | Alta | Banco financeiro armazenado em `.enc` (criptografado) via Fernet/AES-128 + HMAC-SHA256; descriptografado temporariamente apenas durante a execução. |
| 4 | **Validação silenciosa do CDI Base** | Média | A GUI agora exibe `messagebox.showerror` e impede o cálculo se o CDI base for inválido, em vez de usar silenciosamente o valor padrão 10.75. |
| 5 | **Sem limite superior para taxa/CDI** | Média | Validação de taxa máxima (0–100% para juros, 0–500% para CDI, 0–100% para CDI base) na GUI e CLI. |
| 6 | **Importação circular frágil** | Baixa | Criado `src/ui/gui/theme.py` com `PALETTES` e `THEME_MODES`, importado por `components.py` e `chart.py`, eliminando o ciclo. |
| 7 | **Truncamento silencioso do período** | Baixa | Novo campo `truncado` em `SimulationResult`, preenchido quando o período excede 1200 meses. |
| 8 | **Comparação exata de float com zero** | Baixa | Substituída por tolerância `abs(valor) < 1e-12` (`ZERO_TOLERANCE`). |
| 9 | **Código morto na raiz** | Baixa | Arquivos antigos `simulador.py` e `app_gui.py` (versões não utilizadas) removidos. O único ponto de entrada é `main_gui.py` → `src/ui/gui/app.py`. |
| 10 | **Dependências não fixadas** | Baixa | `requirements.txt` agora usa versões fixas (`==`) para reprodutibilidade de builds. |
| 11 | **Sem tratamento genérico de exceções na GUI** | Baixa | `on_simulate_click` agora captura `Exception` genérico com `messagebox.showerror` amigável. |
| 12 | **Sem auditoria de alterações financeiras** | Baixa | Nova tabela `audit_log` registra INSERT, UPDATE e DELETE de transações com timestamps. |
| 13 | **Imports absolutos acoplados (`src.`)** | Média | Substituídos por imports relativos em todo o código-fonte. |
| 14 | **Lógica de negócio na UI** | Média | Nova camada de Casos de Uso (`src/use_cases/`) orquestra regras de negócio, separando UI de domínio. |
| 15 | **Constantes espalhadas** | Média | Constantes centralizadas em `src/domain/constants.py` (single source of truth). |
| 16 | **Sem interface abstrata para repositório** | Média | Criado `FinancialRepositoryProtocol` em `src/repositories/interfaces.py`. |

### 10.3 Testes Automatizados e Qualidade

O projeto conta com uma suíte de testes unitários que valida 100% das regras críticas de negócio antes de qualquer execução ou empacotamento:

```bash
pytest
```

### Cobertura de Testes

- **Taxas de Juros (`test_domain.py`):**
  - Taxa direta ao mês.
  - Taxa anual nominal vs. taxa equivalente composta.
  - Estratégia de CDI com taxas base customizadas.
  - Tabela regressiva completa de Imposto de Renda (todas as 4 faixas, baseada em dias).
- **Segurança e Validações (`test_security_and_validations.py`):**
  - IR regressivo por dias (não mais por meses).
  - Precisão Decimal no simulador (sem erro de ponto flutuante).
  - Criptografia do banco SQLite em repouso.
  - Validação de limites de taxa e CDI.
  - Módulo theme independente (sem importação circular).
  - Truncamento do período (campo `truncado`).
  - Tolerância de zero (`ZERO_TOLERANCE = 1e-12`).
  - Dependências fixadas no `requirements.txt`.
  - Auditoria de transações (INSERT/UPDATE/DELETE).
- **Serviço e Simulações (`test_services.py`):**
  - Simulação precisa com aporte e rentabilidade mês a mês.
  - Apuração exata de IR retido e saldo líquido.
  - Cálculo analítico de tempo até a meta ($O(1)$).
  - Tratamento de metas já atingidas ou inalcançáveis.
  - Proteção contra limites abusivos de prazo (limite de 100 anos anti-DoS).
- **Controle Financeiro (`test_financial.py`):**
  - Cálculos, persistência, filtros, agregações, edição, exclusão e receita zero.
- **Casos de Uso (`test_use_cases.py`) — NOVO:**
  - Simulação com taxa prefixada.
  - Simulação com CDI.
  - Validação de valores negativos rejeitados.
  - Validação de taxa acima do limite rejeitada.
  - Validação de percentual CDI acima do limite rejeitado.
  - Validação de CDI base inválido rejeitado.
  - Validação de meta zero rejeitada.
  - Truncamento de prazo excedente ao limite anti-DoS.
  - Cálculo de IR com datas de início e fim.
  - Campos obrigatórios do output.
  - Injeção de dependência no caso de uso.

---

## 11. Build e Distribuição (.EXE)

A compilação do executável é gerenciada pelo comando `project update`:

1. Executa a suíte de testes unitários automatizados com `pytest`.
2. Em caso de falha, o build é **imediatamente bloqueado**.
3. Se todos os testes passarem, o PyInstaller compila um novo executável otimizado em:
   ```text
   dist/CDB_Simulator.exe
   ```

O executável pode ser distribuído independentemente, não exigindo Python instalado na máquina final.

---

## 12. Variáveis de Ambiente (`.env`)

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `CDB_DB_ENCRYPTION_KEY` | Chave Fernet para criptografia do banco | base64-encoded-key |
| `CDB_APP_THEME` | Tema padrão (Light/Dark) | `Light` |
| `CDB_MAX_SIMULATION_MONTHS` | Limite máximo de meses para simulação | `1200` |
| `CDB_LIMITE_MONETARIO` | Limite monetário de segurança | `1000000000000.0` |
| `CDB_TAXA_JUROS_MAX` | Limite superior para taxa de juros (%) | `100.0` |
| `CDB_CDI_PERCENTUAL_MAX` | Limite superior para % do CDI | `500.0` |
| `CDB_CDI_BASE_MAX` | Limite superior para taxa base CDI | `100.0` |

Crie um arquivo `.env` na raiz copiando `.env.example` e preencha com sua chave.

---

## 13. Histórico de Melhorias e Correções

- **Controle Financeiro:** adicionada seção independente na GUI, acessível pela barra superior. Permite criar receitas, despesas e investimentos; editar ou excluir lançamentos; filtrar por tipo, categoria e período; e gerenciar categorias com arquivamento seguro quando há lançamentos associados. Os indicadores usam centavos inteiros, e os gráficos reutilizam a mesma `Figure`/canvas Matplotlib com `draw_idle`.

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
  - Módulo `src/ui/gui/theme.py` com `PALETTES` e `THEME_MODES`, importado por `components.py` e `chart.py`, eliminando qualquer ciclo de importação.

- **Criptografia do Banco Financeiro:**
  - O banco SQLite do Controle Financeiro passou a ser armazenado **criptografado em repouso** (`.enc`) via Fernet/AES-128 + HMAC-SHA256, protegendo receitas, despesas e investimentos contra leitura não autorizada no dispositivo.
  - Chave simétrica gerada automaticamente e armazenada com permissões restritas (`.db_key`).

- **Arquitetura (Versão 1.1.0):**
  - Nova camada de Casos de Uso (`src/use_cases/`) separando lógica de negócio da UI.
  - Constantes centralizadas em `src/domain/constants.py` (single source of truth).
  - Utilitários financeiros puros em `src/domain/financial_utils.py`.
  - Interface abstrata `FinancialRepositoryProtocol` em `src/repositories/interfaces.py`.
  - Configuração externa via `.env` em `src/config.py`.
  - Imports relativos em todo o código-fonte (eliminado acoplamento a `src.`).
  - Novos testes de casos de uso em `tests/test_use_cases.py`.

---

# CDB_SIMULATOR
