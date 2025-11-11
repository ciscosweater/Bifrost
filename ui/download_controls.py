"""
Download Controls - Componentes UI para controle de downloads (pause/resume/cancel)
"""

import logging
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont

from ui.theme import theme, Typography, Spacing, BorderRadius
from ui.enhanced_widgets import SecondaryButton

logger = logging.getLogger(__name__)


class DownloadControls(QWidget):
    """Painel de controle para downloads com pause/resume/cancel"""

    # Signals
    pause_clicked = pyqtSignal()
    resume_clicked = pyqtSignal()
    cancel_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_state = "idle"  # idle, downloading, paused, completed
        self._setup_ui()
        self._set_idle_state()

    def _setup_ui(self):
        """Configura interface do componente"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        layout.setSpacing(Spacing.SM)

        # Status label
        self.status_label = QLabel("Ready to download")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(32)
        # Allow the status label to expand horizontally and enforce a minimum width
        self.status_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.status_label.setMinimumWidth(250)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_SECONDARY};
                {Typography.get_font_style(Typography.BODY_SIZE)};
                font-weight: 500;
                background: {theme.colors.SURFACE};
                border: 1px solid {theme.colors.BORDER};
                border-radius: {BorderRadius.SMALL}px;
                padding: {Spacing.XS}px {Spacing.SM}px;
                {theme.animations.get_transition("all", theme.animations.DURATION_NORMAL)};
            }}
        """)
        layout.addWidget(self.status_label)

        # Control buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(Spacing.SM)  # Reduced spacing

        # Pause button
        self.pause_button = QPushButton("Pause")
        self.pause_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pause_button.clicked.connect(self.pause_clicked.emit)
        self._setup_button_style(self.pause_button, "pause")

        # Resume button (initially hidden)
        self.resume_button = QPushButton("Resume")
        self.resume_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.resume_button.clicked.connect(self.resume_clicked.emit)
        self.resume_button.hide()
        self._setup_button_style(self.resume_button, "resume")

        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_button.clicked.connect(self.cancel_clicked.emit)
        self._setup_button_style(self.cancel_button, "cancel")

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.pause_button)
        buttons_layout.addWidget(self.resume_button)
        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)

    def _setup_button_style(self, button, button_type):
        """Configure button style"""
        styles = {
            "pause": f"""
                QPushButton {{
                    background: {theme.colors.PRIMARY};
                    color: white;
                    border: none;
                    padding: {Spacing.XS}px {Spacing.XS}px;
                    border-radius: {BorderRadius.SMALL}px;
                    font-weight: bold;
                    {Typography.get_font_style(Typography.BODY_SIZE)};
                    min-width: 70px;
                    min-height: 16px;
                }}
                QPushButton:hover {{
                    background: {theme.colors.PRIMARY_LIGHT};
                }}
                QPushButton:pressed {{
                    background: {theme.colors.PRIMARY_DARK};
                }}
                QPushButton:disabled {{
                    background: {theme.colors.SURFACE};
                    color: {theme.colors.TEXT_DISABLED};
                }}
            """,
            "resume": f"""
                QPushButton {{
                    background: {theme.colors.SUCCESS};
                    color: white;
                    border: none;
                    padding: {Spacing.XS}px {Spacing.XS}px;
                    border-radius: {BorderRadius.SMALL}px;
                    font-weight: bold;
                    {Typography.get_font_style(Typography.BODY_SIZE)};
                    min-width: 70px;
                    min-height: 16px;
                }}
                QPushButton:hover {{
                    background: {theme.colors.SUCCESS_LIGHT};
                }}
                QPushButton:pressed {{
                    background: {theme.colors.SUCCESS_DARK};
                }}
                QPushButton:disabled {{
                    background: {theme.colors.SURFACE};
                    color: {theme.colors.TEXT_DISABLED};
                }}
            """,
            "cancel": f"""
                QPushButton {{
                    background: {theme.colors.PRIMARY};
                    color: white;
                    border: none;
                    padding: {Spacing.XS}px {Spacing.XS}px;
                    border-radius: {BorderRadius.SMALL}px;
                    font-weight: bold;
                    {Typography.get_font_style(Typography.BODY_SIZE)};
                    min-width: 70px;
                    min-height: 16px;
                }}
                QPushButton:hover {{
                    background: {theme.colors.PRIMARY_LIGHT};
                }}
                QPushButton:pressed {{
                    background: {theme.colors.PRIMARY_DARK};
                }}
                QPushButton:disabled {{
                    background: {theme.colors.SURFACE};
                    color: {theme.colors.TEXT_DISABLED};
                }}
            """,
        }

        button.setStyleSheet(styles.get(button_type, styles["pause"]))
        button.setMinimumWidth(100)

    def set_downloading_state(self):
        """Configura estado de downloading"""
        self.current_state = "downloading"
        self.status_label.setText("Downloading in progress...")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_ON_PRIMARY};
                {Typography.get_font_style(Typography.BODY_SIZE)};
                font-weight: 600;
                background: {theme.colors.PRIMARY};
                border: 1px solid {theme.colors.PRIMARY_DARK};
                border-radius: {BorderRadius.SMALL}px;
                padding: {Spacing.XS}px {Spacing.SM}px;
                {theme.shadows.get_shadow(theme.shadows.SUBTLE)};
            }}
        """)

        self.pause_button.setEnabled(True)
        self.pause_button.show()
        self.resume_button.hide()
        self.cancel_button.setEnabled(True)

    def set_paused_state(self):
        """Configura estado de paused"""
        self.current_state = "paused"
        self.status_label.setText("Download paused")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_ON_PRIMARY};
                {Typography.get_font_style(Typography.BODY_SIZE)};
                font-weight: 600;
                background: {theme.colors.WARNING};
                border: 1px solid {theme.colors.WARNING_DARK};
                border-radius: {BorderRadius.SMALL}px;
                padding: {Spacing.XS}px {Spacing.SM}px;
                {theme.shadows.get_shadow(theme.shadows.SUBTLE)};
            }}
        """)

        self.pause_button.hide()
        self.resume_button.setEnabled(True)
        self.resume_button.show()
        self.cancel_button.setEnabled(True)

    def set_completed_state(self):
        """Configura estado de completed"""
        self.current_state = "completed"
        self.status_label.setText("Download completed successfully!")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_ON_PRIMARY};
                {Typography.get_font_style(Typography.BODY_SIZE)};
                font-weight: 600;
                background: {theme.colors.SUCCESS};
                border: 1px solid {theme.colors.SUCCESS_DARK};
                border-radius: {BorderRadius.SMALL}px;
                padding: {Spacing.XS}px {Spacing.SM}px;
                {theme.shadows.get_shadow(theme.shadows.SUBTLE)};
            }}
        """)

        self.pause_button.setEnabled(False)
        self.pause_button.hide()
        self.resume_button.setEnabled(False)
        self.resume_button.hide()
        self.cancel_button.setEnabled(False)

    def set_cancelling_state(self):
        """Configura estado de cancelling"""
        self.current_state = "cancelling"
        self.status_label.setText("Cancelling download...")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_ON_PRIMARY};
                {Typography.get_font_style(Typography.BODY_SIZE)};
                font-weight: 600;
                background: {theme.colors.ERROR};
                border: 1px solid {theme.colors.ERROR_DARK};
                border-radius: {BorderRadius.SMALL}px;
                padding: {Spacing.XS}px {Spacing.SM}px;
                {theme.shadows.get_shadow(theme.shadows.SUBTLE)};
            }}
        """)

        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.cancel_button.setEnabled(False)

    def set_idle_state(self):
        """Configura estado idle"""
        self._set_idle_state()

    def _set_idle_state(self):
        """Configure idle state (internal method)"""
        self.current_state = "idle"
        self.status_label.setText("Ready to download")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_SECONDARY};
                {Typography.get_font_style(Typography.BODY_SIZE)};
                font-weight: 500;
                background: {theme.colors.SURFACE};
                border: 1px solid {theme.colors.BORDER};
                border-radius: {BorderRadius.SMALL}px;
                padding: {Spacing.XS}px {Spacing.SM}px;
                {theme.animations.get_transition("all", theme.animations.DURATION_NORMAL)};
            }}
        """)

        self.pause_button.setEnabled(False)
        self.pause_button.hide()
        self.resume_button.setEnabled(False)
        self.resume_button.hide()
        self.cancel_button.setEnabled(False)

    def update_status(self, message: str):
        """Atualiza mensagem de status"""
        # Limitar tamanho da mensagem para evitar overflow
        max_length = 60
        if len(message) > max_length:
            message = message[: max_length - 3] + "..."

        if self.current_state == "downloading":
            full_text = f"Downloading: {message}"
        elif self.current_state == "paused":
            full_text = f"Paused: {message}"
        elif self.current_state == "cancelling":
            full_text = f"Cancelling: {message}"
        else:
            full_text = message

        # If full text is still too long, truncate prefix too
        if len(full_text) > 80:
            full_text = full_text[:77] + "..."

        self.status_label.setText(full_text)

        # Update geometry so layout respects configured minimum size
        self.status_label.updateGeometry()


class CompactDownloadControls(QWidget):
    """Compact version of controls for smaller spaces"""

    pause_clicked = pyqtSignal()
    resume_clicked = pyqtSignal()
    cancel_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_state = "idle"
        self._setup_ui()
        self._set_idle_state()

    def _setup_ui(self):
        """Configura interface compacta"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, Spacing.XS, 0, Spacing.XS)
        layout.setSpacing(Spacing.XS)

        # Smaller and more compact buttons
        self.pause_button = QPushButton("||")
        self.pause_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pause_button.clicked.connect(self.pause_clicked.emit)
        self.pause_button.setFixedSize(Spacing.XL * 2, Spacing.XL * 2)
        self.pause_button.hide()

        self.resume_button = QPushButton(">")
        self.resume_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.resume_button.clicked.connect(self.resume_clicked.emit)
        self.resume_button.setFixedSize(Spacing.XL * 2, Spacing.XL * 2)
        self.resume_button.hide()

        self.cancel_button = QPushButton("X")
        self.cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_button.clicked.connect(self.cancel_clicked.emit)
        self.cancel_button.setFixedSize(Spacing.XL * 2, Spacing.XL * 2)

        # Estilo compacto
        compact_style = f"""
            QPushButton {{
                background: {theme.colors.SURFACE};
                color: {theme.colors.TEXT_PRIMARY};
                border: 1px solid {theme.colors.BORDER};
                border-radius: {BorderRadius.SMALL}px;
                {Typography.get_font_style(Typography.BODY_SIZE)};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {theme.colors.PRIMARY};
                color: white;
                border-color: {theme.colors.PRIMARY};
            }}
            QPushButton:disabled {{
                background: {theme.colors.BACKGROUND};
                color: {theme.colors.TEXT_DISABLED};
                border-color: {theme.colors.BORDER};
            }}
        """

        self.pause_button.setStyleSheet(compact_style)
        self.resume_button.setStyleSheet(compact_style)
        self.cancel_button.setStyleSheet(compact_style)

        layout.addWidget(self.pause_button)
        layout.addWidget(self.resume_button)
        layout.addWidget(self.cancel_button)
        layout.addStretch()

    def set_downloading_state(self):
        """Configura estado de downloading"""
        self.current_state = "downloading"
        self.pause_button.show()
        self.pause_button.setEnabled(True)
        self.resume_button.hide()
        self.cancel_button.setEnabled(True)

    def set_paused_state(self):
        """Configura estado de paused"""
        self.current_state = "paused"
        self.pause_button.hide()
        self.resume_button.show()
        self.resume_button.setEnabled(True)
        self.cancel_button.setEnabled(True)

    def set_completed_state(self):
        """Configura estado de completed"""
        self.current_state = "completed"
        self.pause_button.hide()
        self.resume_button.hide()
        self.cancel_button.setEnabled(False)

    def set_cancelling_state(self):
        """Configura estado de cancelling"""
        self.current_state = "cancelling"
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.cancel_button.setEnabled(False)

    def _set_idle_state(self):
        """Configura estado idle"""
        self.current_state = "idle"
        self.pause_button.hide()
        self.resume_button.hide()
        self.cancel_button.setEnabled(False)
