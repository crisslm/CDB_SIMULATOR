@echo off
setlocal EnableDelayedExpansion

REM ==============================================================================
REM CLI DE GERENCIAMENTO DO PROJETO (CDB SIMULATOR - DESKTOP)
REM Uso:
REM   project run     - Executa os testes e inicia a interface grafica
REM   project update  - Roda os testes e recompila o executavel (.exe)
REM   project test    - Executa a suite de testes unitarios
REM ==============================================================================

set COMMAND=%1
set ARG2=%2

if "%COMMAND%"=="" goto help
if "%COMMAND%"=="help" goto help
if "%COMMAND%"=="run" goto run
if "%COMMAND%"=="update" goto update
if "%COMMAND%"=="test" goto test

echo [ERRO] Comando desconhecido: "%COMMAND%"
goto help

:test
echo [1/1] Executando testes unitarios com pytest...
python -m pytest tests/
if %ERRORLEVEL% NEQ 0 (
    echo [FALHA] Os testes falharam! Abortando.
    exit /b %ERRORLEVEL%
)
echo [SUCESSO] Todos os testes passaram!
exit /b 0

:run
echo [1/2] Verificando integridade com testes...
python -m pytest tests/
if %ERRORLEVEL% NEQ 0 (
    echo [FALHA] Testes falharam. Nao e seguro rodar a aplicacao.
    exit /b %ERRORLEVEL%
)

echo [2/2] Iniciando aplicacao com Interface Grafica...
python main_gui.py
exit /b 0

:update
echo ================================================================
echo           COMPILANDO O EXECUTAVEL (.EXE) - DESKTOP             
echo ================================================================

echo [1/2] Executando testes automatizados antes do build...
python -m pytest tests/
if %ERRORLEVEL% NEQ 0 (
    echo [BLOQUEADO] O executavel nao sera gerado porque ha testes falhando!
    exit /b %ERRORLEVEL%
)

echo [2/2] Gerando novo executavel com PyInstaller...
pyinstaller --clean CDB_Simulator.spec
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Falha ao compilar com o PyInstaller.
    exit /b %ERRORLEVEL%
)

echo [3/3] Finalizado com sucesso!
echo ================================================================
echo Executavel gerado em: dist\CDB_Simulator.exe
echo ================================================================
exit /b 0

:help
echo.
echo ================================================================
echo           COMANDOS DISPONIVEIS (PROJECT CLI)                   
echo ================================================================
echo   project run      - Executa testes e roda a interface grafica
echo   project update   - Testa e recompila o .exe (dist\CDB_Simulator.exe)
echo   project test     - Executa apenas os testes unitarios (pytest)
echo ================================================================
echo.
exit /b 0
