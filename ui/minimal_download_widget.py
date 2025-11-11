"""
Minimal Download Widget - Unified and elegant component for download control
"""

import logging
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont

from ui.theme import theme

logger = logging.getLogger(__name__)


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
        self._setup_ui()
        self._set_idle_state()

    def _setup_ui(self):
        """Configure minimalist interface with optimized layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(6)

        # Container principal sem fundo
        self.setStyleSheet(f"""
            QWidget {{
                background: transparent;
                border: none;
                border-radius: 0px;
            }}
        """)

        # Linha 1: Imagem + Nome do jogo
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(16, 0, 16, 0)
        header_layout.setSpacing(12)

        # Container for game image - Steam header ratio (920x430 ≈ 2.14:1)
        self.game_image_label = QLabel()
        self.game_image_label.setFixedSize(120, 56)  # Reduced Steam header ratio
        self.game_image_label.setStyleSheet(f"""
            QLabel {{
                background: transparent;
                border: none;
                border-radius: 4px;
            }}
        """)
        self.game_image_label.hide()

        # Nome do jogo
        self.game_name_label = QLabel("Game Name")
        self.game_name_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_PRIMARY};
                font-size: 18px;
                font-weight: 700;
                background: transparent;
            }}
        """)
        self.game_name_label.hide()

        # Status label
        self.status_label = QLabel("Ready to download")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_SECONDARY};
                font-size: 12px;
                font-weight: 500;
                background: transparent;
            }}
        """)
        self.status_label.hide()

        header_layout.addWidget(self.game_image_label)
        header_layout.addWidget(self.game_name_label)
        header_layout.addStretch()

        # Linha 2: Barra de progresso
        self.progress_container = QWidget()
        self.progress_container.setFixedHeight(6)
        self.progress_container.setStyleSheet(f"""
            QWidget {{
                background: {theme.colors.BACKGROUND};
                border-radius: 3px;
            }}
        """)

        self.progress_bar = QWidget(self.progress_container)
        self.progress_bar.setGeometry(0, 0, 0, 6)
        self.progress_bar.setStyleSheet(f"""
            QWidget {{
                background: {theme.colors.PRIMARY};
                border-radius: 3px;
            }}
        """)

        # Smooth progress bar animation
        self.progress_animation = QPropertyAnimation(self.progress_bar, b"geometry")
        self.progress_animation.setDuration(300)
        self.progress_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Linha 3: Status detalhado + velocidade + controles
        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(16, 4, 16, 0)
        bottom_layout.setSpacing(12)



        # Velocidade label
        self.speed_label = QLabel("")
        self.speed_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.PRIMARY};
                font-size: 11px;
                font-weight: 600;
                background: transparent;
            }}
        """)
        self.speed_label.hide()

        # Minimalist buttons with text
        self.pause_btn = self._create_control_button("Pause", "pause")
        self.resume_btn = self._create_control_button("Resume", "resume")
        self.cancel_btn = self._create_control_button("Cancel", "cancel")

        # Hide buttons initially
        self.pause_btn.hide()
        self.resume_btn.hide()
        self.cancel_btn.hide()

        bottom_layout.addStretch()
        bottom_layout.addWidget(self.speed_label)
        bottom_layout.addWidget(self.pause_btn)
        bottom_layout.addWidget(self.resume_btn)
        bottom_layout.addWidget(self.cancel_btn)

        # Adicionar layouts ao container principal
        layout.addLayout(header_layout)
        layout.addWidget(self.progress_container)
        layout.addLayout(bottom_layout)

        # Conectar signals
        self.pause_btn.clicked.connect(self.pause_clicked.emit)
        self.resume_btn.clicked.connect(self.resume_clicked.emit)
        self.cancel_btn.clicked.connect(self.cancel_clicked.emit)

    def _create_fallback_image(self):
        """Create a fallback placeholder image when no game image is available"""
        from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QPen
        from PyQt6.QtCore import Qt, QSize
        
        # Create a 120x56 pixmap (same size as game_image_label)
        pixmap = QPixmap(120, 56)
        pixmap.fill(QColor('#2A2A2A'))  # Dark background
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw game controller icon
        painter.setPen(QPen(QColor('#666666'), 2))
        painter.setBrush(QColor('#444444'))
        
        # Simple controller shape
        painter.drawRoundedRect(35, 18, 50, 20, 8, 8)
        painter.drawRoundedRect(25, 22, 15, 12, 4, 4)
        painter.drawRoundedRect(80, 22, 15, 12, 4, 4)
        
        # Draw dots for buttons
        painter.setPen(QPen(QColor('#666666'), 1))
        painter.setBrush(QColor('#555555'))
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
                border-radius: 6px;
                font-size: 12px;
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
            colors = (theme.colors.WARNING, theme.colors.WARNING, 
                     theme.colors.WARNING_DARK, theme.colors.WARNING_DARK)
        elif button_type == "resume":
            colors = (theme.colors.SUCCESS, theme.colors.SUCCESS,
                     theme.colors.SUCCESS_DARK, theme.colors.SUCCESS_DARK)
        else:  # cancel
            colors = (theme.colors.ERROR, theme.colors.ERROR,
                     theme.colors.ERROR_DARK, theme.colors.ERROR_DARK)

        btn.setStyleSheet(base_style % colors)
        return btn

    def _update_progress_bar(self, value):
        """Update progress bar with smooth animation"""
        if value < 0:
            value = 0
        elif value > 100:
            value = 100

        container_width = self.progress_container.width()
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
        
        # Enhanced image handling with fallback
        if game_image and not game_image.isNull():
            scaled_pixmap = game_image.scaled(120, 56, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            self.game_image_label.setPixmap(scaled_pixmap)
            self.game_image_label.show()
        else:
            # Use fallback image
            fallback_pixmap = self._create_fallback_image()
            self.game_image_label.setPixmap(fallback_pixmap)
            self.game_image_label.show()
        
        # Mostrar nome do jogo se fornecido
        if game_name:
            self.game_name_label.setText(game_name)
            self.game_name_label.show()
        else:
            self.game_name_label.hide()
            

        
        self.progress_bar.setStyleSheet(f"""
            QWidget {{
                background: {theme.colors.PRIMARY};
                border-radius: 3px;
            }}
        """)
        
        self.speed_label.show()
        self.pause_btn.show()
        self.pause_btn.setEnabled(True)
        self.resume_btn.hide()
        self.cancel_btn.show()
        self.cancel_btn.setEnabled(True)

    def set_paused_state(self):
        """Configure paused state"""
        self.current_state = "paused"
        
        self.progress_bar.setStyleSheet(f"""
            QWidget {{
                background: {theme.colors.WARNING};
                border-radius: 3px;
            }}
        """)
        
        self.pause_btn.hide()
        self.resume_btn.show()
        self.resume_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)

    def set_completed_state(self):
        """Configure completed state"""
        self.current_state = "completed"
        
        self.progress_bar.setStyleSheet(f"""
            QWidget {{
                background: {theme.colors.SUCCESS};
                border-radius: 3px;
            }}
        """)
        
        self.speed_label.hide()
        self.pause_btn.hide()
        self.resume_btn.hide()
        self.cancel_btn.hide()

    def set_error_state(self, message="Error"):
        """Configure error state"""
        self.current_state = "error"
        self.game_image_label.hide()
        
        self.progress_bar.setStyleSheet(f"""
            QWidget {{
                background: {theme.colors.ERROR};
                border-radius: 3px;
            }}
        """)
        
        self.speed_label.hide()
        self.pause_btn.hide()
        self.resume_btn.hide()
        self.cancel_btn.show()

    def _set_idle_state(self):
        """Configure idle state"""
    
    def set_idle_state(self):
        """Public method to set idle state"""
        self._set_idle_state()
        self.current_state = "idle"
        self.game_image_label.hide()
        self.game_name_label.hide()
        
        self.progress_bar.setStyleSheet(f"""
            QWidget {{
                background: {theme.colors.PRIMARY};
                border-radius: 3px;
            }}
        """)
        
        self.speed_label.hide()
        self.pause_btn.hide()
        self.resume_btn.hide()
        self.cancel_btn.hide()

    def update_progress(self, value):
        """Update progress"""
        self.progress = value
        self._update_progress_bar(value)

    def update_speed(self, speed_text):
        """Update download speed"""
        self.current_speed = speed_text
        self.speed_label.setText(speed_text)

    def update_status(self, message):
        """Update detailed status message - removed"""
        pass

    def reset(self):
        """Reset widget to initial state"""
        self._set_idle_state()
        self._update_progress_bar(0)
        self.speed_label.setText("")
