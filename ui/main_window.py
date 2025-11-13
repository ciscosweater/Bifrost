# type: ignore
import logging
import os
import random
import re
import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QMovie
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core import steam_helpers
from core.online_fixes_manager import OnlineFixesManager
from core.tasks.download_manager import DownloadManager
from core.tasks.monitor_speed_task import SpeedMonitorTask
from core.tasks.process_zip_task import ProcessZipTask
from ui.asset_optimizer import AssetManager
from ui.custom_title_bar import CustomTitleBar
from ui.enhanced_dialogs import (
    DepotSelectionDialog,
    DlcSelectionDialog,
    SettingsDialog,
    SteamLibraryDialog,
)
from ui.game_deletion_dialog import GameDeletionDialog

# from ui.game_image_display import GameImageDisplay, ImageFetcher  # Commented out - file not found
from ui.game_image_manager import GameImageManager
from ui.info_cards import InfoCardsContainer
from ui.interactions import ModernFrame
from ui.minimal_download_widget import MinimalDownloadWidget

from ui.shortcuts import KeyboardShortcuts
from ui.theme import Spacing
from utils.image_cache import ImageCacheManager
from utils.settings import get_settings

# from ui.responsive_design import ResponsiveMainWindow  # Disabled temporarily
from utils.task_runner import TaskRunner

# Import i18n
try:
    from utils.i18n import tr
except (ImportError, ModuleNotFoundError):

    def tr(context, text):
        return text


logger = logging.getLogger(__name__)


class ScaledLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMinimumSize(1, 1)
        self._movie = None

    def setMovie(self, movie):
        if self._movie:
            self._movie.frameChanged.disconnect(self.on_frame_changed)
        self._movie = movie
        if self._movie:
            self._movie.frameChanged.connect(self.on_frame_changed)

    def on_frame_changed(self, frame_number=None):
        if self.size().width() > 0 and self.size().height() > 0 and self._movie:
            pixmap = self._movie.currentPixmap()
            scaled_pixmap = pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            super().setPixmap(scaled_pixmap)

    def resizeEvent(self, a0):
        if self._movie:
            self.on_frame_changed(0)
        super(ScaledLabel, self).resizeEvent(a0)


class ScaledFontLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMinimumSize(1, 1)

    def resizeEvent(self, a0):
        super(ScaledFontLabel, self).resizeEvent(a0)
        font = self.font()
        new_size = max(8, min(72, int(self.height() * 0.4)))
        font.setPointSize(new_size)
        self.setFont(font)


class MainWindow(QMainWindow):
    def __init__(self, zip_file=None):
        super().__init__()
        self.setWindowTitle(tr("MainWindow", "Depot Downloader GUI"))
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setGeometry(100, 100, 800, 600)
        self.settings = get_settings()
        self.game_data = None
        self.speed_monitor_task = None
        self.main_movie = QMovie("assets/gifs/main.gif")
        self.download_gifs = [f"assets/gifs/downloading{i}.gif" for i in range(1, 12)]
        self.current_movie = None
        self.depot_dialog = None
        self.current_dest_path = None
        self.slssteam_mode_was_active = False
        self.game_header_image = None
        self._fix_available = False  # Track if fixes are available for current game
        self._fix_processing = False  # Track if a fix is currently being processed
        self.keyboard_shortcuts = KeyboardShortcuts(self)
        self.asset_manager = AssetManager(self)

        # Download Manager for pause/cancel/resume
        self.download_manager = DownloadManager()

        # Online Fixes Manager
        self.online_fixes_manager = OnlineFixesManager()

        # Minimalist download widget (new component)
        self.minimal_download_widget = MinimalDownloadWidget()

        # Info cards container
        self.info_cards = InfoCardsContainer()
        self.info_cards.setVisible(True)

        # Control to avoid multiple restart requests
        self._steam_restart_prompted = False

        # Control to avoid multiple completion messages
        self._completion_message_shown = False

        # Persist game data for Online-Fixes
        self._current_game_data = None

        # Image cache manager and enhanced image manager
        self.image_cache_manager = ImageCacheManager()
        self.game_image_manager = GameImageManager(self.image_cache_manager)

        self._setup_ui()
        self._setup_download_connections()

        # If zip file was provided as argument, start processing it immediately
        if zip_file:
            self._start_zip_processing(zip_file)

    def _setup_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 5)
        self.main_layout.setSpacing(0)

        # Add title bar at the top of the window
        self.title_bar = CustomTitleBar(self)
        self.main_layout.addWidget(self.title_bar)

        main_content_frame = QFrame()
        from .theme import BorderRadius, theme

        main_content_frame.setStyleSheet(f"""
            QFrame {{
                background: {theme.colors.BACKGROUND};
                border: none;
                {BorderRadius.get_border_radius(BorderRadius.LARGE)};
            }}
        """)
        self.main_layout.addWidget(main_content_frame)

        self.content_layout = QVBoxLayout(main_content_frame)
        self.content_layout.setContentsMargins(
            Spacing.MD, Spacing.SM, Spacing.MD, Spacing.XS
        )  # Restore original margins
        self.content_layout.setSpacing(Spacing.MD)  # Adequate spacing between elements

        # Create stacked widget for switching between normal and download modes
        self.main_stacked_widget = QStackedWidget()
        self.content_layout.addWidget(self.main_stacked_widget, 3)

        # Normal mode page (GIF + info cards side by side)
        self.normal_page = QWidget()
        normal_layout = QHBoxLayout(self.normal_page)
        normal_layout.setContentsMargins(0, 0, 0, 0)
        normal_layout.setSpacing(Spacing.SM)  # Restore original spacing

        # Drop zone container for normal mode (left side)
        normal_drop_zone_container = QWidget()
        normal_drop_zone_container.setStyleSheet(f"""
            QWidget {{
                background: transparent;
                border: none;
                {BorderRadius.get_border_radius(BorderRadius.LARGE)};
            }}
        """)
        normal_drop_zone_layout = QVBoxLayout(normal_drop_zone_container)
        normal_drop_zone_layout.setContentsMargins(
            Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM
        )  # Adequate margins for drop zone
        normal_drop_zone_layout.setSpacing(Spacing.SM)  # Adequate spacing

        self.drop_label = ScaledLabel()
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setStyleSheet("""
            ScaledLabel {{
                background: transparent;
                border: none;
            }}
        """)

        if self.main_movie.isValid():
            self.drop_label.setMovie(self.main_movie)
            self.main_movie.start()
            self.current_movie = self.main_movie
        else:
            self.drop_label.setText(tr("MainWindow", "Drag and Drop ZIP File Here"))

        normal_drop_zone_layout.addWidget(self.drop_label, 10)

        self.drop_text_label = ScaledFontLabel(
            tr("MainWindow", "Drag and Drop Zip here")
        )
        self.drop_text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        from .theme import Typography, theme

        self.drop_text_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_SECONDARY};
                background-color: transparent;
                border: none;
                font-family: {Typography.get_font_family()};
                {Typography.get_font_style(Typography.H2_SIZE, Typography.WEIGHT_BOLD)};
            }}
        """)
        normal_drop_zone_layout.addWidget(self.drop_text_label, 1)

        # Add drop zone to left side of normal layout
        normal_layout.addWidget(
            normal_drop_zone_container, 3
        )  # Takes 3/4 of horizontal space

        # Add info cards to right side of normal layout
        self.info_cards_frame = QFrame()
        self.info_cards_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.info_cards_frame.setStyleSheet("""
            QFrame {{
                background: transparent;
                border: none;
            }}
        """)
        info_cards_layout = QVBoxLayout(self.info_cards_frame)
        info_cards_layout.setContentsMargins(
            0, 0, 0, 0
        )  # Remove right margin only for info cards
        info_cards_layout.setSpacing(Spacing.SM)

        # Add info cards container
        self.info_cards.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        info_cards_layout.addWidget(self.info_cards)

        normal_layout.addWidget(
            self.info_cards_frame, 1
        )  # Takes 1/4 of horizontal space

        # Download mode page (GIF + download widget stacked vertically)
        self.download_page = QWidget()
        download_page_layout = QVBoxLayout(self.download_page)
        download_page_layout.setContentsMargins(0, 0, 0, 0)
        download_page_layout.setSpacing(Spacing.SM)

        # Drop zone container for download mode (top)
        download_drop_zone_container = QWidget()
        download_drop_zone_container.setStyleSheet(f"""
            QWidget {{
                background: transparent;
                border: none;
                {BorderRadius.get_border_radius(BorderRadius.LARGE)};
            }}
        """)
        download_drop_zone_layout = QVBoxLayout(download_drop_zone_container)
        download_drop_zone_layout.setContentsMargins(
            Spacing.SM, Spacing.SM, Spacing.SM, Spacing.SM
        )
        download_drop_zone_layout.setSpacing(Spacing.SM)

        # Create separate drop label for download mode
        self.download_drop_label = ScaledLabel()
        self.download_drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.download_drop_label.setStyleSheet("""
            ScaledLabel {{
                background: transparent;
                border: none;
            }}
        """)

        if self.main_movie.isValid():
            self.download_drop_label.setMovie(self.main_movie)
            # Don't start movie here, it's already running from normal mode

        download_drop_zone_layout.addWidget(self.download_drop_label, 10)

        self.download_drop_text_label = ScaledFontLabel(
            tr("MainWindow", "Downloading...")
        )
        self.download_drop_text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.download_drop_text_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_SECONDARY};
                background-color: transparent;
                border: none;
                font-family: {Typography.get_font_family()};
                {Typography.get_font_style(Typography.H2_SIZE, Typography.WEIGHT_BOLD)};
            }}
        """)
        download_drop_zone_layout.addWidget(self.download_drop_text_label, 1)

        # Add download drop zone to top of download page
        download_page_layout.addWidget(
            download_drop_zone_container, 2
        )  # GIF takes 2/3 of vertical space

        # Add download widget below GIF
        download_widget_container = QFrame()
        download_widget_container.setStyleSheet("""
            QFrame {{
                background: transparent;
                border: none;
            }}
        """)
        download_widget_layout = QVBoxLayout(download_widget_container)
        download_widget_layout.setContentsMargins(
            Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM
        )
        download_widget_layout.setSpacing(Spacing.SM)

        # Add minimal download widget
        download_widget_layout.addWidget(self.minimal_download_widget)
        download_widget_layout.addStretch()

        download_page_layout.addWidget(
            download_widget_container, 1
        )  # Download widget takes 1/3 of vertical space

        # Add pages to main stacked widget
        self.main_stacked_widget.addWidget(self.normal_page)  # Index 0 (normal)
        self.main_stacked_widget.addWidget(self.download_page)  # Index 1 (download)

        # Start with normal page
        self.main_stacked_widget.setCurrentIndex(0)

        # Game header image area (initially hidden)
        self.game_image_container = ModernFrame()
        self.game_image_container.setVisible(False)
        self.game_image_container.setMaximumHeight(80)  # Reduced height
        self.game_image_container.setMaximumWidth(
            600
        )  # Constrain width to prevent excess space
        self.game_image_container.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        game_image_layout = QHBoxLayout(self.game_image_container)
        game_image_layout.setContentsMargins(12, 8, 12, 8)  # Adequate margins

        self.game_header_label = QLabel()
        self.game_header_label.setMinimumSize(100, 30)  # Reduced minimum size
        self.game_header_label.setMaximumSize(
            150, 56
        )  # Reduced maximum size (scale down 20%)
        self.game_header_label.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.game_header_label.setScaledContents(
            False
        )  # Let scaled() control the aspect ratio
        self.game_header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        from .theme import theme

        self.game_header_label.setStyleSheet(f"""
            QLabel {{
                border: 1px solid {theme.colors.PRIMARY};
                background: {theme.colors.SURFACE};
            }}
        """)
        game_image_layout.addWidget(self.game_header_label)

        # Game info next to image
        game_info_layout = QVBoxLayout()
        game_info_layout.setSpacing(Spacing.XS)  # Reduced spacing

        self.game_title_label = QLabel(tr("MainWindow", "Game Title"))
        self.game_title_label.setStyleSheet(f"""
            QLabel {{
                font-family: {Typography.get_font_family()};
                {Typography.get_font_style(Typography.BODY_SIZE, Typography.WEIGHT_BOLD)};
                color: {theme.colors.PRIMARY};
                border: none;
            }}
        """)
        game_info_layout.addWidget(self.game_title_label)

        self.game_status_label = QLabel(tr("MainWindow", "Downloading..."))
        self.game_status_label.setStyleSheet(f"""
            QLabel {{
                font-family: {Typography.get_font_family()};
                {Typography.get_font_style(Typography.CAPTION_SIZE)};
                color: {theme.colors.TEXT_SECONDARY};
                border: none;
            }}
        """)
        game_info_layout.addWidget(self.game_status_label)

        game_info_layout.addStretch()
        game_image_layout.addLayout(game_info_layout)

        # Hide old container to avoid duplication
        self.game_image_container.hide()

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        from .theme import Typography

        self.log_output.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme.colors.BACKGROUND};
                color: {theme.colors.TEXT_PRIMARY};
                font-family: {Typography.get_font_family()};
                font-size: 10pt;
                font-weight: 500;
                border: 1px solid {theme.colors.PRIMARY};
                {BorderRadius.get_border_radius(0)};
            }}
            QTextEdit:hover {{
                background-color: {theme.colors.SURFACE_DARK};
            }}
        """)
        # Enable word wrapping and horizontal scrolling for long file paths
        self.log_output.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.log_output.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.log_output.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.content_layout.addWidget(self.log_output, 2)
        # Get the Qt log handler after logging is set up
        try:
            from utils.logger import qt_log_handler

            if qt_log_handler:
                qt_log_handler.new_record.connect(self.log_output.append)
        except (ImportError, AttributeError):
            # Fallback if logging handler is not available
            pass

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setSizeGripEnabled(True)
        self.status_bar.setStyleSheet(
            f"QStatusBar {{ border: 0px; background: {theme.colors.BACKGROUND}; height: 8px; }}"
        )
        self.status_bar.setMaximumHeight(8)  # Minimum status bar just for size grip

        self.setAcceptDrops(True)

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def dragEnterEvent(self, a0):
        if a0.mimeData().hasUrls() and len(a0.mimeData().urls()) == 1:
            url = a0.mimeData().urls()[0]
            if url.isLocalFile() and url.toLocalFile().lower().endswith(".zip"):
                a0.acceptProposedAction()

    def dropEvent(self, a0):
        url = a0.mimeData().urls()[0]
        zip_path = url.toLocalFile()
        self.log_output.clear()
        self._start_zip_processing(zip_path)

    def _setup_download_connections(self):
        """Configure DownloadManager and UI controls connections"""
        # Connect DownloadManager signals
        self.download_manager.download_progress.connect(self._on_download_progress)
        self.download_manager.download_bytes.connect(self._on_download_bytes)
        self.download_manager.download_paused.connect(self._on_download_paused)
        self.download_manager.download_resumed.connect(self._on_download_resumed)
        self.download_manager.download_cancelled.connect(self._on_download_cancelled)
        self.download_manager.download_completed.connect(self._on_download_completed)
        self.download_manager.steamless_progress.connect(self._on_steamless_progress)

        # Connect OnlineFixesManager signals
        self.online_fixes_manager.fix_check_started.connect(self._on_fix_check_started)
        self.online_fixes_manager.fix_check_progress.connect(
            self._on_fix_check_progress
        )
        self.online_fixes_manager.fix_check_completed.connect(
            self._on_fix_check_completed
        )
        self.online_fixes_manager.fix_download_progress.connect(
            self._on_fix_download_progress
        )
        self.online_fixes_manager.fix_applied.connect(lambda appid, fix_type: self._on_fix_applied(fix_type))
        self.online_fixes_manager.fix_error.connect(self._on_fix_error)
        self.download_manager.download_error.connect(self._on_download_error)
        self.download_manager.state_changed.connect(self._on_download_state_changed)
        self.download_manager.depot_completed.connect(self._on_depot_completed)

        # Connect UI controls (minimalist widget)
        self.minimal_download_widget.pause_clicked.connect(
            self.download_manager.pause_download
        )
        self.minimal_download_widget.resume_clicked.connect(
            self.download_manager.resume_download
        )
        self.minimal_download_widget.cancel_clicked.connect(
            self._confirm_cancel_download
        )

    def _select_zip_file(self):
        """Open file dialog to select a ZIP file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("MainWindow", "Select ZIP File"),
            "",
            tr("MainWindow", "ZIP Files (*.zip);;All Files (*)"),
        )

        if file_path:
            self.log_output.clear()
            self._start_zip_processing(file_path)

    def _start_zip_processing(self, zip_path):
        """Start processing a ZIP file that was provided as argument or drag & drop"""
        # Check SLSsteam prerequisite before processing ZIP
        if not self._check_slssteam_prerequisite():
            return

        # 🐛 FIX: Clean up any previous ZIP task and task runner to prevent conflicts
        self._cleanup_zip_processing()

        # Reset completion message control for new processing
        self._completion_message_shown = False
        if hasattr(self, "_fix_applied_recently"):
            delattr(self, "_fix_applied_recently")

        # Reset Steam restart control for new processing
        self._steam_restart_prompted = False

        # Reset UI state for new processing
        try:
            # Reset drop zone
            self.drop_text_label.setText(
                tr("MainWindow", "Drop game files here or click to browse")
            )
            self.drop_text_label.setVisible(True)

            # Reset title bar button
            self.title_bar.select_file_button.setVisible(True)

            # Reset minimal download widget
            if hasattr(self, "minimal_download_widget"):
                self.minimal_download_widget.set_idle_state()
                self.minimal_download_widget.setVisible(False)

            # Reset game title
            if hasattr(self, "game_title_label"):
                self.game_title_label.setText(tr("MainWindow", "ACCELA"))

            # Reset current data - preserve dest_path only if fix might be needed
            self.game_data = None
            # Only clear dest_path if it's from a completed download that won't need fixes
            if not hasattr(self, "_fix_available") or not self._fix_available:
                self.current_dest_path = None
            self.current_session = None

            logger.debug("UI state reset for new processing")

        except Exception as e:
            logger.warning(f"Error resetting UI state: {e}")

        self.log_output.append(
            tr("MainWindow", "Processing ZIP file: {0}").format(zip_path)
        )

        # Show visual feedback during ZIP processing
        self.drop_text_label.setText(tr("MainWindow", "Processing ZIP..."))
        self.drop_text_label.setVisible(True)
        self.title_bar.select_file_button.setVisible(False)

        self.zip_task = ProcessZipTask()
        self.task_runner = TaskRunner()  # Keep reference to prevent GC
        worker = self.task_runner.run(self.zip_task.run, zip_path)
        worker.finished.connect(self._on_zip_processed)
        worker.error.connect(self._handle_task_error)

    def _cleanup_zip_processing(self):
        """Clean up ZIP processing resources to prevent crashes"""
        try:
            # Clean up previous ZIP task
            if hasattr(self, "zip_task") and self.zip_task:
                self.zip_task = None
                logger.debug("Cleaned up previous ZIP task reference")

            # Clean up previous task runner with enhanced safety
            if hasattr(self, "task_runner") and self.task_runner:
                try:
                    # Use the new force_cleanup method for proper thread management
                    self.task_runner.force_cleanup()
                    logger.debug("Force cleaned up previous task runner")

                    # Clear task runner reference
                    self.task_runner = None

                except Exception as thread_error:
                    # Handle PyQt6 object deletion errors gracefully
                    if "wrapped C/C++ object" in str(thread_error):
                        logger.debug("PyQt6 object already deleted during cleanup")
                    else:
                        logger.warning(f"Error during thread cleanup: {thread_error}")

                    # Force clear references even if cleanup failed
                    self.task_runner = None

        except Exception as e:
            logger.warning(f"Error during ZIP processing cleanup: {e}")
            # Force cleanup to prevent crashes
            self.zip_task = None
            self.task_runner = None

    def _on_download_progress(self, percentage, message):
        """Handle download progress updates"""
        if percentage > 0:
            self.minimal_download_widget.update_progress(percentage)
        if message:
            # Don't append to log_output here - the logging system already handles it
            # This prevents duplicate log messages
            self.minimal_download_widget.update_status(message)

    def _on_download_bytes(self, downloaded_bytes):
        """Handle download bytes updates"""
        self.minimal_download_widget.update_downloaded_size(downloaded_bytes)

    def _on_steamless_progress(self, message: str):
        """Handle Steamless progress updates"""
        self.minimal_download_widget.update_status(f"Steamless: {message}")

    def _on_download_paused(self):
        """Handle download pause"""
        self.minimal_download_widget.set_paused_state()
        self.log_output.append(tr("MainWindow", "Download paused"))

    def _on_download_resumed(self):
        """Handle download resume"""
        self.minimal_download_widget.set_downloading_state()
        self.log_output.append(tr("MainWindow", "Download resumed"))

    def _on_download_cancelled(self):
        """Handle download cancellation"""
        self._stop_speed_monitor()
        self.minimal_download_widget.set_error_state(tr("MainWindow", "Cancelled"))
        self.log_output.append(tr("MainWindow", "Download cancelled by user"))
        # Clear current session to avoid unwanted behavior
        self.current_session = None
        self._reset_ui_state()

    def _on_download_completed(self, install_path):
        """Handle download completion"""
        try:
            logger.debug("Download completion handler started")
            self._stop_speed_monitor()
            self.minimal_download_widget.set_completed_state()
            self.log_output.append(tr("MainWindow", "Download completed successfully!"))

            # Create ACF file and handle completion
            logger.debug("Creating ACF file...")
            self._create_acf_file()
            logger.debug("ACF file created")

            # Generate Steam achievements if enabled
            logger.debug("Handling Steam schema generation...")
            self._handle_steam_schema_generation()
            logger.debug("Steam schema generation handled")

            # Check for Online-Fixes after download completion
            if install_path and os.path.exists(install_path):
                logger.debug("Checking for Online-Fixes...")
                self._check_for_online_fixes(install_path)
            else:
                # Always show Steam restart prompt even without install_path
                # (SLSsteam may have been set up during download)
                logger.debug("No install_path available, proceeding with Steam restart check")
                self._steam_restart_prompted = False
                QTimer.singleShot(1000, self._prompt_for_steam_restart)

            game_name = (
                self.game_data.get("game_name", tr("MainWindow", "Game")) if self.game_data else tr("MainWindow", "Game")
            )

            logger.debug("Download completion handler finished")
        except Exception as e:
            logger.error(f"Error in download completion handler: {e}", exc_info=True)
            self.log_output.append(
                tr("MainWindow", "Error during completion: {0}").format(e)
            )

        # Hide controls after a short delay
        QTimer.singleShot(2000, lambda: self.minimal_download_widget.setVisible(False))

        # Store UI reset timer reference so we can cancel it if fixes are needed
        self._ui_reset_timer = QTimer.singleShot(
            8000, self._safe_reset_ui_state
        )  # 8 seconds, only if no fixes

        # Always prompt for Steam restart to ensure SLSsteam integration is applied
        # This will be called after fix check completes, or immediately if no install_path
        # Skip if a fix is currently being processed
        if not hasattr(self, "_steam_restart_scheduled") and not getattr(self, "_fix_processing", False):
            self._steam_restart_scheduled = True
            QTimer.singleShot(5000, self._ensure_steam_restart_prompt)

    def _on_download_error(self, error_message):
        """Handle download errors"""
        self.log_output.append(
            tr("MainWindow", "Download error: {0}").format(error_message)
        )
        self.minimal_download_widget.set_idle_state()

    def _on_download_state_changed(self, state):
        """Handle download state changes"""
        logger.debug(f"Download state changed to: {state}")

    def _on_depot_completed(self, depot_id):
        """Handle individual depot completion"""
        self.log_output.append(tr("MainWindow", "Depot {0} completed").format(depot_id))

    def _check_for_online_fixes(self):
        """Inicia verificação de Online-Fixes para o jogo baixado"""
        try:
            if not self.game_data:
                logger.warning("No game data available for Online-Fixes check")
                return

            appid = self.game_data.get("appid")
            game_name = self.game_data.get("game_name", "")

            if not appid:
                logger.warning("No AppID available for Online-Fixes check")
                return

            logger.info(f"Starting Online-Fixes check for AppID {appid}")
            self.log_output.append(
                tr("MainWindow", "Checking for Online-Fixes for {0}...").format(
                    game_name
                )
            )

            # Iniciar verificação em thread separada para não bloquear UI
            from PyQt6.QtCore import QThread

            class FixCheckThread(QThread):
                def __init__(self, online_fixes_manager, appid, game_name):
                    super().__init__()
                    self.online_fixes_manager = online_fixes_manager
                    self.appid = appid
                    self.game_name = game_name

                def run(self):
                    try:
                        self.online_fixes_manager.check_for_fixes(
                            self.appid, self.game_name
                        )
                    except Exception as e:
                        logger.error(f"Error in FixCheckThread: {e}")

                def cleanup(self):
                    """Cleanup method to prevent deletion warnings"""
                    self.online_fixes_manager = None

            self.fix_check_thread = FixCheckThread(
                self.online_fixes_manager, appid, game_name
            )
            self.fix_check_thread.start()

        except Exception as e:
            logger.error(f"Error starting Online-Fixes check: {e}")
            self.log_output.append(
                tr("MainWindow", "Error checking Online-Fixes: {0}").format(e)
            )

    def _on_fix_check_started(self, appid: int):
        """Handle Online-Fixes check start"""
        logger.info(f"Online-Fixes check started for AppID {appid}")

    def _on_fix_check_progress(self, message: str):
        """Handle Online-Fixes check progress"""
        self.log_output.append(f"{message}")

    def _on_fix_check_completed(self, result: dict):
        """Handle Online-Fixes check completion"""
        try:
            appid = result.get("appid")
            game_name = result.get("gameName", f"App_{appid}")
            generic_fix = result.get("genericFix", {})
            online_fix = result.get("onlineFix", {})

            logger.info(
                f"Online-Fixes check completed for {appid}: Generic={generic_fix.get('available')}, Online={online_fix.get('available')}"
            )

            # Set flag for fix availability
            self._fix_available = bool(
                generic_fix.get("available") or online_fix.get("available")
            )

            fixes_available = []

            if generic_fix.get("available"):
                fixes_available.append(
                    ("Generic Fix", generic_fix.get("url"), "generic")
                )

            if online_fix.get("available"):
                fixes_available.append(("Online-Fix", online_fix.get("url"), "online"))

            if fixes_available:
                # Cancel UI reset timer since we need to show fix dialog
                self._ui_reset_cancelled = True
                logger.debug("Cancelling UI reset timer - fixes dialog will be shown")

                # Usar QTimer para evitar deadlock com modais
                QTimer.singleShot(
                    100,
                    lambda: self._show_fixes_available_dialog(
                        game_name, appid, fixes_available
                    ),
                )
            else:
                self.log_output.append(f"No Online-Fixes available for {game_name}")
                logger.info(f"No Online-Fixes available for AppID {appid}")
                # Se não há fixes disponíveis, apenas mostrar prompt para reiniciar Steam
                # (SLSsteam pode ter sido configurado durante o download)
                self._steam_restart_prompted = False
                self._prompt_for_steam_restart()

        except Exception as e:
            logger.error(f"Error handling fix check completion: {e}")
            self.log_output.append(f"Error processing Online-Fixes result: {e}")
        finally:
            # Clean up the thread reference
            if hasattr(self, "fix_check_thread"):
                self.fix_check_thread = None

    def _show_fixes_available_dialog(
        self, game_name: str, appid: int, fixes_available: list
    ):
        """Mostra diálogo informativo com fixes disponíveis para aplicação"""
        try:
            from PyQt6.QtCore import Qt
            from PyQt6.QtWidgets import (
                QDialog,
                QFrame,
                QHBoxLayout,
                QLabel,
                QPushButton,
                QScrollArea,
                QVBoxLayout,
                QWidget,
            )

            from .theme import BorderRadius, Spacing, theme

            # Criar diálogo customizado
            dialog = QDialog(self)
            dialog.setWindowTitle(tr("MainWindow", "Online-Fixes Available"))
            dialog.setFixedSize(500, 400)
            dialog.setWindowModality(Qt.WindowModality.ApplicationModal)

            # Layout principal
            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
            layout.setSpacing(Spacing.MD)

            # Título e ícone
            title_layout = QHBoxLayout()
            title_label = QLabel(tr("MainWindow", "Online-Fixes Found!"))
            title_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 18px;
                    font-weight: bold;
                    color: {theme.colors.PRIMARY};
                }}
            """)
            title_layout.addWidget(title_label)
            title_layout.addStretch()
            layout.addLayout(title_layout)

            # Descrição
            desc_label = QLabel(
                tr(
                    "MainWindow",
                    "Online-Fixes were found for <b>{0}</b>! "
                    "These fixes allow the game to work without an internet connection.",
                ).format(game_name)
            )
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 14px;
                    color: {theme.colors.TEXT_PRIMARY};
                    padding: {Spacing.SM}px;
                    background: {theme.colors.SURFACE};
                    border-radius: {BorderRadius.MEDIUM};
                }}
            """)
            layout.addWidget(desc_label)

            # Scroll area para lista de fixes
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet(f"""
                QScrollArea {{
                    border: 1px solid {theme.colors.BORDER};
                    border-radius: {BorderRadius.MEDIUM};
                    background: {theme.colors.BACKGROUND};
                }}
            """)

            scroll_widget = QWidget()
            scroll_layout = QVBoxLayout(scroll_widget)
            scroll_layout.setSpacing(Spacing.SM)

            # Adicionar cada fix disponível
            for fix_name, fix_url, fix_type in enumerate(fixes_available):
                fix_frame = QFrame()
                fix_frame.setStyleSheet(f"""
                    QFrame {{
                        background: {theme.colors.SURFACE};
                        border: 1px solid {theme.colors.BORDER};
                        border-radius: {BorderRadius.MEDIUM};
                        padding: {Spacing.SM}px;
                    }}
                """)

                fix_layout = QVBoxLayout(fix_frame)

                # Nome do fix
                fix_title = QLabel(fix_name)
                fix_title.setStyleSheet(f"""
                    QLabel {{
                        font-size: 16px;
                        font-weight: bold;
                        color: {theme.colors.PRIMARY};
                    }}
                """)
                fix_layout.addWidget(fix_title)

                # Descrição do fix
                if fix_type == "generic":
                    fix_desc = QLabel(
                        tr(
                            "MainWindow",
                            "• Bypasses basic DRM protection\n• Works for most games",
                        )
                    )
                else:  # online
                    fix_desc = QLabel(
                        tr(
                            "MainWindow",
                            "• Enables online features offline\n• Multiplayer/LAN support",
                        )
                    )

                fix_desc.setStyleSheet(f"""
                    QLabel {{
                        font-size: 12px;
                        color: {theme.colors.TEXT_SECONDARY};
                        padding-left: {Spacing.SM}px;
                    }}
                """)
                fix_layout.addWidget(fix_desc)

                # Botão de aplicação
                apply_btn = QPushButton(
                    tr("MainWindow", "Install {0}").format(fix_name)
                )
                apply_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {theme.colors.PRIMARY};
                        color: white;
                        border: none;
                        border-radius: {BorderRadius.SMALL};
                        padding: {Spacing.SM}px {Spacing.MD}px;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background: {theme.colors.PRIMARY_DARK};
                    }}
                """)
                apply_btn.clicked.connect(
                    lambda checked,
                    url=fix_url,
                    type=fix_type,
                    name=fix_name: self._apply_fix_from_dialog(
                        dialog, appid, url, type, name, game_name
                    )
                )
                fix_layout.addWidget(apply_btn)

                scroll_layout.addWidget(fix_frame)

            scroll.setWidget(scroll_widget)
            layout.addWidget(scroll)

            # Botões de ação principal
            buttons_layout = QHBoxLayout()
            buttons_layout.addStretch()

            # Botão "Don't Install"
            skip_btn = QPushButton(tr("MainWindow", "Don't Install Any Fix"))
            skip_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {theme.colors.SURFACE};
                    color: {theme.colors.TEXT_PRIMARY};
                    border: 1px solid {theme.colors.BORDER};
                    border-radius: {BorderRadius.SMALL};
                    padding: {Spacing.SM}px {Spacing.MD}px;
                }}
                QPushButton:hover {{
                    background: {theme.colors.SURFACE_LIGHT};
                }}
            """)
            skip_btn.clicked.connect(dialog.reject)
            buttons_layout.addWidget(skip_btn)

            layout.addLayout(buttons_layout)

            # Mostrar diálogo
            result = dialog.exec()

            # Se o usuário fechou sem escolher, mostrar mensagem informativa
            if result == QDialog.DialogCode.Rejected:
                self.log_output.append(
                    tr(
                        "MainWindow", "User chose not to install Online-Fixes for {0}"
                    ).format(game_name)
                )
                logger.info(
                    f"User declined Online-Fixes installation for AppID {appid}"
                )

                # Fix was declined, clear the flag
                self._fix_available = False

                # Reset UI reset cancellation flag since dialog is closed
                self._ui_reset_cancelled = False

                # Still prompt for Steam restart in case SLSsteam was set up during download
                # Reset the flag to allow the prompt even though no fix was installed
                self._steam_restart_prompted = False
                self._prompt_for_steam_restart()

                # NOTA: Não mostrar modal "No Fix Installed" aqui
                # Apenas o modal de reiniciar Steam deve aparecer para evitar confusão

                # Schedule UI reset after Steam restart prompt handling
                QTimer.singleShot(3000, self._safe_reset_ui_state)

        except Exception as e:
            logger.error(f"Error showing fixes available dialog: {e}")
            self.log_output.append(
                tr("MainWindow", "Error showing fixes dialog: {0}").format(e)
            )

    def _on_fix_download_progress(self, message: str):
        """Handle Online-Fixes download progress"""
        self.log_output.append(tr("MainWindow", "Fix download: {0}").format(message))

    def _on_fix_applied(self, fix_type: str):
        """Handle successful Online-Fixes application"""
        self.log_output.append(f"✓ {fix_type.title()} Fix successfully applied!")
        # Fix was applied, clear the flag
        self._fix_available = False
        # Mark that fix processing is complete
        self._fix_processing = False
        # Mark that a fix was recently applied to allow Steam restart prompt
        self._fix_applied_recently = True
        # Reset steam restart prompt flag to allow new prompt after fix
        self._steam_restart_prompted = False
        # Clear any existing timers to avoid multiple calls
        if hasattr(self, "_steam_restart_timer"):
            self._steam_restart_timer.stop()
            self._steam_restart_timer.deleteLater()
        
        # Trigger Steam restart prompt after fix is fully applied
        self._steam_restart_timer = QTimer()
        self._steam_restart_timer.setSingleShot(True)
        self._steam_restart_timer.timeout.connect(self._prompt_for_steam_restart)
        self._steam_restart_timer.start(1000)

    def _on_fix_error(self, error_message: str):
        """Handle Online-Fixes errors"""
        self.log_output.append(tr("MainWindow", "Fix error: {0}").format(error_message))
        # Clear fix processing flag on error
        self._fix_processing = False

    def _confirm_cancel_download(self):
        """Confirm download cancellation with user"""
        reply = QMessageBox.question(
            self,
            tr("MainWindow", "Cancel Download"),
            tr("MainWindow", "Are you sure you want to cancel the current download?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.download_manager.cancel_download()

    def _apply_fix_from_dialog(
        self,
        dialog: QDialog,
        appid: int,
        fix_url: str,
        fix_type: str,
        fix_name: str,
        game_name: str,
    ):
        """Aplica Online-Fix a partir de um diálogo"""
        try:
            # Mark that fix dialog is open to prevent premature UI reset
            self._fix_dialog_open = True

            # Obter caminho de instalação do jogo
            install_path = self._get_current_install_path()
            if not install_path:
                self.log_output.append(
                    tr(
                        "MainWindow",
                        "Error: Could not determine game installation path",
                    )
                )
                QMessageBox.warning(
                    self,
                    tr("MainWindow", "Path Error"),
                    tr(
                        "MainWindow",
                        "Could not determine the game installation path. "
                        "The download session may have been cleared.",
                    ),
                )
                self._fix_dialog_open = False
                return

            self.log_output.append(
                tr("MainWindow", "Installing {0}...").format(fix_name)
            )

            # Confirmar instalação
            reply = QMessageBox.question(
                self,
                tr("MainWindow", "Install {0}").format(fix_name),
                tr("MainWindow", "Install {0} for {1}?\n\nPath: {2}").format(
                    fix_name, game_name, install_path
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Adicionar tratamento de exceções ao redor da aplicação do fix
                try:
                    success = self.online_fixes_manager.apply_fix(
                        appid, fix_url, install_path, fix_type, game_name
                    )
                    if not success:
                        raise Exception(tr("MainWindow", "Failed to start fix installation"))

                    # Fix installation started successfully - close the fixes dialog
                    dialog.accept()

                    # Mark that fix processing has started
                    self._fix_processing = True

                    # Reset UI reset cancellation flag since fix is being applied
                    self._ui_reset_cancelled = False

                except Exception as fix_error:
                    logger.error(f"Error starting fix installation: {fix_error}")
                    self.log_output.append(
                        tr("MainWindow", "Error starting installation: {0}").format(
                            fix_error
                        )
                    )
                    QMessageBox.critical(
                        self,
                        tr("MainWindow", "Installation Error"),
                        tr(
                            "MainWindow", "Failed to start {0} installation:\n{1}"
                        ).format(fix_name, str(fix_error)),
                    )
            else:
                self.log_output.append(
                    tr("MainWindow", "Installation cancelled by user")
                )

        except Exception as e:
            logger.error(f"Error applying fix from dialog: {e}", exc_info=True)
            self.log_output.append(
                tr("MainWindow", "Error installing fix: {0}").format(e)
            )
            QMessageBox.critical(
                self,
                tr("MainWindow", "Installation Error"),
                tr("MainWindow", "An unexpected error occurred:\n{0}").format(str(e)),
            )
        finally:
            # Always reset the flag when done
            self._fix_dialog_open = False

            # Reset UI reset cancellation flag since fix operation is complete
            self._ui_reset_cancelled = False

            # Trigger UI reset after a short delay if no other operations are pending
            QTimer.singleShot(2000, self._safe_reset_ui_state)

    def _get_current_install_path(self) -> str:
        """Obtém caminho de instalação do jogo atual"""
        try:
            if not self.game_data:
                return ""

            appid = self.game_data.get("appid")
            if not appid:
                return ""

            # Priority 1: Use current_dest_path if available
            if self.current_dest_path:
                install_path = self.download_manager._get_game_install_directory(
                    self.current_dest_path, self.game_data
                )
                if install_path and os.path.exists(install_path):
                    logger.debug(
                        f"Using install path from current_dest_path: {install_path}"
                    )
                    return install_path

            # Priority 2: Tentar obter da sessão atual do download manager
            if (
                hasattr(self.download_manager, "current_session")
                and self.download_manager.current_session
            ):
                dest_path = self.download_manager.current_session.dest_path
                install_path = self.download_manager._get_game_install_directory(
                    dest_path, self.game_data
                )
                if install_path and os.path.exists(install_path):
                    logger.debug(
                        f"Using install path from current session: {install_path}"
                    )
                    return install_path

            # Priority 3: Se não houver sessão ativa, tentar obter da biblioteca Steam
            from core import steam_helpers

            steam_libraries = steam_helpers.get_steam_libraries()

            for library in steam_libraries:
                acf_path = os.path.join(
                    library, "steamapps", f"appmanifest_{appid}.acf"
                )
                if os.path.exists(acf_path):
                    install_dir = steam_helpers.parse_acf_file(acf_path).get(
                        "installdir"
                    )
                    if install_dir:
                        install_path = os.path.join(
                            library, "steamapps", "common", install_dir
                        )
                        if os.path.exists(install_path):
                            logger.debug(
                                f"Using install path from Steam library: {install_path}"
                            )
                            return install_path

            logger.warning(f"Could not find install path for appid {appid}")
            return ""

        except Exception as e:
            logger.error(f"Error getting install path: {e}")
            return ""

    def _on_zip_processed(self, game_data):
        # Don't clear current_dest_path - preserve it for potential fix installation
        self.game_data = game_data
        # Reset fix availability for new game
        self._fix_available = False
        # Reset fix processing state for new game
        self._fix_processing = False
        # Reset completion message control for new game
        self._completion_message_shown = False
        # Reset Steam restart controls for new game
        self._steam_restart_prompted = False
        if hasattr(self, "_steam_restart_scheduled"):
            delattr(self, "_steam_restart_scheduled")

        # Reset UI elements after ZIP processing
        self.drop_text_label.setVisible(False)
        self.title_bar.select_file_button.setVisible(False)

        if self.game_data and self.game_data.get("depots"):
            self._show_depot_selection_dialog()
        else:
            QMessageBox.warning(
                self,
                tr("MainWindow", "No Depots Found"),
                tr(
                    "MainWindow",
                    "Zip file processed, but no downloadable depots were found.",
                ),
            )
            self._reset_ui_state()

    def _show_depot_selection_dialog(self):
        if not self.game_data:
            self.log_output.append(
                tr("MainWindow", "Error: No game data available for depot selection")
            )
            return
        depot_sizes = self.game_data.get("depot_sizes", {})
        total_game_size = self.game_data.get("total_game_size", 0)
        self.depot_dialog = DepotSelectionDialog(
            self.game_data["appid"],
            self.game_data["depots"],
            depot_sizes,
            self,
            total_game_size,
        )
        if self.depot_dialog.exec():
            selected_depots = self.depot_dialog.get_selected_depots()
            # Get total game size from dialog
            total_game_size = self.depot_dialog.get_total_game_size()
            # Store the header image from dialog for later use in download
            dialog_image = self.depot_dialog.get_header_image()
            if dialog_image and not dialog_image.isNull():
                self.game_header_image = dialog_image
                logger.debug("Stored header image from depot dialog")
            if not selected_depots:
                self._reset_ui_state()
                return

            dest_path = None
            slssteam_mode = self.settings.value("slssteam_mode", True, type=bool)

            logger.debug(f"SLSsteam mode: {slssteam_mode}")

            if slssteam_mode:
                if self.game_data and self.game_data.get("dlcs"):
                    dlc_dialog = DlcSelectionDialog(self.game_data["dlcs"], self)
                    if dlc_dialog.exec():
                        self.game_data["selected_dlcs"] = dlc_dialog.get_selected_dlcs()

                libraries = steam_helpers.get_steam_libraries()
                logger.debug(f"Found Steam libraries: {libraries}")
                if libraries:
                    dialog = SteamLibraryDialog(libraries, self)
                    if dialog.exec():
                        dest_path = dialog.get_selected_path()
                    else:
                        self._reset_ui_state()
                        return
                else:
                    dest_path = QFileDialog.getExistingDirectory(
                        self, "Select Destination Folder"
                    )
            else:
                dest_path = QFileDialog.getExistingDirectory(
                    self, "Select Destination Folder"
                )

            if dest_path:
                self._start_download(
                    selected_depots, dest_path, slssteam_mode, total_game_size
                )
            else:
                self._reset_ui_state()
        else:
            self._reset_ui_state()

    def _start_download(
        self, selected_depots, dest_path, slssteam_mode, total_game_size=0
    ):
        # Check SLSsteam prerequisite before starting download
        if not self._check_slssteam_prerequisite():
            return

        # Clear any previous dest_path and set new one
        self.current_dest_path = dest_path
        self.slssteam_mode_was_active = slssteam_mode

        # Reset completion message control for new download
        self._completion_message_shown = False
        if hasattr(self, "_fix_applied_recently"):
            delattr(self, "_fix_applied_recently")

        # Reset fix processing control for new download
        self._fix_processing = False
        if hasattr(self, "_steam_restart_scheduled"):
            delattr(self, "_steam_restart_scheduled")

        # Reset Steam restart control for new download
        self._steam_restart_prompted = False

        # Store current game data for Online-Fixes
        self._current_game_data = self.game_data.copy() if self.game_data else None
        logger.debug(f"Stored game data for Online-Fixes: {self._current_game_data}")

        # Hide drop zone and show progress
        self.drop_text_label.setVisible(False)
        # Show game image display (integrado no widget minimalista)
        if self.game_data:
            self.game_title_label.setText(
                self.game_data.get("game_name", "Unknown Game")
            )
            # Load game header image asynchronously
            self._load_game_image()

        # Start download GIF
        random_gif_path = random.choice(self.download_gifs)
        download_movie = QMovie(random_gif_path)
        if download_movie.isValid():
            self.current_movie = download_movie
            self.download_drop_label.setMovie(self.current_movie)
            self.current_movie.start()

        # Configurar UI para download com widget minimalista

        # Mostrar widget minimalista de download
        game_name = (
            self.game_data.get("game_name", "Unknown Game") if self.game_data else None
        )

        # Enhanced game image retrieval with multiple fallbacks
        game_image = self._get_game_image_for_download()

        self.minimal_download_widget.set_downloading_state(game_name, game_image)

        # Ensure the download widget is visible
        self.minimal_download_widget.show()

        # Switch to download page (GIF + download widget vertically)
        self.main_stacked_widget.setCurrentIndex(1)

        # Hide old container to avoid duplication
        self.game_image_container.hide()

        # Connect minimalist widget signals to download manager
        self.minimal_download_widget.pause_clicked.connect(
            self.download_manager.pause_download
        )
        self.minimal_download_widget.resume_clicked.connect(
            self.download_manager.resume_download
        )
        # Cancel is already connected to _confirm_cancel_download

        # Calculate total download size
        # Use total_game_size from dialog if available, otherwise calculate from selected depots
        if total_game_size > 0:
            total_size = total_game_size
        else:
            total_size = 0
            depot_sizes = self.game_data.get("depot_sizes", {})
            for depot_id in selected_depots:
                total_size += depot_sizes.get(depot_id, 0)

        # Set size in download widget
        self.minimal_download_widget.set_download_size(total_size)

        # Start download using NEW DownloadManager
        if self.game_data:
            session_id = self.download_manager.start_download(
                self.game_data, selected_depots, dest_path
            )
        else:
            session_id = None

        if session_id:
            self.log_output.append(
                tr("MainWindow", "Download started (Session: {0}...)").format(
                    session_id[:8]
                )
            )
            self._start_speed_monitor()
        else:
            self.log_output.append(tr("MainWindow", "Failed to start download"))
            self._reset_ui_state()

    def _get_game_image_for_download(self):
        """Enhanced game image retrieval with multiple fallback strategies"""
        game_image = None

        # Strategy 1: Try to get from current game_header_label (most likely to have image)
        if hasattr(self, "game_header_label") and self.game_header_label.pixmap():
            pixmap = self.game_header_label.pixmap()
            if pixmap and not pixmap.isNull():
                game_image = pixmap
                logger.debug("Using image from game_header_label")

        # Strategy 2: Try from cached game_header_image
        if (
            not game_image
            and hasattr(self, "game_header_image")
            and self.game_header_image
        ):
            if not self.game_header_image.isNull():
                game_image = self.game_header_image
                logger.debug("Using cached game_header_image")

        # Strategy 3: Try to get from enhanced image cache manager (multiple formats)
        if not game_image and self.game_data:
            app_id = self.game_data.get("appid")
            if app_id:
                # Try all possible image URLs from enhanced manager
                urls = self.game_image_manager.get_image_urls(str(app_id))
                for url_info in urls:
                    cached_image = self.image_cache_manager.get_cached_image(
                        str(app_id), url_info["url"]
                    )
                    if cached_image and not cached_image.isNull():
                        game_image = cached_image
                        logger.debug(f"Using cached image from {url_info['format']}")
                        break

        # Strategy 4: Create fallback placeholder
        if not game_image:
            game_image = self._create_fallback_image()
            logger.debug("Using fallback image")

        return game_image

    def _create_fallback_image(self):
        """Create a fallback placeholder image when no game image is available"""
        from PyQt6.QtGui import QPainter, QPen, QPixmap

        # Create a 120x56 pixmap (same size as game_image_label)
        from .theme import theme

        pixmap = QPixmap(120, 56)
        pixmap.fill(
            theme.colors.get_qcolor(theme.colors.SURFACE_DARK)
        )  # Dark background

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw game controller icon
        painter.setPen(QPen(theme.colors.get_qcolor(theme.colors.BORDER_LIGHT), 2))
        painter.setBrush(theme.colors.get_qcolor(theme.colors.BORDER))

        # Simple controller shape
        painter.drawRoundedRect(35, 18, 50, 20, 8, 8)
        painter.drawRoundedRect(25, 22, 15, 12, 4, 4)
        painter.drawRoundedRect(80, 22, 15, 12, 4, 4)

        # Draw dots for buttons
        painter.setPen(QPen(theme.colors.get_qcolor(theme.colors.BORDER_LIGHT), 1))
        painter.setBrush(theme.colors.get_qcolor(theme.colors.BORDER))
        painter.drawEllipse(85, 25, 3, 3)
        painter.drawEllipse(90, 25, 3, 3)
        painter.drawEllipse(87, 28, 3, 3)
        painter.drawEllipse(87, 22, 3, 3)

        painter.end()

        return pixmap

    def _load_game_image(self):
        """Load game header image using existing UI components"""
        try:
            if self.game_data:
                # Set game title
                game_name = self.game_data.get("game_name", "Unknown Game")
                self.game_title_label.setText(game_name)

                # Fetch header image
                app_id = self.game_data.get("appid") if self.game_data else None
                if app_id:
                    self._fetch_game_header_image(app_id)
        except Exception as e:
            logger.warning(f"Failed to load game image: {e}")

    def _create_acf_file(self):
        self.log_output.append(
            tr("MainWindow", "Generating Steam .acf manifest file...")
        )

        if not self.game_data:
            self.log_output.append(tr("MainWindow", "Error: No game data available"))
            return

        safe_game_name_fallback = (
            re.sub(r"[^\w\s-]", "", self.game_data.get("game_name", ""))
            .strip()
            .replace(" ", "_")
        )
        install_folder_name = self.game_data.get("installdir", safe_game_name_fallback)
        if not install_folder_name:
            install_folder_name = f"App_{self.game_data['appid']}"

        acf_path = os.path.join(
            self.current_dest_path,
            "steamapps",
            f"appmanifest_{self.game_data['appid']}.acf",
        )

        acf_content = f'''
"AppState"
{{
    "appid"         "{self.game_data["appid"]}"
    "Universe"       "1"
    "name"          "{self.game_data["game_name"]}"
    "StateFlags"    "4"
    "installdir"    "{install_folder_name}"
    "LastUpdated"   "0"
    "UpdateResult"  "0"
    "SizeOnDisk"    "0"
    "buildid"       "0"
    "LastOwner"     "0"
    "BytesToDownload"   "0"
    "BytesDownloaded"   "0"
    "AutoUpdateBehavior"   "0"
    "AllowOtherDownloadsWhileRunning"   "0"
    "ScheduledAutoUpdate"   "0"
}}
'''

        try:
            with open(acf_path, "w", encoding="utf-8") as f:
                f.write(acf_content)
            self.log_output.append(
                tr("MainWindow", "Created .acf file at {0}").format(acf_path)
            )

            # Limpar cache para que o novo jogo apareça na lista
            from core.game_manager import GameManager

            GameManager.clear_games_cache()
            self.log_output.append(
                tr("MainWindow", "Cleared games cache - new game will be visible")
            )

            # Forçar atualização dos cards de informação na UI
            if hasattr(self, "games_card"):
                self.games_card._update_stats(force_refresh=True)
            if hasattr(self, "storage_card"):
                self.storage_card._update_storage(force_refresh=True)
        except IOError as e:
            self.log_output.append(
                tr("MainWindow", "Error creating .acf file: {0}").format(e)
            )

    def _handle_task_error(self, error_info):
        _, error_value, _ = error_info
        logger.error(f"Task error occurred: {error_value}", exc_info=True)
        QMessageBox.critical(
            self,
            tr("MainWindow", "Error"),
            tr("MainWindow", "An error occurred: {0}").format(error_value),
        )
        # 🐛 FIX: Clean up ZIP task and runner references on error
        if hasattr(self, "zip_task"):
            self.zip_task = None
        if hasattr(self, "task_runner"):
            self.task_runner = None
        self._reset_ui_state()
        self._stop_speed_monitor()

    def _reset_ui_state(self):
        if self.current_movie:
            self.current_movie.stop()
        if self.main_movie.isValid():
            self.drop_label.setMovie(self.main_movie)
            self.main_movie.start()
            self.current_movie = self.main_movie

        self.drop_text_label.setVisible(True)
        self.drop_text_label.setText(tr("MainWindow", "Drag and Drop Zip here"))

        self.game_image_container.setVisible(False)
        self.title_bar.select_file_button.setVisible(True)  # Show button again
        # Switch back to normal page (GIF + info cards side by side)
        self.main_stacked_widget.setCurrentIndex(0)

        # 🐛 FIX: Clean up state variables but preserve critical data for fix operations
        self.game_data = None
        # Don't clear current_dest_path immediately - it might be needed for fix installation
        # It will be cleared when a new ZIP is processed
        self.slssteam_mode_was_active = False
        self._steam_restart_prompted = False  # Reset flag for next download
        self.zip_task = None  # Ensure ZIP task is cleaned up

        # Clean up task runner and threads properly with enhanced safety
        if self.task_runner:
            try:
                # Check if thread exists and is valid before accessing
                if (
                    hasattr(self.task_runner, "thread")
                    and self.task_runner.thread is not None
                ):
                    thread = self.task_runner.thread
                    if thread.isRunning():
                        thread.quit()
                        if not thread.wait(3000):  # Increased timeout
                            logger.warning("Task runner thread did not finish cleanly")
                            thread.terminate()
                            thread.wait(1000)

                    # Clear reference safely
                    try:
                        self.task_runner.thread = None
                    except (AttributeError, TypeError):
                        # Thread already deleted, which is fine
                        pass

                # Clear task runner reference
                self.task_runner = None

            except Exception as e:
                # Handle PyQt6 object deletion errors gracefully
                if "wrapped C/C++ object" in str(e):
                    logger.debug("PyQt6 object already deleted during UI reset")
                else:
                    logger.warning(f"Error cleaning up task runner thread: {e}")

                # Force clear references even if cleanup failed
                self.task_runner = None

        logger.debug("UI state fully reset, ready for next operation")

    def _safe_reset_ui_state(self):
        """Safe reset that preserves critical data if fix might be applied"""
        # Check if UI reset was cancelled due to fix operations
        if hasattr(self, "_ui_reset_cancelled") and self._ui_reset_cancelled:
            logger.debug("UI reset cancelled - fix operations in progress")
            return

        # Only reset if we're not in the middle of fix operations
        if not hasattr(self, "_fix_dialog_open") or not self._fix_dialog_open:
            self._reset_ui_state()
        else:
            logger.debug("Skipping UI reset - fix dialog might be open")

    def _start_speed_monitor(self):
        self.speed_monitor_task = SpeedMonitorTask()
        self.speed_monitor_task.speed_update.connect(
            self.minimal_download_widget.update_speed
        )
        self.speed_monitor_runner = TaskRunner()
        self.speed_monitor_runner.run(self.speed_monitor_task.run)

    def _stop_speed_monitor(self):
        if self.speed_monitor_task:
            self.speed_monitor_task.stop()
            self.speed_monitor_task = None

        # Clean up speed monitor task runner and thread
        if hasattr(self, "speed_monitor_runner") and self.speed_monitor_runner:
            try:
                if (
                    hasattr(self.speed_monitor_runner, "thread")
                    and self.speed_monitor_runner.thread
                ):
                    if self.speed_monitor_runner.thread.isRunning():
                        self.speed_monitor_runner.thread.quit()
                        self.speed_monitor_runner.thread.wait(1000)
            except Exception as e:
                logger.warning(f"Error cleaning up speed monitor thread: {e}")
            self.speed_monitor_runner = None

    def _prompt_for_steam_restart(self):
        """Prompt user to restart Steam after SLSsteam setup"""
        # Allow multiple prompts if they come from different operations (like after fixes)
        # But avoid spamming in the same operation
        if self._steam_restart_prompted:
            logger.debug("Steam restart already prompted for this operation, skipping")
            return

        self._steam_restart_prompted = True
        logger.debug(
            f"Steam restart prompt - _steam_restart_prompted: {self._steam_restart_prompted}"
        )
        logger.debug(
            f"Steam restart prompt - _fix_applied_recently: {hasattr(self, '_fix_applied_recently')}"
        )

        reply = QMessageBox.question(
            self,
            tr("MainWindow", "SLSsteam Integration"),
            tr(
                "MainWindow",
                "SLSsteam files have been created. Would you like to restart Steam now to apply the changes?",
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            logger.info("User agreed to restart Steam.")
            self.log_output.append(tr("MainWindow", "Closing Steam..."))

            if sys.platform == "linux":
                if not steam_helpers.kill_steam_process():
                    self.log_output.append(
                        tr(
                            "MainWindow",
                            "Steam process not found, attempting to launch directly.",
                        )
                    )
                else:
                    self.log_output.append(
                        tr(
                            "MainWindow",
                            "Steam closed successfully. Waiting 3 seconds before restart...",
                        )
                    )
                    # Wait for Steam to fully close - use non-blocking approach
                    import time

                    start_time = time.time()
                    while time.time() - start_time < 3:
                        QApplication.processEvents()
                        time.sleep(0.1)

                self.log_output.append(tr("MainWindow", "Restarting Steam..."))
                status = steam_helpers.start_steam()

                if status == "NEEDS_USER_PATH":
                    self.log_output.append(
                        tr(
                            "MainWindow",
                            "SLSsteam.so not found. Please locate it manually.",
                        )
                    )
                    filePath, _ = QFileDialog.getOpenFileName(
                        self,
                        tr("MainWindow", "Select SLSsteam.so"),
                        os.path.expanduser("~"),
                        "SLSsteam.so (SLSsteam.so)",
                    )
                    if filePath:
                        if not steam_helpers.start_steam_with_path(filePath):
                            QMessageBox.warning(
                                self,
                                tr("MainWindow", "Execution Failed"),
                                tr(
                                    "MainWindow",
                                    "Could not start Steam with the selected file.",
                                ),
                            )
                    else:
                        self.log_output.append(
                            tr("MainWindow", "User cancelled file selection.")
                        )

                elif status == "FAILED":
                    QMessageBox.warning(
                        self,
                        tr("MainWindow", "Steam Not Found"),
                        tr(
                            "MainWindow",
                            "Could not restart Steam automatically. Please start it manually.",
                        ),
                    )

            else:
                steam_helpers.kill_steam_process()
                if not steam_helpers.start_steam() == "SUCCESS":
                    QMessageBox.warning(
                        self,
                        tr("MainWindow", "Steam Not Found"),
                        tr(
                            "MainWindow",
                            "Could not restart Steam automatically. Please start it manually.",
                        ),
                    )

    def _ensure_steam_restart_prompt(self):
        """Ensure Steam restart prompt is shown, but avoid duplication"""
        # Skip if a fix is currently being processed
        if self._fix_processing:
            logger.debug("Fix is currently being processed, skipping Steam restart prompt")
            return

        # Reset the flag to allow the prompt and call the existing method
        if hasattr(self, "_steam_restart_prompted") and self._steam_restart_prompted:
            # If already prompted in this session, skip to avoid spam
            logger.debug("Steam restart already prompted, skipping duplicate prompt")
            return

        logger.debug("Ensuring Steam restart prompt is shown")
        self._steam_restart_prompted = False
        self._prompt_for_steam_restart()

    def _fetch_game_header_image(self, app_id):
        """Fetch game header image for display during download using enhanced manager."""
        # Use enhanced image manager with multiple fallbacks
        self.image_thread = self.game_image_manager.get_game_image(
            str(app_id), preferred_format="header"
        )
        self.image_thread.image_ready.connect(self._on_enhanced_game_image_ready)
        self.image_thread.image_failed.connect(self._on_enhanced_game_image_error)

    def _display_game_image(self, pixmap):
        """Display game image with proper scaling"""
        if not pixmap or pixmap.isNull():
            self._display_no_image()
            return

        self.game_header_image = pixmap

        # Calculate size maintaining aspect ratio with max 184x69
        scaled_pixmap = pixmap.scaled(
            184,
            69,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        # Adjust label size to exactly the scaled image size
        self.game_header_label.setFixedSize(
            scaled_pixmap.width(), scaled_pixmap.height()
        )
        self.game_header_label.setPixmap(scaled_pixmap)

    def _display_no_image(self):
        """Display enhanced placeholder when no image is available"""
        fallback_pixmap = self._create_fallback_image_large()
        self.game_header_label.setPixmap(fallback_pixmap)
        self.game_header_label.setFixedSize(184, 69)  # Steam header size

    def _on_enhanced_game_image_ready(self, app_id, pixmap, source_info):
        """Handle successfully fetched game image from enhanced manager."""
        if pixmap and not pixmap.isNull():
            self._display_game_image(pixmap)
            self.game_header_image = pixmap
            logger.debug(f"Loaded game image for app {app_id} from {source_info}")
        else:
            self._display_no_image()

    def _on_enhanced_game_image_error(self, app_id, error_message):
        """Handle game image fetch error from enhanced manager."""
        logger.warning(f"Failed to fetch image for app {app_id}: {error_message}")
        self._display_no_image()

    def _create_fallback_image_large(self):
        """Create a large fallback placeholder image for header display"""
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QFont, QPainter, QPen, QPixmap

        # Create a 184x69 pixmap (Steam header size)
        from .theme import theme

        pixmap = QPixmap(184, 69)
        pixmap.fill(
            theme.colors.get_qcolor(theme.colors.SURFACE_DARK)
        )  # Dark background

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw game controller icon
        painter.setPen(QPen(theme.colors.get_qcolor(theme.colors.BORDER_LIGHT), 2))
        painter.setBrush(theme.colors.get_qcolor(theme.colors.BORDER))

        # Simple controller shape centered
        controller_x = 92 - 30  # Center horizontally
        controller_y = 34 - 10  # Center vertically
        painter.drawRoundedRect(controller_x, controller_y, 60, 20, 8, 8)
        painter.drawRoundedRect(controller_x - 10, controller_y + 4, 20, 12, 4, 4)
        painter.drawRoundedRect(controller_x + 50, controller_y + 4, 20, 12, 4, 4)

        # Draw dots for buttons
        painter.setPen(QPen(theme.colors.get_qcolor(theme.colors.BORDER_LIGHT), 1))
        painter.setBrush(theme.colors.get_qcolor(theme.colors.BORDER))
        painter.drawEllipse(controller_x + 55, controller_y + 7, 4, 4)
        painter.drawEllipse(controller_x + 62, controller_y + 7, 4, 4)
        painter.drawEllipse(controller_x + 58, controller_y + 11, 4, 4)
        painter.drawEllipse(controller_x + 58, controller_y + 3, 4, 4)

        # Add "No Image" text
        painter.setPen(theme.colors.get_qcolor(theme.colors.TEXT_DISABLED))
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "No Image")

        painter.end()

        return pixmap

    def _handle_steam_schema_generation(self):
        """Handle Steam Schema generation with proper error handling"""
        try:
            from utils.settings import is_steam_schema_enabled

            if not is_steam_schema_enabled():
                logger.debug("Steam schema is disabled")
                return

            from core.steam_schema_integration import SteamSchemaIntegration

            schema_integration = SteamSchemaIntegration()

            app_id = self.game_data.get("appid")
            if not app_id:
                logger.warning("App ID not found for Steam Schema generation")
                return

            self.log_output.append(tr("MainWindow", "Generating Steam Schema..."))
            success = schema_integration.get_game_schema_steam_client(app_id)

            if success:
                self.log_output.append(
                    tr("MainWindow", "Steam Schema generated successfully!")
                )
            else:
                self.log_output.append(
                    tr("MainWindow", "Steam Schema generation completed with warnings")
                )

        except ImportError:
            logger.warning("Steam schema utilities not available")
        except Exception as e:
            logger.warning(f"Failed to generate Steam achievements: {e}")
            self.log_output.append(f"Steam Schema generation failed: {e}")

    def open_steam_login(self):
        """Steam login is now handled by SLScheevo - no dialog needed"""
        QMessageBox.information(
            self,
            tr("MainWindow", "Steam Login"),
            tr(
                "MainWindow",
                "Steam login is now handled by SLScheevo!\n\nSLScheevo will automatically login when generating schemas.",
            ),
        )

    def _check_slssteam_prerequisite(self) -> bool:
        """Check if SLSsteam is ready for operations, show dialog if not"""
        if (
            not hasattr(self.title_bar, "slssteam_status")
            or not self.title_bar.slssteam_status
        ):
            QMessageBox.critical(
                self,
                tr("MainWindow", "SLSsteam Error"),
                tr(
                    "MainWindow",
                    "SLSsteam status widget not available. Please restart ACCELA.",
                ),
            )
            return False

        if not self.title_bar.slssteam_status.can_start_operations():
            # Show blocking dialog with setup option
            blocking_msg = self.title_bar.slssteam_status.get_blocking_message()
            reply = QMessageBox.critical(
                self,
                tr("MainWindow", "SLSsteam Required"),
                tr(
                    "MainWindow",
                    "SLSsteam is required for ACCELA to function.\n\n{0}\n\n"
                    "Would you like to configure SLSsteam now?",
                ).format(blocking_msg),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Trigger setup dialog
                self.title_bar.slssteam_status._on_action_clicked()

            return False

        return True

    def _on_slssteam_setup_requested(self):
        """Handle SLSsteam setup completion"""
        if (
            hasattr(self.title_bar, "slssteam_status")
            and self.title_bar.slssteam_status
            and self.title_bar.slssteam_status.is_slssteam_ready()
        ):
            # Auto-enable slssteam_mode when SLSsteam becomes ready
            self.settings.setValue("slssteam_mode", True)

    def _open_game_manager(self):
        """Open the Game Manager dialog for deleting ACCELA games"""
        try:
            dialog = GameDeletionDialog(self)
            dialog.exec()
            logger.debug("Game Manager dialog opened and closed")
        except Exception as e:
            logger.error(f"Error opening Game Manager: {e}")
            QMessageBox.critical(
                self,
                tr("MainWindow", "Error"),
                tr("MainWindow", "Failed to open Game Manager: {0}").format(e),
            )

    def _open_backup_dialog(self):
        """Open the Backup/Restore dialog for Steam stats"""
        try:
            from ui.backup_dialog import BackupDialog

            dialog = BackupDialog(self)
            dialog.exec()
            logger.debug("Backup dialog opened and closed")
        except Exception as e:
            logger.error(f"Error opening Backup dialog: {e}")
            QMessageBox.critical(
                self,
                tr("MainWindow", "Error"),
                tr("MainWindow", "Failed to open Backup dialog: {0}").format(e),
            )

    def closeEvent(self, event):
        self._stop_speed_monitor()

        # Clean up download manager and its threads
        if hasattr(self, "download_manager") and self.download_manager:
            self.download_manager.cleanup()

        # Clean up online fixes manager
        if hasattr(self, "online_fixes_manager") and self.online_fixes_manager:
            self.online_fixes_manager.cleanup()

        # Clean up image thread if exists
        if hasattr(self, "image_thread") and self.image_thread:
            try:
                if self.image_thread.isRunning():
                    self.image_thread.quit()
                    self.image_thread.wait(3000)
                # Clear reference
                self.image_thread = None
            except Exception as e:
                # Silenciar warning de deleção de C/C++ object - é normal no PyQt6
                if "wrapped C/C++ object" not in str(e):
                    logger.warning(f"Error cleaning up image thread: {e}")
                # Ensure reference is cleared even on error
                self.image_thread = None

        # Clean up fix check thread if exists
        if hasattr(self, "fix_check_thread") and self.fix_check_thread:
            try:
                thread = self.fix_check_thread
                if thread.isRunning():
                    thread.quit()
                    thread.wait(2000)
                # Call cleanup if available
                if hasattr(thread, "cleanup"):
                    thread.cleanup()
                # Clear reference
                self.fix_check_thread = None
            except Exception as e:
                # Silenciar warning de deleção de C/C++ object - é normal no PyQt6
                if "wrapped C/C++ object" not in str(e):
                    logger.warning(f"Error cleaning up fix check thread: {e}")
                # Ensure reference is cleared even on error
                self.fix_check_thread = None

        # Clean up ZIP processing task runner if exists
        if hasattr(self, "task_runner") and self.task_runner:
            try:
                self.task_runner.force_cleanup()
                self.task_runner = None
                logger.debug("Cleaned up ZIP task runner on close")
            except Exception as e:
                if "wrapped C/C++ object" not in str(e):
                    logger.warning(f"Error cleaning up ZIP task runner: {e}")
                self.task_runner = None

        # Clean up any remaining active TaskRunner instances
        try:
            from utils.task_runner import TaskRunner

            # Force cleanup of all active runners
            for runner in TaskRunner._active_runners[
                :
            ]:  # Copy list to avoid modification during iteration
                runner.force_cleanup()
            TaskRunner._active_runners.clear()
            logger.debug("Cleaned up all remaining TaskRunner instances")
        except Exception as e:
            logger.warning(f"Error cleaning up remaining TaskRunner instances: {e}")

        # Process any remaining events to ensure clean shutdown
        QApplication.processEvents()

        super().closeEvent(event)
