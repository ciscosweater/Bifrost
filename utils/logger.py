import logging
import sys

from PyQt6.QtCore import QObject, pyqtSignal

from utils.settings import get_settings


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


def update_logging_mode():
    """
    Updates logging configuration when settings change.
    Call this after changing logging settings.
    """
    setup_logging()
