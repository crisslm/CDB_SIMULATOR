#!/usr/bin/env bash
# ==============================================================================
# SCRIPT DE GERENCIAMENTO DO PROJETO PARA BASH (GIT BASH / WSL / LINUX / MAC)
# ==============================================================================

ACTION="${1:-help}"

show_help() {
    echo ""
    echo -e "\033[1;36m================================================================\033[0m"
    echo -e "\033[1;36m          COMANDOS DISPONIVEIS (PROJECT CLI - BASH)             \033[0m"
    echo -e "\033[1;36m================================================================\033[0m"
    echo "  ./project.sh run      - Executa testes e roda a interface grafica"
    echo "  ./project.sh update   - Testa e recompila o .exe (dist/CDB_Simulator.exe)"
    echo "  ./project.sh test     - Executa apenas os testes unitarios"
    echo -e "\033[1;36m================================================================\033[0m"
    echo ""
}

case "$ACTION" in
    test)
        echo -e "\033[1;33m[1/1] Executando testes unitarios com pytest...\033[0m"
        python -m pytest tests/
        EXIT_CODE=$?
        if [ $EXIT_CODE -ne 0 ]; then
            echo -e "\033[1;31m[FALHA] Os testes falharam!\033[0m"
            exit $EXIT_CODE
        fi
        echo -e "\033[1;32m[SUCESSO] Todos os testes passaram!\033[0m"
        ;;

    run)
        echo -e "\033[1;33m[1/2] Verificando integridade com testes...\033[0m"
        python -m pytest tests/
        EXIT_CODE=$?
        if [ $EXIT_CODE -ne 0 ]; then
            echo -e "\033[1;31m[FALHA] Testes falharam. Abortando execucao.\033[0m"
            exit $EXIT_CODE
        fi

        echo -e "\033[1;36m[2/2] Iniciando Interface Grafica...\033[0m"
        python main_gui.py
        ;;

    update)
        echo -e "\033[1;36m================================================================\033[0m"
        echo -e "\033[1;36m          COMPILANDO O EXECUTAVEL (.EXE) - DESKTOP              \033[0m"
        echo -e "\033[1;36m================================================================\033[0m"

        echo -e "\033[1;33m[1/2] Executando testes antes da compilacao...\033[0m"
        python -m pytest tests/
        EXIT_CODE=$?
        if [ $EXIT_CODE -ne 0 ]; then
            echo -e "\033[1;31m[BLOQUEADO] O executavel nao sera gerado porque ha testes falhando!\033[0m"
            exit $EXIT_CODE
        fi

        echo -e "\033[1;33m[2/2] Gerando novo executavel via PyInstaller...\033[0m"
        rm -rf build 2>/dev/null
        pyinstaller --clean CDB_Simulator.spec

        if [ $? -eq 0 ]; then
            echo -e "\033[1;32m[3/3] Finalizado com sucesso!\033[0m"
            echo -e "\033[1;32mExecutavel atualizado em: dist/CDB_Simulator.exe\033[0m"
        else
            echo -e "\033[1;31m[ERRO] Falha durante a geracao do executavel.\033[0m"
            exit 1
        fi
        ;;

    help|*)
        show_help
        ;;
esac
