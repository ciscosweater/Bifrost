"""
Accessibility components for ACCELA application
Provides visual accessibility enhancements and keyboard navigation
"""

from PyQt6.QtWidgets import QWidget, QLabel, QApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QEvent
from PyQt6.QtGui import QKeyEvent, QFocusEvent, QPainter, QColor, QPen
from .theme import theme, BorderRadius, Typography


class AccessibleWidget(QWidget):
    """
    Base widget with accessibility features
    """
    
    def __init__(self, accessible_name="", accessible_description="", parent=None):
        super().__init__(parent)
        self._accessible_name = accessible_name
        self._accessible_description = accessible_description
        self._setup_accessibility()
        
    def _setup_accessibility(self):
        """Setup accessibility features"""
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessible(True)
        
        if self._accessible_name:
            self.setAccessibleName(self._accessible_name)
        
        if self._accessible_description:
            self.setAccessibleDescription(self._accessible_description)
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard navigation"""
        if event.key() == Qt.Key.Key_Tab:
            self.focusNextChild()
        elif event.key() == Qt.Key.Key_Backtab:
            self.focusPreviousChild()
        elif event.key() == Qt.Key.Key_Enter or event.key() == Qt.Key.Key_Return:
            self.activate()
        else:
            super().keyPressEvent(event)
    
    def activate(self):
        """Activate widget (to be overridden by subclasses)"""
        pass


class FocusIndicator(QWidget):
    """
    Widget that shows focus indicator for accessibility
    """
    
    def __init__(self, target_widget, parent=None):
        super().__init__(parent)
        self.target_widget = target_widget
        self._setup_focus_tracking()
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.raise_()
        
    def _setup_focus_tracking(self):
        """Setup focus event tracking"""
        self.target_widget.installEventFilter(self)
        
    def eventFilter(self, obj, event):
        """Filter events to track focus changes"""
        if obj == self.target_widget:
            if event.type() == QEvent.Type.FocusIn:
                self.show()
                self.update_geometry()
            elif event.type() == QEvent.Type.FocusOut:
                self.hide()
            elif event.type() == QEvent.Type.Move or event.type() == QEvent.Type.Resize:
                self.update_geometry()
        return super().eventFilter(obj, event)
    
    def update_geometry(self):
        """Update indicator geometry to match target"""
        if self.target_widget:
            geo = self.target_widget.geometry()
            self.setGeometry(geo.adjusted(-2, -2, 2, 2))
    
    def paintEvent(self, event):
        """Paint focus indicator"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw focus ring
        pen = QPen(QColor(theme.colors.PRIMARY))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRect(self.rect().adjusted(1, 1, -1, -1))


class HighContrastTheme:
    """
    High contrast theme for accessibility
    """
    
    @staticmethod
    def get_high_contrast_colors():
        """Get high contrast color palette"""
        return {
            'background': '#000000',
            'surface': '#1A1A1A',
            'text_primary': '#FFFFFF',
            'text_secondary': '#CCCCCC',
            'primary': '#FFFF00',
            'primary_light': '#FFFF66',
            'primary_dark': '#CCCC00',
            'border': '#FFFFFF',
            'success': '#00FF00',
            'warning': '#FFA500',
            'error': '#FF0000'
        }
    
    @staticmethod
    def apply_high_contrast(app):
        """Apply high contrast theme to application"""
        colors = HighContrastTheme.get_high_contrast_colors()
        
        high_contrast_style = f"""
            QMainWindow {{
                background: {colors['background']};
                color: {colors['text_primary']};
            }}
            
            QWidget {{
                background: transparent;
                color: {colors['text_primary']};
            }}
            
            QLabel {{
                color: {colors['text_primary']};
                {Typography.get_font_style(Typography.BODY_SIZE)};
                font-weight: bold;
            }}
            
            QPushButton {{
                background: {colors['surface']};
                border: 2px solid {colors['border']};
                color: {colors['text_primary']};
                font-weight: bold;
                padding: 8px 16px;
                border-radius: {BorderRadius.SMALL}px;
            }}
            
            QPushButton:hover {{
                background: {colors['primary']};
                color: {colors['background']};
            }}
            
            QPushButton:focus {{
                border: 3px solid {colors['primary']};
            }}
            
            QLineEdit, QTextEdit {{
                background: {colors['surface']};
                border: 2px solid {colors['border']};
                color: {colors['text_primary']};
                font-weight: bold;
                padding: 8px;
                border-radius: {BorderRadius.SMALL}px;
            }}
            
            QLineEdit:focus, QTextEdit:focus {{
                border: 3px solid {colors['primary']};
            }}
            
            QProgressBar {{
                border: 2px solid {colors['border']};
                text-align: center;
                color: {colors['text_primary']};
                font-weight: bold;
                background: {colors['surface']};
                border-radius: {BorderRadius.SMALL}px;
                padding: 2px;
            }}
            
            QProgressBar::chunk {{
                background: {colors['primary']};
                border-radius: {BorderRadius.SMALL}px;
            }}
        """
        
        app.setStyleSheet(high_contrast_style)


class AccessibleButton(AccessibleWidget):
    """
    Accessible button with keyboard navigation and screen reader support
    """
    
    clicked = pyqtSignal()
    
    def __init__(self, text="", accessible_name="", accessible_description="", parent=None):
        self.text = text
        super().__init__(accessible_name or text, accessible_description, parent)
        self._setup_button_style()
        
    def _setup_button_style(self):
        """Setup button styling"""
        self.setStyleSheet(f"""
            AccessibleButton {{
                background: {theme.colors.SURFACE};
                border: 1px solid {theme.colors.PRIMARY};
                color: {theme.colors.TEXT_PRIMARY};
                padding: 8px 16px;
                border-radius: {BorderRadius.SMALL}px;
            }}
            AccessibleButton:hover {{
                background: {theme.colors.PRIMARY};
                color: {theme.colors.TEXT_ON_PRIMARY};
            }}
            AccessibleButton:focus {{
                border: 2px solid {theme.colors.PRIMARY};
            }}
        """)
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def paintEvent(self, event):
        """Paint button text"""
        painter = QPainter(self)
        painter.setPen(QPen(theme.colors.TEXT_PRIMARY if not self.hasFocus() else theme.colors.TEXT_ON_PRIMARY))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text)
    
    def activate(self):
        """Activate button"""
        self.clicked.emit()
    
    def mousePressEvent(self, event):
        """Handle mouse press"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.activate()
        super().mousePressEvent(event)


class KeyboardNavigationHelper:
    """
    Helper class for keyboard navigation patterns
    """
    
    @staticmethod
    def setup_tab_navigation(widgets):
        """Setup tab navigation for a list of widgets"""
        for i, widget in enumerate(widgets):
            if i > 0:
                widgets[i-1].setTabOrder(widgets[i-1], widget)
    
    @staticmethod
    def setup_shortcut_keys(widget, shortcuts):
        """Setup shortcut keys for widget"""
        for key, callback in shortcuts.items():
            if hasattr(widget, 'setShortcut'):
                widget.setShortcut(key)
                if hasattr(widget, 'triggered'):
                    widget.triggered.connect(callback)
    
    @staticmethod
    def add_keyboard_help(parent_widget, shortcuts_dict):
        """Add keyboard help dialog"""
        help_text = "Keyboard Shortcuts:\n\n"
        for shortcut, description in shortcuts_dict.items():
            help_text += f"{shortcut}: {description}\n"
        
        help_label = QLabel(help_text)
        help_label.setStyleSheet(f"""
            QLabel {{
                background: {theme.colors.SURFACE};
                border: 1px solid {theme.colors.BORDER};
                padding: 16px;
                border-radius: {BorderRadius.LARGE}px;
                {Typography.get_font_style(Typography.BODY_SIZE)};
            }}
        """)
        
        return help_label


class ScreenReaderHelper:
    """
    Helper class for screen reader compatibility
    """
    
    @staticmethod
    def announce_to_screen_reader(message):
        """Announce message to screen reader"""
        # This would integrate with actual screen reader APIs
        # For now, we'll use Qt's accessibility system
        if QApplication.instance():
            QApplication.instance().accessibility().setActive(True)
            # In a real implementation, this would interface with
            # screen readers like NVDA, JAWS, or Orca
    
    @staticmethod
    def set_widget_accessibility(widget, name, description, role=None):
        """Set accessibility properties for widget"""
        widget.setAccessibleName(name)
        widget.setAccessibleDescription(description)
        
        if role:
            widget.setAccessibleRole(role)
        
        widget.setAccessible(True)


class AccessibilityManager:
    """
    Main accessibility manager for the application
    """
    
    def __init__(self, app):
        self.app = app
        self.high_contrast_enabled = False
        self.focus_indicators = []
        
    def toggle_high_contrast(self):
        """Toggle high contrast mode"""
        self.high_contrast_enabled = not self.high_contrast_enabled
        
        if self.high_contrast_enabled:
            HighContrastTheme.apply_high_contrast(self.app)
        else:
            theme.apply_theme_to_app(self.app)
    
    def add_focus_indicator(self, widget):
        """Add focus indicator to widget"""
        indicator = FocusIndicator(widget, widget.parent())
        self.focus_indicators.append(indicator)
        return indicator
    
    def setup_widget_accessibility(self, widget, name, description, role=None):
        """Setup accessibility for widget"""
        ScreenReaderHelper.set_widget_accessibility(widget, name, description, role)
        
        # Add focus indicator if widget can receive focus
        if widget.focusPolicy() != Qt.FocusPolicy.NoFocus:
            self.add_focus_indicator(widget)
    
    def announce_change(self, message):
        """Announce UI change to screen reader"""
        ScreenReaderHelper.announce_to_screen_reader(message)


class AccessibilityMixin:
    """
    Mixin to add accessibility features to existing widgets
    """
    
    def make_accessible(self, name, description, role=None):
        """Make widget accessible"""
        self.setAccessibleName(name)
        self.setAccessibleDescription(description)
        
        if role:
            self.setAccessibleRole(role)
        
        self.setAccessible(True)
        
        # Enable keyboard focus
        if self.focusPolicy() == Qt.FocusPolicy.NoFocus:
            self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
    
    def add_accessibility_action(self, action_name, callback):
        """Add accessibility action"""
        # This would integrate with platform accessibility APIs
        pass