import logging
from utils.logger import get_internationalized_logger

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .assets import GEAR_SVG
from .theme import BorderRadius, Spacing, Typography

# Import i18n
try:
    from utils.i18n import tr
except (ImportError, ModuleNotFoundError):

    def tr(context, text):
        return text


logger = get_internationalized_logger()


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
        self.current_tip_index = 0
        # self.setFixedHeight(35)  # Increased to avoid cutting and better proportion
        from .theme import theme

        self.setStyleSheet(f"""
            QFrame {{
                background: {theme.colors.BACKGROUND};
                border: none;
            }}
        """)
        logger.debug("CustomTitleBar initialized.")

        layout = QHBoxLayout()
        layout.setContentsMargins(
            Spacing.MD, 12, Spacing.MD, Spacing.XS
        )  # Melhores margens para altura maior
        layout.setSpacing(Spacing.SM)  # Better spacing

        # Create containers for left and right elements to properly balance them.
        left_widget = QWidget()
        left_layout = QHBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Add SLSsteam status indicator (compact) - before version label
        from .slssteam_status import SlssteamStatusWidget

        self.slssteam_status = SlssteamStatusWidget(parent, compact=True)
        # Only connect if parent has the method
        if hasattr(parent, "_on_slssteam_setup_requested"):
            self.slssteam_status.setup_requested.connect(
                parent._on_slssteam_setup_requested
            )
        left_layout.addWidget(self.slssteam_status)

        self.navi_label = QLabel(tr("CustomTitleBar", "SLSsteam"))
        from .theme import theme

        self.navi_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_ACCENT};
                {Typography.get_font_style(Typography.BODY_SIZE)};
                font-weight: bold;
                border: none;
                background: transparent;
                padding: 0px;
                margin: 0px;
            }}
        """)
        left_layout.addWidget(self.navi_label)

        # Central tip widget with transparent background
        self.tip_widget = QFrame()
        self.tip_widget.setFixedHeight(24)
        self.tip_widget.setMinimumWidth(300)
        self.tip_widget.setMaximumWidth(500)
        self.tip_widget.setStyleSheet(f"""
            QFrame {{
                background: transparent;
                border: none;
            }}
        """)

        tip_layout = QVBoxLayout(self.tip_widget)
        tip_layout.setContentsMargins(8, 2, 8, 2)
        tip_layout.setSpacing(0)

        self.tip_label = QLabel()
        self.tip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tip_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_SECONDARY};
                {Typography.get_font_style(Typography.CAPTION_SIZE)};
                border: none;
                background: transparent;
                padding: 2px 8px;
                border-radius: 12px;
            }}
        """)
        tip_layout.addWidget(self.tip_label)

        # Timer para alternar as dicas periodicamente
        self.tip_timer = QTimer()
        self.tip_timer.timeout.connect(self._update_tip)
        self.tip_timer.start(5000)  # 5 segundos

        # Definir as dicas traduzidas
        self.bifrost_tips = [
            tr("CustomTitleBar.Tip", "Tip 2"),
            tr("CustomTitleBar.Tip", "Tip 3"),
            tr("CustomTitleBar.Tip", "Tip 4"),
            tr("CustomTitleBar.Tip", "Tip 5"),
            tr("CustomTitleBar.Tip", "Tip 6"),
            tr("CustomTitleBar.Tip", "Tip 7"),
            tr("CustomTitleBar.Tip", "Tip 8"),
            tr("CustomTitleBar.Tip", "Tip 9"),
            tr("CustomTitleBar.Tip", "Tip 10"),
        ]

        # Mostrar primeira dica
        self._update_tip()

        right_widget = QWidget()
        right_layout = QHBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(Spacing.SM)  # Better spacing between buttons

        # Add select file button
        self.select_file_button = self._create_text_button(
            tr("CustomTitleBar", "ZIP"),
            getattr(parent, "_select_zip_file", lambda: None),
            tr("CustomTitleBar", "Select ZIP File"),
        )
        right_layout.addWidget(self.select_file_button)

        # Add game manager button
        self.game_manager_button = self._create_text_button(
            tr("CustomTitleBar", "UN"),
            getattr(parent, "_open_game_manager", lambda: None),
            tr("CustomTitleBar", "Uninstall Games"),
        )
        right_layout.addWidget(self.game_manager_button)

        # Add backup button
        self.backup_button = self._create_text_button(
            tr("CustomTitleBar", "BK"),
            getattr(parent, "_open_backup_dialog", lambda: None),
            tr("CustomTitleBar", "Backup/Restore Stats"),
        )
        right_layout.addWidget(self.backup_button)

        self.settings_button = self._create_svg_button(
            GEAR_SVG,
            getattr(parent, "open_settings", lambda: None),
            tr("CustomTitleBar", "Open Settings"),
        )
        right_layout.addWidget(self.settings_button)

        # Main layout assembly
        layout.addWidget(left_widget)
        layout.addStretch(1)
        layout.addWidget(self.tip_widget)  # Adicionar a caixa de dicas no centro
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

    def mousePressEvent(self, a0):
        """
        Captures initial mouse press event to start dragging window.
        """
        if a0 and hasattr(a0, "button") and a0.button() == Qt.MouseButton.LeftButton:
            if hasattr(self.parent, "frameGeometry"):
                try:
                    self.drag_pos = (
                        a0.globalPosition().toPoint()
                        - self.parent.frameGeometry().topLeft()  # type: ignore[attr-defined]
                    )
                except (AttributeError, TypeError):
                    pass
            a0.accept()

    def mouseMoveEvent(self, a0):
        """
        Moves window as mouse is dragged.
        """
        if (
            a0
            and hasattr(a0, "buttons")
            and a0.buttons() == Qt.MouseButton.LeftButton
            and self.drag_pos
        ):
            if hasattr(self.parent, "move"):
                try:
                    self.parent.move(a0.globalPosition().toPoint() - self.drag_pos)  # type: ignore[attr-defined]
                except (AttributeError, TypeError):
                    pass
            a0.accept()

    def mouseReleaseEvent(self, a0):
        """
        Resets drag position when mouse button is released.
        """
        self.drag_pos = None
        if a0:
            a0.accept()

    def _update_tip(self):
        """Atualiza a dica exibida no centro da barra de título"""
        if hasattr(self, 'tip_label') and hasattr(self, 'bifrost_tips'):
            self.tip_label.setText(self.bifrost_tips[self.current_tip_index])
            self.current_tip_index = (self.current_tip_index + 1) % len(self.bifrost_tips)

    def _create_svg_button(self, svg_data, on_click, tooltip):
        """
        Helper method to create a button from SVG data, recoloring the icon without distortion.
        """
        try:

            class SvgButton(QPushButton):
                def __init__(self, svg_data, icon_size):
                    super().__init__()
                    self.svg_data = svg_data
                    self.icon_size = icon_size

                def update_icon(self, color):
                    """Update icon with specified color"""
                    renderer = QSvgRenderer(self.svg_data.encode("utf-8"))
                    pixmap = QPixmap(self.icon_size)
                    pixmap.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(pixmap)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    renderer.render(painter)
                    painter.setCompositionMode(
                        QPainter.CompositionMode.CompositionMode_SourceIn
                    )
                    painter.fillRect(pixmap.rect(), QColor(color))
                    painter.end()
                    self.setIcon(QIcon(pixmap))
                    self.setIconSize(self.icon_size)

                def enterEvent(self, event):
                    from .theme import theme

                    self.update_icon(theme.colors.TEXT_ON_PRIMARY)
                    super().enterEvent(event)

                def leaveEvent(self, a0):
                    from .theme import theme

                    self.update_icon(theme.colors.TEXT_ACCENT)
                    super().leaveEvent(a0)

            button = SvgButton(svg_data, QSize(18, 18))
            button.setToolTip(tooltip)

            from .theme import theme

            # Set initial icon
            button.update_icon(theme.colors.TEXT_ACCENT)

            button.setFixedSize(22, 22)  # Larger buttons for increased title bar

            button.setStyleSheet(f"""
                QPushButton {{
                    border: 1px solid {theme.colors.PRIMARY};
                    {BorderRadius.get_border_radius(BorderRadius.SMALL)};
                    background: {theme.colors.BACKGROUND};
                }}
                QPushButton:hover {{
                    background: {theme.colors.SURFACE_DARK};
                    border: 1px solid {theme.colors.PRIMARY};
                }}
                QPushButton:pressed {{
                    background: {theme.colors.SURFACE_DARK};
                    border: 1px solid {theme.colors.PRIMARY_DARK};
                }}
            """)

            button.clicked.connect(on_click)
            return button
        except Exception as e:
            logger.error(f"Failed to create SVG button: {e}", exc_info=True)
            fallback_button = QPushButton(tr("CustomTitleBar", "✕"))
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
            button.setFixedSize(22, 22)  # Larger buttons for increased title bar
            from .theme import theme

            button.setStyleSheet(f"""
                QPushButton {{
                    border: 1px solid {theme.colors.PRIMARY};
                    border-radius: {BorderRadius.SMALL}px;
                    color: {theme.colors.TEXT_ACCENT};
                    {Typography.get_font_style(Typography.CAPTION_SIZE)};
                    font-weight: bold;
                    background: {theme.colors.BACKGROUND};
                }}
                QPushButton:hover {{
                    background: {theme.colors.SURFACE_DARK};
                    color: {theme.colors.TEXT_ON_PRIMARY};
                    border: 1px solid {theme.colors.PRIMARY};
                }}
                QPushButton:pressed {{
                    background: {theme.colors.SURFACE_DARK};
                    border: 1px solid {theme.colors.PRIMARY_DARK};
                }}
            """)
            button.clicked.connect(on_click)
            return button
        except Exception as e:
            logger.error(f"Failed to create text button: {e}", exc_info=True)
            fallback_button = QPushButton(tr("CustomTitleBar", "?"))
            fallback_button.setFixedSize(22, 22)
            fallback_button.clicked.connect(on_click)
            return fallback_button
