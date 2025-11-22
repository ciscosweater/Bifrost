"""
Image Cache Manager - Cache system for game header images
"""

import gc
import hashlib
import os
import time
import weakref
from collections import OrderedDict
from utils.i18n import tr
from typing import Any, Dict, Optional

import requests
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from utils.logger import get_internationalized_logger

logger = get_internationalized_logger("ImageCache")


class ImageCacheManager(QObject):
    """Manages caching of game header images with memory pressure handling"""

    # Signals
    image_cached = pyqtSignal(str, str)  # app_id, cache_path
    cache_error = pyqtSignal(str, str)  # app_id, error_message

    def __init__(self, cache_dir: Optional[str] = None):
        super().__init__()

        if cache_dir is None:
            cache_dir = os.path.join(
                os.path.expanduser("~"), ".cache", "bifrost", "images"
            )

        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

        # Optimized cache settings for memory efficiency
        self.max_cache_size_mb = 20  # Reduced from 50MB for memory pressure
        self.max_age_days = 7  # Reduced from 30 days for more aggressive cleanup
        self.max_file_count = 500  # Reduced from 1000 for memory efficiency

        # Memory tracking
        self._current_memory_mb = 0
        self._memory_pressure_threshold = 0.8  # Trigger cleanup at 80%

        # LRU Cache tracking (in-memory for fast access)
        self._lru_cache = OrderedDict()  # app_id_url -> (filepath, access_time, size)
        self._weak_cache = weakref.WeakValueDictionary()  # Weak references for QPixmap
        self._cache_loaded = False

        logger.info(f"{tr('ImageCache', 'Image cache initialized at')}: {self.cache_dir}")
        self._load_cache_metadata()

    def _load_cache_metadata(self):
        """Load existing cache files into LRU tracking"""
        if self._cache_loaded:
            return

        try:
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                if os.path.isfile(filepath):
                    try:
                        # Extract app_id from filename (format: app_id_hash.jpg)
                        parts = filename.replace(".jpg", "").split("_")
                        if len(parts) >= 2:
                            app_id = parts[0]
                            cache_key = f"{app_id}_{filename}"

                            mtime = os.path.getmtime(filepath)
                            size = os.path.getsize(filepath)

                            self._lru_cache[cache_key] = (filepath, mtime, size)
                    except (ValueError, OSError):
                        continue

            self._cache_loaded = True
            logger.debug(f"Loaded {len(self._lru_cache)} files into LRU cache")

        except Exception as e:
            logger.error(f"Error loading cache metadata: {e}")

    def _update_lru_access(self, cache_key: str, filepath: str, size: int):
        """Update LRU cache when file is accessed"""
        current_time = time.time()
        self._lru_cache[cache_key] = (filepath, current_time, size)
        # Move to end (most recently used)
        self._lru_cache.move_to_end(cache_key)

    def get_cache_path(self, app_id: str, url: str) -> str:
        """Generate cache file path for an app"""
        # Create hash from URL to handle URL changes
        url_hash = hashlib.md5(url.encode()).hexdigest()
        filename = f"{app_id}_{url_hash}.jpg"
        return os.path.join(self.cache_dir, filename)

    def is_cached(self, app_id: str, url: str) -> bool:
        """Check if image is cached and valid"""
        cache_path = self.get_cache_path(app_id, url)

        if not os.path.exists(cache_path):
            return False

        # Check file age
        import time

        file_age = time.time() - os.path.getmtime(cache_path)
        max_age_seconds = self.max_age_days * 24 * 3600

        if file_age > max_age_seconds:
            logger.debug(f"Cached image expired for app {app_id}")
            os.remove(cache_path)
            return False

        # Check file size (should be greater than 0)
        if os.path.getsize(cache_path) == 0:
            logger.debug(f"Cached image is empty for app {app_id}")
            os.remove(cache_path)
            return False

        return True

    def get_cached_image(self, app_id: str, url: str) -> Optional[QPixmap]:
        """Get cached image if available with memory pressure handling"""
        if not self.is_cached(app_id, url):
            return None

        cache_path = self.get_cache_path(app_id, url)
        cache_key = f"{app_id}_{os.path.basename(cache_path)}"

        # Check weak cache first (memory efficient)
        if cache_key in self._weak_cache:
            weak_ref = self._weak_cache[cache_key]
            if weak_ref is not None:
                logger.debug(f"Using weak cached image for app {app_id}")
                return weak_ref

        try:
            # Check memory pressure before loading
            if hasattr(self, "_check_memory_pressure"):
                self._check_memory_pressure()

            pixmap = QPixmap(cache_path)
            if not pixmap.isNull():
                # Update LRU access
                file_size = os.path.getsize(cache_path)
                self._update_lru_access(cache_key, cache_path, file_size)

                # Store in weak cache for memory efficiency
                self._weak_cache[cache_key] = pixmap
                self._current_memory_mb += file_size / (1024 * 1024)

                logger.debug(f"Loaded cached image for app {app_id}")
                return pixmap
            else:
                logger.warning(f"Cached image is corrupted for app {app_id}")
                os.remove(cache_path)
                # Remove from LRU cache
                self._lru_cache.pop(cache_key, None)
                return None
        except Exception as e:
            logger.error(f"Error loading cached image for app {app_id}: {e}")
            return None

    def cache_image(self, app_id: str, url: str, image_data: bytes) -> bool:
        """Cache image data"""
        try:
            cache_path = self.get_cache_path(app_id, url)

            with open(cache_path, "wb") as f:
                f.write(image_data)

            logger.debug(f"Cached image for app {app_id}: {len(image_data)} bytes")
            self.image_cached.emit(app_id, cache_path)

            # Clean up old cache if needed
            self._cleanup_cache()

            return True

        except Exception as e:
            logger.error(f"Error caching image for app {app_id}: {e}")
            self.cache_error.emit(app_id, str(e))
            return False

    def download_and_cache(
        self, app_id: str, url: str, timeout: int = 10
    ) -> Optional[QPixmap]:
        """Download image and cache it"""
        try:
            logger.debug(f"Downloading image for app {app_id}: {url}")

            headers = {"User-Agent": "Bifrost/1.0 (Steam Game Manager)"}

            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()

            # Create pixmap from downloaded data first
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)

            # Cache the image
            if self.cache_image(app_id, url, response.content):
                return pixmap

            if not pixmap.isNull():
                logger.debug(f"Successfully downloaded image for app {app_id}")
                return pixmap
            else:
                logger.warning(f"Downloaded image is invalid for app {app_id}")
                return None

        except requests.RequestException as e:
            logger.error(f"Error downloading image for app {app_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading image for app {app_id}: {e}")
            return None

    def _cleanup_cache(self):
        """Enhanced cache cleanup with LRU eviction and multiple limits"""
        try:
            # Ensure LRU cache is loaded
            if not self._cache_loaded:
                self._load_cache_metadata()

            # Check file count limit
            if len(self._lru_cache) > self.max_file_count:
                self._evict_lru_files(target_count=int(self.max_file_count * 0.8))

            # Calculate current cache size from LRU data
            total_size = sum(size for (_, _, size) in self._lru_cache.values())
            total_size_mb = total_size / (1024 * 1024)

            if total_size_mb <= self.max_cache_size_mb:
                return

            # Evict based on size limit
            target_size = int(self.max_cache_size_mb * 0.8 * 1024 * 1024)  # 80% of max
            self._evict_lru_files(target_size=target_size)

        except Exception as e:
            logger.error(f"Error during enhanced cache cleanup: {e}")

    def _check_memory_pressure(self):
        """Check if we're approaching memory limits and trigger cleanup"""
        if (
            self._current_memory_mb
            > self.max_cache_size_mb * self._memory_pressure_threshold
        ):
            logger.warning(
                f"Memory pressure detected: {self._current_memory_mb:.1f}MB > {self.max_cache_size_mb * self._memory_pressure_threshold:.1f}MB"
            )
            self._emergency_cleanup()

    def _emergency_cleanup(self):
        """Aggressive cleanup when memory pressure detected"""
        try:
            # Remove oldest 50% of cache immediately
            items_to_remove = len(self._lru_cache) // 2
            removed_count = 0

            # Sort by access time (oldest first)
            sorted_items = sorted(self._lru_cache.items(), key=lambda x: x[1][1])

            for cache_key, (filepath, _, size) in sorted_items[:items_to_remove]:
                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)

                    # Remove from both caches
                    self._lru_cache.pop(cache_key, None)
                    self._weak_cache.pop(cache_key, None)

                    # Update memory tracking
                    self._current_memory_mb -= size / (1024 * 1024)
                    removed_count += 1

                except Exception as e:
                    logger.warning(f"Error in emergency cleanup for {cache_key}: {e}")

            # Force garbage collection
            gc.collect()

            logger.info(
                f"Emergency cleanup: removed {removed_count} files, freed memory"
            )

        except Exception as e:
            logger.error(f"Error during emergency cleanup: {e}")

    def _evict_lru_files(
        self, target_count: Optional[int] = None, target_size: Optional[int] = None
    ):
        """Evict least recently used files from cache"""
        try:
            removed_count = 0
            freed_size = 0
            current_size = sum(size for (_, _, size) in self._lru_cache.values())

            # Sort by access time (oldest first)
            sorted_items = sorted(self._lru_cache.items(), key=lambda x: x[1][1])

            for cache_key, (filepath, _, size) in sorted_items:
                should_remove = False

                if target_count and len(self._lru_cache) > target_count:
                    should_remove = True
                elif target_size and current_size > target_size:
                    should_remove = True

                if not should_remove:
                    break

                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)

                    # Remove from LRU cache
                    self._lru_cache.pop(cache_key, None)

                    current_size -= size
                    freed_size += size
                    removed_count += 1

                    logger.debug(
                        f"Evicted LRU cache file: {os.path.basename(filepath)}"
                    )

                except Exception as e:
                    logger.warning(f"Error evicting cache file {filepath}: {e}")

            if removed_count > 0:
                logger.info(
                    f"LRU eviction: removed {removed_count} files, freed {freed_size / (1024 * 1024):.1f} MB"
                )

        except Exception as e:
            logger.error(f"Error during LRU eviction: {e}")

    def clear_cache(self):
        """Clear all cached images"""
        try:
            removed_count = 0
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
                    removed_count += 1

            logger.info(f"Cleared image cache: removed {removed_count} files")

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            total_size = 0
            file_count = 0

            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                if os.path.isfile(filepath):
                    total_size += os.path.getsize(filepath)
                    file_count += 1

            return {
                "file_count": file_count,
                "total_size_mb": total_size / (1024 * 1024),
                "cache_dir": self.cache_dir,
            }

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}


class ImageFetcher(QThread):
    """Thread for fetching game images with caching"""

    image_ready = pyqtSignal(str, object)  # app_id, QPixmap or None
    error_occurred = pyqtSignal(str, str)  # app_id, error_message

    def __init__(self, app_id: str, url: str, cache_manager: ImageCacheManager):
        super().__init__()
        self.app_id = app_id
        self.url = url
        self.cache_manager = cache_manager

    def run(self):
        """Fetch image with caching"""
        try:
            # Try cache first
            cached_image = self.cache_manager.get_cached_image(self.app_id, self.url)
            if cached_image:
                self.image_ready.emit(self.app_id, cached_image)
                return

            # Download and cache
            pixmap = self.cache_manager.download_and_cache(self.app_id, self.url)
            self.image_ready.emit(self.app_id, pixmap)

        except Exception as e:
            logger.error(f"Error in ImageFetcher for app {self.app_id}: {e}")
            self.error_occurred.emit(self.app_id, str(e))
