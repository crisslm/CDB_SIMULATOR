# ==============================================================================
# SCRIPT DE GERENCIAMENTO DO PROJETO PARA POWERSHELL
# ==============================================================================
param (
    [Parameter(Position=0)]
    [string]$Action = "help",

    [Parameter(Position=1)]
    [string]$Target = "gui"
)

function Show-Help {
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "          COMANDOS DISPONIVEIS (PROJECT CLI)                   " -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "  project preview      - Inicia Live-Reload (atualiza ao salvar o codigo)"
    Write-Host "  project run          - Executa testes e roda a interface grafica"
    Write-Host "  project run cli      - Executa testes e roda o modo terminal"
    Write-Host "  project update       - Testa, recompila e publica o .exe na Area de Trabalho"
    Write-Host "  project test         - Executa apenas os testes unitarios"
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""
}

switch ($Action.ToLower()) {
    "preview" {
        Write-Host "Iniciando Live-Reload Preview..." -ForegroundColor Cyan
        python preview.py
    }

    "test" {
        Write-Host "[1/1] Executando testes unitarios com pytest..." -ForegroundColor Yellow
        python -m pytest tests/
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[FALHA] Os testes falharam!" -ForegroundColor Red
            exit $LASTEXITCODE
        }
        Write-Host "[SUCESSO] Todos os testes passaram!" -ForegroundColor Green
    }

    "run" {
        Write-Host "[1/2] Verificando integridade com testes..." -ForegroundColor Yellow
        python -m pytest tests/
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[FALHA] Testes falharam. Abortando execucao." -ForegroundColor Red
            exit $LASTEXITCODE
        }

        if ($Target -eq "cli") {
            Write-Host "[2/2] Iniciando em modo Terminal (CLI)..." -ForegroundColor Cyan
            python main_cli.py
        } else {
            Write-Host "[2/2] Iniciando Interface Grafica..." -ForegroundColor Cyan
            python main_gui.py
        }
    }

    "update" {
        Write-Host "================================================================" -ForegroundColor Cyan
        Write-Host "          COMPILANDO E ATUALIZANDO O EXECUTAVEL (.EXE)          " -ForegroundColor Cyan
        Write-Host "================================================================" -ForegroundColor Cyan

        Write-Host "[1/4] Executando testes antes da compilacao..." -ForegroundColor Yellow
        python -m pytest tests/
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[BLOQUEADO] O executavel nao sera gerado porque ha testes falhando!" -ForegroundColor Red
            exit $LASTEXITCODE
        }

        Write-Host "[2/4] Gerando novo executavel via PyInstaller..." -ForegroundColor Yellow
        pyinstaller --noconsole --clean --onefile --name "CDB_Simulator" main_gui.py

        if ($LASTEXITCODE -eq 0) {
            Write-Host "[3/4] Publicando executavel na Area de Trabalho..." -ForegroundColor Yellow
            python publish.py
            if ($LASTEXITCODE -ne 0) {
                Write-Host "[AVISO] Build concluido em dist\, mas a publicacao na Area de Trabalho falhou." -ForegroundColor Yellow
            }
            Write-Host "[4/4] Finalizado com sucesso!" -ForegroundColor Green
            Write-Host "Executavel atualizado em: dist\CDB_Simulator.exe" -ForegroundColor Green
        } else {
            Write-Host "[ERRO] Falha durante a geracao do executavel." -ForegroundColor Red
            exit $LASTEXITCODE
        }
    }

    default {
        Show-Help
    }
}
