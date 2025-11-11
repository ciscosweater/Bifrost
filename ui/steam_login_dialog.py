import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, 
    QMessageBox, QComboBox, QHBoxLayout, QApplication,
    QInputDialog, QCheckBox
)
from ui.custom_checkbox import CustomCheckBox
from PyQt6.QtCore import Qt, QTimer

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
        self.setStyleSheet("""
            QDialog {
                background-color: #000000;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                background-color: transparent;
                font-size: 12px;
            }
            QLineEdit {
                background-color: #1a1a1a;
                border: 1px solid #333333;
                padding: 10px;
                color: #ffffff;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #C06C84;
            }
            QComboBox {
                background-color: #1a1a1a;
                border: 1px solid #333333;
                padding: 10px;
                color: #ffffff;
                font-size: 12px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #C06C84;
            }
            QComboBox QAbstractItemView {
                background-color: #1a1a1a;
                border: 1px solid #333333;
                color: #ffffff;
                selection-background-color: #C06C84;
            }
            QCheckBox {
                color: #ffffff;
                background-color: transparent;
                font-size: 11px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                background-color: #1a1a1a;
                border: 1px solid #333333;
                border-radius: 2px;
            }
            QCheckBox::indicator:checked {
                background-color: #C06C84;
                border: 1px solid #C06C84;
            }
            QPushButton {
                background-color: #C06C84;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                color: #000000;
                font-size: 11px;
                font-weight: bold;
                text-transform: uppercase;
            }
            QPushButton:hover {
                background-color: #d07d94;
            }
            QPushButton:pressed {
                background-color: #b05c74;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #666666;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("STEAM LOGIN")
        title.setStyleSheet("color: #C06C84; font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Authenticate with your Steam account")
        subtitle.setStyleSheet("color: #888888; font-size: 10px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        # Login method
        self.use_saved_checkbox = QCheckBox("Use saved credentials")
        self.use_saved_checkbox.setChecked(True)
        self.use_saved_checkbox.toggled.connect(self.toggle_login_method)
        layout.addWidget(self.use_saved_checkbox)
        
        # Saved account
        self.saved_label = QLabel("Account:")
        self.saved_label.setStyleSheet("color: #C06C84; font-size: 10px; font-weight: bold;")
        layout.addWidget(self.saved_label)
        
        self.saved_accounts_combo = QComboBox()
        layout.addWidget(self.saved_accounts_combo)
        
        # New login fields
        self.username_label = QLabel("Username:")
        self.username_label.setStyleSheet("color: #C06C84; font-size: 10px; font-weight: bold;")
        layout.addWidget(self.username_label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Steam username")
        self.username_input.returnPressed.connect(self.attempt_login)
        layout.addWidget(self.username_input)
        
        self.password_label = QLabel("Password:")
        self.password_label.setStyleSheet("color: #C06C84; font-size: 10px; font-weight: bold;")
        layout.addWidget(self.password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Steam password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(self.attempt_login)
        layout.addWidget(self.password_input)
        
        # 2FA Code field (initially hidden)
        self.twofa_label = QLabel("2FA Code:")
        self.twofa_label.setStyleSheet("color: #C06C84; font-size: 10px; font-weight: bold;")
        self.twofa_label.setVisible(False)
        layout.addWidget(self.twofa_label)
        
        self.twofa_input = QLineEdit()
        self.twofa_input.setPlaceholderText("Enter Steam Guard code")
        self.twofa_input.returnPressed.connect(self.attempt_login)
        self.twofa_input.setVisible(False)
        layout.addWidget(self.twofa_input)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #4a9eff; font-size: 11px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
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
        
        self.setStyleSheet("""
            QDialog {
                background-color: #000000;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
            }
            QPushButton {
                background-color: #C06C84;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                color: #000000;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d07d94;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel("Steam Status")
        title.setStyleSheet("color: #C06C84; font-size: 14px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        status = QLabel("Steam login functionality is currently unavailable.")
        status.setStyleSheet("color: #888888; font-size: 11px;")
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status.setWordWrap(True)
        layout.addWidget(status)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)