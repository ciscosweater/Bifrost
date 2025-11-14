import logging
from utils.logger import get_internationalized_logger
from utils.i18n import tr

from PyQt6.QtCore import QEasingCurve, QObject, QPropertyAnimation, Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ui.custom_checkbox import CustomCheckBox
from ui.interactions import AnimatedLabel, HoverButton, ModernFrame
from ui.theme import BorderRadius, Spacing, Typography
from utils.settings import (
    get_font_setting,
    get_logging_setting,
    get_settings,
    is_steam_schema_enabled,
    set_font_setting,
    set_logging_setting,
    set_steam_schema_setting,
    should_auto_setup_credentials,
)

# Import i18n
try:
    from utils.i18n import tr
except (ImportError, ModuleNotFoundError):

    def tr(context, text):
        return text


logger = get_internationalized_logger()


class ImageFetcher(QObject):
    finished = pyqtSignal(bytes)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            import urllib.request

            with urllib.request.urlopen(self.url) as response:
                data = response.read()
                self.finished.emit(data)
        except Exception as e:
            logger.warning(f"Failed to fetch header image from {self.url}: {e}")
            self.finished.emit(b"")


class ModernDialog(QDialog):
    """
    Base class for modern dialogs with enhanced styling and animations.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_modern_style()
        self._setup_animations()

    def _setup_modern_style(self):
        """Apply modern styling to dialog."""
        from .theme import theme

        self.setStyleSheet(f"""
            QDialog {{
                background: {theme.colors.BACKGROUND};
                border: 2px solid {theme.colors.PRIMARY};
                color: {theme.colors.TEXT_PRIMARY};
                border-radius: {BorderRadius.LARGE}px;
            }}
            QLabel {{
                color: {theme.colors.TEXT_PRIMARY};
                font-weight: 500;
                padding: 4px;
            }}
            QListWidget {{
                background: {theme.colors.SURFACE};
                border: 1px solid {theme.colors.BORDER};
                padding: 4px;
                color: {theme.colors.TEXT_PRIMARY};
                border-radius: {BorderRadius.MEDIUM}px;
            }}
            QListWidget::item {{
                padding: 8px;
                margin: 2px;
                background: {theme.colors.SURFACE_LIGHT};
                border: 1px solid {theme.colors.BORDER};
                border-radius: {BorderRadius.SMALL}px;
            }}
            QListWidget::item:selected {{
                background: {theme.colors.PRIMARY};
                color: {theme.colors.TEXT_ON_PRIMARY};
                border: 1px solid {theme.colors.PRIMARY};
            }}
            QListWidget::item:hover {{
                background: {theme.colors.SURFACE_LIGHT};
                border: 1px solid {theme.colors.PRIMARY};
            }}
        """)

    def _setup_animations(self):
        """Setup fade-in animation."""
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self._fade_animation.setDuration(300)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def showEvent(self, a0):
        """Trigger fade-in animation when showing dialog."""
        super().showEvent(a0)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.start()


class SettingsDialog(ModernDialog):
    """
    Enhanced settings dialog with modern layout and better organization.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("EnhancedDialogs", "Settings"))
        self.setFixedSize(500, 400)
        self.settings = get_settings()
        self._original_settings = {}
        self._setup_ui()
        self._store_original_settings()

        logger.debug("Opening enhanced SettingsDialog.")

    def _setup_ui(self):
        """Setup modern UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(Spacing.MD)
        main_layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)

        # Title
        title = AnimatedLabel(tr("EnhancedDialogs", "Application Settings"))
        from .theme import theme

        title.setStyleSheet(
            f"{Typography.get_font_style(Typography.H1_SIZE, Typography.WEIGHT_BOLD)}; color: {theme.colors.TEXT_ACCENT};"
        )
        main_layout.addWidget(title)

        # Create scroll area for settings
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: {theme.colors.SURFACE_DARK};
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background: {theme.colors.PRIMARY};
                min-height: 20px;
            }
        """)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(Spacing.MD)

        # SLSsteam Integration Section
        sls_frame = ModernFrame()
        sls_layout = QVBoxLayout(sls_frame)

        sls_title = QLabel(tr("EnhancedDialogs", "SLSsteam Integration"))
        from .theme import theme

        sls_title.setStyleSheet(
            f"{Typography.get_font_style(Typography.H3_SIZE, Typography.WEIGHT_BOLD)}; color: {theme.colors.TEXT_ACCENT};"
        )
        sls_layout.addWidget(sls_title)

        self.slssteam_mode_checkbox = CustomCheckBox(
            tr("EnhancedDialogs", "SLSsteam Mode")
        )
        self.slssteam_mode_checkbox.setChecked(
            self.settings.value("slssteam_mode", True, type=bool)
        )
        self.slssteam_mode_checkbox.setToolTip(
            tr(
                "EnhancedDialogs",
                "Enable SLSsteam mode to automatically select Steam library folders as destination.",
            )
        )
        sls_layout.addWidget(self.slssteam_mode_checkbox)

        scroll_layout.addWidget(sls_frame)

        # Steam Schema Section
        schema_frame = ModernFrame()
        schema_layout = QVBoxLayout(schema_frame)

        schema_title = QLabel(tr("EnhancedDialogs", "SLScheevo Schema Generator"))
        from .theme import theme

        schema_title.setStyleSheet(
            f"{Typography.get_font_style(Typography.H3_SIZE, Typography.WEIGHT_BOLD)}; color: {theme.colors.TEXT_ACCENT};"
        )
        schema_layout.addWidget(schema_title)

        self.steam_schema_enabled_checkbox = CustomCheckBox(
            tr("EnhancedDialogs", "Enable SLScheevo Schema Generation")
        )
        self.steam_schema_enabled_checkbox.setChecked(bool(is_steam_schema_enabled()))
        self.steam_schema_enabled_checkbox.setToolTip(
            tr(
                "EnhancedDialogs",
                "Automatically generate achievement schemas using SLScheevo after downloading games.",
            )
        )
        schema_layout.addWidget(self.steam_schema_enabled_checkbox)

        self.auto_setup_checkbox = CustomCheckBox(
            tr("EnhancedDialogs", "Auto-Setup SLScheevo Credentials")
        )
        self.auto_setup_checkbox.setChecked(bool(should_auto_setup_credentials()))
        self.auto_setup_checkbox.setToolTip(
            tr(
                "EnhancedDialogs",
                "Automatically configure SLScheevo login credentials for schema generation.",
            )
        )
        schema_layout.addWidget(self.auto_setup_checkbox)

        # SLScheevo username setting
        username_layout = QHBoxLayout()
        username_label = QLabel(tr("EnhancedDialogs", "SLScheevo Username:"))
        from .theme import theme

        username_label.setStyleSheet(
            f"color: {theme.colors.TEXT_SECONDARY}; {Typography.get_font_style(Typography.BODY_SIZE)};"
        )
        username_layout.addWidget(username_label)

        self.slscheevo_username_edit = QLineEdit()
        self.slscheevo_username_edit.setPlaceholderText(
            tr("EnhancedDialogs", "Leave empty to auto-detect")
        )
        self.slscheevo_username_edit.setText(
            self.settings.value("slscheevo_username", "", type=str)
        )
        self.slscheevo_username_edit.setToolTip(
            tr(
                "EnhancedDialogs",
                "SLScheevo username for schema generation. Leave empty to auto-detect from saved accounts.",
            )
        )
        username_layout.addWidget(self.slscheevo_username_edit)

        # Add refresh button to detect usernames
        refresh_button = HoverButton(tr("EnhancedDialogs", "Refresh"))
        refresh_button.setFixedSize(25, 20)
        refresh_button.setToolTip(
            tr("EnhancedDialogs", "Detect available SLScheevo usernames")
        )
        refresh_button.clicked.connect(self._detect_slscheevo_usernames)
        username_layout.addWidget(refresh_button)

        schema_layout.addLayout(username_layout)

        scroll_layout.addWidget(schema_frame)

        # Logging Section
        logging_frame = ModernFrame()
        logging_layout = QVBoxLayout(logging_frame)

        logging_title = QLabel(tr("EnhancedDialogs", "Logging Configuration"))
        from .theme import theme

        logging_title.setStyleSheet(
            f"{Typography.get_font_style(Typography.H3_SIZE, Typography.WEIGHT_BOLD)}; color: {theme.colors.TEXT_ACCENT};"
        )
        logging_layout.addWidget(logging_title)

        self.simple_mode_checkbox = CustomCheckBox(
            tr("EnhancedDialogs", "Simplified Log Format")
        )
        self.simple_mode_checkbox.setChecked(
            bool(get_logging_setting("simple_mode", False))
        )
        self.simple_mode_checkbox.setToolTip(
            tr(
                "EnhancedDialogs",
                "Use simplified format: 'LEVEL: message' instead of full timestamp and module info",
            )
        )
        logging_layout.addWidget(self.simple_mode_checkbox)

        # Log level setting
        level_layout = QHBoxLayout()
        level_label = QLabel(tr("EnhancedDialogs", "Log Level:"))
        from .theme import theme

        level_label.setStyleSheet(
            f"color: {theme.colors.TEXT_SECONDARY}; {Typography.get_font_style(Typography.BODY_SIZE)};"
        )
        level_layout.addWidget(level_label)

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        current_level = str(get_logging_setting("level", "INFO"))
        index = self.log_level_combo.findText(current_level.upper())
        if index >= 0:
            self.log_level_combo.setCurrentIndex(index)
        self.log_level_combo.setToolTip(
            tr(
                "EnhancedDialogs",
                "Minimum log level to display (DEBUG shows everything, CRITICAL shows only errors)",
            )
        )
        level_layout.addWidget(self.log_level_combo)

        logging_layout.addLayout(level_layout)

        # Info label
        info_label = QLabel(
            tr("EnhancedDialogs", "File 'app.log' always saves complete DEBUG logs")
        )
        from .theme import theme

        info_label.setStyleSheet(
            f"color: {theme.colors.TEXT_DISABLED}; {Typography.get_font_style(Typography.CAPTION_SIZE)}; font-style: italic;"
        )
        info_label.setWordWrap(True)
        logging_layout.addWidget(info_label)

        scroll_layout.addWidget(logging_frame)

        # Font Settings Section
        font_frame = ModernFrame()
        font_layout = QVBoxLayout(font_frame)

        font_title = QLabel(tr("EnhancedDialogs", "Font Settings"))
        from .theme import theme

        font_title.setStyleSheet(
            f"{Typography.get_font_style(Typography.H3_SIZE, Typography.WEIGHT_BOLD)}; color: {theme.colors.TEXT_ACCENT};"
        )
        font_layout.addWidget(font_title)

        # Font selection
        font_selection_layout = QHBoxLayout()
        font_label = QLabel(tr("EnhancedDialogs", "Application Font:"))
        font_label.setStyleSheet(
            f"color: {theme.colors.TEXT_SECONDARY}; {Typography.get_font_style(Typography.BODY_SIZE)};"
        )
        font_selection_layout.addWidget(font_label)

        self.font_combo = QComboBox()
        self.font_combo.addItems(
            ["TrixieCyrG-Plain Regular (Default)", "MotivaSansRegular (New)"]
        )
        current_font = str(
            get_font_setting("selected_font", "TrixieCyrG-Plain Regular")
        )
        if current_font == "MotivaSansRegular":
            self.font_combo.setCurrentIndex(1)
        else:
            self.font_combo.setCurrentIndex(0)
        self.font_combo.setToolTip(
            tr("EnhancedDialogs", "Select font to use throughout the application")
        )
        font_selection_layout.addWidget(self.font_combo)

        font_layout.addLayout(font_selection_layout)

        # Info label
        font_info_label = QLabel(
            tr("EnhancedDialogs", "Requires application restart to take effect")
        )
        font_info_label.setStyleSheet(
            f"color: {theme.colors.TEXT_DISABLED}; {Typography.get_font_style(Typography.CAPTION_SIZE)}; font-style: italic;"
        )
        font_layout.addWidget(font_info_label)

        scroll_layout.addWidget(font_frame)

        # Language Settings Section
        language_frame = ModernFrame()
        language_layout = QVBoxLayout(language_frame)

        language_title = QLabel(tr("EnhancedDialogs", "Language Settings"))
        from .theme import theme

        language_title.setStyleSheet(
            f"{Typography.get_font_style(Typography.H3_SIZE, Typography.WEIGHT_BOLD)}; color: {theme.colors.TEXT_ACCENT};"
        )
        language_layout.addWidget(language_title)

        # Language selection
        language_selection_layout = QHBoxLayout()
        language_label = QLabel(tr("EnhancedDialogs", "Application Language:"))
        language_label.setStyleSheet(
            f"color: {theme.colors.TEXT_SECONDARY}; {Typography.get_font_style(Typography.BODY_SIZE)};"
        )
        language_selection_layout.addWidget(language_label)

        self.language_combo = QComboBox()
        self.language_combo.addItems(["English", "Português (Brasil)"])

        # Map language codes to indices
        self.language_codes = ["en", "pt_BR"]

        # Set current language from settings
        current_language = self.settings.value("language", "en", type=str)

        # Find index for current language
        try:
            current_index = self.language_codes.index(current_language)
            self.language_combo.setCurrentIndex(current_index)
        except ValueError:
            self.language_combo.setCurrentIndex(0)  # Default to English

        self.language_combo.setToolTip(
            tr("EnhancedDialogs", "Select application language (requires restart)")
        )
        language_selection_layout.addWidget(self.language_combo)

        language_layout.addLayout(language_selection_layout)

        # Info label
        language_info_label = QLabel(
            tr("EnhancedDialogs", "Requires application restart to take effect")
        )
        language_info_label.setStyleSheet(
            f"color: {theme.colors.TEXT_DISABLED}; {Typography.get_font_style(Typography.CAPTION_SIZE)}; font-style: italic;"
        )
        language_layout.addWidget(language_info_label)

        scroll_layout.addWidget(language_frame)

        # DRM Removal Section
        drm_frame = ModernFrame()
        drm_layout = QVBoxLayout(drm_frame)

        drm_title = QLabel(tr("EnhancedDialogs", "DRM Removal"))
        from .theme import theme

        drm_title.setStyleSheet(
            f"{Typography.get_font_style(Typography.H3_SIZE, Typography.WEIGHT_BOLD)}; color: {theme.colors.TEXT_ACCENT};"
        )
        drm_layout.addWidget(drm_title)

        self.steamless_enabled_checkbox = CustomCheckBox(
            tr("EnhancedDialogs", "Enable Steamless DRM Removal")
        )
        is_steamless_enabled = self.settings.value("steamless_enabled", True, type=bool)
        self.steamless_enabled_checkbox.setChecked(is_steamless_enabled)
        self.steamless_enabled_checkbox.setToolTip(
            tr(
                "EnhancedDialogs",
                "Automatically remove Steam DRM from downloaded executables after download.",
            )
        )
        drm_layout.addWidget(self.steamless_enabled_checkbox)

        scroll_layout.addWidget(drm_frame)

        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        # Modern buttons
        button_layout = QHBoxLayout()

        help_button = HoverButton(tr("EnhancedDialogs", "Help (F1)"))
        help_button.clicked.connect(self._show_help)
        button_layout.addWidget(help_button)

        button_layout.addStretch()

        cancel_button = HoverButton(tr("EnhancedDialogs", "Cancel"))
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        save_button = HoverButton(tr("EnhancedDialogs", "Save Settings"))
        save_button.clicked.connect(self.accept)
        button_layout.addWidget(save_button)

        main_layout.addLayout(button_layout)

    def _store_original_settings(self):
        """Store original settings to detect changes."""
        self._original_settings = {
            "slssteam_mode": self.settings.value("slssteam_mode", True, type=bool),
            "steam_schema_enabled": bool(is_steam_schema_enabled()),
            "auto_setup_credentials": bool(should_auto_setup_credentials()),
            "slscheevo_username": self.settings.value(
                "slscheevo_username", "", type=str
            ),
            "steamless_enabled": self.settings.value(
                "steamless_enabled", True, type=bool
            ),
            "simple_mode": bool(get_logging_setting("simple_mode", False)),
            "log_level": str(get_logging_setting("level", "INFO")),
            "selected_font": str(
                get_font_setting("selected_font", "TrixieCyrG-Plain Regular")
            ),
            "language": self.settings.value("language", "en", type=str),
        }

    def _detect_slscheevo_usernames(self):
        """Detect available SLScheevo usernames and show selection dialog"""
        try:
            # Import here to avoid circular imports
            from core.steam_schema_integration import SteamSchemaIntegration

            schema_integration = SteamSchemaIntegration()

            # Find SLScheevo directory
            import os

            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            slscheevo_dir = os.path.join(current_dir, "slscheevo_build")

            if not os.path.exists(slscheevo_dir):
                QMessageBox.warning(
                    self,
                    tr("EnhancedDialogs", "SLScheevo Not Found"),
                    tr(
                        "EnhancedDialogs",
                        "SLScheevo directory not found. Please install SLScheevo first.",
                    ),
                )
                return

            # Get available usernames
            usernames = schema_integration._get_available_slscheevo_usernames(
                slscheevo_dir
            )

            if not usernames:
                QMessageBox.information(
                    self,
                    tr("EnhancedDialogs", "No Accounts Found"),
                    tr(
                        "EnhancedDialogs",
                        "No SLScheevo accounts found. Please run SLScheevo manually first to set up your Steam login.",
                    ),
                )
                return

            # Show selection dialog
            msg = QMessageBox(self)
            msg.setWindowTitle(tr("EnhancedDialogs", "Select SLScheevo Account"))
            msg.setText(tr("EnhancedDialogs", "Available SLScheevo accounts found:"))
            msg.setInformativeText(
                tr("EnhancedDialogs", "Choose an account to set as default:")
            )

            # Add buttons for each username
            for username in usernames:
                msg.addButton(username, QMessageBox.ButtonRole.AcceptRole)

            # Add cancel button
            cancel_button = msg.addButton(
                tr("EnhancedDialogs", "Cancel"), QMessageBox.ButtonRole.RejectRole
            )

            msg.exec()

            # Get selected username
            clicked_button = msg.clickedButton()
            if clicked_button and clicked_button != cancel_button:
                selected_username = clicked_button.text()
                self.slscheevo_username_edit.setText(selected_username)
                QMessageBox.information(
                    self,
                    tr("EnhancedDialogs", "Username Set"),
                    tr(
                        "EnhancedDialogs", "SLScheevo username set to: {username}"
                    ).format(username=selected_username),
                )

        except Exception as e:
            logger.error(f"Error detecting SLScheevo usernames: {e}")
            QMessageBox.critical(
                self,
                tr("EnhancedDialogs", "Error"),
                tr(
                    "EnhancedDialogs", "Failed to detect SLScheevo usernames: {e}"
                ).format(e=e),
            )

    def _show_help(self):
        """Show settings help dialog."""
        help_text = """
  Settings Help:

  SLSsteam Integration
  • Enables compatibility with SLSsteam wrapper
  • Required for Linux Steam integration
  • SLSsteam mode auto-selects Steam library folders

  Steam Schema Generator
  • Auto-generates achievement schemas
  • Requires SLScheevo login credentials
  • Configure username or leave empty to auto-detect

  DRM Removal
  • Removes Steam DRM from executables
  • Makes games playable without Steam client

  Logging Configuration
  • Simplified format: 'ERROR: message' vs full timestamp
  • Log levels: DEBUG (all), INFO (normal), WARNING/ERROR/CRITICAL (less)
  • File 'app.log' always saves complete DEBUG logs for troubleshooting

  Font Settings
  • Choose between default and new font styles
  • Changes require application restart
  • Font affects entire application interface

  Keyboard Shortcuts:
  F1 - Show this help
  Ctrl+S - Open Settings
  Ctrl+F - Font Settings
        """
        QMessageBox.information(
            self, tr("EnhancedDialogs", "Settings Help"), help_text.strip()
        )

    def accept(self):
        """Save settings with enhanced feedback."""
        # Get current values
        current_values = {
            "slssteam_mode": self.slssteam_mode_checkbox.isChecked(),
            "steam_schema_enabled": self.steam_schema_enabled_checkbox.isChecked(),
            "auto_setup_credentials": self.auto_setup_checkbox.isChecked(),
            "slscheevo_username": self.slscheevo_username_edit.text().strip(),
            "steamless_enabled": self.steamless_enabled_checkbox.isChecked(),
            "simple_mode": self.simple_mode_checkbox.isChecked(),
            "log_level": self.log_level_combo.currentText(),
        }

        selected_text = self.font_combo.currentText()
        if "MotivaSansRegular" in selected_text:
            current_values["selected_font"] = "MotivaSansRegular"
        else:
            current_values["selected_font"] = "TrixieCyrG-Plain Regular"

        # Get selected language
        language_index = self.language_combo.currentIndex()
        current_values["language"] = self.language_codes[language_index]

        # Check for changes
        changes_made = []

        # Check each setting for changes
        for key, current_value in current_values.items():
            if key in self._original_settings:
                original_value = self._original_settings[key]
                if original_value != current_value:
                    changes_made.append(f"{key}: {original_value} → {current_value}")
                    # Any setting change requires restart
                    restart_required = True

        # Save SLSsteam mode setting
        self.settings.setValue("slssteam_mode", current_values["slssteam_mode"])
        logger.debug(f"SLSsteam mode changed to: {current_values['slssteam_mode']}")

        logger.debug("SLSsteam integration settings updated successfully.")

        # Save Steam Schema settings
        set_steam_schema_setting("enabled", current_values["steam_schema_enabled"])
        set_steam_schema_setting(
            "auto_setup_credentials", current_values["auto_setup_credentials"]
        )

        # Save SLScheevo username
        self.settings.setValue(
            "slscheevo_username", current_values["slscheevo_username"]
        )
        logger.info(
            f"SLScheevo username saved: {current_values['slscheevo_username'] if current_values['slscheevo_username'] else '(auto-detect)'}"
        )

        # Save Steamless setting
        self.settings.setValue("steamless_enabled", current_values["steamless_enabled"])
        logger.info(
            f"Steamless DRM removal setting changed to: {current_values['steamless_enabled']}"
        )

        # Save logging settings
        set_logging_setting("simple_mode", current_values["simple_mode"])
        set_logging_setting("level", current_values["log_level"])
        logger.info(
            f"Logging settings updated: simple_mode={current_values['simple_mode']}, level={current_values['log_level']}"
        )

        # Save font settings
        set_font_setting("selected_font", current_values["selected_font"])
        logger.info(
            f"Font setting updated: selected_font={current_values['selected_font']}"
        )

        # Save language setting
        self.settings.setValue("language", current_values["language"])
        logger.info(f"Language setting updated: language={current_values['language']}")

        # Apply logging changes immediately
        from utils.logger import update_logging_mode

        update_logging_mode()

        logger.info("Enhanced settings updated successfully.")

        # Always show restart dialog if changes were made
        if changes_made:
            reply = QMessageBox.question(
                self,
                tr("EnhancedDialogs", "Restart Application"),
                tr(
                    "EnhancedDialogs",
                    "The following settings were changed:\n\n{changes}\n\nApplication restart is required to apply all changes.\nDo you want to restart now?",
                ).format(
                    changes="\n".join([f"• {change}" for change in changes_made])
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Restart application
                import os
                import sys

                from PyQt6.QtWidgets import QApplication

                logger.info("Restarting application to apply settings...")
                QApplication.quit()
                os.execv(sys.executable, ["python"] + sys.argv)

        super().accept()


class DepotSelectionDialog(ModernDialog):
    """
    Enhanced depot selection dialog with search and better UX.
    """

    def __init__(
        self, app_id, depots, depot_sizes=None, parent=None, total_game_size=0
    ):
        super().__init__(parent)
        self.setWindowTitle(tr("EnhancedDialogs", "Select Depots to Download"))
        self.depots = depots
        self.depot_sizes = depot_sizes or {}
        self.total_game_size = total_game_size
        logger.info(
            f"{tr('DepotSelectionDialog', 'DepotSelectionDialog initialized with')} {len(depots)} {tr('DepotSelectionDialog', 'depots and')} {len(self.depot_sizes)} size entries"
        )
        logger.debug(f"Depot sizes: {self.depot_sizes}")
        logger.debug(
            f"Total game size: {total_game_size} bytes ({total_game_size / 1024 / 1024 / 1024:.2f} GB)"
        )
        self.setMinimumSize(480, 400)
        self.setMaximumSize(500, 900)
        self.resize(480, 700)
        self._setup_ui(app_id)

    def _setup_ui(self, app_id):
        """Setup enhanced UI with search functionality."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(Spacing.SM)
        main_layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)

        # Header with image
        self.header_label = QLabel(tr("EnhancedDialogs", "Loading header image..."))
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header_label.setMinimumHeight(215)
        self.header_label.setMaximumHeight(215)
        self.header_label.setScaledContents(False)
        from .theme import theme

        self.header_label.setStyleSheet(f"""
            QLabel {{
                border: 1px solid {theme.colors.BORDER};
                background: {theme.colors.SURFACE};
                border-radius: {BorderRadius.MEDIUM}px;
            }}
        """)
        self._fetch_header_image(app_id)

        main_layout.addWidget(self.header_label)

        # Game size info
        if self.total_game_size > 0:
            size_gb = self.total_game_size / (1024**3)
            size_mb = self.total_game_size / (1024**2)

            if size_gb >= 1:
                size_text = tr("EnhancedDialogs", "Total Size: {size:.2f} GB").format(
                    size=size_gb
                )
            else:
                size_text = tr("EnhancedDialogs", "Total Size: {size:.0f} MB").format(
                    size=size_mb
                )

            self.size_label = QLabel(size_text)
            self.size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.size_label.setStyleSheet(f"""
                QLabel {{
                    background: {theme.colors.PRIMARY};
                    color: {theme.colors.TEXT_ON_PRIMARY};
                    border-radius: {BorderRadius.SMALL}px;
                    padding: 8px;
                    font-weight: bold;
                    margin: 4px 0px;
                }}
            """)
            main_layout.addWidget(self.size_label)

        # Select all/none buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        select_all_btn = HoverButton(tr("EnhancedDialogs", "Select All"))
        select_all_btn.clicked.connect(self._select_all)
        button_layout.addWidget(select_all_btn)

        select_none_btn = HoverButton(tr("EnhancedDialogs", "Select None"))
        select_none_btn.clicked.connect(self._select_none)
        button_layout.addWidget(select_none_btn)

        main_layout.addLayout(button_layout)

        # Create scroll area for depot list
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setMinimumHeight(200)
        scroll_area.setMaximumHeight(400)

        # Depot list
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
        # Enable checkbox clicking using itemClicked signal for immediate response
        self.list_widget.itemClicked.connect(self._on_item_clicked)

        # Set better styling for list items to prevent overlap
        from .theme import theme

        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background: {theme.colors.SURFACE};
                border: 1px solid {theme.colors.BORDER};
                border-radius: {BorderRadius.MEDIUM}px;
                padding: 4px;
            }}
            QListWidget::item {{
                background: {theme.colors.SURFACE_LIGHT};
                border: 1px solid {theme.colors.BORDER};
                border-radius: {BorderRadius.SMALL}px;
                padding: 8px;
                margin: 2px;
                min-height: 32px;
                color: {theme.colors.TEXT_PRIMARY};
            }}
            QListWidget::item:hover {{
                background: {theme.colors.SURFACE_LIGHT};
                border: 1px solid {theme.colors.PRIMARY};
            }}
            QListWidget::item:selected {{
                background: {theme.colors.PRIMARY};
                color: {theme.colors.TEXT_ON_PRIMARY};
                border: 1px solid {theme.colors.PRIMARY};
            }}
        """)

        # Calculate optimal height based on number of depots
        depot_count = len(self.depots)
        optimal_height = min(
            400, max(200, depot_count * 40 + 20)
        )  # 40px per item + padding
        self.list_widget.setMinimumHeight(optimal_height)

        for depot_id, depot_data in self.depots.items():
            item_text = f"{depot_id} - {depot_data.get('name', depot_data.get('desc', 'Unknown Depot'))}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, depot_id)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            # Set proper size hint to prevent overlap
            from PyQt6.QtCore import QSize

            item.setSizeHint(QSize(-1, 36))  # Fixed height of 36px per item
            self.list_widget.addItem(item)

        scroll_area.setWidget(self.list_widget)
        main_layout.addWidget(scroll_area)

        # Status label
        self.status_label = QLabel(
            tr("EnhancedDialogs", "Found {count} depots").format(count=len(self.depots))
        )
        from .theme import theme

        self.status_label.setStyleSheet(
            f"color: {theme.colors.TEXT_SECONDARY}; font-style: italic;"
        )
        main_layout.addWidget(self.status_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = HoverButton(tr("EnhancedDialogs", "Cancel"))
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        download_button = HoverButton(tr("EnhancedDialogs", "Download Selected"))
        download_button.clicked.connect(self.accept)
        button_layout.addWidget(download_button)

        main_layout.addLayout(button_layout)

    def _select_all(self):
        """Select all depots."""
        if self.list_widget:
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item:
                    item.setCheckState(Qt.CheckState.Checked)

    def _select_none(self):
        """Deselect all depots."""
        if self.list_widget:
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item:
                    item.setCheckState(Qt.CheckState.Unchecked)

    def _on_item_clicked(self, item):
        """Handle item click to toggle checkbox state."""
        if item:
            # Toggle the check state
            current_state = item.checkState()
            new_state = (
                Qt.CheckState.Unchecked
                if current_state == Qt.CheckState.Checked
                else Qt.CheckState.Checked
            )
            item.setCheckState(new_state)

    def _fetch_header_image(self, app_id):
        """Fetches the game's header image using GameImageManager with API fallback."""
        from utils.image_cache import ImageCacheManager

        from .game_image_manager import GameImageManager

        cache_manager = ImageCacheManager()
        self.image_manager = GameImageManager(cache_manager)
        self.image_thread = self.image_manager.get_game_image(app_id, "header")
        self.image_manager.image_ready.connect(self.on_image_ready)
        self.image_manager.image_failed.connect(self.on_image_failed)
        self.image_thread.finished.connect(self.image_thread.deleteLater)

    def on_image_ready(self, app_id, pixmap, source_info):
        """Slot to handle successfully fetched image."""
        logger.info(f"Image loaded for app {app_id} from {source_info}")
        # Store original pixmap for sharing with main window
        self.original_pixmap = pixmap
        # Scale while maintaining aspect ratio, fit within 440x215
        scaled_pixmap = pixmap.scaled(
            440,
            215,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.header_label.setPixmap(scaled_pixmap)

    def on_image_failed(self, app_id, error_message):
        """Slot to handle image fetch failure."""
        logger.warning(f"Failed to load image for app {app_id}: {error_message}")
        self.header_label.setText(tr("EnhancedDialogs", "Header image not available."))
        self.original_pixmap = None

    def on_image_fetched(self, image_data):
        """Legacy method - kept for backward compatibility."""
        if image_data:
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            self.on_image_ready("unknown", pixmap, "legacy")
        else:
            self.on_image_failed("unknown", "Legacy fetch failed")

    def get_header_image(self):
        """Return the original header image pixmap for sharing with main window"""
        return getattr(self, "original_pixmap", None)

    def get_selected_depots(self):
        """Get list of selected depot IDs."""
        selected = []
        if self.list_widget:
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item and item.checkState() == Qt.CheckState.Checked:
                    depot_id = item.data(Qt.ItemDataRole.UserRole)
                    selected.append(depot_id)
        return selected

    def get_total_game_size(self):
        """Return the total game size that was displayed in the dialog."""
        return self.total_game_size


class SteamLibraryDialog(ModernDialog):
    """
    A dialog to let the user choose from a list of found Steam library folders.
    """

    def __init__(self, library_paths, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("EnhancedDialogs", "Select Steam Library"))
        self.selected_path = None
        self.setMinimumWidth(500)
        self._setup_ui(library_paths)

    def _setup_ui(self, library_paths):
        """Setup UI for library selection."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(Spacing.SM)
        main_layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)

        # Title
        title = AnimatedLabel(tr("EnhancedDialogs", "Select Steam Library"))
        from .theme import theme

        title.setStyleSheet(
            f"{Typography.get_font_style(Typography.H2_SIZE, Typography.WEIGHT_BOLD)}; color: {theme.colors.TEXT_ACCENT};"
        )
        main_layout.addWidget(title)

        # Library list
        self.list_widget = QListWidget()
        for path in library_paths:
            self.list_widget.addItem(QListWidgetItem(path))
        main_layout.addWidget(self.list_widget)

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = HoverButton(tr("EnhancedDialogs", "Cancel"))
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        select_button = HoverButton(tr("EnhancedDialogs", "Select"))
        select_button.clicked.connect(self.accept)
        button_layout.addWidget(select_button)

        main_layout.addLayout(button_layout)

    def accept(self):
        current_item = self.list_widget.currentItem()
        if current_item:
            self.selected_path = current_item.text()
            logger.info(f"User selected Steam library: {self.selected_path}")
            super().accept()
        else:
            QMessageBox.warning(
                self,
                tr("EnhancedDialogs", "No Selection"),
                tr("EnhancedDialogs", "Please select a library folder."),
            )

    def get_selected_path(self):
        return self.selected_path


class DlcSelectionDialog(ModernDialog):
    """
    A dialog that allows the user to select which DLC AppIDs to add for the
    SLSsteam wrapper.
    """

    def __init__(self, dlcs, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("EnhancedDialogs", "Select DLC for SLSsteam Wrapper"))
        self.dlcs = dlcs
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        self._setup_ui()

    def _setup_ui(self):
        """Setup UI for DLC selection."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(Spacing.SM)
        main_layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)

        # Title
        title = AnimatedLabel(tr("EnhancedDialogs", "Select DLC"))
        from .theme import theme

        title.setStyleSheet(
            f"{Typography.get_font_style(Typography.H2_SIZE, Typography.WEIGHT_BOLD)}; color: {theme.colors.TEXT_ACCENT};"
        )
        main_layout.addWidget(title)

        # Select all/none buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        select_all_btn = HoverButton(tr("EnhancedDialogs", "Select All"))
        select_all_btn.clicked.connect(self._select_all)
        button_layout.addWidget(select_all_btn)

        select_none_btn = HoverButton(tr("EnhancedDialogs", "Select None"))
        select_none_btn.clicked.connect(self._select_none)
        button_layout.addWidget(select_none_btn)

        main_layout.addLayout(button_layout)

        # Create scroll area for DLC list
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setMinimumHeight(200)
        scroll_area.setMaximumHeight(400)

        # DLC list
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
        # Enable checkbox clicking using itemClicked signal for immediate response
        self.list_widget.itemClicked.connect(self._on_item_clicked)

        # Set better styling for list items to prevent overlap
        from .theme import theme

        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background: {theme.colors.SURFACE};
                border: 1px solid {theme.colors.BORDER};
                border-radius: {BorderRadius.MEDIUM}px;
                padding: 4px;
            }}
            QListWidget::item {{
                background: {theme.colors.SURFACE_LIGHT};
                border: 1px solid {theme.colors.BORDER};
                border-radius: {BorderRadius.SMALL}px;
                padding: 8px;
                margin: 2px;
                min-height: 32px;
                color: {theme.colors.TEXT_PRIMARY};
            }}
            QListWidget::item:hover {{
                background: {theme.colors.SURFACE_LIGHT};
                border: 1px solid {theme.colors.PRIMARY};
            }}
            QListWidget::item:selected {{
                background: {theme.colors.PRIMARY};
                color: {theme.colors.TEXT_ON_PRIMARY};
                border: 1px solid {theme.colors.PRIMARY};
            }}
        """)

        # Calculate optimal height based on number of DLCs
        dlc_count = len(self.dlcs)
        optimal_height = min(
            400, max(200, dlc_count * 40 + 20)
        )  # 40px per item + padding
        self.list_widget.setMinimumHeight(optimal_height)

        for dlc_id, dlc_desc in self.dlcs.items():
            item_text = f"{dlc_id} - {dlc_desc}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, dlc_id)
            item.setCheckState(Qt.CheckState.Checked)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            # Set proper size hint to prevent overlap
            from PyQt6.QtCore import QSize

            item.setSizeHint(QSize(-1, 36))  # Fixed height of 36px per item
            self.list_widget.addItem(item)

        scroll_area.setWidget(self.list_widget)
        main_layout.addWidget(scroll_area)

        # Status label
        self.status_label = QLabel(
            tr("EnhancedDialogs", "Found {count} DLCs").format(count=len(self.dlcs))
        )
        from .theme import theme

        self.status_label.setStyleSheet(
            f"color: {theme.colors.TEXT_SECONDARY}; font-style: italic;"
        )
        main_layout.addWidget(self.status_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = HoverButton(tr("EnhancedDialogs", "Cancel"))
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        add_button = HoverButton(tr("EnhancedDialogs", "Add Selected"))
        add_button.clicked.connect(self.accept)
        button_layout.addWidget(add_button)

        main_layout.addLayout(button_layout)

    def _on_item_clicked(self, item):
        """Handle item click to toggle checkbox state."""
        if item:
            # Toggle the check state
            current_state = item.checkState()
            new_state = (
                Qt.CheckState.Unchecked
                if current_state == Qt.CheckState.Checked
                else Qt.CheckState.Checked
            )
            item.setCheckState(new_state)

    def _select_all(self):
        """Select all DLCs."""
        if self.list_widget:
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item:
                    item.setCheckState(Qt.CheckState.Checked)

    def _select_none(self):
        """Deselect all DLCs."""
        if self.list_widget:
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item:
                    item.setCheckState(Qt.CheckState.Unchecked)

    def get_selected_dlcs(self):
        selected = []
        if self.list_widget:
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item and item.checkState() == Qt.CheckState.Checked:
                    selected.append(item.data(Qt.ItemDataRole.UserRole))
        return selected
