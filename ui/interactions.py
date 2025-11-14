import logging
from utils.logger import get_internationalized_logger

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, pyqtSignal
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton

logger = get_internationalized_logger()


class HoverButton(QPushButton):
    """
    Enhanced button with smooth hover animations and visual feedback.
    """

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._setup_animations()
        self._setup_style()

    def _setup_animations(self):
        """Setup smooth transition animations."""
        self._hover_animation = QPropertyAnimation(self, b"color")
        self._hover_animation.setDuration(200)
        self._hover_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _setup_style(self):
        """Apply modern styling with hover states."""
        from ui.theme import theme

        self.setStyleSheet(f"""
            QPushButton {{
                background: {theme.colors.SURFACE};
                border: 1px solid {theme.colors.PRIMARY};
                color: {theme.colors.PRIMARY};
                font-weight: 700;
                padding: 4px 8px;
                text-transform: none;
                letter-spacing: 0.5px;
                {theme.border_radius.get_border_radius(theme.border_radius.MEDIUM)};
            }}
            QPushButton:hover {{
                background: {theme.colors.PRIMARY};
                border: 1px solid {theme.colors.PRIMARY_LIGHT};
                color: {theme.colors.TEXT_ON_PRIMARY};
            }}
            QPushButton:pressed {{
                background: {theme.colors.PRIMARY_DARK};
                border: 1px solid {theme.colors.PRIMARY_DARK};
            }}
        """)


class ModernFrame(QFrame):
    """
    Modern frame with glassmorphism effect and subtle shadows.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_style()

    def _setup_style(self):
        """Apply glassmorphism styling."""
        from ui.theme import theme

        self.setStyleSheet(f"""
            QFrame {{
                background: {theme.colors.SURFACE};
                border: 1px solid {theme.colors.GLASS_BORDER};
                {theme.border_radius.get_border_radius(theme.border_radius.LARGE)};
                box-shadow: {theme.shadows.SUBTLE};
            }}

        """)


class AnimatedLabel(QLabel):
    """
    Label with smooth fade-in animations and enhanced typography.
    """

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._setup_animations()
        self._setup_style()

    def _setup_animations(self):
        """Setup fade-in animation."""
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self._fade_animation.setDuration(300)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _setup_style(self):
        """Apply enhanced typography styling."""
        from ui.theme import theme

        self.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_ACCENT};
                font-weight: 500;
                letter-spacing: 0.3px;
                padding: 4px;
            }}
        """)

    def fade_in(self):
        """Trigger fade-in animation."""
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.start()


class NotificationWidget(QFrame):
    """
    Modern notification widget with auto-dismiss and smooth animations.
    """

    close_requested = pyqtSignal()

    def __init__(self, message, notification_type="info", parent=None):
        super().__init__(parent)
        self.message = message
        self.notification_type = notification_type
        self._setup_ui()
        self._setup_animations()
        self._setup_auto_dismiss()

    def _setup_ui(self):
        """Setup notification UI elements."""
        self.setFixedSize(300, 60)
        self._setup_style()

    def _setup_style(self):
        """Apply notification styling based on type."""
        colors = {
            "info": ("#6C84C0", "#5A6C9E"),
            "success": ("#6CC084", "#5AA06E"),
            "warning": ("#C0A06C", "#9E805A"),
            "error": ("#C06C84", "#A05C74"),
        }

        primary = colors.get(self.notification_type, colors["info"])

        self.setStyleSheet(f"""
            QFrame {{
                background: {primary};
                border: 1px solid {primary};
                color: #1E1E1E;
                font-weight: bold;
                padding: 8px;
            }}
        """)

    def _setup_animations(self):
        """Setup slide and fade animations."""
        self._slide_animation = QPropertyAnimation(self, b"geometry")
        self._slide_animation.setDuration(400)
        self._slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _setup_auto_dismiss(self):
        """Setup auto-dismiss timer."""
        from PyQt6.QtCore import QTimer

        self._dismiss_timer = QTimer()
        self._dismiss_timer.timeout.connect(self.close_requested.emit)
        self._dismiss_timer.setSingleShot(True)

    def show_notification(self):
        """Show notification with animation."""
        self._dismiss_timer.start(5000)  # Auto-dismiss after 5 seconds
        # Animation logic would go here

    def dismiss(self):
        """Dismiss notification with animation."""
        self._dismiss_timer.stop()
        # Dismiss animation logic would go here
