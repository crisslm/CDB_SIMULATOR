#!/usr/bin/env bash
# ==============================================================================
# SCRIPT DE GERENCIAMENTO DO PROJETO PARA BASH (GIT BASH / WSL / LINUX / MAC)
# ==============================================================================

ACTION="${1:-help}"
TARGET="${2:-gui}"

show_help() {
    echo ""
    echo -e "\033[1;36m================================================================\033[0m"
    echo -e "\033[1;36m          COMANDOS DISPONIVEIS (PROJECT CLI - BASH)             \033[0m"
    echo -e "\033[1;36m================================================================\033[0m"
    echo "  ./project.sh preview      - Inicia Live-Reload (atualiza ao salvar o codigo)"
    echo "  ./project.sh run          - Executa testes e roda a interface grafica"
    echo "  ./project.sh run cli      - Executa testes e roda o modo terminal"
    echo "  ./project.sh update       - Testa, recompila e publica o .exe na Area de Trabalho"
    echo "  ./project.sh test         - Executa apenas os testes unitarios"
    echo -e "\033[1;36m================================================================\033[0m"
    echo ""
}

case "$ACTION" in
    preview)
        echo -e "\033[1;36mIniciando Live-Reload Preview...\033[0m"
        python preview.py
        ;;

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

        if [ "$TARGET" = "cli" ]; then
            echo -e "\033[1;36m[2/2] Iniciando em modo Terminal (CLI)...\033[0m"
            python main_cli.py
        else
            echo -e "\033[1;36m[2/2] Iniciando Interface Grafica...\033[0m"
            python main_gui.py
        fi
        ;;

    update)
        echo -e "\033[1;36m================================================================\033[0m"
        echo -e "\033[1;36m          COMPILANDO E ATUALIZANDO O EXECUTAVEL (.EXE)          \033[0m"
        echo -e "\033[1;36m================================================================\033[0m"

        echo -e "\033[1;33m[1/4] Executando testes antes da compilacao...\033[0m"
        python -m pytest tests/
        EXIT_CODE=$?
        if [ $EXIT_CODE -ne 0 ]; then
            echo -e "\033[1;31m[BLOQUEADO] O executavel nao sera gerado porque ha testes falhando!\033[0m"
            exit $EXIT_CODE
        fi

        echo -e "\033[1;33m[2/4] Gerando novo executavel via PyInstaller...\033[0m"
        # Limpa build anterior para evitar PermissionError [WinError 5] com OneDrive/Antivirus
        rm -rf build 2>/dev/null
        pyinstaller --noconsole --clean --onefile --name "CDB_Simulator" main_gui.py

        if [ $? -eq 0 ]; then
            echo -e "\033[1;33m[3/4] Publicando executavel na Area de Trabalho...\033[0m"
            python publish.py
            if [ $? -ne 0 ]; then
                echo -e "\033[1;33m[AVISO] Build concluido em dist/, mas a publicacao na Area de Trabalho falhou.\033[0m"
            fi
            echo -e "\033[1;32m[4/4] Finalizado com sucesso!\033[0m"
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
