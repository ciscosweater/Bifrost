import hashlib
import logging
import os

from PyQt6.QtCore import QObject, Qt, QTimer
from PyQt6.QtGui import QMovie, QPixmap
from PyQt6.QtWidgets import QLabel

logger = logging.getLogger(__name__)


class AssetManager(QObject):
    """
    Asset optimization and caching system for improved performance.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cache = {}
        self._cache_dir = "cache"
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """Create cache directory if it doesn't exist."""
        if not os.path.exists(self._cache_dir):
            os.makedirs(self._cache_dir)

    def get_optimized_pixmap(self, file_path, size=None):
        """Get cached or create optimized pixmap."""
        cache_key = self._get_cache_key(file_path, size)

        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            pixmap = QPixmap(file_path)
            if size and not pixmap.isNull():
                pixmap = pixmap.scaled(
                    size.width(),
                    size.height(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

            self._cache[cache_key] = pixmap
            return pixmap
        except Exception as e:
            logger.warning(f"Failed to load pixmap {file_path}: {e}")
            return QPixmap()

    def get_optimized_movie(self, file_path, size=None):
        """Get cached or create optimized movie."""
        cache_key = self._get_cache_key(file_path, size)

        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            movie = QMovie(file_path)
            if size:
                movie.setScaledSize(size)

            self._cache[cache_key] = movie
            return movie
        except Exception as e:
            logger.warning(f"Failed to load movie {file_path}: {e}")
            return QMovie()

    def _get_cache_key(self, file_path, size=None):
        """Generate cache key for asset."""
        key = file_path
        if size:
            key += f"_{size.width()}x{size.height()}"
        return hashlib.md5(key.encode()).hexdigest()

    def preload_assets(self, asset_list):
        """Preload commonly used assets."""
        for asset_path in asset_list:
            if os.path.exists(asset_path):
                if asset_path.endswith(".gif"):
                    self.get_optimized_movie(asset_path)
                else:
                    self.get_optimized_pixmap(asset_path)

    def clear_cache(self):
        """Clear asset cache."""
        self._cache.clear()
        logger.info("Asset cache cleared")


class OptimizedLabel(QLabel):
    """
    Label with built-in asset optimization and lazy loading.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.asset_manager = AssetManager(self)
        self._current_size = None
        self._lazy_load_timer = QTimer()
        self._lazy_load_timer.setSingleShot(True)
        self._lazy_load_timer.timeout.connect(self._load_asset)
        self._pending_asset = None
        self._asset_path = None

    def setOptimizedPixmap(self, file_path, size=None):
        """Set optimized pixmap with lazy loading."""
        self._pending_asset = (file_path, size, "pixmap")
        self._lazy_load_timer.start(100)  # 100ms delay for lazy loading

    def setOptimizedMovie(self, file_path, size=None):
        """Set optimized movie with lazy loading."""
        self._pending_asset = (file_path, size, "movie")
        self._lazy_load_timer.start(100)

    def _load_asset(self):
        """Load pending asset."""
        if not self._pending_asset:
            return

        file_path, size, asset_type = self._pending_asset

        if asset_type == "pixmap":
            pixmap = self.asset_manager.get_optimized_pixmap(file_path, size)
            self.setPixmap(pixmap)
        elif asset_type == "movie":
            movie = self.asset_manager.get_optimized_movie(file_path, size)
            self.setMovie(movie)
            movie.start()

        self._pending_asset = None

    def resizeEvent(self, a0):
        """Handle resize with asset optimization."""
        super().resizeEvent(a0)
        new_size = self.size()

        if self._current_size != new_size:
            self._current_size = new_size
            # Reload asset with new size if needed
            if hasattr(self, "_asset_path") and self._asset_path:
                self._reload_asset()

    def _reload_asset(self):
        """Reload current asset with new size."""
        if self._asset_path:
            self.setOptimizedPixmap(self._asset_path, self._current_size)


class ResponsiveWidget(QObject):
    """
    Mixin for responsive design capabilities.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._breakpoints = {"small": 600, "medium": 900, "large": 1200}
        self._current_size_class = "medium"

    def get_size_class(self, width):
        """Determine size class based on width."""
        if width < self._breakpoints["small"]:
            return "small"
        elif width < self._breakpoints["medium"]:
            return "medium"
        elif width < self._breakpoints["large"]:
            return "large"
        else:
            return "xlarge"

    def apply_responsive_style(self, size_class):
        """Apply styles based on size class. Override in subclasses."""
        pass

    def update_responsive(self, width):
        """Update responsive layout."""
        new_size_class = self.get_size_class(width)
        if new_size_class != self._current_size_class:
            self._current_size_class = new_size_class
            self.apply_responsive_style(new_size_class)


class AssetOptimizer:
    """
    Static utility class for asset optimization.
    """

    @staticmethod
    def get_asset_info(file_path):
        """Get asset file information."""
        if not os.path.exists(file_path):
            return None

        stat = os.stat(file_path)
        return {
            "size": stat.st_size,
            "size_mb": stat.st_size / (1024 * 1024),
            "modified": stat.st_mtime,
        }

    @staticmethod
    def analyze_gif_performance(file_path):
        """Analyze GIF performance characteristics."""
        try:
            movie = QMovie(file_path)
            if not movie.isValid():
                return None

            frame_count = movie.frameCount()
            speed = movie.speed()

            return {
                "frame_count": frame_count,
                "speed": speed,
                "estimated_duration": frame_count / (speed / 1000) if speed > 0 else 0,
            }
        except Exception as e:
            logger.warning(f"Failed to analyze GIF {file_path}: {e}")
            return None

    @staticmethod
    def suggest_optimization(file_path):
        """Suggest optimization strategies for asset."""
        info = AssetOptimizer.get_asset_info(file_path)
        if not info:
            return "File not found"

        suggestions = []

        if info["size_mb"] > 1.0:
            suggestions.append("Consider compressing this large asset")

        if file_path.endswith(".gif"):
            perf = AssetOptimizer.analyze_gif_performance(file_path)
            if perf and perf["frame_count"] > 30:
                suggestions.append("High frame count - consider reducing frames")

        return suggestions if suggestions else ["Asset appears optimized"]
