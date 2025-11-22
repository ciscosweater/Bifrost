"""
Info Card - Minimalist information cards for Bifrost main window
Provides clean, modern cards for displaying Bifrost info and game statistics
"""

from utils.logger import get_internationalized_logger

import logging

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.theme import BorderRadius, Colors, Spacing, Typography

# Import i18n
try:
    from utils.i18n import tr
except (ImportError, ModuleNotFoundError):

    def tr(context, text):
        return text


logger = get_internationalized_logger()


class InfoCard(QFrame):
    """Minimalist info card with hover effects"""

    def __init__(
        self,
        title: str,
        value: str,
        icon_text: str = "",
        color: str = Colors.PRIMARY,
        parent=None,
    ):
        super().__init__(parent)
        self.title = title
        self.value = value
        self.icon_text = icon_text
        self.color = color

        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        """Setup card layout"""
        self.setMinimumHeight(80)
        self.setMaximumHeight(80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        layout.setSpacing(Spacing.XS)

        # Top row with title only
        top_layout = QHBoxLayout()
        top_layout.setSpacing(Spacing.XS)

        # Title
        self.title_label = QLabel(self.title)
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_ACCENT};
                background: transparent;
                border: none;
                font-family: {Typography.get_font_family()};
                {Typography.get_font_style(Typography.H2_SIZE, Typography.WEIGHT_BOLD)};
            }}
        """)
        top_layout.addWidget(self.title_label)
        top_layout.addStretch()

        layout.addLayout(top_layout)

        # Value
        self.value_label = QLabel(self.value)
        self.value_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.value_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                background: transparent;
                border: none;
                font-family: {Typography.get_font_family()};
                {Typography.get_font_style(Typography.H1_SIZE, Typography.WEIGHT_NORMAL)};
            }}
        """)
        layout.addWidget(self.value_label)

        layout.addStretch()

    def _apply_style(self):
        """Apply minimalist card style"""
        self.setStyleSheet(f"""
            QFrame {{
                background: {Colors.BACKGROUND};
                border: 1px solid {Colors.PRIMARY};
                {BorderRadius.get_border_radius(BorderRadius.MEDIUM)};
            }}
            QFrame:hover {{
                background: {Colors.SURFACE_DARK};
            }}
        """)

    def update_value(self, new_value: str):
        """Update card value"""
        self.value = new_value
        self.value_label.setText(new_value)


class BifrostInfoCard(InfoCard):
    """Card showing Bifrost information"""

    def __init__(self):
        super().__init__(
            title=tr("InfoCards", "Bifrost"),
            value="v1.1.1",
            icon_text="",
            color=Colors.PRIMARY,
        )


class GamesStatsCard(InfoCard):
    """Card showing installed games statistics"""

    def __init__(self):
        super().__init__(
            title=tr("InfoCards", "Games"),
            value=(f"0 {tr('InfoCards', 'installed')}"),
            icon_text="[G]",
            color=Colors.SUCCESS,
        )

        self._setup_stats_timer()

    def _setup_stats_timer(self):
        """Setup periodic stats update"""
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._update_stats)
        self.stats_timer.start(10000)  # Update every 10 seconds

        # Initial update
        QTimer.singleShot(2000, self._update_stats)

    def _update_stats(self, force_refresh: bool = False):
        """Update games statistics"""
        try:
            # Try to get Bifrost games count
            from core.game_manager import GameManager

            games = GameManager.scan_bifrost_games(force_refresh=force_refresh)
            count = len(games) if games else 0

            if count > 0:
                self.update_value(f"{count} {tr('InfoCards', 'installed')}")
            else:
                self.update_value(f"0 {tr('InfoCards', 'installed')}")

        except Exception as e:
            logger.debug(f"Could not update games stats: {e}")
            self.update_value("?")


class StorageCard(InfoCard):
    """Card showing storage information"""

    def __init__(self):
        super().__init__(
            title=tr("InfoCards", "Storage"),
            value="0 GB",
            icon_text="",
            color=Colors.SECONDARY,
        )

        self._setup_storage_timer()

    def _setup_storage_timer(self):
        """Setup periodic storage update"""
        self.storage_timer = QTimer()
        self.storage_timer.timeout.connect(self._update_storage)
        self.storage_timer.start(15000)  # Update every 15 seconds

        # Initial update
        QTimer.singleShot(2000, self._update_storage)

    def _update_storage(self, force_refresh: bool = False):
        """Update storage information"""
        try:
            import os

            from core.game_manager import GameManager

            # Try to get Steam libraries and calculate Bifrost games size
            from core.steam_helpers import get_steam_libraries

            libraries = get_steam_libraries()
            games = GameManager.scan_bifrost_games(force_refresh=force_refresh)

            if not libraries or not games:
                self.update_value("N/A")
                return

            total_size = 0
            for library in libraries:
                for game in games:
                    game_path = os.path.join(
                        library, "steamapps", "common", game.get("installdir", "")
                    )
                    if os.path.exists(game_path):
                        try:
                            for root, dirs, files in os.walk(game_path):
                                total_size += sum(
                                    os.path.getsize(os.path.join(root, file))
                                    for file in files
                                )
                        except (OSError, PermissionError):
                            continue

            # Convert to GB
            size_gb = total_size / (1024**3)
            if size_gb < 1:
                self.update_value(f"{size_gb * 1024:.1f} MB")
            else:
                self.update_value(f"{size_gb:.1f} GB")

        except Exception as e:
            logger.debug(f"Could not update storage info: {e}")
            self.update_value("N/A")


class StatusCard(InfoCard):
    """Card showing Bifrost status"""

    def __init__(self):
        super().__init__(
            title=tr("InfoCards", "Achievements"),
            value=tr("InfoCards", "Ready"),
            icon_text="",
            color=Colors.SUCCESS,
        )

        self._setup_status_timer()

    def _setup_status_timer(self):
        """Setup periodic status update"""
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(8000)  # Update every 8 seconds

        # Initial update
        QTimer.singleShot(4000, self._update_status)

    def _update_status(self):
        """Update Bifrost status"""
        try:
            import os

            # Check if saved_logins.encrypted exists for achievements
            slscheevo_data_path = os.path.join(
                os.getcwd(), "slscheevo_build", "data", "saved_logins.encrypted"
            )

            if os.path.exists(slscheevo_data_path):
                self.update_value(tr("InfoCards", "Ready"))
                self.color = Colors.SUCCESS
            else:
                self.update_value(tr("InfoCards", "Not Ready"))
                self.color = Colors.WARNING

        except Exception as e:
            logger.debug(f"Could not update status: {e}")
            self.update_value("Unknown")


class InfoCardsContainer(QWidget):
    """Container for info cards with responsive layout"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cards = []
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._setup_ui()
        self._create_cards()

    def _setup_ui(self):
        """Setup container layout"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(Spacing.SM)

        # Cards container
        self.cards_widget = QWidget()
        self.cards_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.cards_layout = QVBoxLayout(self.cards_widget)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(Spacing.SM)

        self.main_layout.addWidget(self.cards_widget)

    def _create_cards(self):
        """Create info cards"""
        # Bifrost info card
        self.bifrost_card = BifrostInfoCard()
        self.cards_layout.addWidget(self.bifrost_card)
        self.cards.append(self.bifrost_card)

        # Games stats card
        self.games_card = GamesStatsCard()
        self.cards_layout.addWidget(self.games_card)
        self.cards.append(self.games_card)

        # Storage card
        self.storage_card = StorageCard()
        self.cards_layout.addWidget(self.storage_card)
        self.cards.append(self.storage_card)

        # Status card
        self.status_card = StatusCard()
        self.cards_layout.addWidget(self.status_card)
        self.cards.append(self.status_card)

    def set_visible(self, visible: bool):
        """Show/hide all cards"""
        self.setVisible(visible)
        for card in self.cards:
            card.setVisible(visible)

    def refresh_all(self):
        """Force refresh all cards"""
        for card in self.cards:
            if hasattr(card, "_update_stats"):
                card._update_stats()
            elif hasattr(card, "_update_storage"):
                card._update_storage()
            elif hasattr(card, "_update_status"):
                card._update_status()
            elif hasattr(card, "_update_version_info"):
                card._update_version_info()
