import logging
import sys

from PyQt6.QtCore import QObject, pyqtSignal

from utils.settings import get_settings
from utils.i18n import get_i18n_manager


class InternationalizedLogger:
    """
    Wrapper para o logger padrão que adiciona suporte à internacionalização
    de mensagens de log de nível INFO e superior.
    """

    def __init__(self, logger):
        self._logger = logger
        self._i18n = get_i18n_manager()

    def _translate_message(self, msg, level_name):
        """
        Traduz mensagens de log de nível INFO ou superior.
        Tenta traduzir a parte base da mensagem, ignorando variáveis.
        """
        if level_name in ['INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            import inspect
            frame = inspect.currentframe()
            try:
                if frame is None or frame.f_back is None:
                    return msg
                    
                caller_frame = frame.f_back.f_back  # Pular este frame e o da função wrapper
                if caller_frame is None:
                    return msg
                    
                module_name = caller_frame.f_globals.get('__name__', 'Unknown')
                
                # Usar o nome do módulo como contexto (última parte do nome)
                context = module_name.split('.')[-1] if '.' in module_name else module_name
                if context.startswith('_'):
                    context = context[1:]
                
                # Tentar extrair a parte base da mensagem
                base_msg = msg
                
                # Lista de separadores comuns em logs
                separators = [':', ' for', ' at', ' to', ' from', ' with', ' in', ' by']
                for separator in separators:
                    if separator in msg:
                        # Dividir na primeira ocorrência do separador
                        parts = msg.split(separator, 1)
                        base_msg = parts[0].strip()
                        break
                
                # Primeiro tentar traduzir a mensagem completa
                translated = self._i18n.tr(context, msg)
                if translated != msg:
                    return translated
                
                # Se não funcionar, tentar traduzir apenas a parte base
                translated_base = self._i18n.tr(context, base_msg)
                if translated_base != base_msg:
                    # Substituir a parte base pela tradução
                    return msg.replace(base_msg, translated_base, 1)
                
                return msg
            except:
                return msg
        return msg

    def info(self, msg, *args, **kwargs):
        translated_msg = self._translate_message(msg, 'INFO')
        return self._logger.info(translated_msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        translated_msg = self._translate_message(msg, 'WARNING')
        return self._logger.warning(translated_msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        translated_msg = self._translate_message(msg, 'ERROR')
        return self._logger.error(translated_msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        translated_msg = self._translate_message(msg, 'CRITICAL')
        return self._logger.critical(translated_msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        return self._logger.debug(msg, *args, **kwargs)

    def log(self, level, msg, *args, **kwargs):
        translated_msg = self._translate_message(msg, 'INFO') if level >= logging.INFO else msg
        return self._logger.log(level, translated_msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        translated_msg = self._translate_message(msg, 'ERROR')
        return self._logger.exception(translated_msg, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._logger, name)


class QtLogHandler(QObject, logging.Handler):
    """
    A custom logging handler that emits a signal for each log record.
    This allows log messages to be displayed in a PyQt widget.
    """

    new_record = pyqtSignal(str)

    def __init__(self, simple_mode=False):
        super().__init__()
        self.simple_mode = simple_mode
        if simple_mode:
            formatter = logging.Formatter("%(levelname)s: %(message)s")
        else:
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        self.setFormatter(formatter)

    def emit(self, record):
        """
        Emits the formatted log record as a signal.
        """
        msg = self.format(record)
        self.new_record.emit(msg)


# --- MODIFICATION START ---
# Initialize the handler immediately when the module is imported.
# This prevents a race condition where other modules might try to use it
# before it's been initialized by setup_logging().
qt_log_handler = None
# --- MODIFICATION END ---


def setup_logging():
    """
    Configures the root logger for the application.

    Sets up three handlers:
    1. A stream handler to print logs to the console (for debugging).
    2. A file handler to save logs to 'app.log'.
    3. A custom Qt handler to display logs in the GUI.

    Returns:
        The configured root logger instance.
    """
    global qt_log_handler

    # Get log level preference from settings
    settings = get_settings()
    simple_mode = settings.value("logging/simple_mode", False, type=bool)
    log_level = settings.value("logging/level", "INFO", type=str)

    # Convert string level to logging constant
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    effective_level = level_map.get(log_level.upper(), logging.INFO)

    # Create Qt handler with appropriate mode
    qt_log_handler = QtLogHandler(simple_mode=simple_mode)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(effective_level)

    # Clear existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add handlers
    file_handler = logging.FileHandler("app.log", mode="w")
    file_handler.setLevel(logging.DEBUG)  # Always log everything to file

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(effective_level)

    if simple_mode:
        console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    else:
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    console_handler.setFormatter(console_formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(qt_log_handler)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured (simple_mode={simple_mode}, level={log_level}).")
    return logger


def get_internationalized_logger(name = None) -> InternationalizedLogger:
    """
    Retorna um logger que suporta internacionalização automática
    
    Args:
        name: Nome do logger (usa __name__ se não fornecido)
        
    Returns:
        InternationalizedLogger: Logger wrapper que traduz mensagens automaticamente
    """
    import inspect
    if name is None:
        # Detectar o módulo chamador
        frame = inspect.currentframe()
        try:
            if frame is None or frame.f_back is None:
                name = 'app'
            else:
                caller_frame = frame.f_back
                if caller_frame is None:
                    name = 'app'
                else:
                    name = caller_frame.f_globals.get('__name__', 'app')
        except:
            name = 'app'
    else:
        name = str(name)  # Garantir que é string
    
    base_logger = logging.getLogger(name)
    return InternationalizedLogger(base_logger)


def update_logging_mode():
    """
    Updates logging configuration when settings change.
    Call this after changing logging settings.
    """
    setup_logging()
