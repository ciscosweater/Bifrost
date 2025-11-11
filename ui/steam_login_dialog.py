import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, 
    QMessageBox, QComboBox, QHBoxLayout, QApplication,
    QInputDialog, QCheckBox
)
from ui.custom_checkbox import CustomCheckBox
from PyQt6.QtCore import Qt, QTimer
from ui.theme import theme, Typography, Spacing, BorderRadius

logger = logging.getLogger(__name__)

class SteamLoginDialog(QDialog):
    """
    Modern Steam login dialog matching ACCELA's visual identity
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Steam Login")
        self.setModal(True)
        self.setFixedSize(420, 480)
        
        # Initialize timer variables
        self.mobile_confirmation_timer = None
        self.mobile_confirmation_counter = 0
        
        # Initialize timer variables
        self.mobile_confirmation_timer = None
        self.mobile_confirmation_counter = 0
        
        # Apply ACCELA's dark theme styling
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme.colors.BACKGROUND};
                color: {theme.colors.TEXT_PRIMARY};
            }}
            QLabel {{
                color: {theme.colors.TEXT_PRIMARY};
                background-color: transparent;
                {Typography.get_font_style(Typography.BODY_SIZE)};
            }}
            QLineEdit {{
                background-color: {theme.colors.SURFACE};
                border: 1px solid {theme.colors.BORDER};
                padding: {Spacing.SM}px;
                color: {theme.colors.TEXT_PRIMARY};
                {Typography.get_font_style(Typography.BODY_SIZE)};
            }}
            QLineEdit:focus {{
                border: 2px solid {theme.colors.PRIMARY};
            }}
            QComboBox {{
                background-color: {theme.colors.SURFACE};
                border: 1px solid {theme.colors.BORDER};
                padding: {Spacing.SM}px;
                color: {theme.colors.TEXT_PRIMARY};
                {Typography.get_font_style(Typography.BODY_SIZE)};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid {theme.colors.PRIMARY};
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme.colors.SURFACE};
                border: 1px solid {theme.colors.BORDER};
                color: {theme.colors.TEXT_PRIMARY};
                selection-background-color: {theme.colors.PRIMARY};
            }}
            QCheckBox {{
                color: {theme.colors.TEXT_PRIMARY};
                background-color: transparent;
                {Typography.get_font_style(Typography.BODY_SIZE)};
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                background-color: {theme.colors.SURFACE};
                border: 1px solid {theme.colors.BORDER};
                border-radius: {BorderRadius.SMALL - 2}px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {theme.colors.PRIMARY};
                border: 1px solid {theme.colors.PRIMARY};
            }}
            QPushButton {{
                background-color: {theme.colors.PRIMARY};
                border: none;
                border-radius: {BorderRadius.SMALL}px;
                padding: {Spacing.SM}px {Spacing.MD}px;
                color: {theme.colors.TEXT_ON_PRIMARY};
                {Typography.get_font_style(Typography.BODY_SIZE)};
                font-weight: bold;
                text-transform: uppercase;
            }}
            QPushButton:hover {{
                background-color: {theme.colors.PRIMARY_LIGHT};
            }}
            QPushButton:pressed {{
                background-color: {theme.colors.PRIMARY_DARK};
            }}
            QPushButton:disabled {{
                background-color: {theme.colors.SURFACE_LIGHT};
                color: {theme.colors.TEXT_DISABLED};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG + 5, Spacing.LG + 5, Spacing.LG + 5, Spacing.LG + 5)
        layout.setSpacing(Spacing.MD)
        
        # Title
        title = QLabel("STEAM LOGIN")
        title.setStyleSheet(f"color: {theme.colors.PRIMARY}; {Typography.get_font_style(Typography.H2_SIZE, Typography.WEIGHT_BOLD)};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Authenticate with your Steam account")
        subtitle.setStyleSheet(f"color: {theme.colors.TEXT_SECONDARY}; {Typography.get_font_style(Typography.CAPTION_SIZE)};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        # Login method
        self.use_saved_checkbox = QCheckBox("Use saved credentials")
        self.use_saved_checkbox.setChecked(True)
        self.use_saved_checkbox.toggled.connect(self.toggle_login_method)
        layout.addWidget(self.use_saved_checkbox)
        
        # Saved account
        self.saved_label = QLabel("Account:")
        self.saved_label.setStyleSheet(f"color: {theme.colors.PRIMARY}; {Typography.get_font_style(Typography.CAPTION_SIZE, Typography.WEIGHT_BOLD)};")
        layout.addWidget(self.saved_label)
        
        self.saved_accounts_combo = QComboBox()
        layout.addWidget(self.saved_accounts_combo)
        
        # New login fields
        self.username_label = QLabel("Username:")
        self.username_label.setStyleSheet(f"color: {theme.colors.PRIMARY}; {Typography.get_font_style(Typography.CAPTION_SIZE, Typography.WEIGHT_BOLD)};")
        self.password_label.setStyleSheet(f"color: {theme.colors.PRIMARY}; {Typography.get_font_style(Typography.CAPTION_SIZE, Typography.WEIGHT_BOLD)};")
        self.twofa_label.setStyleSheet(f"color: {theme.colors.PRIMARY}; {Typography.get_font_style(Typography.CAPTION_SIZE, Typography.WEIGHT_BOLD)};")
        self.twofa_label.setVisible(False)
        layout.addWidget(self.twofa_label)
        
        self.twofa_input = QLineEdit()
        self.twofa_input.setPlaceholderText("Enter Steam Guard code")
        self.twofa_input.returnPressed.connect(self.attempt_login)
        self.twofa_input.setVisible(False)
        layout.addWidget(self.twofa_input)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {theme.colors.PRIMARY_LIGHT}; {Typography.get_font_style(Typography.BODY_SIZE)};")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(Spacing.SM)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.attempt_login)
        button_layout.addWidget(self.login_button)
        
        layout.addLayout(button_layout)
        
        # Load saved accounts
        self.load_saved_accounts()
        
        # Set initial state
        self.toggle_login_method()
    
    def load_saved_accounts(self):
        """Load saved Steam accounts"""
        try:
            from core.steam_login import SteamLoginManager
            login_manager = SteamLoginManager()
            accounts = login_manager.get_available_accounts()
            
            self.saved_accounts_combo.clear()
            if accounts:
                self.saved_accounts_combo.addItems(accounts)
                self.saved_accounts_combo.setEnabled(True)
            else:
                self.saved_accounts_combo.addItem("No saved accounts")
                self.saved_accounts_combo.setEnabled(False)
                self.use_saved_checkbox.setChecked(False)
                
        except Exception as e:
            logger.error(f"Failed to load saved accounts: {e}")
            self.saved_accounts_combo.addItem("Error loading accounts")
            self.saved_accounts_combo.setEnabled(False)
    
    def toggle_login_method(self):
        """Toggle between saved credentials and new login"""
        use_saved = self.use_saved_checkbox.isChecked()
        
        self.saved_accounts_combo.setEnabled(use_saved)
        self.saved_label.setEnabled(use_saved)
        
        self.username_label.setEnabled(not use_saved)
        self.username_input.setEnabled(not use_saved)
        self.password_label.setEnabled(not use_saved)
        self.password_input.setEnabled(not use_saved)
        
        if use_saved:
            self.login_button.setText("Login with Saved")
        else:
            self.login_button.setText("Login")
    
    def attempt_login(self):
        """Attempt to login to Steam"""
        # Import exceptions at function level to avoid circular imports
        try:
            from steam.webauth import TwoFactorCodeRequired, EmailCodeRequired, CaptchaRequired
        except ImportError:
            TwoFactorCodeRequired = Exception
            EmailCodeRequired = Exception  
            CaptchaRequired = Exception
            
        username = None
        password = None
        twofa_code = None
        
        if self.use_saved_checkbox.isChecked():
            if self.saved_accounts_combo.count() == 0:
                QMessageBox.warning(self, "Login Error", "No saved accounts available")
                return
            
            username = self.saved_accounts_combo.currentText()
            if username in ["No saved accounts", "Error loading accounts"]:
                QMessageBox.warning(self, "Login Error", "Please select a valid account")
                return
        else:
            username = self.username_input.text().strip()
            password = self.password_input.text().strip()
            twofa_code = self.twofa_input.text().strip() if self.twofa_input.isVisible() else None
            
            if not username:
                QMessageBox.warning(self, "Login Error", "Please enter your username")
                return
            
            if not password:
                QMessageBox.warning(self, "Login Error", "Please enter your password")
                return
        
        # Disable buttons during login
        self.login_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.status_label.setText("Authenticating...")
        QApplication.processEvents()
        
        # Create a timer to update status during mobile confirmation
        self.mobile_confirmation_timer = QTimer()
        self.mobile_confirmation_counter = 0
        self.mobile_confirmation_timer.timeout.connect(self.update_mobile_status)
        self.mobile_confirmation_timer.start(2000)  # Update every 2 seconds
        
        try:
            from core.steam_login import SteamLoginManager
            login_manager = SteamLoginManager()
            
            if self.use_saved_checkbox.isChecked():
                client = login_manager.login_with_saved_account(username)
                login_type = "saved credentials"
            else:
                client = login_manager.login(username, password, twofactor_code=twofa_code)
                login_type = "username and password"
            
            if client and login_manager.is_logged_in():
                self.status_label.setText("Login successful!")
                QApplication.processEvents()
                
                QMessageBox.information(
                    self, 
                    "Login Successful", 
                    f"Successfully logged into Steam!\n\n"
                    f"Username: {login_manager.get_username()}\n"
                    f"Steam ID: {login_manager.get_steam_id64()}\n\n"
                    f"Your credentials have been encrypted and saved."
                )
                
                self.accept()
            else:
                self.status_label.setText("Login failed")
                QApplication.processEvents()
                QMessageBox.warning(
                    self, 
                    "Login Failed", 
                    f"Failed to login to Steam using {login_type}.\n\n"
                    f"Please check your credentials and try again."
                )
                
        except TwoFactorCodeRequired:
            # Show 2FA field and ask for code
            self.twofa_label.setVisible(True)
            self.twofa_input.setVisible(True)
            self.twofa_input.setFocus()
            self.status_label.setText("2FA code required")
            QApplication.processEvents()
            return  # Don't disable buttons, let user try again with code
        except CaptchaRequired as e:
            self.handle_captcha(e)
        except Exception as e:
            logger.error(f"Login error: {e}")
            self.status_label.setText("Login error")
            QApplication.processEvents()
            
            # Check for specific error types
            error_msg = str(e).lower()
            if "invalid password" in error_msg:
                QMessageBox.critical(
                    self, 
                    "Login Failed", 
                    "Invalid password or username.\n\n"
                    "Please check your credentials and try again."
                )
            elif "mobile confirmation" in error_msg or "timed out" in error_msg:
                QMessageBox.critical(
                    self, 
                    "Mobile Confirmation", 
                    "Mobile confirmation timed out.\n\n"
                    "Please try again and approve quickly on your mobile device."
                )
            elif "rate limit" in error_msg or "429" in error_msg:
                QMessageBox.critical(
                    self, 
                    "Rate Limited", 
                    "Too many login attempts.\n\n"
                    "Please wait a few minutes before trying again."
                )
            else:
                QMessageBox.critical(
                    self, 
                    "Login Error", 
                    f"An error occurred during login:\n\n{str(e)}\n\n"
                    f"If you have Steam Guard enabled, approve the login on your mobile device."
                )
        
        # Stop mobile confirmation timer
        if hasattr(self, 'mobile_confirmation_timer'):
            self.mobile_confirmation_timer.stop()
        
        # Stop mobile confirmation timer
        if hasattr(self, 'mobile_confirmation_timer'):
            self.mobile_confirmation_timer.stop()
        
        self.login_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
    
    def update_mobile_status(self):
        """Update status during mobile confirmation"""
        self.mobile_confirmation_counter += 1
        messages = [
            "Awaiting mobile confirmation...",
            "Check your phone for Steam Guard...",
            "Approve the login on your mobile device...",
            "Still waiting for mobile confirmation..."
        ]
        message = messages[self.mobile_confirmation_counter % len(messages)]
        self.status_label.setText(f"{message} ({self.mobile_confirmation_counter * 2}s)")
        QApplication.processEvents()
    
    def closeEvent(self, a0):
        """Handle dialog close event"""
        # Stop mobile confirmation timer
        if hasattr(self, 'mobile_confirmation_timer') and self.mobile_confirmation_timer:
            self.mobile_confirmation_timer.stop()
        super().closeEvent(a0)
    
    def handle_2fa(self, exception, login_manager, username, password):
        """Handle 2FA authentication"""
        logger.error(f"2FA required: {exception}")
        self.status_label.setText("2FA required")
        QApplication.processEvents()
        
        auth_type = "Steam Guard" if "TwoFactor" in str(type(exception)) else "Email"
        
        code, ok = QInputDialog.getText(
            self, 
            f"{auth_type} Required", 
            f"Please enter your {auth_type} code:",
            QLineEdit.EchoMode.Normal
        )
        
        if ok and code:
            try:
                client = login_manager.login(username, password, twofactor_code=code)
                if client and login_manager.is_logged_in():
                    self.status_label.setText("Login successful!")
                    QApplication.processEvents()
                    
                    QMessageBox.information(
                        self, 
                        "Login Successful", 
                        f"Successfully logged into Steam!\n\n"
                        f"Username: {login_manager.get_username()}\n"
                        f"Steam ID: {login_manager.get_steam_id64()}"
                    )
                    
                    self.accept()
                else:
                    self.status_label.setText("2FA failed")
                    QApplication.processEvents()
                    QMessageBox.warning(self, "2FA Failed", "Failed to login with the provided 2FA code.")
            except Exception as retry_e:
                logger.error(f"2FA retry error: {retry_e}")
                self.status_label.setText("2FA error")
                QApplication.processEvents()
                QMessageBox.critical(self, "2FA Error", f"2FA authentication error:\n\n{str(retry_e)}")
        else:
            self.status_label.setText("2FA cancelled")
            QApplication.processEvents()
    
    def handle_captcha(self, exception):
        """Handle captcha requirement"""
        logger.error(f"Captcha required: {exception}")
        self.status_label.setText("Captcha required")
        QApplication.processEvents()
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Captcha Required")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText("Steam requires captcha verification.")
        msg.setInformativeText(
            "This usually happens when Steam detects unusual login activity.\n\n"
            "Solutions:\n"
            "1. Login through the official Steam client first\n"
            "2. Wait 15-30 minutes and try again\n"
            "3. Use saved credentials if available\n\n"
            "Would you like to open the Steam client?"
        )
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | 
            QMessageBox.StandardButton.No
        )
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            try:
                import subprocess
                import platform
                
                system = platform.system()
                if system == "Windows":
                    subprocess.Popen(["steam://"])
                elif system == "Linux":
                    subprocess.Popen(["steam"])
                elif system == "Darwin":  # macOS
                    subprocess.Popen(["open", "-a", "Steam"])
                    
                QMessageBox.information(
                    self, 
                    "Steam Client", 
                    "Steam client should be opening.\n\n"
                    "After logging in successfully, come back and try again."
                )
            except Exception as e:
                QMessageBox.warning(
                    self, 
                    "Error", 
                    f"Could not open Steam client automatically.\n\n"
                    f"Please open it manually and try again later.\n\n"
                    f"Error: {str(e)}"
                )


class SteamStatusDialog(QDialog):
    """
    Simple status dialog for when Steam login is unavailable
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Steam Status")
        self.setModal(True)
        self.setFixedSize(350, 150)
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme.colors.BACKGROUND};
                color: {theme.colors.TEXT_PRIMARY};
            }}
            QLabel {{
                color: {theme.colors.TEXT_PRIMARY};
                {Typography.get_font_style(Typography.BODY_SIZE)};
            }}
            QPushButton {{
                background-color: {theme.colors.PRIMARY};
                border: none;
                border-radius: {BorderRadius.SMALL}px;
                padding: {Spacing.XS}px {Spacing.SM}px;
                color: {theme.colors.TEXT_ON_PRIMARY};
                {Typography.get_font_style(Typography.BODY_SIZE)};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme.colors.PRIMARY_LIGHT};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        layout.setSpacing(Spacing.MD)
        
        title = QLabel("Steam Status")
        title.setStyleSheet(f"color: {theme.colors.PRIMARY}; {Typography.get_font_style(Typography.H3_SIZE, Typography.WEIGHT_BOLD)};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        status = QLabel("Steam login functionality is currently unavailable.")
        status.setStyleSheet(f"color: {theme.colors.TEXT_SECONDARY}; {Typography.get_font_style(Typography.BODY_SIZE)};")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status.setWordWrap(True)
        layout.addWidget(status)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)