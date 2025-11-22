import logging
from utils.logger import get_internationalized_logger

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QHBoxLayout, QLabel

from core.slssteam_checker import SlssteamChecker, SlssteamStatus
from ui.interactions import HoverButton, ModernFrame
from ui.slssteam_setup_dialog import SlssteamSetupDialog

from .theme import BorderRadius, Typography, theme

# Import i18n
try:
    from utils.i18n import tr
except (ImportError, ModuleNotFoundError):

    def tr(context, text):
        return text


logger = get_internationalized_logger()


class StatusIndicator(QLabel):
    """Custom status indicator with colored circles"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self.status = SlssteamStatus.ERROR
        self.setStyleSheet(f"{BorderRadius.get_border_radius(BorderRadius.LARGE)}")

    def set_status(self, status: SlssteamStatus):
        """Update indicator color based on status"""
        self.status = status

        colors = {
            SlssteamStatus.INSTALLED_GOOD_CONFIG: theme.colors.SUCCESS,  # Green
            SlssteamStatus.INSTALLED_BAD_CONFIG: theme.colors.WARNING,  # Orange
            SlssteamStatus.NOT_INSTALLED: theme.colors.ERROR,  # Red
            SlssteamStatus.ERROR: theme.colors.TEXT_DISABLED,  # Gray
        }

        color = colors.get(status, theme.colors.TEXT_DISABLED)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                border-radius: 8px;
                border: 2px solid {theme.colors.SURFACE};
            }}
        """)

        # Set tooltip
        tooltips = {
            SlssteamStatus.INSTALLED_GOOD_CONFIG: tr("SlssteamStatus", "SLSsteam OK"),
            SlssteamStatus.INSTALLED_BAD_CONFIG: tr(
                "SlssteamStatus", "Configuration needed"
            ),
            SlssteamStatus.NOT_INSTALLED: tr("SlssteamStatus", "Not installed"),
            SlssteamStatus.ERROR: tr("SlssteamStatus", "Verification error"),
        }

        tooltip = tooltips.get(status, tr("SlssteamStatus", "Status desconhecido"))
        self.setToolTip(tooltip)

    def paintEvent(self, a0):
        """Custom paint for smooth circle"""
        super().paintEvent(a0)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw circle
        pen = QPen(QColor(theme.colors.SURFACE), 2)
        painter.setPen(pen)

        colors = {
            SlssteamStatus.INSTALLED_GOOD_CONFIG: QColor(theme.colors.SUCCESS),
            SlssteamStatus.INSTALLED_BAD_CONFIG: QColor(theme.colors.WARNING),
            SlssteamStatus.NOT_INSTALLED: QColor(theme.colors.ERROR),
            SlssteamStatus.ERROR: QColor(theme.colors.TEXT_DISABLED),
        }

        color = colors.get(self.status, QColor(theme.colors.TEXT_DISABLED))
        painter.setBrush(color)

        painter.drawEllipse(2, 2, 12, 12)


class ClickableStatusIndicator(StatusIndicator):
    """Clickable status indicator for compact mode"""

    # Signal for click events
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, ev: QMouseEvent | None):
        """Handle mouse press events"""
        if ev is not None and ev.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        else:
            super().mousePressEvent(ev)


class SlssteamStatusWidget(ModernFrame):
    """
    SLSsteam status indicator widget for Bifrost main window.

    Shows installation status with visual indicator and action button.
    """

    # Signals
    setup_requested = pyqtSignal()

    def __init__(self, parent=None, compact=False):
        super().__init__(parent)
        self.compact_mode = compact
        self.checker = SlssteamChecker()
        self.current_status = SlssteamStatus.ERROR
        self.current_details = {}
        self.setup_dialog = None

        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_status)
        self.refresh_timer.setInterval(30000)  # 30 seconds

        self._setup_ui()
        self.refresh_status()

        # Start auto-refresh
        self.refresh_timer.start()

    def _setup_ui(self):
        """Setup the UI components"""
        if self.compact_mode:
            self._setup_compact_ui()
        else:
            self._setup_full_ui()

    def _setup_compact_ui(self):
        """Setup compact UI for title bar integration"""
        self.setFixedSize(18, 18)
        self.setStyleSheet("background-color: transparent; border: none;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Compact status indicator (clickable)
        self.status_indicator = ClickableStatusIndicator()
        self.status_indicator.setFixedSize(16, 16)
        self.status_indicator.clicked.connect(self._on_indicator_clicked)
        layout.addWidget(self.status_indicator)

        # Hide text and button in compact mode
        self.status_label = None
        self.action_button = None

    def _setup_full_ui(self):
        """Setup full UI for standalone use"""
        self.setFixedHeight(40)
        self.setStyleSheet(f"""
            ModernFrame {{
                background-color: {theme.colors.SURFACE};
                border: none;
                {BorderRadius.get_border_radius(BorderRadius.NONE)};
                margin: 0px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(12)

        # Status indicator
        self.status_indicator = StatusIndicator()
        layout.addWidget(self.status_indicator)

        # Status text - single line for cleaner look
        self.status_label = QLabel(tr("SlssteamStatus", "Checking SLSsteam..."))
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.PRIMARY};
                font-weight: bold;
                {Typography.get_font_style(Typography.BODY_SIZE)};
                background-color: transparent;
            }}
        """)
        self.status_label.setFont(
            QFont(Typography.get_font_family(), Typography.BODY_SIZE - 1)
        )
        self.status_label.setWordWrap(False)
        layout.addWidget(self.status_label, 1)  # Takes available space

        # Action button
        self.action_button = HoverButton(tr("SlssteamStatus", "Configure"))
        self.action_button.setFixedSize(75, 28)
        self.action_button.setFont(
            QFont(Typography.get_font_family(), Typography.CAPTION_SIZE - 1)
        )
        self.action_button.clicked.connect(self._on_action_clicked)
        self.action_button.hide()  # Hide initially

        layout.addWidget(self.action_button)

    def refresh_status(self):
        """Refresh SLSsteam status"""
        try:
            status, details = self.checker.check_installation()
            self.current_status = status
            self.current_details = details

            self._update_ui()

        except Exception as e:
            logger.error(f"Error refreshing SLSsteam status: {e}")
            self.current_status = SlssteamStatus.ERROR
            self.current_details = {"error_message": str(e)}
            self._update_ui()

    def _update_ui(self):
        """Update UI based on current status"""
        # Update indicator
        self.status_indicator.set_status(self.current_status)

        if self.compact_mode:
            # Compact mode: only update tooltip
            self._update_compact_tooltip()
        else:
            # Full mode: update text and button
            self._update_full_ui()

    def _update_compact_tooltip(self):
        """Update tooltip for compact mode"""
        status_message = self.checker.get_status_message(
            self.current_status, self.current_details
        )
        description = self.checker.get_status_description(
            self.current_status, self.current_details
        )

        if not self.can_start_operations():
            status_message += f" ({tr('SlssteamStatus', 'BLOCKED')})"
            description += f"\n\n{tr('SlssteamStatus', 'Click to configure SLSsteam.')}"
        else:
            description += (
                f"\n\n{tr('SlssteamStatus', 'Click to manage SLSsteam settings.')}"
            )

        self.status_indicator.setToolTip(f"SLSsteam: {status_message}\n\n{description}")
        self.setToolTip(self.status_indicator.toolTip())

    def _update_full_ui(self):
        """Update UI for full mode"""
        # Update text with tooltip info
        status_message = self.checker.get_status_message(
            self.current_status, self.current_details
        )

        # Add blocking indicator if not ready
        if not self.can_start_operations():
            status_message += f" ({tr('SlssteamStatus', 'BLOCKED')})"

        if self.status_label:
            self.status_label.setText(status_message)

        # Set detailed tooltip
        description = self.checker.get_status_description(
            self.current_status, self.current_details
        )
        if not self.can_start_operations():
            description += f"\n\n{tr('SlssteamStatus', 'Bifrost operations are blocked until SLSsteam is configured.')}"

        self.setToolTip(description)

        # Update action button
        if self.action_button:
            if self.current_status in [
                SlssteamStatus.NOT_INSTALLED,
                SlssteamStatus.INSTALLED_BAD_CONFIG,
            ]:
                self.action_button.show()

                if self.current_status == SlssteamStatus.NOT_INSTALLED:
                    self.action_button.setText(tr("SlssteamStatus", "Install"))
                else:
                    self.action_button.setText(tr("SlssteamStatus", "Fix"))
            else:
                self.action_button.hide()

    def _update_tooltip(self):
        """Update widget tooltip with detailed information"""
        if self.current_status == SlssteamStatus.ERROR:
            tooltip = f"Error: {self.current_details.get('error_message', 'Unknown')}"
        elif self.current_status == SlssteamStatus.INSTALLED_BAD_CONFIG:
            pno = self.current_details.get("play_not_owned_games", "unknown")
            tooltip = f"PlayNotOwnedGames: {pno} (should be 'yes')"
        elif self.current_status == SlssteamStatus.INSTALLED_GOOD_CONFIG:
            tooltip = "SLSsteam is ready for use"
        else:
            tooltip = "Click to install/configure"

        self.setToolTip(tooltip)

    def _on_indicator_clicked(self):
        """Handle indicator click in compact mode"""
        try:
            if self.current_status == SlssteamStatus.NOT_INSTALLED:
                self._show_install_dialog()
            elif self.current_status == SlssteamStatus.INSTALLED_BAD_CONFIG:
                self._show_fix_dialog()
            else:
                # If everything is OK, show settings or info
                self._show_info_dialog()
        except Exception as e:
            logger.error(f"Error handling indicator click: {e}")

    def _on_action_clicked(self):
        """Handle action button click"""
        try:
            if self.current_status == SlssteamStatus.NOT_INSTALLED:
                self._show_install_dialog()
            elif self.current_status == SlssteamStatus.INSTALLED_BAD_CONFIG:
                self._show_fix_dialog()
        except Exception as e:
            logger.error(f"Error handling action click: {e}")

    def _show_info_dialog(self):
        """Show info dialog when SLSsteam is working"""
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.information(
            self,
            tr("SlssteamStatus", "SLSsteam Status"),
            tr(
                "SlssteamStatus",
                "SLSsteam is properly installed and configured.\n\n"
                "PlayNotOwnedGames is active and ready for use.",
            ),
        )

    def _show_install_dialog(self):
        """Show SLSsteam installation dialog"""
        if not self.setup_dialog:
            self.setup_dialog = SlssteamSetupDialog(self)
            self.setup_dialog.setup_completed.connect(self._on_setup_completed)

        self.setup_dialog.set_mode("install")
        self.setup_dialog.show()

    def _show_fix_dialog(self):
        """Show SLSsteam configuration fix dialog"""
        if not self.setup_dialog:
            self.setup_dialog = SlssteamSetupDialog(self)
            self.setup_dialog.setup_completed.connect(self._on_setup_completed)

        self.setup_dialog.set_mode("fix")
        self.setup_dialog.show()

    def _on_setup_completed(self, success: bool):
        """Handle setup completion"""
        if success:
            # Refresh status after a short delay to allow file operations to complete
            QTimer.singleShot(1000, self.refresh_status)

        self.setup_requested.emit()

    def get_current_status(self) -> tuple[SlssteamStatus, dict]:
        """Get current status and details"""
        return self.current_status, self.current_details

    def is_slssteam_ready(self) -> bool:
        """Check if SLSsteam is ready for use"""
        return self.current_status == SlssteamStatus.INSTALLED_GOOD_CONFIG

    def can_start_operations(self) -> bool:
        """Check if Bifrost operations can start (SLSsteam must be ready)"""
        return self.is_slssteam_ready()

    def get_blocking_message(self) -> str:
        """Get message explaining why operations are blocked"""
        if self.current_status == SlssteamStatus.INSTALLED_GOOD_CONFIG:
            return ""

        return self.checker.get_status_description(
            self.current_status, self.current_details
        )

    def closeEvent(self, a0):
        """Handle widget close event"""
        if self.refresh_timer:
            self.refresh_timer.stop()

        if self.setup_dialog:
            self.setup_dialog.close()

        super().closeEvent(a0)
