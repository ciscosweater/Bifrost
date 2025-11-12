"""
ACCELA Internationalization Manager
Gerencia internacionalização e tradução de strings da aplicação
"""

import os
import logging
from typing import Optional
from PyQt6.QtCore import QCoreApplication, QTranslator, QLocale
from PyQt6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

class I18nManager:
    """Gerenciador de internacionalização para ACCELA"""
    
    def __init__(self):
        self.translator = QTranslator()
        self.current_language = 'en'
        self.available_languages = {
            'en': 'English',
            'pt_BR': 'Português (Brasil)',
            'es': 'Español',
            'fr': 'Français'
        }
        self.translations_dir = 'translations'
        self.translations = {}  # Dicionário para traduções .ts
        
    def load_language(self, language_code: str) -> bool:
        """
        Carrega tradução para o idioma especificado
        
        Args:
            language_code: Código do idioma (ex: 'pt_BR')
            
        Returns:
            bool: True se carregado com sucesso
        """
        try:
            app = QApplication.instance()
            if app:
                # Remove translator anterior se existir
                app.removeTranslator(self.translator)
            
            # Carrega novo tradutor
            if language_code == 'en':
                # Inglês é o idioma base, não precisa de arquivo
                self.current_language = language_code
                return True
                
            # Tentar carregar arquivo .qm primeiro
            translation_file = os.path.join(self.translations_dir, f"app_{language_code}")
            
            if self.translator.load(translation_file):
                if app:
                    app.installTranslator(self.translator)
                    self.current_language = language_code
                    logger.info(f"Translation loaded for {language_code}")
                    return True
                else:
                    logger.warning("No QApplication instance found")
                    return False
            else:
                # Se não encontrar .qm, tentar usar .ts diretamente
                ts_file = f"{translation_file}.ts"
                if os.path.exists(ts_file):
                    logger.info(f"Using .ts file directly: {ts_file}")
                    self.current_language = language_code
                    self._load_ts_file(ts_file)
                    return True
                else:
                    logger.warning(f"Translation file not found: {translation_file} (.qm or .ts)")
                    return False
                
        except Exception as e:
            logger.error(f"Error loading translation {language_code}: {e}")
            return False
    
    def _load_ts_file(self, ts_file: str):
        """
        Carrega traduções de arquivo .ts diretamente (fallback)
        
        Args:
            ts_file: Caminho do arquivo .ts
        """
        try:
            import xml.etree.ElementTree as ET
            
            tree = ET.parse(ts_file)
            root = tree.getroot()
            
            # Dicionário de traduções
            self.translations = {}
            
            for context in root.findall('context'):
                name_elem = context.find('name')
                if name_elem is not None and name_elem.text:
                    context_name = name_elem.text
                    self.translations[context_name] = {}
                    
                    for message in context.findall('message'):
                        source_elem = message.find('source')
                        translation_elem = message.find('translation')
                        
                        if source_elem is not None and translation_elem is not None:
                            source = source_elem.text
                            translation = translation_elem.text
                            if source and translation:
                                self.translations[context_name][source] = translation
            
            logger.info(f"Loaded {len(self.translations)} contexts from {ts_file}")
            
        except Exception as e:
            logger.error(f"Error loading .ts file {ts_file}: {e}")
            self.translations = {}
    
    def get_available_languages(self) -> dict:
        """Retorna idiomas disponíveis"""
        return self.available_languages.copy()
    
    def get_current_language(self) -> str:
        """Retorna idioma atual"""
        return self.current_language
    
    def auto_detect_language(self) -> str:
        """Detecta idioma do sistema"""
        locale = QLocale.system()
        language_code = locale.name()
        
        # Mapeia códigos completos para códigos suportados
        if language_code.startswith('pt'):
            return 'pt_BR'
        elif language_code.startswith('es'):
            return 'es'
        elif language_code.startswith('fr'):
            return 'fr'
        else:
            return 'en'

# Instância global do gerenciador
_i18n_manager = I18nManager()

def get_i18n_manager() -> I18nManager:
    """Retorna instância global do I18nManager"""
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
    # Primeiro tentar usar o sistema Qt
    translated = QCoreApplication.translate(context, text)
    
    # Se não houver tradução ou for igual ao original, tentar nosso dicionário
    if translated == text:
        manager = get_i18n_manager()
        if hasattr(manager, 'translations') and context in manager.translations:
            if text in manager.translations[context]:
                return manager.translations[context][text]
    
    return translated

def init_i18n(app: QApplication, language: Optional[str] = None) -> bool:
    """
    Inicializa sistema de internacionalização
    
    Args:
        app: Instância da QApplication
        language: Idioma específico ou None para auto-detectar
        
    Returns:
        bool: True se inicializado com sucesso
    """
    if language is None:
        language = _i18n_manager.auto_detect_language()
    
    return _i18n_manager.load_language(language)

def reload_language(app: QApplication, language: str) -> bool:
    """
    Recarrega idioma dinamicamente
    
    Args:
        app: Instância da QApplication
        language: Código do idioma para carregar
        
    Returns:
        bool: True se carregado com sucesso
    """
    return _i18n_manager.load_language(language)

# Alias para facilitar uso
_ = tr