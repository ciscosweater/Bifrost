"""
Minimal Download Widget - Unified and elegant component for download control
"""

from utils.logger import get_internationalized_logger

import logging

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget, QSizePolicy

from ui.theme import BorderRadius, Spacing, Typography, theme

# Import i18n
try:
    from utils.i18n import tr
except (ImportError, ModuleNotFoundError):

    def tr(context, text):
        return text


logger = get_internationalized_logger()


class MinimalDownloadWidget(QWidget):
    """
    Widget minimalista e elegante que combina:
    - Status do download
    - Barra de progresso integrada
    - Velocidade de download
    - Controles (pause/resume/cancel)
    """

    # Signals
    pause_clicked = pyqtSignal()
    resume_clicked = pyqtSignal()
    cancel_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_state = "idle"  # idle, downloading, paused, completed, error
        self.current_speed = "0 B/s"
        self.progress = 0
        self.total_size = 0
        self.downloaded_size = 0

        # Debouncing timers for performance
        self._progress_timer = QTimer()
        self._progress_timer.setSingleShot(True)
        self._pending_progress = 0

        self._speed_timer = QTimer()
        self._speed_timer.setSingleShot(True)
        self._pending_speed = ""

        self._setup_ui()
        self._set_idle_state()

    def _setup_ui(self):
        """Configure minimalist interface with optimized layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        layout.setSpacing(Spacing.SM)

        # Container principal sem fundo
        self.setStyleSheet(f"""
            QWidget {{
                background: transparent;
                border: none;
                {BorderRadius.get_border_radius(0)};
            }}
        """)

        # Linha 1: Imagem + Nome do jogo (ocupando largura total)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(Spacing.MD)

        # Container for game image - Steam header ratio (920x430 ≈ 2.14:1)
        self.game_image_label = QLabel()
        self.game_image_label.setFixedSize(120, 56)  # Reduced Steam header ratio
        self.game_image_label.setStyleSheet(f"""
            QLabel {{
                background: transparent;
                border: none;
                border-radius: {BorderRadius.SMALL}px;
            }}
        """)
        self.game_image_label.hide()

        # Nome do jogo
        self.game_name_label = QLabel(tr("MinimalDownloadWidget", "Game Name"))
        self.game_name_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.PRIMARY};
                {Typography.get_font_style(Typography.H1_SIZE)};
                font-weight: 700;
                background: transparent;
            }}
        """)
        self.game_name_label.hide()

        # Status label
        self.status_label = QLabel(tr("MinimalDownloadWidget", "Ready to download"))
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_SECONDARY};
                {Typography.get_font_style(Typography.BODY_SIZE)};
                font-weight: 500;
                background: transparent;
            }}
        """)
        self.status_label.setWordWrap(False)
        self.status_label.setMaximumWidth(400)
        self.status_label.setMinimumHeight(20)
        self.status_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.status_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.status_label.hide()

        header_layout.addWidget(self.game_image_label)
        header_layout.addWidget(self.game_name_label)
        header_layout.addStretch()

        # Linha 2: Barra de progresso (ocupando largura total)
        self.progress_container = QWidget()
        self.progress_container.setMinimumHeight(16)
        self.progress_container.setMaximumHeight(16)
        self.progress_container.setStyleSheet(f"""
            QWidget {{
                background: {theme.colors.BACKGROUND};
                border-radius: {BorderRadius.SMALL}px;
            }}
        """)

        self.progress_bar = QWidget(self.progress_container)
        self.progress_bar.setGeometry(0, 0, 0, 16)
        self.progress_bar.setStyleSheet(f"""
            QWidget {{
                background: {theme.colors.PRIMARY};
                border-radius: {BorderRadius.SMALL}px;
            }}
        """)

        # Smooth progress bar animation
        self.progress_animation = QPropertyAnimation(self.progress_bar, b"geometry")
        self.progress_animation.setDuration(300)
        self.progress_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Linha 3: Velocidade e tamanho (esquerda) + controles (direita)
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, Spacing.XS, 0, 0)
        bottom_layout.setSpacing(Spacing.MD)

        # Container para velocidade e tamanho
        info_container = QVBoxLayout()
        info_container.setContentsMargins(0, 0, 0, 0)
        info_container.setSpacing(2)

        # Velocidade label
        self.speed_label = QLabel("")
        self.speed_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.PRIMARY};
                {Typography.get_font_style(Typography.BODY_SIZE)};
                font-weight: 600;
                background: transparent;
            }}
        """)
        self.speed_label.hide()

        # Size label (movido para cá)
        self.size_label = QLabel(f"{tr('MinimalDownloadWidget', 'Size')}: --")
        self.size_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_PRIMARY};
                {Typography.get_font_style(Typography.BODY_SIZE)};
                font-weight: 600;
                background: transparent;
            }}
        """)
        self.size_label.show()  # Show by default

        info_container.addWidget(self.speed_label)
        info_container.addWidget(self.size_label)

        # Minimalist buttons with text
        self.pause_btn = self._create_control_button(
            tr("MinimalDownloadWidget", "Pause"), "pause"
        )
        self.resume_btn = self._create_control_button(
            tr("MinimalDownloadWidget", "Resume"), "resume"
        )
        self.cancel_btn = self._create_control_button(
            tr("MinimalDownloadWidget", "Cancel"), "cancel"
        )

        # Hide buttons initially
        self.pause_btn.hide()
        self.resume_btn.hide()
        self.cancel_btn.hide()

        # Layout: info container à esquerda, controles à direita
        bottom_layout.addLayout(info_container)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.pause_btn)
        bottom_layout.addWidget(self.resume_btn)
        bottom_layout.addWidget(self.cancel_btn)

        # Adicionar layouts ao container principal
        layout.addLayout(header_layout)
        layout.addWidget(self.progress_container)
        layout.addWidget(self.status_label)  # Adicionado status_label ao layout
        layout.addLayout(bottom_layout)

        # Conectar signals
        self.pause_btn.clicked.connect(self.pause_clicked.emit)
        self.resume_btn.clicked.connect(self.resume_clicked.emit)
        self.cancel_btn.clicked.connect(self.cancel_clicked.emit)

        # Connect debouncing timers
        self._progress_timer.timeout.connect(self._apply_progress_update)
        self._speed_timer.timeout.connect(self._apply_speed_update)

    def _create_fallback_image(self):
        """Create a fallback placeholder image when no game image is available"""
        from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap

        # Create a 120x56 pixmap (same size as game_image_label)
        pixmap = QPixmap(120, 56)
        pixmap.fill(QColor(theme.colors.SURFACE))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw game controller icon
        painter.setPen(QPen(QColor(theme.colors.TEXT_SECONDARY), 2))
        painter.setBrush(QColor(theme.colors.BACKGROUND))

        # Simple controller shape
        painter.drawRoundedRect(35, 18, 50, 20, 8, 8)
        painter.drawRoundedRect(25, 22, 15, 12, 4, 4)
        painter.drawRoundedRect(80, 22, 15, 12, 4, 4)

        # Draw dots for buttons
        painter.setPen(QPen(QColor(theme.colors.TEXT_SECONDARY), 1))
        painter.setBrush(QColor(theme.colors.TEXT_SECONDARY))
        painter.drawEllipse(85, 25, 3, 3)
        painter.drawEllipse(90, 25, 3, 3)
        painter.drawEllipse(87, 28, 3, 3)
        painter.drawEllipse(87, 22, 3, 3)

        painter.end()

        return pixmap

    def _create_control_button(self, text, button_type):
        """Create minimalist control button"""
        btn = QPushButton(text)
        btn.setFixedSize(80, 30)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # Estilo base
        base_style = f"""
            QPushButton {{
                background: {theme.colors.SURFACE};
                color: {theme.colors.TEXT_SECONDARY};
                border: 1px solid {theme.colors.BORDER};
                border-radius: {BorderRadius.MEDIUM}px;
                {Typography.get_font_style(Typography.BODY_SIZE)};
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: %s;
                color: white;
                border-color: %s;
            }}
            QPushButton:pressed {{
                background: %s;
                border-color: %s;
            }}
            QPushButton:disabled {{
                background: {theme.colors.BACKGROUND};
                color: {theme.colors.TEXT_DISABLED};
                border-color: {theme.colors.BORDER};
            }}
        """

        # Specific colors by type
        if button_type == "pause":
            colors = (
                theme.colors.WARNING,
                theme.colors.WARNING,
                theme.colors.WARNING_DARK,
                theme.colors.WARNING_DARK,
            )
        elif button_type == "resume":
            colors = (
                theme.colors.SUCCESS,
                theme.colors.SUCCESS,
                theme.colors.SUCCESS_DARK,
                theme.colors.SUCCESS_DARK,
            )
        else:  # cancel
            colors = (
                theme.colors.ERROR,
                theme.colors.ERROR,
                theme.colors.ERROR_DARK,
                theme.colors.ERROR_DARK,
            )

        btn.setStyleSheet(base_style % colors)
        return btn

    def _update_progress_bar(self, value):
        """Update progress bar with smooth animation"""
        if value < 0:
            value = 0
        elif value > 100:
            value = 100

        container_width = max(1, self.progress_container.width())
        new_width = int((container_width * value) / 100)

        # Smooth animation
        current_geometry = self.progress_bar.geometry()
        new_geometry = current_geometry
        new_geometry.setWidth(new_width)

        self.progress_animation.stop()
        self.progress_animation.setStartValue(current_geometry)
        self.progress_animation.setEndValue(new_geometry)
        self.progress_animation.start()

    def set_downloading_state(self, game_name=None, game_image=None):
        """Configure downloading state"""
        self.current_state = "downloading"

        # Hide status label when downloading
        self.status_label.hide()

        # Enhanced image handling with fallback
        # Only clear and update image if a new image is provided
        if game_image is not None:
            # Clear previous image only when updating with new image
            self.game_image_label.clear()

            if not game_image.isNull():
                # Create a copy to avoid reference issues
                from PyQt6.QtGui import QPixmap
                image_copy = QPixmap(game_image)
                scaled_pixmap = image_copy.scaled(
                    120,
                    56,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.game_image_label.setPixmap(scaled_pixmap)
                self.game_image_label.show()
            else:
                # Use fallback image only if new image is explicitly provided but invalid
                fallback_pixmap = self._create_fallback_image()
                self.game_image_label.setPixmap(fallback_pixmap)
                self.game_image_label.show()
        # If no new image provided, preserve existing image (important for resume functionality)

        # Mostrar nome do jogo se fornecido
        if game_name:
            self.game_name_label.setText(game_name)
            self.game_name_label.show()
        else:
            self.game_name_label.hide()

        self.progress_bar.setStyleSheet(f"""
            QWidget {{
                background: {theme.colors.PRIMARY};
                border-radius: {BorderRadius.SMALL}px;
            }}
        """)

        self.speed_label.show()
        self._update_size_display()  # This will show size_label
        self.pause_btn.show()
        self.pause_btn.setEnabled(True)
        self.resume_btn.hide()
        self.cancel_btn.show()
        self.cancel_btn.setEnabled(True)

    def set_paused_state(self):
        """Configure paused state"""
        self.current_state = "paused"

        # Hide status label when paused
        self.status_label.hide()

        self.progress_bar.setStyleSheet(f"""
            QWidget {{
                background: {theme.colors.WARNING};
                border-radius: {BorderRadius.SMALL}px;
            }}
        """)

        self.pause_btn.hide()
        self.resume_btn.show()
        self.resume_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        self._update_size_display()
        # Note: Keep the game image visible in paused state

    def set_completed_state(self):
        """Configure completed state"""
        self.current_state = "completed"

        # Show completion status
        self.status_label.setText(tr("MinimalDownloadWidget", "Download completed!"))
        self.status_label.setToolTip(tr("MinimalDownloadWidget", "Download completed!"))
        self.status_label.show()

        self.progress_bar.setStyleSheet(f"""
            QWidget {{
                background: {theme.colors.SUCCESS};
                border-radius: {BorderRadius.SMALL}px;
            }}
        """)

        self.speed_label.hide()
        self._update_size_display()
        self.pause_btn.hide()
        self.resume_btn.hide()
        self.cancel_btn.hide()
        # Note: Keep the game image visible in completed state

    def set_error_state(self, message=tr("MinimalDownloadWidget", "Error")):
        """Configure error state"""
        self.current_state = "error"
        self.game_image_label.hide()
        self.game_image_label.clear()  # Clear image to prevent stale references
        self.game_name_label.hide()

        # Show error message
        self.status_label.setText(message)
        self.status_label.setToolTip(message)
        self.status_label.show()

        self.progress_bar.setStyleSheet(f"""
            QWidget {{
                background: {theme.colors.ERROR};
                border-radius: {BorderRadius.SMALL}px;
            }}
        """)

        self.speed_label.hide()
        self.pause_btn.hide()
        self.resume_btn.hide()
        self.cancel_btn.show()

    def _set_idle_state(self):
        """Configure idle state"""
        self.current_state = "idle"

        # Show basic elements in idle state
        self.status_label.setText(tr("MinimalDownloadWidget", "Ready to download"))
        self.status_label.setToolTip(tr("MinimalDownloadWidget", "Ready to download"))
        self.status_label.show()
        self.game_image_label.hide()
        self.game_image_label.clear()  # Clear image to prevent stale references
        self.game_name_label.hide()
        self.size_label.hide()
        self.speed_label.hide()
        self.pause_btn.hide()
        self.resume_btn.hide()
        self.cancel_btn.hide()

        # Reset progress bar
        self.progress_bar.setStyleSheet(f"""
            QWidget {{
                background: {theme.colors.BACKGROUND};
                border-radius: {BorderRadius.SMALL}px;
            }}
        """)
        self._update_progress_bar(0)

    def set_idle_state(self):
        """Public method to set idle state"""
        self._set_idle_state()

    def update_progress(self, value):
        """Debounced progress update to improve performance"""
        self.progress = value
        self._pending_progress = value
        self._progress_timer.start(50)  # 50ms debounce

    def _apply_progress_update(self):
        """Actually apply the progress update"""
        if hasattr(self, "_pending_progress"):
            self._update_progress_bar(self._pending_progress)

    def update_speed(self, speed_text):
        """Debounced speed update to improve performance"""
        self.current_speed = speed_text
        self._pending_speed = speed_text
        self._speed_timer.start(100)  # 100ms debounce for speed updates

    def _apply_speed_update(self):
        """Actually apply speed update"""
        if hasattr(self, "_pending_speed") and hasattr(self, "speed_label"):
            self.speed_label.setText(self._pending_speed)

    def set_download_size(self, total_size: int):
        """Define o tamanho total do download"""
        self.total_size = total_size
        self._update_size_display()

    def update_downloaded_size(self, downloaded_size: int):
        """Atualiza o tamanho baixado"""
        self.downloaded_size = downloaded_size
        self._update_size_display()

    def _update_size_display(self):
        """Atualiza exibição das informações de tamanho"""
        total_formatted = self._format_size(self.total_size)
        downloaded_formatted = self._format_size(self.downloaded_size)

        if self.current_state == "downloading":
            if self.total_size > 0:
                text = f"{tr('MinimalDownloadWidget', 'Size')}: {total_formatted}"
            else:
                text = f"{tr('MinimalDownloadWidget', 'Downloaded')}: {downloaded_formatted}"
            self.size_label.setText(text)
        elif self.current_state == "completed":
            if self.total_size > 0:
                self.size_label.setText(
                    f"{tr('MinimalDownloadWidget', 'Completed')}: {total_formatted}"
                )
            else:
                self.size_label.setText(
                    f"{tr('MinimalDownloadWidget', 'Completed')}: {downloaded_formatted}"
                )
        elif self.current_state == "paused":
            if self.total_size > 0:
                text = f"{tr('MinimalDownloadWidget', 'Size')}: {total_formatted}"
            else:
                text = (
                    f"{tr('MinimalDownloadWidget', 'Paused')}: {downloaded_formatted}"
                )
            self.size_label.setText(text)
        else:
            if self.total_size > 0:
                self.size_label.setText(
                    f"{tr('MinimalDownloadWidget', 'Size')}: {total_formatted}"
                )
            else:
                self.size_label.setText(f"{tr('MinimalDownloadWidget', 'Size')}: --")

        self.size_label.show()  # Always show size label

    def _format_size(self, size_bytes: int) -> str:
        """Formata tamanho em bytes para exibição"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def update_status(self, message):
        """Update status message"""
        if hasattr(self, 'status_label') and self.status_label:
            self.status_label.setText(message)
            # Set tooltip with full text in case it gets truncated
            self.status_label.setToolTip(message)
            self.status_label.show()

    def reset(self):
        """Reset widget to initial state"""
        self._set_idle_state()
        self._update_progress_bar(0)
        self.speed_label.setText("")
        self.downloaded_size = 0
        self.total_size = 0
        # Clear image to ensure fresh state for next use
        self.game_image_label.clear()
