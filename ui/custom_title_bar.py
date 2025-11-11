import logging
import re

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QIcon, QMouseEvent, QMovie, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizeGrip,
    QSizePolicy,
    QSpacerItem,
    QWidget,
)

from .assets import GEAR_SVG, POWER_SVG

logger = logging.getLogger(__name__)


class CustomTitleBar(QFrame):
    """
    A custom, frameless title bar with SVG buttons for settings and closing.
    This is placed at the bottom of the main window as requested.
    It also handles window dragging and resizing.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.drag_pos = None
        self.setFixedHeight(35)  # Aumentado para evitar corte e melhor proporção
        from .theme import get_current_theme

        current_theme = get_current_theme()

        self.setStyleSheet(f"""
            QFrame {{
                background: {current_theme.colors.BACKGROUND};
                border-top: 1px solid {current_theme.colors.BORDER};
            }}
        """)
        logger.debug("CustomTitleBar initialized.")

        layout = QHBoxLayout()
        layout.setContentsMargins(8, 6, 8, 6)  # Melhores margens para altura maior
        layout.setSpacing(8)  # Melhor espaçamento

        # Create containers for left and right elements to properly balance them.
        left_widget = QWidget()
        left_layout = QHBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.version_label = QLabel("v1.1.0 - ciskao")
        self.version_label.setStyleSheet(f"""
            QLabel {{
                color: {current_theme.colors.TEXT_SECONDARY};
                font-size: 12px;
                font-weight: 600;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }}
        """)
        left_layout.addWidget(self.version_label)

        right_widget = QWidget()
        right_layout = QHBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)  # Melhor espaçamento entre botões

        # Add SLSsteam status indicator (compact) - before ZIP button
        from .slssteam_status import SlssteamStatusWidget

        self.slssteam_status = SlssteamStatusWidget(parent, compact=True)
        # Only connect if parent has the method
        if hasattr(parent, "_on_slssteam_setup_requested"):
            self.slssteam_status.setup_requested.connect(
                parent._on_slssteam_setup_requested
            )
        right_layout.addWidget(self.slssteam_status)

        # Add select file button
        self.select_file_button = self._create_text_button(
            "ZIP", getattr(parent, "_select_zip_file", lambda: None), "Select ZIP File"
        )
        right_layout.addWidget(self.select_file_button)

        # Add game manager button
        self.game_manager_button = self._create_text_button(
            "UN", getattr(parent, "_open_game_manager", lambda: None), "Uninstall Games"
        )
        right_layout.addWidget(self.game_manager_button)

        self.settings_button = self._create_svg_button(
            GEAR_SVG, getattr(parent, "open_settings", lambda: None), "Open Settings"
        )
        right_layout.addWidget(self.settings_button)

        self.close_button = self._create_svg_button(
            POWER_SVG, getattr(parent, "close", lambda: None), "Close Application"
        )
        right_layout.addWidget(self.close_button)

        # Main layout assembly
        layout.addWidget(left_widget)
        layout.addStretch(1)
        self.title_label = QLabel("ACCELA")
        from .theme import theme

        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_ACCENT};
                font-size: 16px;
                font-weight: bold;
                letter-spacing: 1px;
                padding: 4px 12px;
                border: none;
                background: transparent;
            }}
        """)
        layout.addWidget(self.title_label)
        layout.addStretch(1)
        layout.addWidget(right_widget)

        # Balance the layout by setting the containers to equal width
        left_width = left_widget.sizeHint().width()
        right_width = right_widget.sizeHint().width()
        if left_width > right_width:
            right_widget.setMinimumWidth(left_width)
        else:
            left_widget.setMinimumWidth(right_width)

        self.setLayout(layout)

    def mousePressEvent(self, event: QMouseEvent):
        """
        Records initial mouse position for window dragging.
        """
        if event and hasattr(event, "button") and event.button() == Qt.MouseButton.LeftButton:
            if hasattr(self.parent, "frameGeometry"):
                try:
                    self.drag_pos = (
                        event.globalPosition().toPoint()
                        - self.parent.frameGeometry().topLeft()
                    )
                except:
                    pass
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        """
        Moves window as mouse is dragged.
        """
        if (
            event
            and hasattr(event, "buttons")
            and event.buttons() == Qt.MouseButton.LeftButton
            and self.drag_pos
        ):
            if hasattr(self.parent, "move"):
                try:
                    self.parent.move(event.globalPosition().toPoint() - self.drag_pos)
                except:
                    pass
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        """
        Resets the drag position when the mouse button is released.
        """
        self.drag_pos = None
        event.accept()

    def _create_svg_button(self, svg_data, on_click, tooltip):
        """
        Helper method to create a button from SVG data, recoloring the icon without distortion.
        """
        try:
            button = QPushButton()
            button.setToolTip(tooltip)

            renderer = QSvgRenderer(svg_data.encode("utf-8"))
            icon_size = QSize(18, 18)  # Ícones maiores para botões maiores

            pixmap = QPixmap(icon_size)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)

            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            renderer.render(painter)

            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceIn
            )

            from .theme import get_current_theme

            current_theme = get_current_theme()
            painter.fillRect(pixmap.rect(), QColor(current_theme.colors.TEXT_ACCENT))

            painter.end()

            icon = QIcon(pixmap)

            button.setIcon(icon)
            button.setIconSize(icon_size)
            button.setFixedSize(22, 22)  # Botões maiores para title bar aumentada
            button.clicked.connect(on_click)
            return button
        except Exception as e:
            logger.error(f"Failed to create SVG button: {e}", exc_info=True)
            fallback_button = QPushButton("X")
            fallback_button.setFixedSize(22, 22)
            fallback_button.clicked.connect(on_click)
            return fallback_button

    def _create_text_button(self, text, on_click, tooltip):
        """
        Helper method to create a simple text button.
        """
        try:
            button = QPushButton(text)
            button.setToolTip(tooltip)
            button.setFixedSize(22, 22)  # Botões maiores para title bar aumentada
            from .theme import get_current_theme

            current_theme = get_current_theme()

            button.setStyleSheet(f"""
                QPushButton {{
                    border: 1px solid {current_theme.colors.BORDER};
                    border-radius: 4px;
                    color: {current_theme.colors.TEXT_ACCENT};
                    font-size: 11px;
                    font-weight: bold;
                    background: {current_theme.colors.SURFACE};
                }}
                QPushButton:hover {{
                    background: {current_theme.colors.PRIMARY};
                    color: {current_theme.colors.TEXT_ON_PRIMARY};
                    border: 1px solid {current_theme.colors.PRIMARY};
                }}
                QPushButton:pressed {{
                    background: {current_theme.colors.PRIMARY_DARK};
                    border: 1px solid {current_theme.colors.PRIMARY_DARK};
                }}
            """)
            button.clicked.connect(on_click)
            return button
        except Exception as e:
            logger.error(f"Failed to create text button: {e}", exc_info=True)
            fallback_button = QPushButton("?")
            fallback_button.setFixedSize(22, 22)
            fallback_button.clicked.connect(on_click)
            return fallback_button
