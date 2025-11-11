import logging
import subprocess
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QProgressBar, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from core.slssteam_checker import SlssteamChecker, SlssteamStatus
from ui.interactions import ModernFrame, HoverButton
from ui.enhanced_widgets import EnhancedProgressBar
from ui.enhanced_dialogs import ModernDialog

logger = logging.getLogger(__name__)

class SlssteamInstallThread(QThread):
    """Thread for running SLSsteam installation commands"""
    
    # Signals
    output_received = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, command: str):
        super().__init__()
        self.command = command
        self.process = None
    
    def run(self):
        """Execute the installation command"""
        try:
            logger.info(f"Running SLSsteam command: {self.command}")
            
            # Run the command
            self.process = subprocess.Popen(
                self.command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                universal_newlines=True,
                bufsize=1
            )
            
            # Read output line by line
            if self.process.stdout:
                while True:
                    output = self.process.stdout.readline()
                    if output == '' and self.process.poll() is not None:
                        break
                    if output:
                        self.output_received.emit(output.strip())
            
            # Get return code
            return_code = self.process.poll()
            
            if return_code == 0:
                self.finished.emit(True, "Installation completed successfully")
            else:
                self.finished.emit(False, f"Installation failed with code {return_code}")
                
        except Exception as e:
            logger.error(f"Error running SLSsteam command: {e}")
            self.finished.emit(False, str(e))
    
    def stop(self):
        """Stop the installation process"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()

class SlssteamSetupDialog(ModernDialog):
    """
    Dialog for SLSsteam installation and configuration.
    
    Provides options for:
    - Full SLSsteam installation
    - Configuration fix (PlayNotOwnedGames)
    - Progress tracking
    - Output display
    """
    
    # Signals
    setup_completed = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.checker = SlssteamChecker()
        self.install_thread = None
        self.current_mode = "install"
        
        self._setup_ui()
        self._setup_dialog_properties()
    
    def _setup_dialog_properties(self):
        """Setup dialog-specific properties"""
        self.setFixedSize(600, 500)
        self.setWindowTitle("SLSsteam Setup")
    
    def _setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        self.title_label = QLabel("SLSsteam Setup")
        self.title_label.setStyleSheet("""
            QLabel {
                color: #C06C84;
                font-weight: bold;
                font-size: 18px;
                margin-bottom: 10px;
            }
        """)
        self.title_label.setFont(QFont("TrixieCyrG-Plain", 16))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)
        
        # Description
        self.description_label = QLabel("")
        self.description_label.setStyleSheet("""
            QLabel {
                color: #808080;
                font-size: 12px;
                margin-bottom: 15px;
            }
        """)
        self.description_label.setFont(QFont("TrixieCyrG-Plain", 11))
        self.description_label.setWordWrap(True)
        self.description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.description_label)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #404040; height: 1px;")
        layout.addWidget(separator)
        
        # Status area
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("Ready to setup SLSsteam")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #C06C84;
                font-weight: bold;
                font-size: 14px;
            }
        """)
        self.status_label.setFont(QFont("TrixieCyrG-Plain", 12))
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = EnhancedProgressBar()
        self.progress_bar.setFixedHeight(25)
        self.progress_bar.hide()
        status_layout.addWidget(self.progress_bar)
        
        layout.addLayout(status_layout)
        
        # Output area
        self.output_text = QTextEdit()
        self.output_text.setStyleSheet("""
            QTextEdit {
                background-color: #282828;
                color: #C06C84;
                border: 1px solid #404040;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 10px;
            }
        """)
        self.output_text.setReadOnly(True)
        self.output_text.setMaximumHeight(200)
        layout.addWidget(self.output_text)
        
        # Button area
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = HoverButton("Cancel")
        self.cancel_button.setFixedSize(100, 36)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        button_layout.addWidget(self.cancel_button)
        
        self.action_button = HoverButton("Install")
        self.action_button.setFixedSize(100, 36)
        self.action_button.clicked.connect(self._on_action_clicked)
        button_layout.addWidget(self.action_button)
        
        layout.addLayout(button_layout)
    
    def set_mode(self, mode: str):
        """Set dialog mode (install or fix)"""
        self.current_mode = mode
        
        if mode == "install":
            self.title_label.setText("SLSsteam Installation")
            self.description_label.setText(
                "SLSsteam is required for ACCELA to function properly. "
                "This will install SLSsteam and configure it for Steam integration."
            )
            self.action_button.setText("Install")
            self.status_label.setText("Ready to install SLSsteam")
            
        elif mode == "fix":
            self.title_label.setText("SLSsteam Configuration")
            self.description_label.setText(
                "SLSsteam is installed but needs configuration. "
                "This will fix the PlayNotOwnedGames setting to enable game access."
            )
            self.action_button.setText("Fix Config")
            self.status_label.setText("Ready to fix configuration")
        
        self.output_text.clear()
    
    def _on_action_clicked(self):
        """Handle action button click"""
        if self.install_thread and self.install_thread.isRunning():
            return
        
        # Clear output and show progress
        self.output_text.clear()
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        self.action_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        
        if self.current_mode == "install":
            self._start_installation()
        elif self.current_mode == "fix":
            self._start_fix()
    
    def _start_installation(self):
        """Start SLSsteam installation"""
        if not self.checker.can_install():
            QMessageBox.critical(
                self,
                "Installation Error",
                "SLSsteam installation files not found. Please ensure SLSsteam-Any directory exists."
            )
            self._on_setup_finished(False, "Installation files not found")
            return
        
        commands = self.checker.get_installation_commands()
        install_command = commands.get("install", "")
        
        if not install_command:
            self._on_setup_finished(False, "Could not get install command")
            return
        
        self.status_label.setText("Installing SLSsteam...")
        self.output_text.append(f"Running: {install_command}")
        
        # Start installation thread
        self.install_thread = SlssteamInstallThread(install_command)
        self.install_thread.output_received.connect(self._on_output_received)
        self.install_thread.finished.connect(self._on_setup_finished)
        self.install_thread.progress_updated.connect(self._on_progress_updated)
        self.install_thread.start()
    
    def _start_fix(self):
        """Start configuration fix"""
        self.status_label.setText("Fixing configuration...")
        self.output_text.append("Updating PlayNotOwnedGames setting...")
        
        # Simulate progress
        self.progress_bar.setValue(30)
        QTimer.singleShot(500, lambda: self._apply_fix())
    
    def _apply_fix(self):
        """Apply the configuration fix"""
        try:
            success = self.checker.fix_play_not_owned_games()
            
            if success:
                self.output_text.append("[OK] PlayNotOwnedGames set to 'yes'")
                self.progress_bar.setValue(100)
                self._on_setup_finished(True, "Configuration fixed successfully")
            else:
                self.output_text.append("[X] Failed to update configuration")
                self._on_setup_finished(False, "Failed to fix configuration")
                
        except Exception as e:
            logger.error(f"Error fixing configuration: {e}")
            self.output_text.append(f"[X] Error: {e}")
            self._on_setup_finished(False, str(e))
    
    def _on_output_received(self, output: str):
        """Handle installation output"""
        self.output_text.append(output)
        
        # Auto-scroll to bottom
        scrollbar = self.output_text.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())
        
        # Update progress based on output
        if "Installing" in output or "Creating" in output:
            self.progress_bar.setValue(min(50, self.progress_bar.value() + 10))
        elif "Install script done" in output or "success" in output.lower():
            self.progress_bar.setValue(90)
    
    def _on_progress_updated(self, value: int):
        """Handle progress updates"""
        self.progress_bar.setValue(value)
    
    def _on_setup_finished(self, success: bool, message: str):
        """Handle setup completion"""
        self.progress_bar.setValue(100 if success else 0)
        
        if success:
            self.status_label.setText("Setup completed successfully!")
            self.output_text.append(f"\n[OK] {message}")
        else:
            self.status_label.setText("Setup failed!")
            self.output_text.append(f"\n[X] {message}")
        
        # Reset buttons
        self.action_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.action_button.setText("Close" if not success else "Close")
        
        # Emit signal
        self.setup_completed.emit(success)
        
        # Show message box
        if success:
            # Auto-enable slssteam_mode in settings after successful setup
            try:
                from utils.settings import get_settings
                settings = get_settings()
                settings.setValue("slssteam_mode", True)
                logger.info("Auto-enabled slssteam_mode after successful SLSsteam setup")
            except Exception as e:
                logger.warning(f"Failed to auto-enable slssteam_mode: {e}")
            
            QMessageBox.information(
                self,
                "Setup Complete",
                "SLSsteam has been successfully configured!\n\nSLSsteam mode has been automatically enabled."
            )
        else:
            QMessageBox.warning(
                self,
                "Setup Failed",
                f"SLSsteam setup failed: {message}"
            )
    
    def _on_cancel_clicked(self):
        """Handle cancel button click"""
        if self.install_thread and self.install_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Cancel Installation",
                "Are you sure you want to cancel the installation?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.install_thread.stop()
                self.install_thread.wait()
                self._on_setup_finished(False, "Installation cancelled")
        else:
            self.close()
    
    def closeEvent(self, a0):
        """Handle dialog close event"""
        if self.install_thread and self.install_thread.isRunning():
            self.install_thread.stop()
            self.install_thread.wait()
        
        super().closeEvent(a0)