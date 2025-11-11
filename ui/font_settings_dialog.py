import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QGroupBox, QMessageBox, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt
from ui.enhanced_dialogs import ModernDialog
from ui.theme import theme, Typography, Spacing, BorderRadius
from utils.settings import get_font_setting, set_font_setting

logger = logging.getLogger(__name__)

class FontSettingsDialog(ModernDialog):
    """
    Dialog for configuring font settings.
    """
    
    # Available fonts
    AVAILABLE_FONTS = {
        "TrixieCyrG-Plain Regular": "TrixieCyrG-Plain Regular (Default)",
        "MotivaSansRegular": "MotivaSansRegular (New)"
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Font Settings")
        self.setMinimumWidth(450)
        self._original_font = None
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout()
        
        # Font selection group
        font_group = QGroupBox("Select Font")
        font_layout = QVBoxLayout()
        
        # Create radio buttons for font selection
        self.font_button_group = QButtonGroup()
        self.font_radio_buttons = {}
        
        for font_key, font_display in self.AVAILABLE_FONTS.items():
            radio = QRadioButton(font_display)
            radio.setProperty("font_key", font_key)
            self.font_radio_buttons[font_key] = radio
            self.font_button_group.addButton(radio)
            font_layout.addWidget(radio)
        
        # Add preview area
        preview_label = QLabel("Preview:")
        preview_label.setStyleSheet(f"font-weight: bold; margin-top: {Spacing.SM}px;")
        font_layout.addWidget(preview_label)
        
        self.preview_text = QLabel(
            "ACCELA - Font Test\n"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ\n"
            "abcdefghijklmnopqrstuvwxyz\n"
            "0123456789 !@#$%&*()"
        )
        self.preview_text.setStyleSheet(f"""
            QLabel {{
                background: {theme.colors.SURFACE};
                border: 1px solid {theme.colors.BORDER};
                padding: {Spacing.SM}px;
                border-radius: {BorderRadius.SMALL}px;
                {Typography.get_font_style(Typography.BODY_SIZE)};
            }}
        """)
        self.preview_text.setWordWrap(True)
        font_layout.addWidget(self.preview_text)
        
        font_group.setLayout(font_layout)
        
        # Info label
        info_label = QLabel(
            "• Font change will be applied to the entire application\n"
            "• Application restart is required to see the changes\n"
            "• Default font is TrixieCyrG-Plain Regular"
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
        layout.addWidget(font_group)
        layout.addWidget(info_label)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Connect radio button changes to update preview
        self.font_button_group.buttonToggled.connect(self._update_preview)
    
    def _load_settings(self):
        """Load current settings into the UI."""
        current_font = str(get_font_setting("selected_font", "TrixieCyrG-Plain Regular"))
        self._original_font = current_font
        
        # Set the radio button for current font
        if current_font in self.font_radio_buttons:
            self.font_radio_buttons[current_font].setChecked(True)
    
    def _update_preview(self):
        """Update the preview text with the selected font."""
        selected_button = self.font_button_group.checkedButton()
        if selected_button:
            font_key = selected_button.property("font_key")
            self.preview_text.setStyleSheet(f"""
                QLabel {{
                    background: {theme.colors.SURFACE};
                    border: 1px solid {theme.colors.BORDER};
                    padding: {Spacing.SM}px;
                    border-radius: {BorderRadius.SMALL}px;
                    {Typography.get_font_style(Typography.BODY_SIZE)};
                    font-family: '{font_key}';
                }}
            """)
    
    def _save_settings(self):
        """Save settings and apply changes."""
        try:
            selected_button = self.font_button_group.checkedButton()
            if not selected_button:
                QMessageBox.warning(self, "Warning", "Please select a font.")
                return
            
            new_font = selected_button.property("font_key")
            
            # Check if font was actually changed
            if self._original_font != new_font:
                # Save setting
                set_font_setting("selected_font", new_font)
                
                logger.info(f"Font setting updated: selected_font={new_font}")
                
                # Ask for restart
                reply = QMessageBox.question(
                    self,
                    "Restart Application",
                    f"Font changed from '{self._original_font}' to '{new_font}'.\n\n"
                    "Application restart is required to apply the change.\n"
                    "Do you want to restart now?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # Restart application
                    import sys
                    import os
                    from PyQt6.QtWidgets import QApplication
                    logger.info("Restarting application to apply font settings...")
                    QApplication.quit()
                    os.execv(sys.executable, ['python'] + sys.argv)
                    return
                else:
                    QMessageBox.information(
                        self,
                        "Settings Saved",
                        "Font settings have been updated!\n\n"
                        "Restart the application manually to see the changes."
                    )
            else:
                QMessageBox.information(
                    self,
                    "No Changes",
                    "No changes were made to font settings."
                )
            
            self.accept()
            
        except Exception as e:
            logger.error(f"Error saving font settings: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while saving settings: {e}"
            )