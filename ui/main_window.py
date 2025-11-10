import logging
import logging
import os
import random
import sys
import re
import time
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QProgressBar,
    QTextEdit, QFrame, QFileDialog, QMessageBox,
    QStatusBar, QDialog, QHBoxLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QMovie, QPixmap

from ui.custom_title_bar import CustomTitleBar
from ui.enhanced_dialogs import SettingsDialog, DepotSelectionDialog, SteamLibraryDialog, DlcSelectionDialog
from ui.enhanced_widgets import EnhancedProgressBar
from ui.game_image_display import GameImageDisplay, ImageFetcher
from ui.interactions import HoverButton, ModernFrame, AnimatedLabel
from ui.shortcuts import KeyboardShortcuts
from ui.notification_system import NotificationManager
from ui.asset_optimizer import AssetManager

from ui.game_deletion_dialog import GameDeletionDialog
from ui.download_controls import DownloadControls
from utils.image_cache import ImageCacheManager
# from ui.responsive_design import ResponsiveMainWindow  # Disabled temporarily
from utils.task_runner import TaskRunner
from core.tasks.process_zip_task import ProcessZipTask
from core.tasks.download_depots_task import DownloadDepotsTask
from core.tasks.download_manager import DownloadManager
from core.tasks.monitor_speed_task import SpeedMonitorTask
from core import steam_helpers
from utils.logger import setup_logging
from utils.settings import get_settings

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

    def on_frame_changed(self, frame_number):
        if self.size().width() > 0 and self.size().height() > 0 and self._movie:
            pixmap = self._movie.currentPixmap()
            scaled_pixmap = pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
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
        self.setWindowTitle("Depot Downloader GUI")
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
        self.keyboard_shortcuts = KeyboardShortcuts(self)
        self.asset_manager = AssetManager(self)
        
        # Download Manager para pause/cancel/retomada
        self.download_manager = DownloadManager()
        self.download_controls = DownloadControls()
        
        # Controle para evitar múltiplas solicitações de reinicialização
        self._steam_restart_prompted = False
        
        # Image cache manager
        self.image_cache_manager = ImageCacheManager()
        
        self._setup_ui()
        self._setup_download_connections()
        
        # If zip file was provided as argument, start processing it immediately
        if zip_file:
            self._start_zip_processing(zip_file)

    def _setup_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Add title bar at the top of the window
        self.title_bar = CustomTitleBar(self)
        self.layout.addWidget(self.title_bar)

        main_content_frame = QFrame()
        main_content_frame.setStyleSheet("""
            QFrame {
                background: #000000;
                border: none;
                border-radius: 8px;
            }
        """)
        self.layout.addWidget(main_content_frame)
        
        main_layout = QVBoxLayout(main_content_frame)
        main_layout.setContentsMargins(16,8,16,4)  # Reduzir margem inferior para eliminar espaço extra
        main_layout.setSpacing(12)  # Spacing adequado entre elementos
        
        drop_zone_container = QWidget()
        drop_zone_layout = QVBoxLayout(drop_zone_container)
        drop_zone_layout.setContentsMargins(8,8,8,8)  # Margens adequadas para drop zone
        drop_zone_layout.setSpacing(8)  # Spacing adequado

        self.drop_label = ScaledLabel()
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if self.main_movie.isValid():
            self.drop_label.setMovie(self.main_movie)
            self.main_movie.start()
            self.current_movie = self.main_movie
        else:
            self.drop_label.setText("Drag and Drop ZIP File Here")

        drop_zone_layout.addWidget(self.drop_label, 10)

        self.drop_text_label = ScaledFontLabel("Drag and Drop Zip here")
        self.drop_text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        from .theme import theme
        self.drop_text_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_SECONDARY};
                background-color: transparent;
                font-size: 14px;
                font-weight: 500;
            }}
        """)
        drop_zone_layout.addWidget(self.drop_text_label, 1)

        

        main_layout.addWidget(drop_zone_container, 3)

        # Game header image area (initially hidden)
        self.game_image_container = ModernFrame()
        self.game_image_container.setVisible(False)
        self.game_image_container.setMaximumHeight(80)  # Reduced height
        self.game_image_container.setMaximumWidth(600)  # Constrain width to prevent excess space
        self.game_image_container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        game_image_layout = QHBoxLayout(self.game_image_container)
        game_image_layout.setContentsMargins(12, 8, 12, 8)  # Margens adequadas
        
        self.game_header_label = QLabel()
        self.game_header_label.setMinimumSize(100, 30)  # Reduced minimum size
        self.game_header_label.setMaximumSize(150, 56)  # Reduced maximum size (scale down 20%)
        self.game_header_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.game_header_label.setScaledContents(False)  # Deixa scaled() controlar a proporção
        self.game_header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.game_header_label.setStyleSheet("""
            QLabel {
                border: 1px solid #C06C84;
                background: #1E1E1E;
            }
        """)
        game_image_layout.addWidget(self.game_header_label)
        
        # Game info next to image
        game_info_layout = QVBoxLayout()
        game_info_layout.setSpacing(2)  # Reduced spacing
        
        self.game_title_label = QLabel("Game Title")
        self.game_title_label.setStyleSheet("""
            QLabel {
                font-size: 12px;  # Reduced font size
                font-weight: bold;
                color: #C06C84;
                border: none;
            }
        """)
        game_info_layout.addWidget(self.game_title_label)
        
        self.game_status_label = QLabel("Downloading...")
        self.game_status_label.setStyleSheet("""
            QLabel {
                font-size: 10px;  # Reduced font size
                color: #808080;
                border: none;
            }
        """)
        game_info_layout.addWidget(self.game_status_label)
        
        game_info_layout.addStretch()
        game_image_layout.addLayout(game_info_layout)
        
        main_layout.addWidget(self.game_image_container, 0, Qt.AlignmentFlag.AlignCenter)

        # Enhanced progress bar
        self.progress_bar = EnhancedProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Download controls (pause/resume/cancel)
        self.download_controls.setVisible(False)
        self.download_controls.setMaximumWidth(350)  # Reduced width
        self.download_controls.setMaximumHeight(80)  # Increased max height
        self.download_controls.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        main_layout.addWidget(self.download_controls, 0, Qt.AlignmentFlag.AlignCenter)

        # Initialize notification system
        self.notification_manager = NotificationManager(self)

        self.speed_label = QLabel("")
        self.speed_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.speed_label.setStyleSheet("""
            QLabel {
                font-size: 9px;
                color: #808080;
                padding: 2px 5px;
            }
        """)
        self.speed_label.setVisible(False)
        main_layout.addWidget(self.speed_label)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #C06C84;
                font-family: 'Courier New', monospace;
                font-size: 10px;
                border: 1px solid #C06C84;
            }
        """)
        # Enable word wrapping and horizontal scrolling for long file paths
        self.log_output.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.log_output.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.log_output.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        main_layout.addWidget(self.log_output, 1)
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
        self.status_bar.setStyleSheet("QStatusBar { border: 0px; background: #000000; height: 8px; }")
        self.status_bar.setMaximumHeight(8)  # Status bar mínimo apenas para size grip

        self.setAcceptDrops(True)

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() and len(event.mimeData().urls()) == 1:
            url = event.mimeData().urls()[0]
            if url.isLocalFile() and url.toLocalFile().lower().endswith('.zip'):
                event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        url = event.mimeData().urls()[0]
        zip_path = url.toLocalFile()
        self.log_output.clear()
        self._start_zip_processing(zip_path)

    def _setup_download_connections(self):
        """Configura conexões do DownloadManager e UI controls"""
        # Conectar signals do DownloadManager
        self.download_manager.download_progress.connect(self._on_download_progress)
        self.download_manager.download_paused.connect(self._on_download_paused)
        self.download_manager.download_resumed.connect(self._on_download_resumed)
        self.download_manager.download_cancelled.connect(self._on_download_cancelled)
        self.download_manager.download_completed.connect(self._on_download_completed)
        self.download_manager.download_error.connect(self._on_download_error)
        self.download_manager.state_changed.connect(self._on_download_state_changed)
        self.download_manager.depot_completed.connect(self._on_depot_completed)
        
        # Conectar controles UI
        self.download_controls.pause_clicked.connect(self.download_manager.pause_download)
        self.download_controls.resume_clicked.connect(self.download_manager.resume_download)
        self.download_controls.cancel_clicked.connect(self._confirm_cancel_download)
        
    def _select_zip_file(self):
        """Open file dialog to select a ZIP file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select ZIP File",
            "",
            "ZIP Files (*.zip);;All Files (*)"
        )
        
        if file_path:
            self.log_output.clear()
            self._start_zip_processing(file_path)

    def _start_zip_processing(self, zip_path):
        """Start processing a ZIP file that was provided as argument or drag & drop"""
        # Check SLSsteam prerequisite before processing ZIP
        if not self._check_slssteam_prerequisite():
            return

        # 🐛 FIX: Clean up any previous ZIP task to prevent conflicts
        if hasattr(self, 'zip_task'):
            self.zip_task = None
            logger.debug("Cleaned up previous ZIP task reference")

        self.log_output.append(f"Processing ZIP file: {zip_path}")

        # Show visual feedback during ZIP processing
        self.drop_text_label.setText("Processing ZIP...")
        self.drop_text_label.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setValue(0)
        self.title_bar.select_file_button.setVisible(False)

        self.zip_task = ProcessZipTask()
        runner = TaskRunner()
        worker = runner.run(self.zip_task.run, zip_path)
        worker.finished.connect(self._on_zip_processed)
        worker.error.connect(self._handle_task_error)

    def _on_download_progress(self, percentage, message):
        """Handle download progress updates"""
        if percentage > 0:
            self.progress_bar.setValue(percentage)
        if message:
            # Don't append to log_output here - the logging system already handles it
            # This prevents duplicate log messages
            self.download_controls.update_status(message)
            
    def _on_download_paused(self):
        """Handle download pause"""
        self.progress_bar.set_download_state("paused")
        self.download_controls.set_paused_state()
        self.log_output.append("⏸ Download pausado")
        
    def _on_download_resumed(self):
        """Handle download resume"""
        self.progress_bar.set_download_state("downloading")
        self.download_controls.set_downloading_state()
        self.log_output.append("▶ Download retomado")
        
    def _on_download_cancelled(self):
        """Handle download cancellation"""
        self._stop_speed_monitor()
        self.progress_bar.set_download_state("cancelled")
        self.download_controls.set_idle_state()
        self.download_controls.setVisible(False)
        self.log_output.append("✕ Download cancelado pelo usuário")
        # Limpar sessão atual para evitar comportamento indesejado
        self.current_session = None
        self._reset_ui_state()
        
    def _on_download_completed(self, session_id):
        """Handle download completion"""
        self._stop_speed_monitor()
        self.progress_bar.setValue(100)
        self.progress_bar.set_download_state("completed")
        self.download_controls.set_completed_state()
        self.log_output.append("✓ Download concluído com sucesso!")
        
        # Create ACF file and handle completion
        self._create_acf_file()
        
        # Generate Steam achievements if enabled
        self._handle_steam_schema_generation()
        
        self.notification_manager.show_notification(f"Successfully downloaded {self.game_data.get('game_name', 'Game')}!", "success")
        
        if self.slssteam_mode_was_active:
            self._prompt_for_steam_restart()
        else:
            QMessageBox.information(self, "Success", "All files have been downloaded successfully!")
        
        # Esconder controles após um tempo
        QTimer.singleShot(3000, self._hide_download_controls)
        
        # Reset UI state after completion
        QTimer.singleShot(3500, self._reset_ui_state)
        
    def _on_download_error(self, error_message):
        """Handle download errors"""
        self.log_output.append(f"❌ Erro no download: {error_message}")
        self.download_controls.set_idle_state()
        
    def _on_download_state_changed(self, state):
        """Handle download state changes"""
        logger.debug(f"Download state changed to: {state}")
        
    def _on_depot_completed(self, depot_id):
        """Handle individual depot completion"""
        self.log_output.append(f"✓ Depot {depot_id} concluído")
        
    def _confirm_cancel_download(self):
        """Show confirmation dialog before cancelling"""
        reply = QMessageBox.question(
            self, 
            "Cancelar Download",
            "Tem certeza que deseja cancelar o download? Os arquivos parciais serão removidos.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.download_manager.cancel_download()
            
    def _hide_download_controls(self):
        """Hide download controls after completion"""
        self.download_controls.setVisible(False)
        
    def _on_zip_processed(self, game_data):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.game_data = game_data
        
        if self.game_data and self.game_data.get('depots'):
            self.notification_manager.show_notification(f"Loaded {self.game_data.get('game_name', 'Game')} with {len(self.game_data.get('depots', []))} depots", "success")
            self._show_depot_selection_dialog()
        else:
            self.notification_manager.show_notification("No downloadable depots found in ZIP file", "error")
            QMessageBox.warning(self, "No Depots Found", "Zip file processed, but no downloadable depots were found.")
            self._reset_ui_state()

    def _show_depot_selection_dialog(self):
        self.depot_dialog = DepotSelectionDialog(self.game_data['appid'], self.game_data['depots'], self)
        if self.depot_dialog.exec():
            selected_depots = self.depot_dialog.get_selected_depots()
            if not selected_depots:
                self._reset_ui_state()
                return

            dest_path = None
            slssteam_mode = self.settings.value("slssteam_mode", False, type=bool)

            if slssteam_mode:
                if self.game_data.get('dlcs'):
                    dlc_dialog = DlcSelectionDialog(self.game_data['dlcs'], self)
                    if dlc_dialog.exec():
                        self.game_data['selected_dlcs'] = dlc_dialog.get_selected_dlcs()
                
                libraries = steam_helpers.get_steam_libraries()
                if libraries:
                    dialog = SteamLibraryDialog(libraries, self)
                    if dialog.exec():
                        dest_path = dialog.get_selected_path()
                    else:
                        self._reset_ui_state()
                        return
                else:
                    dest_path = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
            else:
                dest_path = QFileDialog.getExistingDirectory(self, "Select Destination Folder")

            if dest_path:
                self._start_download(selected_depots, dest_path, slssteam_mode)
            else:
                self._reset_ui_state()
        else:
            self._reset_ui_state()

    def _start_download(self, selected_depots, dest_path, slssteam_mode):
        # Check SLSsteam prerequisite before starting download
        if not self._check_slssteam_prerequisite():
            return
        
        self.current_dest_path = dest_path
        self.slssteam_mode_was_active = slssteam_mode
        
        # Hide drop zone and show progress
        self.drop_text_label.setVisible(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Show game image display
        if self.game_data:
            self.game_title_label.setText(self.game_data.get('game_name', 'Unknown Game'))
            self.game_image_container.setVisible(True)
            # Load game header image asynchronously
            self._load_game_image()
        
        # Start download GIF
        random_gif_path = random.choice(self.download_gifs)
        download_movie = QMovie(random_gif_path)
        if download_movie.isValid():
            self.current_movie = download_movie
            self.drop_label.setMovie(self.current_movie)
            self.current_movie.start()
        
        # Configurar UI para download com NOVO sistema
        self.progress_bar.set_download_state("downloading")
        self.progress_bar.start_progress()
        self.speed_label.setVisible(True)
        
        # Mostrar controles de download NOVOS
        self.download_controls.set_downloading_state()
        self.download_controls.setVisible(True)
        
        # Iniciar download usando NOVO DownloadManager
        session_id = self.download_manager.start_download(
            self.game_data, 
            selected_depots, 
            dest_path
        )
        
        if session_id:
            self.log_output.append(f"🚀 Download iniciado (Session: {session_id[:8]}...)")
            self._start_speed_monitor()
        else:
            self.log_output.append("❌ Falha ao iniciar download")
            self._reset_ui_state()

    def _load_game_image(self):
        """Load game header image using existing UI components"""
        try:
            if self.game_data:
                # Set game title
                game_name = self.game_data.get('game_name', 'Unknown Game')
                self.game_title_label.setText(game_name)
                
                # Show the game image container
                self.game_image_container.setVisible(True)
                
                # Fetch header image
                app_id = self.game_data.get('appid')
                if app_id:
                    self._fetch_game_header_image(app_id)
        except Exception as e:
            logger.warning(f"Failed to load game image: {e}")

    

    def _create_acf_file(self):
        self.log_output.append("Generating Steam .acf manifest file...")
        
        safe_game_name_fallback = re.sub(r'[^\w\s-]', '', self.game_data.get('game_name', '')).strip().replace(' ', '_')
        install_folder_name = self.game_data.get('installdir', safe_game_name_fallback)
        if not install_folder_name:
            install_folder_name = f"App_{self.game_data['appid']}"
            
        acf_path = os.path.join(self.current_dest_path, 'steamapps', f"appmanifest_{self.game_data['appid']}.acf")

        acf_content = f'''
"AppState"
{{
    "appid"         "{self.game_data['appid']}"
    "name"          "{self.game_data['game_name']}"
    "universe"      "1"
    "installdir"    "{install_folder_name}"
    "StateFlags"    "4"
}}
'''

        try:
            with open(acf_path, 'w', encoding='utf-8') as f:
                f.write(acf_content)
            self.log_output.append(f"Created .acf file at {acf_path}")
        except IOError as e:
            self.log_output.append(f"Error creating .acf file: {e}")

    def _handle_task_error(self, error_info):
        _, error_value, _ = error_info
        logger.error(f"Task error occurred: {error_value}", exc_info=True)
        QMessageBox.critical(self, "Error", f"An error occurred: {error_value}")
        # 🐛 FIX: Clean up ZIP task reference on error
        if hasattr(self, 'zip_task'):
            self.zip_task = None
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
        self.drop_text_label.setText("Drag and Drop Zip here")
        self.progress_bar.setVisible(False)
        self.speed_label.setVisible(False)
        self.game_image_container.setVisible(False)
        self.title_bar.select_file_button.setVisible(True)  # Show button again

        # 🐛 FIX: Clean up all state variables to prevent conflicts on next ZIP
        self.game_data = None
        self.current_dest_path = None
        self.slssteam_mode_was_active = False
        self._steam_restart_prompted = False  # Reset flag for next download
        self.zip_task = None  # Ensure ZIP task is cleaned up

        logger.debug("UI state fully reset, ready for next operation")

    def _start_speed_monitor(self):
        self.speed_monitor_task = SpeedMonitorTask()
        self.speed_monitor_task.speed_update.connect(self.speed_label.setText)
        runner = TaskRunner()
        runner.run(self.speed_monitor_task.run)

    def _stop_speed_monitor(self):
        if self.speed_monitor_task:
            self.speed_monitor_task.stop()
            self.speed_monitor_task = None

    def _prompt_for_steam_restart(self):
        # Evitar múltiplas solicitações
        if self._steam_restart_prompted:
            logger.debug("Steam restart already prompted, skipping")
            return
            
        self._steam_restart_prompted = True
        
        reply = QMessageBox.question(self, 'SLSsteam Integration', 
                                     "SLSsteam files have been created. Would you like to restart Steam now to apply the changes?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            logger.info("User agreed to restart Steam.")
            self.log_output.append("Closing Steam...")
            
            if sys.platform == 'linux':
                if not steam_helpers.kill_steam_process():
                    self.log_output.append("Steam process not found, attempting to launch directly.")
                else:
                    self.log_output.append("Steam closed successfully. Waiting 3 seconds before restart...")
                    # Wait for Steam to fully close
                    import time
                    time.sleep(3)
                
                self.log_output.append("Restarting Steam...")
                status = steam_helpers.start_steam()

                if status == 'NEEDS_USER_PATH':
                    self.log_output.append("SLSsteam.so not found. Please locate it manually.")
                    filePath, _ = QFileDialog.getOpenFileName(self, "Select SLSsteam.so", os.path.expanduser("~"), "SLSsteam.so (SLSsteam.so)")
                    if filePath:
                        if not steam_helpers.start_steam_with_path(filePath):
                            QMessageBox.warning(self, "Execution Failed", "Could not start Steam with the selected file.")
                    else:
                        self.log_output.append("User cancelled file selection.")
                
                elif status == 'FAILED':
                    QMessageBox.warning(self, "Steam Not Found", "Could not restart Steam automatically. Please start it manually.")

            else:
                steam_helpers.kill_steam_process()
                if not steam_helpers.start_steam() == 'SUCCESS':
                    QMessageBox.warning(self, "Steam Not Found", "Could not restart Steam automatically. Please start it manually.")

    def _fetch_game_header_image(self, app_id):
        """Fetch game header image for display during download."""
        url = f"https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/header.jpg"
        
        # Try cache first
        cached_image = self.image_cache_manager.get_cached_image(str(app_id), url)
        if cached_image:
            self._display_game_image(cached_image)
            return
        
        # Download with cache
        from utils.image_cache import ImageFetcher
        self.image_thread = QThread()
        self.image_fetcher = ImageFetcher(str(app_id), url, self.image_cache_manager)
        self.image_fetcher.moveToThread(self.image_thread)
        
        self.image_thread.started.connect(self.image_fetcher.run)
        self.image_fetcher.image_ready.connect(self._on_game_image_ready)
        self.image_fetcher.error_occurred.connect(self._on_game_image_error)
        
        self.image_fetcher.finished.connect(self.image_thread.quit)
        self.image_fetcher.finished.connect(self.image_fetcher.deleteLater)
        self.image_thread.finished.connect(self.image_thread.deleteLater)
        
        self.image_thread.start()
    
    def _on_game_image_ready(self, app_id, pixmap):
        """Handle successfully fetched game image"""
        if pixmap and not pixmap.isNull():
            self._display_game_image(pixmap)
        else:
            self._display_no_image()
    
    def _on_game_image_error(self, app_id, error_message):
        """Handle game image fetch error"""
        logger.warning(f"Failed to fetch image for app {app_id}: {error_message}")
        self._display_no_image()
    
    def _display_game_image(self, pixmap):
        """Display game image with proper scaling"""
        if not pixmap or pixmap.isNull():
            self._display_no_image()
            return
            
        self.game_header_image = pixmap
        
        # Calculate size maintaining aspect ratio with max 184x69
        scaled_pixmap = pixmap.scaled(
            184, 69, 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        
        # Adjust label size to exactly the scaled image size
        self.game_header_label.setFixedSize(scaled_pixmap.width(), scaled_pixmap.height())
        self.game_header_label.setPixmap(scaled_pixmap)
    
    def _display_no_image(self):
        """Display placeholder when no image is available"""
        self.game_header_label.setText("📷\nNo Image")
        self.game_header_label.setFixedSize(184, 69)  # Restore default size

    def on_game_image_fetched(self, image_data):
        """Handle fetched game header image."""
        if image_data:
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            self.game_header_image = pixmap
            
            # Calcula tamanho mantendo proporção máxima de 184x69
            scaled_pixmap = pixmap.scaled(
                184, 69, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Ajusta o tamanho do label para exatamente o tamanho da imagem redimensionada
            self.game_header_label.setFixedSize(scaled_pixmap.width(), scaled_pixmap.height())
            self.game_header_label.setPixmap(scaled_pixmap)
        else:
            self.game_header_label.setText("📷\nNo Image")
            self.game_header_label.setFixedSize(184, 69)  # Restaura tamanho padrão

    def _handle_steam_schema_generation(self):
        """Handle Steam Schema generation with proper error handling"""
        try:
            from utils.steam_schema import is_steam_schema_enabled
            if not is_steam_schema_enabled():
                logger.debug("Steam schema is disabled")
                return
                
            from core.steam_schema_integration import SteamSchemaIntegration
            schema_integration = SteamSchemaIntegration()
            
            app_id = self.game_data.get('appid')
            if not app_id:
                logger.warning("App ID not found for Steam Schema generation")
                return
                
            self.log_output.append("Generating Steam Schema...")
            success = schema_integration.get_game_schema_steam_client(app_id)
            
            if success:
                self.log_output.append("✓ Steam Schema generated successfully!")
                self.show_notification("Steam achievements generated successfully!", "success")
            else:
                self.log_output.append("⚠ Steam Schema generation completed with warnings")
                self.show_notification("Steam Schema generation completed with warnings", "warning")
                
        except ImportError:
            logger.warning("Steam schema utilities not available")
        except Exception as e:
            logger.warning(f"Failed to generate Steam achievements: {e}")
            self.log_output.append(f"⚠ Steam Schema generation failed: {e}")

    def _generate_steam_achievements(self):
        """Legacy method - use _handle_steam_schema_generation instead"""
        self._handle_steam_schema_generation()

    def show_notification(self, message, notification_type="info"):
        """Show a notification using the notification manager"""
        if hasattr(self, 'notification_manager'):
            self.notification_manager.show_notification(message, notification_type)

    def open_steam_login(self):
        """Steam login is now handled by SLScheevo - no dialog needed"""
        QMessageBox.information(self, "Steam Login", "Steam login is now handled by SLScheevo!\n\nSLScheevo will automatically login when generating schemas.")
    
    def _check_slssteam_prerequisite(self) -> bool:
        """Check if SLSsteam is ready for operations, show dialog if not"""
        if not hasattr(self.title_bar, 'slssteam_status') or not self.title_bar.slssteam_status:
            QMessageBox.critical(self, "SLSsteam Error", 
                                "SLSsteam status widget not available. Please restart ACCELA.")
            return False
        
        if not self.title_bar.slssteam_status.can_start_operations():
            # Show blocking dialog with setup option
            blocking_msg = self.title_bar.slssteam_status.get_blocking_message()
            reply = QMessageBox.critical(self, "SLSsteam Required", 
                                        f"SLSsteam is required for ACCELA to function.\n\n{blocking_msg}\n\n"
                                        "Would you like to configure SLSsteam now?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                # Trigger setup dialog
                self.title_bar.slssteam_status._on_action_clicked()
            
            return False
        
        return True
    
    def _on_slssteam_setup_requested(self):
        """Handle SLSsteam setup completion"""
        if (hasattr(self.title_bar, 'slssteam_status') and 
            self.title_bar.slssteam_status and 
            self.title_bar.slssteam_status.is_slssteam_ready()):
            self.show_notification("SLSsteam is ready for use!", "success")
            # Auto-enable slssteam_mode when SLSsteam becomes ready
            self.settings.setValue("slssteam_mode", True)
        else:
            self.show_notification("SLSsteam setup completed. Please check status.", "info")
    
    def _open_game_manager(self):
        """Open the Game Manager dialog for deleting ACCELA games"""
        try:
            dialog = GameDeletionDialog(self)
            dialog.exec()
            logger.info("Game Manager dialog opened and closed")
        except Exception as e:
            logger.error(f"Error opening Game Manager: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open Game Manager: {e}")
    
    def closeEvent(self, event):
        self._stop_speed_monitor()
        
        # Clean up image thread if exists
        if hasattr(self, 'image_thread') and self.image_thread:
            self.image_thread.quit()
            self.image_thread.wait(3000)
        
        super().closeEvent(event)
