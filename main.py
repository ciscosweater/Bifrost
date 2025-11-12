import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor, QFontDatabase, QFont

# Add the project root to the Python path. This allows absolute imports
# (e.g., 'from core.tasks...') to work from any submodule.
# This must be done BEFORE importing any project modules.
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from ui.main_window import MainWindow
from ui.theme import theme, Typography
from utils.logger import setup_logging
from utils.settings import get_font_setting, get_settings

# Import i18n after path setup
try:
    from utils.i18n import init_i18n, get_i18n_manager
except (ImportError, ModuleNotFoundError):
    # Fallback for development
    def init_i18n(app, language=None):
        pass
    def get_i18n_manager():
        return None

def main():
    """
    The main entry point for the Depot Downloader GUI application.
    Initializes logging, sets the application style, and launches the main window.
    """
    # Set up the application-wide logger to capture logs from all modules.
    logger = setup_logging()
    logger.info("========================================")
    logger.info("Application starting...")
    logger.info("========================================")

    app = QApplication(sys.argv)

    # Initialize internationalization with language from settings
    settings = get_settings()
    saved_language = settings.value("language", None, type=str)
    init_i18n(app, saved_language)

    # Set a custom dark theme using the new design system
    app.setStyle("Fusion")
    
    # --- MODIFICATION START ---
    # Load fonts and apply selected font
    selected_font = get_font_setting("selected_font", "TrixieCyrG-Plain Regular")
    
    # Load TrixieCyrG font
    trixie_path = "assets/fonts/TrixieCyrG-Plain Regular.otf"
    trixie_id = QFontDatabase.addApplicationFont(trixie_path)
    
    # Load MotivaSans font
    motiva_path = "assets/fonts/MotivaSansRegular.woff.ttf"
    motiva_id = QFontDatabase.addApplicationFont(motiva_path)
    
    font_loaded = False
    font_name = "Arial"  # Default fallback
    
    if selected_font == "TrixieCyrG-Plain Regular":
        if trixie_id != -1:
            font_families = QFontDatabase.applicationFontFamilies(trixie_id)
            if font_families:
                font_name = font_families[0]  # Use "TrixieCyrG-Plain" instead of "TrixieCyrG-Plain Regular"
                font_loaded = True
                logger.info(f"Loaded TrixieCyrG font: '{font_name}'")
        else:
            logger.warning(f"Failed to load TrixieCyrG font from: {trixie_path}")
    
    elif selected_font == "MotivaSansRegular":
        if motiva_id != -1:
            font_families = QFontDatabase.applicationFontFamilies(motiva_id)
            if font_families:
                font_name = font_families[0]
                font_loaded = True
                logger.info(f"Loaded MotivaSans font: '{font_name}'")
        else:
            logger.warning(f"Failed to load MotivaSans font from: {motiva_path}")
    
    # Apply font if loaded successfully
    if font_loaded:
        custom_font = QFont(font_name, Typography.BODY_SIZE)
        app.setFont(custom_font)
        logger.info(f"Applied selected font: '{font_name}' with size {Typography.BODY_SIZE}px")
    else:
        logger.warning(f"Could not load selected font '{selected_font}', using fallback: {font_name}")
    
    # Apply theme after font is loaded
    theme.apply_theme_to_app(app)
    # --- MODIFICATION END ---

    try:
        # Check if a zip file was passed as command line argument
        zip_file_arg = None
        if len(sys.argv) > 1:
            zip_file_arg = sys.argv[1]
            if zip_file_arg.lower().endswith('.zip') and os.path.isfile(zip_file_arg):
                logger.info(f"Zip file provided as argument: {zip_file_arg}")
            else:
                zip_file_arg = None

        main_win = MainWindow(zip_file_arg)
        main_win.show()
        logger.info("Main window displayed successfully.")
        # Start the Qt event loop.
        sys.exit(app.exec())
    except Exception as e:
        # A global catch-all for any unhandled exceptions during initialization.
        logger.critical(f"A critical error occurred, and the application must close. Error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
