"""
Enhanced Game Image Manager - Multiple fallback sources and formats
"""

from utils.logger import get_internationalized_logger

import logging
import os
from typing import Dict, List, Optional

import requests
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap

from utils.image_cache import ImageCacheManager

logger = get_internationalized_logger()


class GameImageManager(QObject):
    """
    Enhanced game image manager with multiple fallback sources and formats
    """

    # Signals
    image_ready = pyqtSignal(str, object, str)  # app_id, QPixmap, source_info
    image_failed = pyqtSignal(str, str)  # app_id, error_message

    def __init__(self, cache_manager: ImageCacheManager):
        super().__init__()
        self.cache_manager = cache_manager

        # CDN endpoints in order of preference
        self.cdn_endpoints = [
            "https://cdn.akamai.steamstatic.com",
            "https://steamcdn-a.akamaihd.net",
            "https://media.steampowered.com",
        ]

        # Image formats in order of preference (largest to smallest)
        self.image_formats = [
            {
                "name": "header",
                "path": "/steam/apps/{app_id}/header.jpg",
                "width": 460,
                "height": 215,
            },
            {
                "name": "library",
                "path": "/steam/apps/{app_id}/library_600x900.jpg",
                "width": 600,
                "height": 900,
            },
            {
                "name": "capsule_231x87",
                "path": "/steam/apps/{app_id}/capsule_231x87.jpg",
                "width": 231,
                "height": 87,
            },
            {
                "name": "capsule_184x69",
                "path": "/steam/apps/{app_id}/capsule_184x69.jpg",
                "width": 184,
                "height": 69,
            },
            {
                "name": "header_292x136",
                "path": "/steam/apps/{app_id}/header_292x136.jpg",
                "width": 292,
                "height": 136,
            },
        ]

        # API endpoints for fallback
        self.api_endpoints = [
            "https://store.steampowered.com/api/appdetails",
            "https://store.steampowered.com/api/appdetails?cc=US",
        ]

    def get_game_image(self, app_id: str, preferred_format: str = "header", force_refresh: bool = False) -> QThread:
        """
        Get game image with multiple fallback strategies

        Args:
            app_id: Steam App ID
            preferred_format: Preferred image format name
            force_refresh: If True, bypass cache and fetch fresh image

        Returns:
            QThread for async operation
        """
        thread = GameImageThread(app_id, preferred_format, self, force_refresh)
        thread.image_ready.connect(self.image_ready.emit)
        thread.image_failed.connect(self.image_failed.emit)
        thread.finished.connect(thread.deleteLater)  # Clean up thread when finished
        thread.start()
        return thread

    def get_image_urls(self, app_id: str) -> List[Dict[str, str]]:
        """
        Generate all possible image URLs for an app ID

        Args:
            app_id: Steam App ID

        Returns:
            List of dictionaries with url, format, and endpoint info
        """
        urls = []

        for endpoint in self.cdn_endpoints:
            for format_info in self.image_formats:
                url = endpoint + format_info["path"].format(app_id=app_id)
                urls.append(
                    {
                        "url": url,
                        "format": format_info["name"],
                        "endpoint": endpoint,
                        "width": format_info["width"],
                        "height": format_info["height"],
                    }
                )

        return urls

    def try_api_fallback(self, app_id: str) -> Optional[List[str]]:
        """
        Try to get image URLs from Steam Store API

        Args:
            app_id: Steam App ID

        Returns:
            List of image URLs or None if failed
        """
        try:
            headers = {
                "User-Agent": "Bifrost/1.0 (Steam Game Manager)",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
            }

            for api_endpoint in self.api_endpoints:
                try:
                    url = f"{api_endpoint}&appids={app_id}"
                    response = requests.get(url, headers=headers, timeout=5)
                    response.raise_for_status()

                    data = response.json()
                    if str(app_id) in data and data[str(app_id)]["success"]:
                        app_data = data[str(app_id)]["data"]
                        image_urls = []

                        # Extract header image
                        if "header_image" in app_data:
                            image_urls.append(app_data["header_image"])

                        # Extract screenshots
                        if "screenshots" in app_data:
                            for screenshot in app_data["screenshots"][
                                :2
                            ]:  # Take first 2
                                if "path_full" in screenshot:
                                    image_urls.append(screenshot["path_full"])

                        # Extract capsule image if available
                        if "capsule_image" in app_data:
                            image_urls.append(app_data["capsule_image"])

                        if image_urls:
                            logger.debug(
                                f"Found {len(image_urls)} images from API for app {app_id}"
                            )
                            return image_urls

                except requests.RequestException as e:
                    logger.debug(
                        f"API endpoint {api_endpoint} failed for app {app_id}: {e}"
                    )
                    continue
                except Exception as e:
                    logger.debug(f"Error parsing API response for app {app_id}: {e}")
                    continue

        except Exception as e:
            logger.error(f"API fallback failed for app {app_id}: {e}")

        return None

    def get_fallback_image(self) -> Optional[QPixmap]:
        """
        Get fallback image when no game image is available

        Returns:
            QPixmap with fallback image or None
        """
        try:
            # Try to load a default image from assets
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            fallback_path = os.path.join(project_root, "assets", "images", "bifrost.png")

            if os.path.exists(fallback_path):
                pixmap = QPixmap()
                if pixmap.load(fallback_path):
                    logger.debug("Using fallback Bifrost image")
                    return pixmap

            # Create a simple colored placeholder if no image available
            from PyQt6.QtGui import QColor, QFont, QPainter

            pixmap = QPixmap(460, 215)  # Standard header size
            pixmap.fill(QColor(64, 64, 64))  # Dark gray background

            painter = QPainter(pixmap)
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 16))

            # Draw "No Image" text
            text = "No Image Available"
            rect = pixmap.rect()
            painter.drawText(rect, 1, text)  # Qt.AlignCenter
            painter.end()

            return pixmap

        except Exception as e:
            logger.error(f"Error creating fallback image: {e}")
            return None

    def download_image(self, url: str, timeout: int = 10) -> Optional[bytes]:
        """
        Download image from URL with proper headers

        Args:
            url: Image URL
            timeout: Request timeout in seconds

        Returns:
            Image data as bytes or None if failed
        """
        try:
            headers = {
                "User-Agent": "Bifrost/1.0 (Steam Game Manager)",
                "Accept": "image/jpeg,image/png,image/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
            }

            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()

            # Check if response contains image data
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                logger.debug(f"URL {url} returned non-image content: {content_type}")
                return None

            # Check minimum size (avoid empty or too small images)
            if len(response.content) < 1024:  # Less than 1KB
                logger.debug(
                    f"Image from {url} is too small: {len(response.content)} bytes"
                )
                return None

            return response.content

        except requests.RequestException as e:
            logger.debug(f"Failed to download image from {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading from {url}: {e}")
            return None

    def validate_image_data(self, image_data: bytes) -> bool:
        """
        Validate if image data is a valid image

        Args:
            image_data: Raw image data

        Returns:
            True if valid image, False otherwise
        """
        try:
            pixmap = QPixmap()
            if pixmap.loadFromData(image_data):
                # Check minimum dimensions
                if pixmap.width() < 50 or pixmap.height() < 50:
                    logger.debug(f"Image too small: {pixmap.width()}x{pixmap.height()}")
                    return False
                return True
            else:
                logger.debug("Failed to load image data into QPixmap")
                return False
        except Exception as e:
            logger.debug(f"Error validating image data: {e}")
            return False


class GameImageThread(QThread):
    """
    Thread for fetching game images with multiple fallback strategies
    """

    image_ready = pyqtSignal(str, object, str)  # app_id, QPixmap, source_info
    image_failed = pyqtSignal(str, str)  # app_id, error_message
    finished = pyqtSignal()  # Thread completion signal

    def __init__(self, app_id: str, preferred_format: str, manager: GameImageManager, force_refresh: bool = False):
        super().__init__()
        self.app_id = app_id
        self.preferred_format = preferred_format
        self.manager = manager
        self.force_refresh = force_refresh

    def run(self):
        """Execute image fetching with fallback strategies"""
        try:
            # Strategy 1: Try cache first (unless force_refresh is True)
            if not self.force_refresh:
                cached_image = self._try_cache()
                if cached_image:
                    self.image_ready.emit(
                        self.app_id, cached_image, f"cache:{self.preferred_format}"
                    )
                    return

            # Strategy 2: Try API fallback FIRST (many games only have API URLs)
            image = self._try_api_fallback()
            if image:
                self.image_ready.emit(self.app_id, image, "fallback:api")
                return

            # Strategy 3: Try preferred format on CDN
            image = self._try_preferred_format()
            if image:
                self.image_ready.emit(
                    self.app_id, image, f"preferred:{self.preferred_format}"
                )
                return

            # Strategy 4: Try all formats on primary CDN
            image = self._try_all_formats(primary_only=True)
            if image:
                self.image_ready.emit(self.app_id, image, "fallback:primary_cdn")
                return

            # Strategy 5: Try all formats on all CDNs
            image = self._try_all_formats(primary_only=False)
            if image:
                self.image_ready.emit(self.app_id, image, "fallback:all_cdns")
                return

            # Strategy 6: Try fallback image
            image = self.manager.get_fallback_image()
            if image:
                self.image_ready.emit(self.app_id, image, "fallback:default")
                return

            # All strategies failed
            self.image_failed.emit(
                self.app_id, "No valid image found after all fallback strategies"
            )

        except Exception as e:
            logger.error(f"Error in GameImageThread for app {self.app_id}: {e}")
            self.image_failed.emit(self.app_id, str(e))
        finally:
            self.finished.emit()  # Always emit finished signal

    def _try_cache(self) -> Optional[QPixmap]:
        """Try to get image from cache"""
        try:
            # Get URLs for preferred format
            urls = self.manager.get_image_urls(self.app_id)
            for url_info in urls:
                if url_info["format"] == self.preferred_format:
                    cached = self.manager.cache_manager.get_cached_image(
                        self.app_id, url_info["url"]
                    )
                    if cached and not cached.isNull():
                        logger.debug(f"Using cached image for app {self.app_id}")
                        return cached
            return None
        except Exception as e:
            logger.debug(f"Cache check failed for app {self.app_id}: {e}")
            return None

    def _try_preferred_format(self) -> Optional[QPixmap]:
        """Try preferred format on all CDNs"""
        try:
            for endpoint in self.manager.cdn_endpoints:
                format_info = next(
                    (
                        f
                        for f in self.manager.image_formats
                        if f["name"] == self.preferred_format
                    ),
                    None,
                )
                if format_info:
                    url = endpoint + format_info["path"].format(app_id=self.app_id)

                    # Check cache first (unless force_refresh)
                    if not self.force_refresh:
                        cached = self.manager.cache_manager.get_cached_image(
                            self.app_id, url
                        )
                        if cached and not cached.isNull():
                            return cached

                    # Download
                    image_data = self.manager.download_image(url)
                    if image_data and self.manager.validate_image_data(image_data):
                        pixmap = QPixmap()
                        if pixmap.loadFromData(image_data):
                            # Cache the successful download
                            self.manager.cache_manager.cache_image(
                                self.app_id, url, image_data
                            )
                            logger.debug(
                                f"Downloaded preferred format for app {self.app_id}"
                            )
                            return pixmap
            return None
        except Exception as e:
            logger.debug(f"Preferred format failed for app {self.app_id}: {e}")
            return None

    def _try_all_formats(self, primary_only: bool = False) -> Optional[QPixmap]:
        """Try all image formats"""
        try:
            endpoints = (
                [self.manager.cdn_endpoints[0]]
                if primary_only
                else self.manager.cdn_endpoints
            )

            for endpoint in endpoints:
                for format_info in self.manager.image_formats:
                    url = endpoint + format_info["path"].format(app_id=self.app_id)

                    # Check cache first
                    cached = self.manager.cache_manager.get_cached_image(
                        self.app_id, url
                    )
                    if cached and not cached.isNull():
                        logger.debug(
                            f"Found cached {format_info['name']} for app {self.app_id}"
                        )
                        return cached

                    # Download
                    image_data = self.manager.download_image(url)
                    if image_data and self.manager.validate_image_data(image_data):
                        pixmap = QPixmap()
                        if pixmap.loadFromData(image_data):
                            # Cache the successful download
                            self.manager.cache_manager.cache_image(
                                self.app_id, url, image_data
                            )
                            logger.debug(
                                f"Downloaded {format_info['name']} for app {self.app_id}"
                            )
                            return pixmap
            return None
        except Exception as e:
            logger.debug(f"All formats failed for app {self.app_id}: {e}")
            return None

    def _try_api_fallback(self) -> Optional[QPixmap]:
        """Try to get images from Steam Store API"""
        try:
            logger.debug(f"Trying API fallback for app {self.app_id}")
            api_urls = self.manager.try_api_fallback(self.app_id)
            if not api_urls:
                logger.warning(f"No API URLs found for app {self.app_id}")
                return None
            logger.debug(f"Found {len(api_urls)} API URLs for app {self.app_id}")

            for url in api_urls:
                # Check cache first (unless force_refresh)
                if not self.force_refresh:
                    cached = self.manager.cache_manager.get_cached_image(self.app_id, url)
                    if cached and not cached.isNull():
                        logger.debug(f"Found API cached image for app {self.app_id}")
                        return cached

                # Download
                image_data = self.manager.download_image(url)
                if image_data and self.manager.validate_image_data(image_data):
                    pixmap = QPixmap()
                    if pixmap.loadFromData(image_data):
                        # Cache the successful download
                        self.manager.cache_manager.cache_image(
                            self.app_id, url, image_data
                        )
                        logger.debug(f"Downloaded API image for app {self.app_id}")
                        return pixmap

            return None
        except Exception as e:
            logger.debug(f"API fallback failed for app {self.app_id}: {e}")
            return None

    def get_fallback_image(self) -> Optional[QPixmap]:
        """
        Get fallback image when no game image is available

        Returns:
            QPixmap with fallback image or None
        """
        try:
            # Try to load a default image from assets
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            fallback_path = os.path.join(project_root, "assets", "images", "bifrost.png")

            if os.path.exists(fallback_path):
                pixmap = QPixmap()
                if pixmap.load(fallback_path):
                    logger.debug("Using fallback Bifrost image")
                    return pixmap

            # Create a simple colored placeholder if no image available
            from PyQt6.QtGui import QColor, QFont, QPainter

            pixmap = QPixmap(460, 215)  # Standard header size
            pixmap.fill(QColor(64, 64, 64))  # Dark gray background

            painter = QPainter(pixmap)
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 16))

            # Draw "No Image" text
            text = "No Image Available"
            rect = pixmap.rect()
            painter.drawText(rect, 1, text)  # Qt.AlignCenter
            painter.end()

            return pixmap

        except Exception as e:
            logger.error(f"Error creating fallback image: {e}")
            return None
