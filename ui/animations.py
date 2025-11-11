"""
Animation and micro-interaction components for ACCELA application
Provides smooth transitions and enhanced user feedback
"""

from PyQt6.QtWidgets import QWidget, QGraphicsOpacityEffect
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QTimer, pyqtSignal, Qt, QRect
from PyQt6.QtGui import QPainter, QColor, QPen
from .theme import theme, Animations, BorderRadius


class AnimatedWidget(QWidget):
    """
    Base widget with animation capabilities
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.animations = []
        self._setup_opacity_effect()
        
    def _setup_opacity_effect(self):
        """Setup opacity effect for fade animations"""
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)
    
    def fade_in(self, duration=None):
        """Fade in animation"""
        duration = duration or int(Animations.DURATION_NORMAL.rstrip('s')) * 1000
        
        fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        fade_animation.setDuration(duration)
        fade_animation.setStartValue(0.0)
        fade_animation.setEndValue(1.0)
        fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.animations.append(fade_animation)
        fade_animation.start()
        return fade_animation
    
    def fade_out(self, duration=None):
        """Fade out animation"""
        duration = duration or int(Animations.DURATION_NORMAL.rstrip('s')) * 1000
        
        fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        fade_animation.setDuration(duration)
        fade_animation.setStartValue(1.0)
        fade_animation.setEndValue(0.0)
        fade_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        
        self.animations.append(fade_animation)
        fade_animation.start()
        return fade_animation
    
    def slide_in(self, direction="right", duration=None):
        """Slide in animation from specified direction"""
        duration = duration or int(Animations.DURATION_NORMAL.rstrip('s')) * 1000
        
        parent = self.parent()
        if not parent:
            return None
            
        parent_rect = parent.rect()
        
        # Set start position based on direction
        if direction == "right":
            start_pos = QRect(parent_rect.width(), 0, self.width(), self.height())
        elif direction == "left":
            start_pos = QRect(-self.width(), 0, self.width(), self.height())
        elif direction == "top":
            start_pos = QRect(0, -self.height(), self.width(), self.height())
        elif direction == "bottom":
            start_pos = QRect(0, parent_rect.height(), self.width(), self.height())
        else:
            start_pos = QRect(parent_rect.width(), 0, self.width(), self.height())
        
        end_pos = QRect(self.x(), self.y(), self.width(), self.height())
        
        slide_animation = QPropertyAnimation(self, b"geometry")
        slide_animation.setDuration(duration)
        slide_animation.setStartValue(start_pos)
        slide_animation.setEndValue(end_pos)
        slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.animations.append(slide_animation)
        slide_animation.start()
        return slide_animation
    
    def scale_pulse(self, scale_factor=1.05, duration=None):
        """Scale pulse animation"""
        duration = duration or int(Animations.DURATION_FAST.rstrip('s')) * 1000
        
        # Create scale animation using geometry
        original_rect = self.geometry()
        center_x = original_rect.x() + original_rect.width() // 2
        center_y = original_rect.y() + original_rect.height() // 2
        
        new_width = int(original_rect.width() * scale_factor)
        new_height = int(original_rect.height() * scale_factor)
        new_x = center_x - new_width // 2
        new_y = center_y - new_height // 2
        
        scaled_rect = QRect(new_x, new_y, new_width, new_height)
        
        scale_animation = QPropertyAnimation(self, b"geometry")
        scale_animation.setDuration(duration // 2)
        scale_animation.setStartValue(original_rect)
        scale_animation.setEndValue(scaled_rect)
        scale_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # Add reverse animation
        reverse_animation = QPropertyAnimation(self, b"geometry")
        reverse_animation.setDuration(duration // 2)
        reverse_animation.setStartValue(scaled_rect)
        reverse_animation.setEndValue(original_rect)
        reverse_animation.setEasingCurve(QEasingCurve.Type.InQuad)
        
        scale_animation.finished.connect(reverse_animation.start)
        
        self.animations.extend([scale_animation, reverse_animation])
        scale_animation.start()
        return scale_animation


class HoverButton(QWidget):
    """
    Button with hover animations and effects
    """
    
    clicked = pyqtSignal()
    
    def __init__(self, text="", style_type="primary", parent=None):
        super().__init__(parent)
        self.text = text
        self.style_type = style_type
        self.is_hovered = False
        self.is_pressed = False
        self._setup_style()
        self._setup_animations()
        
    def _setup_style(self):
        """Setup button styling"""
        if self.style_type == "primary":
            self.setStyleSheet(theme.components.PRIMARY_BUTTON)
        else:
            self.setStyleSheet(theme.components.SECONDARY_BUTTON)
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def _setup_animations(self):
        """Setup hover animations"""
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)
    
    def enterEvent(self, event):
        """Handle mouse enter"""
        self.is_hovered = True
        self.scale_pulse(1.02)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Handle mouse leave"""
        self.is_hovered = False
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Handle mouse press"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_pressed = True
            self.scale_pulse(0.95)
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.MouseButton.LeftButton and self.is_pressed:
            self.is_pressed = False
            self.clicked.emit()
        super().mouseReleaseEvent(event)
    
    def paintEvent(self, event):
        """Custom paint for text"""
        painter = QPainter(self)
        painter.setPen(QPen(theme.colors.TEXT_ON_PRIMARY))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text)
    
    def scale_pulse(self, scale_factor=1.0):
        """Scale pulse animation"""
        original_rect = self.geometry()
        center_x = original_rect.x() + original_rect.width() // 2
        center_y = original_rect.y() + original_rect.height() // 2
        
        new_width = int(original_rect.width() * scale_factor)
        new_height = int(original_rect.height() * scale_factor)
        new_x = center_x - new_width // 2
        new_y = center_y - new_height // 2
        
        scaled_rect = QRect(new_x, new_y, new_width, new_height)
        
        animation = QPropertyAnimation(self, b"geometry")
        animation.setDuration(100)
        animation.setStartValue(original_rect)
        animation.setEndValue(scaled_rect)
        animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # Auto-reverse after short delay
        QTimer.singleShot(100, lambda: self._reverse_scale(original_rect))
        
        animation.start()
    
    def _reverse_scale(self, original_rect):
        """Reverse scale animation"""
        animation = QPropertyAnimation(self, b"geometry")
        animation.setDuration(100)
        animation.setStartValue(self.geometry())
        animation.setEndValue(original_rect)
        animation.setEasingCurve(QEasingCurve.Type.InQuad)
        animation.start()


class LoadingIndicator(QWidget):
    """
    Animated loading indicator
    """
    
    def __init__(self, size=32, parent=None):
        super().__init__(parent)
        self.size = size
        self.angle = 0
        self._setup_timer()
        self.setFixedSize(size, size)
        
    def _setup_timer(self):
        """Setup animation timer"""
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_rotation)
        self.timer.setInterval(50)  # 20 FPS
        
    def start_loading(self):
        """Start loading animation"""
        self.timer.start()
        
    def stop_loading(self):
        """Stop loading animation"""
        self.timer.stop()
        self.angle = 0
        self.update()
        
    def _update_rotation(self):
        """Update rotation angle"""
        self.angle = (self.angle + 10) % 360
        self.update()
        
    def paintEvent(self, event):
        """Paint loading indicator"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw rotating arc
        pen = QPen(theme.colors.PRIMARY)
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        center_x = self.width() // 2
        center_y = self.height() // 2
        radius = min(center_x, center_y) - 3
        
        # Draw arc segment
        painter.drawArc(
            center_x - radius, center_y - radius,
            radius * 2, radius * 2,
            self.angle * 16, 90 * 16  # 90 degree arc
        )


class ProgressAnimation(QWidget):
    """
    Animated progress indicator with smooth transitions
    """
    
    progress_changed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_progress = 0
        self.target_progress = 0
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._update_progress)
        self.setFixedHeight(6)
        
    def set_progress(self, value, animated=True):
        """Set progress with optional animation"""
        self.target_progress = max(0, min(100, value))
        
        if animated:
            self.animation_timer.start(16)  # ~60 FPS
        else:
            self.current_progress = self.target_progress
            self.update()
            self.progress_changed.emit(self.current_progress)
    
    def _update_progress(self):
        """Update progress with smooth animation"""
        if abs(self.current_progress - self.target_progress) < 1:
            self.current_progress = self.target_progress
            self.animation_timer.stop()
        else:
            diff = self.target_progress - self.current_progress
            self.current_progress += diff * 0.1  # Smooth easing
        
        self.update()
        self.progress_changed.emit(int(self.current_progress))
    
    def paintEvent(self, event):
        """Paint progress bar"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background
        painter.fillRect(self.rect(), theme.colors.SURFACE)
        
        # Draw progress
        if self.current_progress > 0:
            progress_width = int(self.width() * (self.current_progress / 100))
            progress_rect = self.rect().adjusted(0, 0, -(self.width() - progress_width), 0)
            painter.fillRect(progress_rect, theme.colors.PRIMARY)


class NotificationToast(AnimatedWidget):
    """
    Animated notification toast
    """
    
    dismissed = pyqtSignal()
    
    def __init__(self, message, notification_type="info", duration=3000, parent=None):
        super().__init__(parent)
        self.message = message
        self.notification_type = notification_type
        self.duration = duration
        self._setup_toast()
        self._setup_auto_dismiss()
        
    def _setup_toast(self):
        """Setup toast appearance"""
        self.setFixedSize(300, 80)
        
        # Set background color based on type
        colors = {
            'info': theme.colors.SECONDARY,
            'success': theme.colors.SUCCESS,
            'warning': theme.colors.WARNING,
            'error': theme.colors.ERROR
        }
        
        color = colors.get(self.notification_type, theme.colors.SECONDARY)
        self.setStyleSheet(f"""
            QWidget {{
                background: {color};
                border-radius: {BorderRadius.LARGE}px;
                color: white;
            }}
        """)
    
    def _setup_auto_dismiss(self):
        """Setup auto-dismiss timer"""
        if self.duration > 0:
            QTimer.singleShot(self.duration, self.dismiss)
    
    def show_toast(self):
        """Show toast with animation"""
        self.show()
        self.fade_in()
        QTimer.singleShot(500, lambda: self.slide_in("top"))
    
    def dismiss(self):
        """Dismiss toast with animation"""
        self.fade_out()
        QTimer.singleShot(300, self._handle_dismiss)
    
    def _handle_dismiss(self):
        """Handle dismiss completion"""
        self.dismissed.emit()
        self.hide()
        self.deleteLater()
    
    def paintEvent(self, event):
        """Paint toast message"""
        painter = QPainter(self)
        painter.setPen(QPen(theme.colors.TEXT_ON_PRIMARY))
        painter.drawText(self.rect().adjusted(10, 10, -10, -10), 
                        Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, 
                        self.message)


class AnimationHelper:
    """
    Helper class for common animation patterns
    """
    
    @staticmethod
    def animate_widget_sequence(widgets, animation_type="fade_in", delay=100):
        """Animate sequence of widgets with delay"""
        for i, widget in enumerate(widgets):
            QTimer.singleShot(i * delay, lambda w=widget: AnimationHelper._animate_widget(w, animation_type))
    
    @staticmethod
    def _animate_widget(widget, animation_type):
        """Animate single widget"""
        if hasattr(widget, animation_type):
            getattr(widget, animation_type)()
    
    @staticmethod
    def create_loading_overlay(parent_widget):
        """Create loading overlay for parent widget"""
        overlay = QWidget(parent_widget)
        overlay.setGeometry(parent_widget.rect())
        overlay.setStyleSheet(f"""
            QWidget {{
                background: {theme.colors.OVERLAY};
                border-radius: {BorderRadius.LARGE}px;
            }}
        """)
        
        # Add loading indicator
        loading = LoadingIndicator(32, overlay)
        loading.move(
            overlay.width() // 2 - loading.width() // 2,
            overlay.height() // 2 - loading.height() // 2
        )
        loading.start_loading()
        
        return overlay