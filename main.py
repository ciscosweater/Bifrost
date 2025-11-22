import os
import sys
from utils.logger import get_internationalized_logger

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.theme import Typography, theme
from utils.logger import setup_logging, get_internationalized_logger
from utils.settings import get_settings

# Add the project root to the Python path. This allows absolute imports
# (e.g., 'from core.tasks...') to work from any submodule.
# This must be done BEFORE importing any project modules.
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import i18n after path setup
try:
    from utils.i18n import init_i18n
except (ImportError, ModuleNotFoundError):
    # Fallback for development
    from typing import Optional, Union

    def init_i18n(language: Optional[str] = None) -> bool:
        return True

    def get_i18n_manager() -> Union[object, None]:
        return None


def main():
    """
    The main entry point for the Depot Downloader GUI application.
    Initializes logging, sets the application style, and launches the main window.
    """
    # Set up the application-wide logger to capture logs from all modules.
    logger = setup_logging()
    app_logger = get_internationalized_logger()
    app_logger.debug("========================================")
    app_logger.info("Application starting...")
    app_logger.debug("========================================")

    app = QApplication(sys.argv)

    # Set application name for proper desktop integration
    app.setApplicationName("Bifrost")
    app.setApplicationDisplayName("Bifrost")

    # Set application icon
    try:
        from PyQt6.QtGui import QIcon
        app.setWindowIcon(QIcon("bifrost.png"))
    except Exception as e:
        print(f"Warning: Could not set application icon: {e}")

    # Initialize internationalization with language from settings
    settings = get_settings()
    saved_language = settings.value("language", None, type=str)
    init_i18n(saved_language)

    # Set a custom dark theme using the new design system
    app.setStyle("Fusion")

    # --- MODIFICATION START ---
    # Load MotivaSans font
    motiva_path = "assets/fonts/MotivaSansRegular.woff.ttf"
    motiva_id = QFontDatabase.addApplicationFont(motiva_path)

    font_loaded = False
    font_name = "Arial"  # Default fallback

    if motiva_id != -1:
        font_families = QFontDatabase.applicationFontFamilies(motiva_id)
        if font_families:
            font_name = font_families[0]
            font_loaded = True
            logger.debug(f"Loaded MotivaSans font: '{font_name}'")
    else:
        logger.warning(f"Failed to load MotivaSans font from: {motiva_path}")

    # Apply font if loaded successfully
    if font_loaded:
        custom_font = QFont(font_name, Typography.BODY_SIZE)
        app.setFont(custom_font)
        app_logger.debug(
            f"Applied MotivaSans font: '{font_name}' with size {Typography.BODY_SIZE}px"
        )
    else:
        app_logger.warning(
            f"Could not load MotivaSans font, using fallback: {font_name}"
        )

    # Apply theme after font is loaded
    theme.apply_theme_to_app(app)
    # --- MODIFICATION END ---

    try:
        # Check if a zip file was passed as command line argument
        zip_file_arg = None
        if len(sys.argv) > 1:
            zip_file_arg = sys.argv[1]
            if zip_file_arg.lower().endswith(".zip") and os.path.isfile(zip_file_arg):
                logger.info(f"Zip file provided as argument: {zip_file_arg}")
            else:
                zip_file_arg = None

        main_win = MainWindow(zip_file_arg)
        main_win.show()
        app_logger.info("Main window displayed successfully.")
        # Start the Qt event loop.
        sys.exit(app.exec())
    except Exception as e:
        # A global catch-all for any unhandled exceptions during initialization.
        app_logger.critical(
            f"A critical error occurred, and the application must close. Error: {e}",
            exc_info=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
