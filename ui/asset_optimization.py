"""
Asset optimization and lazy loading system for ACCELA application
Provides efficient asset management and loading strategies
"""

import os
import threading
from typing import Dict, Optional, Callable
from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject
from PyQt6.QtGui import QPixmap, QImage, QMovie
from .theme import theme, BorderRadius


class AssetCache:
    """
    Thread-safe asset cache for efficient resource management
    """
    
    def __init__(self, max_size=100):
        self._cache: Dict[str, any] = {}
        self._max_size = max_size
        self._access_order = []
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[any]:
        """Get asset from cache"""
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                self._access_order.remove(key)
                self._access_order.append(key)
                return self._cache[key]
            return None
    
    def put(self, key: str, value: any) -> None:
        """Put asset in cache"""
        with self._lock:
            if key in self._cache:
                # Update existing
                self._cache[key] = value
                self._access_order.remove(key)
                self._access_order.append(key)
            else:
                # Add new
                if len(self._cache) >= self._max_size:
                    # Remove least recently used
                    oldest = self._access_order.pop(0)
                    del self._cache[oldest]
                
                self._cache[key] = value
                self._access_order.append(key)
    
    def clear(self) -> None:
        """Clear cache"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    def size(self) -> int:
        """Get cache size"""
        with self._lock:
            return len(self._cache)


class AssetLoader(QThread):
    """
    Background thread for loading assets
    """
    
    asset_loaded = pyqtSignal(str, object)
    asset_failed = pyqtSignal(str, str)
    
    def __init__(self, asset_path: str, asset_type: str = "image"):
        super().__init__()
        self.asset_path = asset_path
        self.asset_type = asset_type
        self._should_stop = False
    
    def run(self):
        """Load asset in background"""
        try:
            if self._should_stop:
                return
            
            if self.asset_type == "image":
                asset = self._load_image()
            elif self.asset_type == "movie":
                asset = self._load_movie()
            else:
                asset = self._load_generic()
            
            if not self._should_stop:
                self.asset_loaded.emit(self.asset_path, asset)
                
        except Exception as e:
            if not self._should_stop:
                self.asset_failed.emit(self.asset_path, str(e))
    
    def _load_image(self):
        """Load image asset"""
        if os.path.exists(self.asset_path):
            pixmap = QPixmap(self.asset_path)
            if not pixmap.isNull():
                return pixmap
        raise FileNotFoundError(f"Image not found: {self.asset_path}")
    
    def _load_movie(self):
        """Load movie/GIF asset"""
        if os.path.exists(self.asset_path):
            movie = QMovie(self.asset_path)
            if movie.isValid():
                return movie
        raise FileNotFoundError(f"Movie not found: {self.asset_path}")
    
    def _load_generic(self):
        """Load generic asset"""
        if os.path.exists(self.asset_path):
            return self.asset_path
        raise FileNotFoundError(f"Asset not found: {self.asset_path}")
    
    def stop(self):
        """Stop loading"""
        self._should_stop = True


class LazyImageLabel(QLabel):
    """
    Image label with lazy loading and caching
    """
    
    loading_started = pyqtSignal(str)
    loading_finished = pyqtSignal(str)
    loading_failed = pyqtSignal(str, str)
    
    def __init__(self, placeholder_text="Loading...", parent=None):
        super().__init__(parent)
        self.placeholder_text = placeholder_text
        self.current_loader = None
        self.asset_cache = AssetCache()
        
        self._setup_placeholder()
        self._setup_style()
    
    def _setup_placeholder(self):
        """Setup placeholder appearance"""
        self.setText(self.placeholder_text)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"""
            QLabel {{
                background: {theme.colors.SURFACE};
                border: 1px dashed {theme.colors.BORDER};
                color: {theme.colors.TEXT_SECONDARY};
                border-radius: {BorderRadius.SMALL}px;
                padding: 16px;
            }}
        """)
    
    def _setup_style(self):
        """Setup final style"""
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(64, 64)
    
    def load_image(self, image_path: str, use_cache: bool = True) -> None:
        """Load image with lazy loading"""
        # Check cache first
        if use_cache:
            cached = self.asset_cache.get(image_path)
            if cached:
                self.setPixmap(cached)
                self.loading_finished.emit(image_path)
                return
        
        # Stop current loading
        if self.current_loader:
            self.current_loader.stop()
            self.current_loader.wait()
        
        # Start new loading
        self.current_loader = AssetLoader(image_path, "image")
        self.current_loader.asset_loaded.connect(self._on_image_loaded)
        self.current_loader.asset_failed.connect(self._on_loading_failed)
        
        self.loading_started.emit(image_path)
        self.current_loader.start()
    
    def _on_image_loaded(self, path: str, pixmap: QPixmap) -> None:
        """Handle successful image loading"""
        if pixmap and not pixmap.isNull():
            # Cache the loaded image
            self.asset_cache.put(path, pixmap)
            
            # Scale pixmap to fit label while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(
                self.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            
            self.setPixmap(scaled_pixmap)
            self.setStyleSheet("")  # Remove placeholder style
            self.loading_finished.emit(path)
    
    def _on_loading_failed(self, path: str, error: str) -> None:
        """Handle loading failure"""
        self.setText(f"Failed to load\n{os.path.basename(path)}")
        self.setStyleSheet(f"""
            QLabel {{
                background: {theme.colors.ERROR}20;
                border: 1px solid {theme.colors.ERROR};
                color: {theme.colors.ERROR};
                border-radius: {BorderRadius.SMALL}px;
                padding: 16px;
            }}
        """)
        self.loading_failed.emit(path, error)
    
    def resizeEvent(self, event):
        """Handle resize to maintain aspect ratio"""
        super().resizeEvent(event)
        if self.pixmap():
            # Rescale pixmap to new size
            scaled_pixmap = self.pixmap().scaled(
                self.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.setPixmap(scaled_pixmap)


class OptimizedGifWidget(QWidget):
    """
    Optimized GIF widget with lazy loading and performance optimization
    """
    
    def __init__(self, gif_path: str = None, parent=None):
        super().__init__(parent)
        self.gif_path = gif_path
        self.movie = None
        self.is_playing = False
        self.asset_cache = AssetCache()
        
        self._setup_widget()
        
        if gif_path:
            self.load_gif(gif_path)
    
    def _setup_widget(self):
        """Setup widget properties"""
        self.setMinimumSize(32, 32)
        self.setStyleSheet(f"""
            QWidget {{
                background: transparent;
            }}
        """)
    
    def load_gif(self, gif_path: str, use_cache: bool = True) -> None:
        """Load GIF with optimization"""
        # Check cache first
        if use_cache:
            cached = self.asset_cache.get(gif_path)
            if cached:
                self.movie = cached
                self._setup_movie()
                return
        
        # Load and optimize GIF
        try:
            movie = QMovie(gif_path)
            if movie.isValid():
                # Optimize GIF settings
                movie.setSpeed(100)  # Normal speed
                
                # Cache the movie
                self.asset_cache.put(gif_path, movie)
                
                self.gif_path = gif_path
                self.movie = movie
                self._setup_movie()
                
        except Exception as e:
            print(f"Failed to load GIF: {e}")
    
    def _setup_movie(self):
        """Setup movie for playback"""
        if self.movie:
            self.movie.setCacheMode(QMovie.CacheMode.CacheAll)
            label = QLabel(self)
            label.setMovie(self.movie)
            label.setGeometry(self.rect())
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    def start(self) -> None:
        """Start GIF playback"""
        if self.movie and not self.is_playing:
            self.movie.start()
            self.is_playing = True
    
    def stop(self) -> None:
        """Stop GIF playback"""
        if self.movie and self.is_playing:
            self.movie.stop()
            self.is_playing = False
    
    def set_paused(self, paused: bool) -> None:
        """Pause/resume GIF playback"""
        if self.movie:
            if paused and self.is_playing:
                self.movie.setPaused(True)
            elif not paused and self.is_playing:
                self.movie.setPaused(False)


class AssetManager:
    """
    Centralized asset management system
    """
    
    def __init__(self):
        self.image_cache = AssetCache(max_size=50)
        self.gif_cache = AssetCache(max_size=20)
        self.loading_threads = []
        
    def preload_assets(self, asset_paths: list, asset_type: str = "image") -> None:
        """Preload assets in background"""
        for path in asset_paths:
            if os.path.exists(path):
                loader = AssetLoader(path, asset_type)
                loader.asset_loaded.connect(
                    lambda p, asset: self._cache_asset(p, asset, asset_type)
                )
                self.loading_threads.append(loader)
                loader.start()
    
    def _cache_asset(self, path: str, asset: any, asset_type: str) -> None:
        """Cache loaded asset"""
        if asset_type == "image":
            self.image_cache.put(path, asset)
        elif asset_type == "movie":
            self.gif_cache.put(path, asset)
    
    def get_cached_image(self, path: str) -> Optional[QPixmap]:
        """Get cached image"""
        return self.image_cache.get(path)
    
    def get_cached_gif(self, path: str) -> Optional[QMovie]:
        """Get cached GIF"""
        return self.gif_cache.get(path)
    
    def clear_cache(self) -> None:
        """Clear all caches"""
        self.image_cache.clear()
        self.gif_cache.clear()
    
    def stop_all_loading(self) -> None:
        """Stop all background loading"""
        for thread in self.loading_threads:
            if thread.isRunning():
                thread.stop()
                thread.wait()
        self.loading_threads.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            'images': self.image_cache.size(),
            'gifs': self.gif_cache.size(),
            'total_threads': len(self.loading_threads)
        }


class AssetOptimizer:
    """
    Asset optimization utilities
    """
    
    @staticmethod
    def optimize_image_size(pixmap: QPixmap, max_width: int = 800, max_height: int = 600) -> QPixmap:
        """Optimize image size for performance"""
        if pixmap.width() > max_width or pixmap.height() > max_height:
            return pixmap.scaled(
                max_width, max_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        return pixmap
    
    @staticmethod
    def create_thumbnail(pixmap: QPixmap, size: int = 64) -> QPixmap:
        """Create thumbnail from image"""
        return pixmap.scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
    
    @staticmethod
    def is_asset_optimized(asset_path: str) -> bool:
        """Check if asset needs optimization"""
        if not os.path.exists(asset_path):
            return False
        
        # Check file size (1MB threshold for images)
        size_mb = os.path.getsize(asset_path) / (1024 * 1024)
        return size_mb <= 1.0


# Global asset manager instance
asset_manager = AssetManager()