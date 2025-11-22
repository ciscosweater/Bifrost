import logging
from utils.logger import get_internationalized_logger

from PyQt6.QtCore import QObject, Qt, pyqtSignal

logger = get_internationalized_logger()


class KeyboardShortcuts(QObject):
    """
    Global keyboard shortcuts manager for enhanced productivity.
    """

    # Signals for different actions
    open_file_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    help_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._shortcuts = {
            Qt.Key.Key_O: self._handle_ctrl_o,  # Ctrl+O: Open file
            Qt.Key.Key_S: self._handle_ctrl_s,  # Ctrl+S: Settings
            Qt.Key.Key_Q: self._handle_ctrl_q,  # Ctrl+Q: Quit
            Qt.Key.Key_W: self._handle_ctrl_w,  # Ctrl+W: Close window
            Qt.Key.Key_F1: self._handle_f1,  # F1: Help
            Qt.Key.Key_F5: self._handle_f5,  # F5: Refresh/Reset
            Qt.Key.Key_Escape: self._handle_escape,  # Escape: Cancel/Reset
        }

    def eventFilter(self, a0, a1):
        """Filter events to catch keyboard shortcuts."""
        try:
            if (
                a1 and hasattr(a1, "type") and a1.type() == 6
            ):  # 6 = QEvent.Type.KeyPress
                self._handle_key_press(a1)
        except (AttributeError, TypeError):
            pass
        return super().eventFilter(a0, a1)

    def _handle_key_press(self, event):
        """Handle individual key press events."""
        key = event.key()
        modifiers = event.modifiers()

        # Check for Ctrl combinations
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            if key in self._shortcuts:
                self._shortcuts[key]()
                event.accept()
                return True

        # Check for standalone keys
        elif key in self._shortcuts and modifiers == Qt.KeyboardModifier.NoModifier:
            if key in [Qt.Key.Key_F1, Qt.Key.Key_F5, Qt.Key.Key_Escape]:
                self._shortcuts[key]()
                event.accept()
                return True

        return False

    def _handle_ctrl_o(self):
        """Ctrl+O: Open file dialog."""
        logger.debug("Ctrl+O pressed - Open file requested")
        self.open_file_requested.emit()

    def _handle_ctrl_s(self):
        """Ctrl+S: Open settings."""
        logger.debug("Ctrl+S pressed - Settings requested")
        self.settings_requested.emit()

    def _handle_ctrl_q(self):
        """Ctrl+Q: Quit application."""
        logger.debug("Ctrl+Q pressed - Quit requested")
        self.quit_requested.emit()

    def _handle_ctrl_w(self):
        """Ctrl+W: Close current window."""
        logger.debug("Ctrl+W pressed - Close window requested")
        self.quit_requested.emit()

    def _handle_f1(self):
        """F1: Show help."""
        logger.debug("F1 pressed - Help requested")
        self.help_requested.emit()

    def _handle_f5(self):
        """F5: Refresh/Reset UI."""
        logger.debug("F5 pressed - Refresh requested")
        # This could trigger a UI reset or refresh

    def _handle_escape(self):
        """Escape: Cancel current operation."""
        logger.debug("Escape pressed - Cancel requested")
        # This could cancel ongoing operations


class ShortcutHelper:
    """
    Helper class to manage shortcut tooltips and documentation.
    """

    SHORTCUTS_DOC = {
        "Ctrl+O": "Open ZIP file",
        "Ctrl+S": "Open Settings",
        "Ctrl+Q": "Quit Application",
        "Ctrl+W": "Close Window",
        "F1": "Show Help",
        "F5": "Refresh Interface",
        "Escape": "Cancel Operation",
    }

    @staticmethod
    def get_tooltip(base_text, shortcut_key):
        """Generate tooltip with shortcut information."""
        shortcut = ShortcutHelper.SHORTCUTS_DOC.get(shortcut_key, "")
        if shortcut:
            return f"{base_text} ({shortcut_key})"
        return base_text

    @staticmethod
    def get_shortcuts_help():
        """Get formatted help text for all shortcuts."""
        help_text = "Keyboard Shortcuts:\n\n"
        for shortcut, description in ShortcutHelper.SHORTCUTS_DOC.items():
            help_text += f"  {shortcut:<12} - {description}\n"
        return help_text
