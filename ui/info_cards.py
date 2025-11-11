"""
Info Card - Minimalist information cards for ACCELA main window
Provides clean, modern cards for displaying ACCELA info and game statistics
"""

import logging
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont

from ui.theme import theme, Colors, Typography, Spacing, BorderRadius

logger = logging.getLogger(__name__)


class InfoCard(QFrame):
    """Minimalist info card with hover effects"""
    
    def __init__(self, title: str, value: str, icon_text: str = "📊", 
                 color: str = Colors.PRIMARY, parent=None):
        super().__init__(parent)
        self.title = title
        self.value = value
        self.icon_text = icon_text
        self.color = color
        
        self._setup_ui()
        self._apply_style()
    
    def _setup_ui(self):
        """Setup card layout"""
        self.setFixedSize(180, 80)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM)
        layout.setSpacing(Spacing.XS)
        
        # Top row with icon and title
        top_layout = QHBoxLayout()
        top_layout.setSpacing(Spacing.XS)
        
        # Icon
        self.icon_label = QLabel(self.icon_text)
        self.icon_label.setStyleSheet(f"""
            QLabel {{
                font-size: 20px;
                color: {self.color};
                background: transparent;
                border: none;
            }}
        """)
        top_layout.addWidget(self.icon_label)
        
        # Title
        self.title_label = QLabel(self.title)
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_SECONDARY};
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
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
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
                background: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                {BorderRadius.get_border_radius(BorderRadius.MEDIUM)};
            }}
            QFrame:hover {{
                background: {Colors.SURFACE_LIGHT};
                border: 1px solid {self.color};
            }}
        """)
    
    def update_value(self, new_value: str):
        """Update card value"""
        self.value = new_value
        self.value_label.setText(new_value)


class AccelaInfoCard(InfoCard):
    """Card showing ACCELA information"""
    
    def __init__(self):
        super().__init__(
            title="ACCELA",
            value="v1.1.0",
            icon_text="🚀",
            color=Colors.PRIMARY
        )
        
        # Add version info animation
        self._setup_version_animation()
    
    def _setup_version_animation(self):
        """Setup subtle version info animation"""
        self.version_timer = QTimer()
        self.version_timer.timeout.connect(self._update_version_info)
        self.version_timer.start(5000)  # Update every 5 seconds
        
        self.info_index = 0
        self.info_items = [
            ("v1.1.0", "🚀"),
            ("SLSsteam", "⚙️"),
            ("Fast Downloads", "⚡"),
            ("Game Manager", "🎮")
        ]
    
    def _update_version_info(self):
        """Cycle through ACCELA info"""
        self.info_index = (self.info_index + 1) % len(self.info_items)
        value, icon = self.info_items[self.info_index]
        
        self.update_value(value)
        self.icon_label.setText(icon)


class GamesStatsCard(InfoCard):
    """Card showing installed games statistics"""
    
    def __init__(self):
        super().__init__(
            title="Games",
            value="0",
            icon_text="🎮",
            color=Colors.SUCCESS
        )
        
        self._setup_stats_timer()
    
    def _setup_stats_timer(self):
        """Setup periodic stats update"""
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._update_stats)
        self.stats_timer.start(10000)  # Update every 10 seconds
        
        # Initial update
        QTimer.singleShot(2000, self._update_stats)
    
    def _update_stats(self):
        """Update games statistics"""
        try:
            # Try to get ACCELA games count
            from core.game_manager import GameManager
            games = GameManager.scan_accela_games()
            count = len(games) if games else 0
            
            if count > 0:
                self.update_value(str(count))
                self.icon_label.setText("🎯")
            else:
                self.update_value("0")
                self.icon_label.setText("🎮")
                
        except Exception as e:
            logger.debug(f"Could not update games stats: {e}")
            self.update_value("?")
            self.icon_label.setText("📊")


class StorageCard(InfoCard):
    """Card showing storage information"""
    
    def __init__(self):
        super().__init__(
            title="Storage",
            value="0 GB",
            icon_text="💾",
            color=Colors.SECONDARY
        )
        
        self._setup_storage_timer()
    
    def _setup_storage_timer(self):
        """Setup periodic storage update"""
        self.storage_timer = QTimer()
        self.storage_timer.timeout.connect(self._update_storage)
        self.storage_timer.start(15000)  # Update every 15 seconds
        
        # Initial update
        QTimer.singleShot(2000, self._update_storage)
    
    def _update_storage(self):
        """Update storage information"""
        try:
            import os
            
            # Try to get Steam libraries and calculate ACCELA games size
            from core.steam_helpers import get_steam_libraries
            from core.game_manager import GameManager
            libraries = get_steam_libraries()
            games = GameManager.scan_accela_games()
            
            if not libraries or not games:
                self.update_value("N/A")
                return
            
            total_size = 0
            for library in libraries:
                for game in games:
                    game_path = os.path.join(library, "steamapps", "common", game.get('installdir', ''))
                    if os.path.exists(game_path):
                        try:
                            for root, dirs, files in os.walk(game_path):
                                total_size += sum(os.path.getsize(os.path.join(root, file)) for file in files)
                        except (OSError, PermissionError):
                            continue
            
            # Convert to GB
            size_gb = total_size / (1024 ** 3)
            if size_gb < 1:
                self.update_value(f"{size_gb * 1024:.1f} MB")
            else:
                self.update_value(f"{size_gb:.1f} GB")
                
        except Exception as e:
            logger.debug(f"Could not update storage info: {e}")
            self.update_value("N/A")


class StatusCard(InfoCard):
    """Card showing ACCELA status"""
    
    def __init__(self):
        super().__init__(
            title="Status",
            value="Ready",
            icon_text="✅",
            color=Colors.SUCCESS
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
        """Update ACCELA status"""
        try:
            from utils.settings import get_settings
            settings = get_settings()
            
            # Check SLSsteam status
            slssteam_mode = settings.value("slssteam_mode", False, type=bool)
            
            if slssteam_mode:
                self.update_value("SLSsteam")
                self.icon_label.setText("🔧")
                self.color = Colors.WARNING
            else:
                self.update_value("Ready")
                self.icon_text = "✅"
                self.color = Colors.SUCCESS
            
            # Update icon color
            self.icon_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 20px;
                    color: {self.color};
                    background: transparent;
                    border: none;
                }}
            """)
            
        except Exception as e:
            logger.debug(f"Could not update status: {e}")
            self.update_value("Unknown")
            self.icon_label.setText("❓")


class InfoCardsContainer(QWidget):
    """Container for info cards with responsive layout"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cards = []
        self._setup_ui()
        self._create_cards()
    
    def _setup_ui(self):
        """Setup container layout"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(Spacing.SM)
        
        # Cards container
        self.cards_widget = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_widget)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(Spacing.SM)
        
        self.main_layout.addWidget(self.cards_widget)
        self.main_layout.addStretch()
    
    def _create_cards(self):
        """Create info cards"""
        # ACCELA info card
        self.accela_card = AccelaInfoCard()
        self.cards_layout.addWidget(self.accela_card)
        self.cards.append(self.accela_card)
        
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
            if hasattr(card, '_update_stats'):
                card._update_stats()
            elif hasattr(card, '_update_storage'):
                card._update_storage()
            elif hasattr(card, '_update_status'):
                card._update_status()
            elif hasattr(card, '_update_version_info'):
                card._update_version_info()