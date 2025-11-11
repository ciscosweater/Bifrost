import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QCheckBox, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt
from ui.enhanced_dialogs import ModernDialog
from ui.theme import theme, Typography, Spacing, BorderRadius
from utils.settings import get_logging_setting, set_logging_setting
from utils.logger import update_logging_mode

logger = logging.getLogger(__name__)

class LoggingSettingsDialog(ModernDialog):
    """
    Dialog for configuring logging settings.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Logging Settings")
        self.setMinimumWidth(400)
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout()
        
        # Log level group
        level_group = QGroupBox("Log Level")
        level_layout = QVBoxLayout()
        
        self.level_combo = QComboBox()
        self.level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_combo.setToolTip("Sets the minimum level of messages that will be displayed")
        
        level_layout.addWidget(QLabel("Minimum Level:"))
        level_layout.addWidget(self.level_combo)
        level_group.setLayout(level_layout)
        
        # Display mode group
        display_group = QGroupBox("Display Mode")
        display_layout = QVBoxLayout()
        
        self.simple_mode_checkbox = QCheckBox("Simplified Mode")
        self.simple_mode_checkbox.setToolTip(
            "Enables simplified format: 'LEVEL: message' instead of 'date - module - level - message'"
        )
        
        display_layout.addWidget(self.simple_mode_checkbox)
        display_group.setLayout(display_layout)
        
        # Info label
        info_label = QLabel(
            "• app.log file will always contain all logs (complete DEBUG)\n"
            "• Changes applied immediately to console and interface\n"
            "• Detailed logs are useful for debugging problems"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"color: {theme.colors.TEXT_SECONDARY}; {Typography.get_font_style(Typography.CAPTION_SIZE)}; margin: {Spacing.SM}px 0;")
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._save_settings)
        self.save_button.setDefault(True)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        
        # Add all to main layout
        layout.addWidget(level_group)
        layout.addWidget(display_group)
        layout.addWidget(info_label)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _load_settings(self):
        """Load current settings into the UI."""
        current_level = str(get_logging_setting("level", "INFO"))
        current_simple = bool(get_logging_setting("simple_mode", False))
        
        # Set level
        index = self.level_combo.findText(current_level.upper())
        if index >= 0:
            self.level_combo.setCurrentIndex(index)
        
        # Set simple mode
        self.simple_mode_checkbox.setChecked(current_simple)
    
    def _save_settings(self):
        """Save settings and apply changes."""
        try:
            new_level = self.level_combo.currentText()
            new_simple = self.simple_mode_checkbox.isChecked()
            
            # Save settings
            set_logging_setting("level", new_level)
            set_logging_setting("simple_mode", new_simple)
            
            # Apply changes
            update_logging_mode()
            
            logger.info(f"Logging settings updated: level={new_level}, simple_mode={new_simple}")
            
            QMessageBox.information(
                self,
                "Settings Saved",
                "Logging settings have been updated successfully!"
            )
            
            self.accept()
            
        except Exception as e:
            logger.error(f"Error saving logging settings: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while saving settings: {e}"
            )