import logging
import urllib.request
from PyQt6.QtCore import QThread, pyqtSignal, QObject, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

logger = logging.getLogger(__name__)

class GameImageDisplay(QObject):
    """
    Component to display game header image and info during download.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.game_header_image = None
        
    def setup_game_image_area(self, main_layout):
        """Create and setup the game image display area."""
        
        # Game header image area (initially hidden)
        self.game_image_container = QFrame()
        self.game_image_container.setVisible(False)
        self.game_image_container.setStyleSheet("""
            QFrame {
                background: rgba(30, 30, 30, 0.95);
                border: 1px solid #C06C84;
                margin: 5px;
                padding: 5px;
            }
        """)
        game_image_layout = QHBoxLayout(self.game_image_container)
        game_image_layout.setContentsMargins(10, 10, 10, 10)
        
        self.game_header_label = QLabel()
        self.game_header_label.setMinimumSize(184, 69)  # Steam header image aspect ratio
        self.game_header_label.setMaximumSize(184, 69)
        self.game_header_label.setStyleSheet("""
            QLabel {
                border: 1px solid #C06C84;
                background: #1E1E1E;
            }
        """)
        game_image_layout.addWidget(self.game_header_label)
        
        # Game info next to image
        game_info_layout = QVBoxLayout()
        game_info_layout.setSpacing(5)
        
        self.game_title_label = QLabel("Game Title")
        self.game_title_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #C06C84;
                border: none;
            }
        """)
        game_info_layout.addWidget(self.game_title_label)
        
        self.game_status_label = QLabel("Downloading...")
        self.game_status_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #808080;
                border: none;
            }
        """)
        game_info_layout.addWidget(self.game_status_label)
        
        game_info_layout.addStretch()
        game_image_layout.addLayout(game_info_layout)
        
        main_layout.addWidget(self.game_image_container)
        
        return self.game_image_container
        
    def show_game_info(self, game_data):
        """Show game information area with header image."""
        if game_data:
            # Set game title
            game_name = game_data.get('game_name', 'Unknown Game')
            self.game_title_label.setText(game_name)
            
            # Show the game image container
            self.game_image_container.setVisible(True)
            
            # Fetch header image
            app_id = game_data.get('appid')
            if app_id:
                self._fetch_game_header_image(app_id)
                
    def hide_game_info(self):
        """Hide game information area."""
        self.game_image_container.setVisible(False)
        self.game_header_image = None
        
    def update_download_status(self, status):
        """Update the download status text."""
        self.game_status_label.setText(status)
        
    def _fetch_game_header_image(self, app_id):
        """Fetch game header image for display during download."""
        url = f"https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg"
        
        self.image_thread = QThread()
        self.image_fetcher = ImageFetcher(url)
        self.image_fetcher.moveToThread(self.image_thread)
        
        self.image_thread.started.connect(self.image_fetcher.run)
        self.image_fetcher.finished.connect(self.on_game_image_fetched)
        
        self.image_fetcher.finished.connect(self.image_thread.quit)
        self.image_fetcher.finished.connect(self.image_fetcher.deleteLater)
        self.image_thread.finished.connect(self.image_thread.deleteLater)
        
        self.image_thread.start()

    def on_game_image_fetched(self, image_data):
        """Handle fetched game header image."""
        if image_data:
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            self.game_header_image = pixmap
            self.game_header_label.setPixmap(pixmap.scaled(
                184, 69, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            self.game_header_label.setText("[IMAGE]\nNo Image")

class ImageFetcher(QObject):
    finished = pyqtSignal(bytes)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            with urllib.request.urlopen(self.url) as response:
                data = response.read()
                self.finished.emit(data)
        except Exception as e:
            logger.warning(f"Failed to fetch header image from {self.url}: {e}")
            self.finished.emit(b'')