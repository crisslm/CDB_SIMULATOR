# ==============================================================================
# SCRIPT DE GERENCIAMENTO DO PROJETO PARA POWERSHELL
# ==============================================================================
param (
    [Parameter(Position=0)]
    [string]$Action = "help"
)

function Show-Help {
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "          COMANDOS DISPONIVEIS (PROJECT CLI)                   " -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "  project run      - Executa testes e roda a interface grafica" -ForegroundColor Cyan
    Write-Host "  project update   - Testa e recompila o .exe (.EXE - DESKTOP) " -ForegroundColor Cyan
    Write-Host "  project test     - Executa apenas os testes unitarios        " -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""
}

switch ($Action.ToLower()) {
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

        Write-Host "[2/2] Iniciando Interface Grafica..." -ForegroundColor Cyan
        python main_gui.py
    }

    "update" {
        Write-Host "================================================================" -ForegroundColor Cyan
        Write-Host "          COMPILANDO O EXECUTAVEL (.EXE) - DESKTOP              " -ForegroundColor Cyan
        Write-Host "================================================================" -ForegroundColor Cyan

        Write-Host "[1/2] Executando testes antes da compilacao..." -ForegroundColor Yellow
        python -m pytest tests/
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[BLOQUEADO] O executavel nao sera gerado porque ha testes falhando!" -ForegroundColor Red
            exit $LASTEXITCODE
        }

        Write-Host "[2/2] Gerando novo executavel via PyInstaller..." -ForegroundColor Yellow
        pyinstaller --clean CDB_Simulator.spec

        if ($LASTEXITCODE -eq 0) {
            Write-Host "[3/3] Finalizado com sucesso!" -ForegroundColor Green
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
