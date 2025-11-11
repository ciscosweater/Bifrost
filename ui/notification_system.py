import logging
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QHBoxLayout, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal, QRect
from PyQt6.QtGui import QFont

from ui.theme import theme, Typography, Spacing

logger = logging.getLogger(__name__)

class NotificationManager:
    """
    Global notification manager for non-intrusive user feedback.
    """
    
    def __init__(self, parent=None):
        self.parent = parent
        self.active_notifications = []
        self.max_visible = 3
        self.notification_spacing = Spacing.SM
        
    def show_notification(self, message, notification_type="info", duration=5000):
        """Show a new notification."""
        notification = NotificationWidget(message, notification_type, self.parent)
        notification.dismiss_requested.connect(lambda: self._remove_notification(notification))
        
        self.active_notifications.append(notification)
        self._reposition_notifications()
        
        # Auto-dismiss after duration
        if duration > 0:
            QTimer.singleShot(duration, notification.dismiss)
            
        return notification
        
    def _remove_notification(self, notification):
        """Remove a notification from the active list."""
        if notification in self.active_notifications:
            self.active_notifications.remove(notification)
            self._reposition_notifications()
            
    def _reposition_notifications(self):
        """Reposition all active notifications."""
        if not self.parent:
            return
            
        parent_rect = self.parent.rect()
        start_y = parent_rect.height() - 100  # Start from bottom
        
        for i, notification in enumerate(self.active_notifications[:self.max_visible]):
            x = parent_rect.width() - notification.width() - 20
            y = start_y - (i * (notification.height() + self.notification_spacing))
            
            notification.move(x, y)
            notification.show()

class NotificationWidget(QFrame):
    """
    Individual notification widget with animations.
    """
    
    dismiss_requested = pyqtSignal()
    
    def __init__(self, message, notification_type="info", parent=None):
        super().__init__(parent)
        self.message = message
        self.notification_type = notification_type
        self._setup_ui()
        self._setup_animations()
        
    def _setup_ui(self):
        """Setup notification UI."""
        self.setFixedSize(300, 80)
        self._setup_style()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        
        # Icon label
        icon_label = QLabel()
        icon_label.setFixedSize(24, 24)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setText(self._get_icon())
        icon_label.setStyleSheet(f"""
            QLabel {{
                {Typography.get_font_style(Typography.H2_SIZE)};
                color: {self._get_color()};
                background: transparent;
            }}
        """)
        layout.addWidget(icon_label)
        
        # Message label
        message_label = QLabel(self.message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet(f"""
            QLabel {{
                color: {self._get_color()};
                {Typography.get_font_style(Typography.BODY_SIZE)};
                background: transparent;
            }}
        """)
        layout.addWidget(message_label)
        
        # Close button
        close_button = QPushButton("×")
        close_button.setFixedSize(20, 20)
        close_button.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {self._get_color()};
                {Typography.get_font_style(Typography.H2_SIZE, Typography.WEIGHT_BOLD)};
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.1);
            }}
        """)
        close_button.clicked.connect(self.dismiss)
        layout.addWidget(close_button)
        
    def _setup_style(self):
        """Apply notification styling based on type."""
        colors = {
            "info": (theme.colors.PRIMARY, theme.colors.PRIMARY_DARK),
            "success": (theme.colors.SUCCESS, theme.colors.SUCCESS_DARK), 
            "warning": (theme.colors.WARNING, theme.colors.WARNING_DARK),
            "error": (theme.colors.ERROR, theme.colors.ERROR_DARK)
        }
        
        primary, secondary = colors.get(self.notification_type, colors["info"])
        
        self.setStyleSheet(f"""
            NotificationWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                                          stop:0 {primary}, stop:1 {secondary});
                border: 1px solid {primary};
                color: {theme.colors.BACKGROUND};
            }}
        """)
        
    def _setup_animations(self):
        """Setup slide and fade animations."""
        self.slide_animation = QPropertyAnimation(self, b"geometry")
        self.slide_animation.setDuration(300)
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
    def _get_icon(self):
        """Get icon for notification type."""
        icons = {
            "info": "[i]",
            "success": "[OK]", 
            "warning": "[!]",
            "error": "[X]"
        }
        return icons.get(self.notification_type, "[i]")
        
    def _get_color(self):
        """Get text color for notification type."""
        return theme.colors.BACKGROUND  # Dark text for all notification types
        
    def show_notification(self):
        """Show notification with slide animation."""
        self.setWindowOpacity(0.0)
        self.show()
        
        # Fade in
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.start()
        
    def dismiss(self):
        """Dismiss notification with animation."""
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.finished.connect(self._on_dismiss_finished)
        self.fade_animation.start()
        
    def _on_dismiss_finished(self):
        """Handle dismiss animation completion."""
        self.dismiss_requested.emit()
        self.hide()

class ToastNotification:
    """
    Simple toast notification utility.
    """
    
    @staticmethod
    def show_info(parent, message, duration=3000):
        """Show info toast."""
        if hasattr(parent, 'notification_manager'):
            parent.notification_manager.show_notification(message, "info", duration)
            
    @staticmethod
    def show_success(parent, message, duration=3000):
        """Show success toast."""
        if hasattr(parent, 'notification_manager'):
            parent.notification_manager.show_notification(message, "success", duration)
            
    @staticmethod
    def show_warning(parent, message, duration=4000):
        """Show warning toast."""
        if hasattr(parent, 'notification_manager'):
            parent.notification_manager.show_notification(message, "warning", duration)
            
    @staticmethod
    def show_error(parent, message, duration=5000):
        """Show error toast."""
        if hasattr(parent, 'notification_manager'):
            parent.notification_manager.show_notification(message, "error", duration)

class ProgressNotification:
    """
    Progress notification with percentage display.
    """
    
    def __init__(self, parent, title="Processing..."):
        self.parent = parent
        self.title = title
        self.notification = None
        self.current_progress = 0
        
    def show(self):
        """Show progress notification."""
        self.notification = self.parent.notification_manager.show_notification(
            self.title, "info", 0  # No auto-dismiss
        )
        
    def update_progress(self, progress, message=None):
        """Update progress percentage."""
        self.current_progress = progress
        if message:
            self.title = message
        # Update notification text with progress
        progress_text = f"{self.title} - {progress}%"
        # Update the notification's message label
        if self.notification:
            for child in self.notification.children():
                if isinstance(child, QLabel) and child.text() != "×" and "[i]" not in child.text():
                    child.setText(progress_text)
                    break
                
    def complete(self, success_message="Completed!"):
        """Mark progress as complete."""
        self.update_progress(100, success_message)
        # Auto-dismiss after completion
        if self.notification and hasattr(self.notification, 'dismiss'):
            QTimer.singleShot(2000, self.notification.dismiss)
        
    def dismiss(self):
        """Dismiss progress notification."""
        if self.notification:
            self.notification.dismiss()