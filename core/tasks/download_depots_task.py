import logging
import subprocess
import sys
import os
import re
import psutil
import shlex
from PyQt6.QtCore import QObject, pyqtSignal, QThread

logger = logging.getLogger(__name__)

class StreamReader(QObject):
    """Reads output from a stream in a separate thread and emits it."""
    new_line = pyqtSignal(str)

    def __init__(self, stream):
        super().__init__()
        self.stream = stream
        self._is_running = True

    def run(self):
        """Reads lines from the stream until it's closed or stopped."""
        for line in iter(self.stream.readline, ''):
            if not self._is_running:
                break
            self.new_line.emit(line)
        self.stream.close()

    def stop(self):
        """Signals the reader to stop."""
        self._is_running = False

class DownloadDepotsTask(QObject):
    """
    A dedicated class for the download task. This is necessary because the task
    needs to emit progress signals during its long-running executiona .
    """
    progress = pyqtSignal(str)
    progress_percentage = pyqtSignal(int)
    steamless_progress = pyqtSignal(str)
    
    # Novos signals para controle de cancelamento
    process_started = pyqtSignal(object)  # subprocess.Popen
    depot_completed = pyqtSignal(str)     # depot_id
    cancellation_requested = pyqtSignal()
    finished = pyqtSignal()
    cancelled = pyqtSignal()  # New specific signal for cancellation
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.percentage_regex = re.compile(r"(\d{1,3}\.\d{2})%")
        self.last_percentage = -1
        self.steamless_integration = None
        self.game_data = None
        
        # Controle de cancelamento
        self._should_stop = False
        self._current_process = None

    def run(self, game_data, selected_depots, dest_path):
        """
        TASK: Prepares and executes the DepotDownloaderMod commands to download
        files directly into the final destination directory.
        """
        logger.debug(f"Download task starting for {len(selected_depots)} depots.")
        self.game_data = game_data  # Store game_data for later use
        self._should_stop = False  # Reset cancel flag
        
        commands, skipped_depots = self._prepare_downloads(game_data, selected_depots, dest_path)
        if not commands:
            self.progress.emit("No valid download commands to execute. Task finished.")
            self.finished.emit()
            return

        total_depots = len(commands)
        
        try:
            for i, command in enumerate(commands):
                # Verificar cancelamento antes de cada depot
                if self._should_stop:
                    self.progress.emit("Download cancelled by user")
                    self.cancelled.emit()
                    return
                    
                depot_id = command[4]
                self.progress.emit(f"--- Starting download for depot {depot_id} ({i+1}/{total_depots}) ---")
                self.last_percentage = -1
                
                try:
                    self._current_process = subprocess.Popen(
                        command, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.STDOUT,
                        text=True, 
                        encoding='utf-8',
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                    )
                    
                    # Emitir signal que processo iniciou
                    self.process_started.emit(self._current_process)
                    
                    reader_thread = QThread()
                    stream_reader = StreamReader(self._current_process.stdout)
                    stream_reader.moveToThread(reader_thread)

                    stream_reader.new_line.connect(self._handle_downloader_output)
                    reader_thread.started.connect(stream_reader.run)
                    
                    reader_thread.start()
                    
                    # Monitor process with cancellation check
                    process_terminated_cleanly = False
                    while self._current_process.poll() is None:
                        if self._should_stop:
                            self.progress.emit("Cancelando download atual...")
                            try:
                                self._current_process.terminate()
                                # Wait up to 5 seconds for graceful termination
                                try:
                                    self._current_process.wait(timeout=5)
                                    process_terminated_cleanly = True
                                except subprocess.TimeoutExpired:
                                    self.progress.emit("Forcing process termination...")
                                    self._current_process.kill()
                                    self._current_process.wait(timeout=2)
                                    process_terminated_cleanly = True
                            except (psutil.NoSuchProcess, OSError) as e:
                                logger.debug(f"Process already terminated: {e}")
                                process_terminated_cleanly = True
                            break
                        QThread.msleep(100)  # Small pause to avoid CPU overload
                    
                    # Wait for process completion if not cancelled
                    if not self._should_stop:
                        self._current_process.wait()
                    
                    # Limpar recursos da thread e processo
                    try:
                        stream_reader.stop()
                        reader_thread.quit()
                        if not reader_thread.wait(3000):  # Timeout de 3 segundos
                            logger.warning("Reader thread did not finish cleanly")
                            reader_thread.terminate()
                            reader_thread.wait(1000)  # Wait for forced completion
                    except Exception as e:
                        logger.error(f"Error cleaning up reader thread: {e}")
                    
                    # Check process result BEFORE cleanup
                    process_returncode = self._current_process.returncode if self._current_process else None
                    
                    # Verificar se foi cancelado durante o processo
                    if self._should_stop:
                        if process_terminated_cleanly:
                            self.progress.emit("Download cancelado com sucesso")
                        else:
                            self.progress.emit("Download cancelado (pode haver processos residuais)")
                        self.cancelled.emit()
                        return

                    # Garantir cleanup do processo
                    try:
                        if self._current_process and self._current_process.poll() is None:
                            self._current_process.terminate()
                            try:
                                self._current_process.wait(timeout=2)
                            except subprocess.TimeoutExpired:
                                self._current_process.kill()
                                self._current_process.wait(timeout=1)
                    except Exception as e:
                        logger.error(f"Error cleaning up process: {e}")
                    
                    self._current_process = None
                    
                    if process_returncode == 0:
                        self.depot_completed.emit(depot_id)
                    elif process_returncode is not None:
                        self.progress.emit(f"Warning: DepotDownloaderMod exited with code {process_returncode} for depot {depot_id}.")
                    else:
                        # Process reference lost is not necessarily an error - can happen after successful completion
                        logger.debug(f"Process reference lost for depot {depot_id} after completion.")
                        self.depot_completed.emit(depot_id)

                except FileNotFoundError:
                    self.progress.emit("ERROR: ./external/DepotDownloaderMod not found. Make sure it's in the external/ directory.")
                    logger.critical("./external/DepotDownloaderMod not found.")
                    self.error.emit("DepotDownloaderMod not found")
                    raise
                except Exception as e:
                    if not self._should_stop:  # Only emit error if not cancelled
                        self.progress.emit(f"An unexpected error occurred during download: {e}")
                        logger.error(f"Download subprocess failed: {e}", exc_info=True)
                        self.error.emit(f"Download error: {e}")
                    raise
            
            # Check cancellation before post-processing
            if self._should_stop:
                self.cancelled.emit()
                return
                
        except Exception as e:
            if not self._should_stop:
                self.error.emit(f"Task failed: {e}")
            raise
        
        if skipped_depots:
            self.progress.emit(f"Skipped {len(skipped_depots)} depots due to missing manifests: {', '.join(skipped_depots)}")
        
        # Verificar cancelamento antes da limpeza
        if self._should_stop:
            self.cancelled.emit()
            return
        
        self.progress.emit("--- Cleaning up temporary files ---")
        for filename in ['keys.vdf', 'manifest']:
            path = os.path.join(os.getcwd(), filename)
            if os.path.exists(path):
                try:
                    if os.path.isdir(path):
                        import shutil
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                    self.progress.emit(f"Removed '{filename}'.")
                except OSError as e:
                    self.progress.emit(f"Error removing '{filename}': {e}")
        
        # Check cancellation before post-processing
        if self._should_stop:
            self.progress.emit("Download cancelled - skipping post-processing")
            self.cancelled.emit()
            return
        
        # Get the download directory for Steamless processing
        safe_game_name_fallback = re.sub(r'[^\w\s-]', '', game_data.get('game_name', '')).strip().replace(' ', '_')
        install_folder_name = game_data.get('installdir', safe_game_name_fallback)
        if not install_folder_name:
            install_folder_name = f"App_{game_data['appid']}"
        
        download_dir = os.path.join(dest_path, 'steamapps', 'common', install_folder_name)
        
        # Initialize Steamless integration after download completion (if enabled)
        if self._is_steamless_enabled():
            self._run_steamless_processing(download_dir)
        
        # Steam Schema Generation will be handled by the UI after download completion
        # This avoids duplicate execution
        self.progress.emit("--- Download completed ---")
        
        # Emit completion signal
        self.finished.emit()

    def _prepare_downloads(self, game_data, selected_depots, dest_path):
        """Prepares keys.vdf and command list."""
        keys_path = os.path.join(os.getcwd(), "keys.vdf")
        self.progress.emit(f"Generating depot keys file at {keys_path}")
        with open(keys_path, "w") as f:
            for depot_id in selected_depots:
                if depot_id in game_data['depots']:
                    f.write(f"{depot_id};{game_data['depots'][depot_id]['key']}\n")
        
        safe_game_name_fallback = re.sub(r'[^\w\s-]', '', game_data.get('game_name', '')).strip().replace(' ', '_')
        install_folder_name = game_data.get('installdir', safe_game_name_fallback)
        if not install_folder_name:
            install_folder_name = f"App_{game_data['appid']}"
        
        # Sanitize directory name to remove filesystem-invalid characters
        install_folder_name = re.sub(r'[<>:"/\\|?*]', '_', str(install_folder_name))

        download_dir = os.path.join(dest_path, 'steamapps', 'common', install_folder_name)
        os.makedirs(download_dir, exist_ok=True)
        self.progress.emit(f"Download destination set to: {download_dir}")

        # Create manifest directory if it doesn't exist
        manifest_dir = os.path.join(os.getcwd(), 'manifest')
        os.makedirs(manifest_dir, exist_ok=True)

        commands = []
        skipped_depots = []
        for depot_id in selected_depots:
            manifest_id = game_data['manifests'].get(depot_id)
            if not manifest_id:
                self.progress.emit(f"Warning: No manifest ID for depot {depot_id}. Skipping.")
                skipped_depots.append(str(depot_id))
                continue
            
            commands.append([
                "./external/DepotDownloaderMod", "-app", str(game_data['appid']), "-depot", str(depot_id),
                "-manifest", str(manifest_id),
                "-manifestfile", os.path.join('manifest', f"{depot_id}_{manifest_id}.manifest"),
                "-depotkeys", keys_path, "-max-downloads", "25",
                "-dir", download_dir
            ])

        return commands, skipped_depots

    def _handle_downloader_output(self, line):
        """Processes a line of output from the downloader."""
        line = line.strip()
        self.progress.emit(line)
        match = self.percentage_regex.search(line)
        if match:
            percentage = float(match.group(1))
            int_percentage = int(percentage)
            
            if int_percentage != self.last_percentage:
                self.progress_percentage.emit(int_percentage)
                self.last_percentage = int_percentage

    def _is_steamless_enabled(self):
        """Check if Steamless DRM removal is enabled in settings"""
        try:
            from utils.settings import get_settings
            settings = get_settings()
            return settings.value("steamless_enabled", True, type=bool)
        except Exception:
            return True  # Default to enabled

    def _run_steamless_processing(self, download_dir):
        """Run Steamless processing on downloaded game."""
        try:
            # Direct import to avoid dynamic execution
            from core.steamless_integration import SteamlessIntegration
            
            self.progress.emit("--- Starting Steamless DRM removal ---")
            self.steamless_integration = SteamlessIntegration()
            
            # Connect signals
            self.steamless_integration.progress.connect(self.steamless_progress.emit)
            self.steamless_integration.error.connect(self.progress.emit)
            self.steamless_integration.finished.connect(self._on_steamless_finished)
            
            # Start Steamless processing
            success = self.steamless_integration.process_game_with_steamless(download_dir)
            
            if not success:
                if self.steamless_integration.wine_available:
                    self.progress.emit("Steamless processing completed with issues.")
                else:
                    self.progress.emit("Steamless processing skipped (Wine not available).")
            else:
                # Steamless finished successfully, _on_steamless_finished will handle schema generation
                return
            
        except ImportError as e:
            self.progress.emit(f"Steamless integration not available: {e}")
            logger.warning(f"Could not import Steamless integration: {e}")
        except Exception as e:
            self.progress.emit(f"Error during Steamless processing: {e}")
            logger.error(f"Steamless processing failed: {e}", exc_info=True)

    def _on_steamless_finished(self, success):
        """Handle Steamless completion."""
        if success:
            self.progress.emit("--- Steamless DRM removal completed successfully ---")
        else:
            self.progress.emit("--- Steamless DRM removal completed with warnings ---")
        
        # Steam Schema Generation will be handled by the UI after download completion
        self.progress.emit("--- All processing completed ---")
    
    def request_cancellation(self):
        """Solicita cancelamento do download"""
        self._should_stop = True
        self.cancellation_requested.emit()
        logger.info("Download cancellation requested")
    

