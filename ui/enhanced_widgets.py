import logging
from utils.logger import get_internationalized_logger

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QFrame, QLabel, QProgressBar

from ui.theme import BorderRadius, Typography, theme

# Import i18n
try:
    from utils.i18n import tr
except (ImportError, ModuleNotFoundError):

    def tr(context, text):
        return text


logger = get_internationalized_logger()


class EnhancedProgressBar(QProgressBar):
    """
    Enhanced progress bar with solid color styling, time estimation, and smooth animations.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._start_time = None
        self._last_update_time = None
        self._estimated_time_remaining = 0
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_time_estimation)
        self._update_timer.setInterval(1000)  # Update every second

        # Estados visuais para downloads
        self.download_state = "idle"  # idle, downloading, paused, cancelled, completed

        self._setup_style()

    def _setup_style(self):
        """Apply enhanced styling with solid colors and modern appearance."""
        self.setStyleSheet(theme.components.PROGRESS_BAR)

    def set_download_state(self, state):
        """Atualiza estado visual do progress bar para downloads"""
        self.download_state = state

        # Definir cores baseadas no estado
        if state == "paused":
            chunk_color = theme.colors.WARNING
            border_color = theme.colors.WARNING
            self.setFormat("%p% - PAUSED")
        elif state == "cancelled":
            chunk_color = theme.colors.ERROR
            border_color = theme.colors.ERROR
            self.setFormat(tr("EnhancedWidgets", "CANCELLED"))
        elif state == "completed":
            chunk_color = theme.colors.SUCCESS
            border_color = theme.colors.SUCCESS
            self.setFormat(tr("EnhancedWidgets", "COMPLETED - %p%"))
        elif state == "downloading":
            chunk_color = theme.colors.PRIMARY
            border_color = theme.colors.PRIMARY
            self.setFormat("%p%")
        else:  # idle
            chunk_color = theme.colors.PRIMARY
            border_color = theme.colors.BORDER
            self.setFormat("%p%")

        # Apply dynamic style with solid colors and shadows
        style = f"""
            QProgressBar {{
                border: 1px solid {border_color};
                border-radius: {BorderRadius.SMALL}px;
                text-align: center;
                font-weight: bold;
                {Typography.get_font_style(Typography.CAPTION_SIZE)};
                color: {theme.colors.TEXT_PRIMARY};
                background: {theme.colors.SURFACE};
                height: 20px;
            }}
            QProgressBar::chunk {{
                background: {chunk_color};
                border-radius: {BorderRadius.SMALL - 1}px;
            }}
        """

        self.setStyleSheet(style)

    def start_progress(self, maximum=100):
        """Initialize progress tracking with time estimation."""
        self.setMaximum(maximum)
        self.setValue(0)
        self._start_time = (
            QTimer().remainingTime() if hasattr(QTimer(), "remainingTime") else 0
        )
        self._last_update_time = self._start_time
        self._update_timer.start()
        self.setFormat("%p%")  # Removido "Calculating..." para mostrar porcentagem real

    def update_progress(self, value, total_size_mb=0, downloaded_mb=0):
        """Update progress with enhanced information display."""
        self.setValue(value)

        if total_size_mb > 0 and downloaded_mb >= 0:
            # Formatar tamanhos de forma mais elegante
            if total_size_mb >= 1024:
                total_text = f"{total_size_mb / 1024:.1f} GB"
                downloaded_text = f"{downloaded_mb / 1024:.1f} GB"
            else:
                total_text = f"{total_size_mb:.1f} MB"
                downloaded_text = f"{downloaded_mb:.1f} MB"

            speed_text = f"{downloaded_text}/{total_text}"

            if self._estimated_time_remaining > 0:
                time_text = (
                    f" - {self._format_time(self._estimated_time_remaining)} remaining"
                )
                if self.download_state == "downloading":
                    self.setFormat(f"%p% - {speed_text}{time_text}")
                else:
                    self.setFormat(f"%p% - {speed_text}{time_text}")
            else:
                self.setFormat(f"%p% - {speed_text}")
        else:
            self.setFormat("%p%")

    def _update_time_estimation(self):
        """Calculate estimated time remaining based on progress rate."""
        if self._start_time is None or self.value() <= 0:
            return

        current_time = (
            QTimer().remainingTime() if hasattr(QTimer(), "remainingTime") else 0
        )
        elapsed_time = (current_time - self._start_time) / 1000.0  # Convert to seconds

        if elapsed_time > 0 and self.value() > 0:
            progress_rate = self.value() / elapsed_time
            remaining_progress = self.maximum() - self.value()

            if progress_rate > 0:
                self._estimated_time_remaining = remaining_progress / progress_rate

    def _format_time(self, seconds):
        """Format time in seconds to human-readable format."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m{secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h{minutes}m"

    def finish_progress(self):
        """Complete progress with success indication."""
        self.setValue(self.maximum())
        self._update_timer.stop()
        self.set_download_state("completed")

    def reset_progress(self):
        """Reset progress bar to initial state."""
        self.setValue(0)
        self._update_timer.stop()
        self._start_time = None
        self._estimated_time_remaining = 0
        self.setFormat("%p%")


class ModernCard(QFrame):
    """
    Modern card component with glassmorphism effect and hover animations
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_style()

    def _setup_style(self):
        """Apply modern card styling"""
        self.setStyleSheet(theme.components.CARD)


class PrimaryButton(QLabel):
    """
    Modern primary button with solid color background and hover effects
    """

    clicked = pyqtSignal()

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._setup_style()
        self._setup_interactions()

    def _setup_style(self):
        """Apply primary button styling"""
        self.setStyleSheet(theme.components.PRIMARY_BUTTON)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _setup_interactions(self):
        """Setup mouse interactions"""
        pass

    def mousePressEvent(self, ev):
        """Handle mouse press"""
        if ev and ev.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class SecondaryButton(QLabel):
    """
    Modern secondary button with outline style
    """

    clicked = pyqtSignal()

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._setup_style()
        self._setup_interactions()

    def _setup_style(self):
        """Apply secondary button styling"""
        self.setStyleSheet(theme.components.SECONDARY_BUTTON)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _setup_interactions(self):
        """Setup mouse interactions"""
        pass

    def mousePressEvent(self, ev):
        """Handle mouse press"""
        if ev and ev.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class StatusIndicator(QLabel):
    """
    Status indicator with different states and colors
    """

    def __init__(self, status="ready", text="", parent=None):
        super().__init__(text, parent)
        self.set_status(status)

    def set_status(self, status):
        """Set status with appropriate styling"""
        self.setStyleSheet(theme.components.get_status_indicator_style(status))
        self.status = status

    def get_status(self):
        """Get current status"""
        return getattr(self, "status", "ready")
