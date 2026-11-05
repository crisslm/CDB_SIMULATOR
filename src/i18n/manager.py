"""
Sistema de Internacionalização (i18n) - CDB Simulator.
=====================================================

Gerencia traduções da interface para múltiplos idiomas.
Suporta troca de idioma em tempo real sem reiniciar a aplicação.

Idiomas suportados:
    - pt_BR: Português do Brasil (padrão)
    - en_US: Inglês (Estados Unidos)
    - es_ES: Espanhol (Espanha)
    - fr_FR: Francês (França)
    - de_DE: Alemão (Alemanha)
    - ru_RU: Russo (Rússia)

Uso:
    from src.i18n.manager import TranslationManager, _

    tm = TranslationManager()
    tm.set_language("en_US")
    print(_("Simulador CDB"))  # "CDB Simulator"
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

# Idiomas suportados e seus nomes nativos
SUPPORTED_LANGUAGES: dict[str, str] = {
    "pt_BR": "Português",
    "en_US": "English",
    "es_ES": "Español",
    "fr_FR": "Français",
    "de_DE": "Deutsch",
    "ru_RU": "Русский",
}

# Código padrão
DEFAULT_LANGUAGE: str = "pt_BR"

# Diretório dos arquivos de tradução
I18N_DIR: Path = Path(__file__).parent


class TranslationManager:
    """
    Gerenciador de traduções da aplicação.

    Carrega arquivos JSON de tradução e fornece método para traduzir
    chaves para o idioma atualmente selecionado.

    Atributos:
        language (str): Código do idioma atual (ex: "en_US").
        translations (dict): Dicionário de traduções do idioma atual.
    """

    def __init__(self, language: str = DEFAULT_LANGUAGE):
        """
        Inicializa o gerenciador com o idioma especificado.

        Parâmetros:
            language: Código do idioma (ex: "pt_BR", "en_US").
        """
        self._translations: dict[str, str] = {}
        self._language: str = DEFAULT_LANGUAGE
        self.set_language(language)

    @property
    def language(self) -> str:
        """Retorna o código do idioma atual."""
        return self._language

    def set_language(self, language: str) -> None:
        """
        Define o idioma e carrega as traduções correspondentes.

        Se o idioma não for suportado, cai de volta para o padrão (pt_BR).

        Parâmetros:
            language: Código do idioma a ser definido.
        """
        if language not in SUPPORTED_LANGUAGES:
            language = DEFAULT_LANGUAGE
        self._language = language
        self._load_translations(language)

    def _load_translations(self, language: str) -> None:
        """
        Carrega as traduções de um arquivo JSON.

        Parâmetros:
            language: Código do idioma.
        """
        file_path = I18N_DIR / f"{language}.json"
        if file_path.exists():
            with open(file_path, encoding="utf-8") as f:
                self._translations = json.load(f)
        else:
            # Fallback: carrega o padrão se o arquivo não existir
            self._language = DEFAULT_LANGUAGE
            fallback_path = I18N_DIR / f"{DEFAULT_LANGUAGE}.json"
            if fallback_path.exists():
                with open(fallback_path, encoding="utf-8") as f:
                    self._translations = json.load(f)
            else:
                self._translations = {}

    def translate(self, key: str, **kwargs) -> str:
        """
        Traduz uma chave para o idioma atual.

        Se a chave não existir, retorna a própria chave.
        Suporta substituição de placeholders com **kwargs.

        Parâmetros:
            key: Chave de tradução (ex: "app.title").
            **kwargs: Valores para substituição de placeholders {nome}.

        Retorna:
            String traduzida.
        """
        text = self._translations.get(key, key)
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                pass
        return text

    def get_available_languages(self) -> dict[str, str]:
        """
        Retorna dicionário de idiomas disponíveis.

        Retorna:
            dict: {código: nome nativo}.
        """
        return dict(SUPPORTED_LANGUAGES)


# Instância global (singleton) para uso em toda a aplicação
_translation_manager: Optional[TranslationManager] = None


def get_translation_manager() -> TranslationManager:
    """
    Retorna a instância singleton do gerenciador de traduções.

    Retorna:
        TranslationManager: Instância configurada.
    """
    global _translation_manager
    if _translation_manager is None:
        _translation_manager = TranslationManager()
    return _translation_manager


def set_language(language: str) -> None:
    """
    Define o idioma global da aplicação.

    Parâmetros:
        language: Código do idioma (ex: "en_US").
    """
    get_translation_manager().set_language(language)


def get_language() -> str:
    """
    Retorna o código do idioma atual.

    Retorna:
        str: Código do idioma.
    """
    return get_translation_manager().language


def t(key: str, **kwargs) -> str:
    """
    Função de atalho para traduzir uma chave.

    Parâmetros:
        key: Chave de tradução.
        **kwargs: Valores para placeholders.

    Retorna:
        String traduzida.
    """
    return get_translation_manager().translate(key, **kwargs)


# Alias comum para gettext
_ = t
