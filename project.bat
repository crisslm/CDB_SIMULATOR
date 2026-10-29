@echo off
setlocal EnableDelayedExpansion

REM ==============================================================================
REM CLI DE GERENCIAMENTO DO PROJETO (CDB SIMULATOR)
REM Uso:
REM   project preview - Modo Live-Reload (atualiza a interface ao salvar arquivos)
REM   project run     - Executa os testes e inicia a interface grafica
REM   project update  - Roda os testes, recompila o .exe e publica na Area de Trabalho
REM   project test    - Executa a suite de testes unitarios
REM ==============================================================================

set COMMAND=%1
set ARG2=%2

if "%COMMAND%"=="" goto help
if "%COMMAND%"=="help" goto help
if "%COMMAND%"=="preview" goto preview
if "%COMMAND%"=="run" goto run
if "%COMMAND%"=="update" goto update
if "%COMMAND%"=="test" goto test

echo [ERRO] Comando desconhecido: "%COMMAND%"
goto help

:preview
echo Iniciando Live-Reload Preview...
python preview.py
exit /b %ERRORLEVEL%

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

if "%ARG2%"=="cli" (
    echo [2/2] Iniciando aplicacao em modo Terminal (CLI)...
    python main_cli.py
) else (
    echo [2/2] Iniciando aplicacao com Interface Grafica...
    python main_gui.py
)
exit /b 0

:update
echo ================================================================
echo           COMPILANDO E ATUALIZANDO O EXECUTAVEL (.EXE)          
echo ================================================================

echo [1/4] Executando testes automatizados antes do build...
python -m pytest tests/
if %ERRORLEVEL% NEQ 0 (
    echo [BLOQUEADO] O executavel nao sera gerado porque ha testes falhando!
    exit /b %ERRORLEVEL%
)

echo [2/4] Gerando novo executavel com PyInstaller (limpando versoes antigas)...
pyinstaller --noconsole --clean --onefile --name "CDB_Simulator" main_gui.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Falha ao compilar com o PyInstaller.
    exit /b %ERRORLEVEL%
)

echo [3/4] Publicando executavel na Area de Trabalho...
python publish.py
if %ERRORLEVEL% NEQ 0 (
    echo [AVISO] Build concluido em dist\, mas a publicacao na Area de Trabalho falhou.
)

echo [4/4] Finalizado com sucesso!
echo ================================================================
echo Executavel gerado em: dist\CDB_Simulator.exe
echo ================================================================
exit /b 0

:help
echo.
echo ================================================================
echo           COMANDOS DISPONIVEIS (PROJECT CLI)                   
echo ================================================================
echo   project preview      - Inicia Live-Reload (atualiza ao salvar o codigo)
echo   project run          - Executa testes e roda a interface grafica
echo   project run cli      - Executa testes e roda o modo terminal
echo   project update       - Testa, recompila e publica o .exe na Area de Trabalho
echo   project test         - Executa apenas os testes unitarios (pytest)
echo ================================================================
echo.
exit /b 0
