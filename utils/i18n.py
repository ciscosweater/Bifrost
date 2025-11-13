"""
ACCELA Internationalization Manager - Simplified Version
Gerencia internacionalização e tradução de strings da aplicação usando JSON
"""

import json
import logging
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SimpleI18n:
    """Gerenciador de internacionalização simplificado para ACCELA"""

    def __init__(self):
        self.current_language = "en"
        self.available_languages = {"en": "English", "pt_BR": "Português (Brasil)"}
        self.translations_dir = "translations"
        self.translations: Dict[str, str] = {}
        self.load_translations()

    def load_translations(self):
        """Carrega traduções do arquivo JSON do idioma atual"""
        try:
            lang_file = os.path.join(
                self.translations_dir, f"{self.current_language}.json"
            )
            if os.path.exists(lang_file):
                with open(lang_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.translations = data.get("translations", {})
                    logger.info(
                        f"Loaded {len(self.translations)} translations for {self.current_language}"
                    )
            else:
                logger.warning(f"Translation file not found: {lang_file}")
                self.translations = {}
        except Exception as e:
            logger.error(f"Error loading translations: {e}")
            self.translations = {}

    def set_language(self, language_code: str) -> bool:
        """
        Muda o idioma atual e recarrega as traduções

        Args:
            language_code: Código do idioma (ex: 'pt_BR')

        Returns:
            bool: True se mudou com sucesso
        """
        if language_code in self.available_languages:
            self.current_language = language_code
            self.load_translations()
            logger.info(f"Language changed to {language_code}")
            return True
        else:
            logger.warning(f"Unsupported language: {language_code}")
            return False

    def tr(self, context: str, text: str) -> str:
        """
        Função de tradução principal

        Args:
            context: Contexto da tradução (geralmente nome da classe)
            text: Texto para traduzir

        Returns:
            str: Texto traduzido ou original se não encontrado
        """
        # Primeiro tenta com o formato de ponto (padrão)
        key_dot = f"{context}.{text}"
        translated = self.translations.get(key_dot, None)
        
        if translated is not None:
            return translated
            
        # Se não encontrar, tenta com espaço (compatibilidade com JSON existente)
        key_space = f"{context} {text}"
        translated = self.translations.get(key_space, text)

        # Log para debug de traduções faltantes
        if translated == text and self.current_language != "en":
            logger.debug(f"Missing translation: {key_dot} or {key_space}")

        return translated

    def get_available_languages(self) -> dict:
        """Retorna idiomas disponíveis"""
        return self.available_languages.copy()

    def get_current_language(self) -> str:
        """Retorna idioma atual"""
        return self.current_language

    def auto_detect_language(self) -> str:
        """Detecta idioma do sistema"""
        import locale

        try:
            system_locale = locale.getdefaultlocale()[0]
            if system_locale and system_locale.startswith("pt"):
                return "pt_BR"
        except (AttributeError, TypeError):
            pass
        return "en"


# Instância global do gerenciador
_i18n_manager = SimpleI18n()


def get_i18n_manager() -> SimpleI18n:
    """Retorna instância global do SimpleI18n"""
    return _i18n_manager


def tr(context: str, text: str) -> str:
    """
    Função de tradução para uso na aplicação

    Args:
        context: Contexto da tradução (geralmente nome da classe)
        text: Texto para traduzir

    Returns:
        str: Texto traduzido ou original se não encontrado
    """
    return _i18n_manager.tr(context, text)


def init_i18n(language: Optional[str] = None) -> bool:
    """
    Inicializa sistema de internacionalização

    Args:
        language: Idioma específico ou None para auto-detectar

    Returns:
        bool: True se inicializado com sucesso
    """
    if language is None:
        language = _i18n_manager.auto_detect_language()

    return _i18n_manager.set_language(language)


def reload_language(language: str) -> bool:
    """
    Recarrega idioma dinamicamente

    Args:
        language: Código do idioma para carregar

    Returns:
        bool: True se carregado com sucesso
    """
    return _i18n_manager.set_language(language)


# Alias para facilitar uso
_ = tr
