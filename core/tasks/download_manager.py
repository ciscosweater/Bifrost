"""
Download Manager - Central control for downloads with pause/cancel/resume
"""

from utils.logger import get_internationalized_logger

import logging
import os
import signal
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Set

import psutil
from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal

from utils.enhanced_file_cleanup import EnhancedFileCleanupManager
from utils.file_cleanup import FileCleanupManager
from utils.task_runner import TaskRunner

from .download_depots_task import DownloadDepotsTask
from .download_session import DownloadSession, DownloadState

logger = get_internationalized_logger()


class DownloadManager(QObject):
    """Manages downloads with pause/cancel/resume capability"""

    # Main signals
    download_started = pyqtSignal(str)  # session_id
    download_progress = pyqtSignal(int, str)  # percentage, current_depot
    download_bytes = pyqtSignal(int, int)  # downloaded_bytes, total_bytes
    download_paused = pyqtSignal()
    download_resumed = pyqtSignal()
    download_cancelled = pyqtSignal()
    download_completed = pyqtSignal(str, str)  # session_id, install_path
    download_error = pyqtSignal(str)

    # State signals
    state_changed = pyqtSignal(str)  # DownloadState value
    depot_completed = pyqtSignal(str)  # depot_id
    steamless_progress = pyqtSignal(str)  # Steamless processing message

    def __init__(self):
        super().__init__()
        self.current_session: Optional[DownloadSession] = None
        self.download_task: Optional[DownloadDepotsTask] = None
        self.current_process: Optional[psutil.Process] = None
        self.task_runner: Optional[TaskRunner] = None
        self.download_state = DownloadState.IDLE

        # Task completion control
        self._task_finishing = False

        # Utilities
        self.cleanup_manager = FileCleanupManager()
        self.enhanced_cleanup_manager = EnhancedFileCleanupManager()

        # Timer for periodic checks
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._monitor_download)
        self.monitor_timer.setInterval(
            2000
        )  # Reduzido para 2s para melhor responsividade

        # Active threads control for memory leak prevention
        self._active_threads: Set[QThread] = set()

        logger.debug("DownloadManager initialized")

    def start_download(
        self, game_data: Dict[str, Any], selected_depots: list, dest_path: str
    ) -> str:
        """
        Start new download with complete state management.

        Args:
            game_data: Dictionary with game data (appid, name, depots, manifests)
            selected_depots: List of depot IDs to download
            dest_path: Destination directory for installation

        Returns:
            str: Unique download session ID or empty string in case of error

        Raises:
            ValueError: If required parameters are invalid
        """
        try:
            # Security validations
            if not game_data or not isinstance(game_data, dict):
                raise ValueError("Invalid game_data: must be a non-empty dictionary")

            if not selected_depots or not isinstance(selected_depots, list):
                raise ValueError("Invalid selected_depots: must be a non-empty list")

            if not dest_path or not isinstance(dest_path, str):
                raise ValueError("Invalid dest_path: must be a non-empty string")

            if not os.path.exists(dest_path):
                raise ValueError(f"Destination path does not exist: {dest_path}")

            # Generate unique ID for session
            session_id = str(uuid.uuid4())

            # Calculate total download size
            depot_sizes = game_data.get("depot_sizes", {})
            total_size = sum(
                depot_sizes.get(depot_id, 0) for depot_id in selected_depots
            )

            # Create download session
            self.current_session = DownloadSession(
                session_id=session_id,
                game_data=game_data,
                selected_depots=selected_depots,
                current_depot_index=0,
                completed_depots=[],
                download_state=DownloadState.DOWNLOADING,
                timestamp=datetime.now(),
                dest_path=dest_path,
                total_size=total_size,
            )

            # Salvar estado inicial
            self.current_session.save()

            # Reset completion control
            self._task_finishing = False

            # Configurar task de download
            self.download_task = DownloadDepotsTask()
            self._setup_task_connections()

            # Mudar estado
            self._set_state(DownloadState.DOWNLOADING)

            # Iniciar download em thread controlada
            self._run_download_task(game_data, selected_depots, dest_path)

            # Iniciar monitoramento
            self.monitor_timer.start()

            # Emitir signal
            self.download_started.emit(session_id)

            logger.debug(f"Download started with session_id: {session_id}")
            return session_id

        except Exception as e:
            logger.error(f"Failed to start download: {e}")
            self.download_error.emit(f"Failed to start download: {e}")
            return ""

    def pause_download(self):
        """Pausa download atual"""
        try:
            if self.download_state != DownloadState.DOWNLOADING:
                logger.warning(f"Cannot pause: download state is {self.download_state.value}")
                return

            if not self.current_process:
                logger.warning("Cannot pause: no active process")
                return

            try:
                if not self.current_process.is_running():
                    logger.warning("Cannot pause: process is not running")
                    return
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                logger.warning("Cannot pause: process no longer exists")
                return

            logger.debug("Pausing download...")

            if sys.platform in ["linux", "darwin"]:
                os.kill(self.current_process.pid, signal.SIGSTOP)
            elif sys.platform == "win32":
                self.current_process.suspend()

            self._set_state(DownloadState.PAUSED)
            if self.current_session:
                self.current_session.download_state = DownloadState.PAUSED
                self.current_session.save()

            self.download_paused.emit()
            logger.debug("Download paused successfully")

        except Exception as e:
            logger.error(f"Failed to pause download: {e}")
            self.download_error.emit(f"Failed to pause download: {e}")

    def resume_download(self):
        """Retoma download pausado"""
        try:
            if self.download_state != DownloadState.PAUSED:
                logger.warning(f"Cannot resume: download state is {self.download_state.value}")
                return

            if not self.current_process:
                logger.warning("Cannot resume: no active process")
                return

            try:
                if not self.current_process.is_running():
                    logger.warning("Cannot resume: process is not running")
                    return
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                logger.warning("Cannot resume: process no longer exists")
                return

            logger.debug("Resuming download...")

            if sys.platform in ["linux", "darwin"]:
                os.kill(self.current_process.pid, signal.SIGCONT)
            elif sys.platform == "win32":
                self.current_process.resume()

            self._set_state(DownloadState.DOWNLOADING)
            if self.current_session:
                self.current_session.download_state = DownloadState.DOWNLOADING
                self.current_session.save()

            self.download_resumed.emit()
            logger.debug("Download resumed successfully")

        except Exception as e:
            logger.error(f"Failed to resume download: {e}")
            self.download_error.emit(f"Failed to resume download: {e}")

    def cancel_download(self):
        """
        Cancel download and clean up resources safely.

        This method ensures that:
        - Processes are terminated gracefully
        - Partial files are removed safely
        - Steam libraries are never affected
        - Session is marked as cancelled
        """
        try:
            logger.debug("Cancelling download...")

            # Change state to cancelling
            self._set_state(DownloadState.CANCELLING)

            # Stop monitoring timer
            self.monitor_timer.stop()

            # Request task cancellation
            if self.download_task:
                self.download_task.request_cancellation()

            # Terminate process with validation
            if self.current_process:
                try:
                    if self.current_process.is_running():
                        self._terminate_process()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    logger.warning("Process already terminated or inaccessible")
                    self.current_process = None

            # ENHANCED CLEANUP: Aggressive but Steam-safe cleanup
            if self.current_session and self.current_session.dest_path:
                # Calcular o diretório de instalação específico do jogo
                game_data = self.current_session.game_data
                install_dir = self._get_game_install_directory(
                    self.current_session.dest_path, game_data
                )

                if install_dir and os.path.exists(install_dir):
                    # Verificação de segurança adicional
                    if not self._is_bifrost_temp_directory(install_dir):
                        logger.warning(
                            f"SAFETY: Skipping cleanup of potentially non-Bifrost directory: {install_dir}"
                        )
                        # Fallback para limpeza legada
                        self.cleanup_manager.cleanup_session(
                            self.current_session.session_id
                        )
                    else:
                        logger.debug(
                            f"Starting ENHANCED cleanup of game install directory: {install_dir}"
                        )

                        # Usar limpeza agressiva mas segura
                        cleanup_result = self.enhanced_cleanup_manager.safe_cancel_cleanup(
                            install_dir=install_dir,
                            game_data=game_data,
                            session_id=self.current_session.session_id,
                        )

                        if cleanup_result.get("success", False):
                            files_removed = cleanup_result.get("total_files_removed", 0)
                            space_freed = cleanup_result.get("total_space_freed_mb", 0)
                            logger.debug(
                                f"Enhanced cleanup completed: {files_removed} files, {space_freed}MB freed"
                            )
                        else:
                            logger.error(
                                f"Enhanced cleanup failed: {cleanup_result.get('errors', [])}"
                            )

                            # Fallback para limpeza legada em caso de erro
                            logger.debug("Falling back to legacy cleanup")
                            self.cleanup_manager.cleanup_session(
                                self.current_session.session_id
                            )
                else:
                    logger.warning(
                        f"Game install directory not found or doesn't exist: {install_dir}"
                    )
                    # Fallback para limpeza legada
                    self.cleanup_manager.cleanup_session(
                        self.current_session.session_id
                    )
            else:
                # Fallback para limpeza legada
                self.cleanup_manager.cleanup_session(
                    self.current_session.session_id if self.current_session else None
                )

        except Exception as e:
            logger.error(f"Error during download cancellation: {e}")
            self.download_error.emit(f"Error during cancellation: {e}")

    def _is_bifrost_temp_directory(self, directory: str) -> bool:
        """
        SAFETY CHECK: Verify this is really an Bifrost temp directory before deletion
        """
        if not directory or not os.path.exists(directory):
            return False

        # NEVER delete if it looks like a Steam library
        dangerous_indicators = [
            "steamapps",
            "common",
            "userdata",
            "config",
            "steam.exe",
            "steam.sh",
        ]

        dir_lower = directory.lower()
        for indicator in dangerous_indicators:
            if indicator in dir_lower:
                logger.error(
                    f"SAFETY: Directory contains Steam indicator '{indicator}': {directory}"
                )
                return False

        # Only delete if clearly an Bifrost temp directory
        accelra_indicators = ["bifrost_temp", "download_temp", "partial_download"]

        for indicator in accelra_indicators:
            if indicator in dir_lower:
                return True

        # Extra safety: check if directory is empty or only contains temp files
        try:
            files = os.listdir(directory)
            temp_files = [
                f for f in files if f.endswith((".tmp", ".partial", ".downloading"))
            ]
            if len(files) > 0 and len(temp_files) == len(files):
                return True
        except Exception:
            pass

        return False

    def get_current_state(self) -> DownloadState:
        """Retorna estado atual do download"""
        return self.download_state

    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """Retorna informações da sessão atual"""
        if self.current_session:
            return {
                "session_id": self.current_session.session_id,
                "game_name": self.current_session.game_data.get("name", "Unknown"),
                "current_depot": self.current_session.current_depot_index,
                "total_depots": len(self.current_session.selected_depots),
                "completed_depots": len(self.current_session.completed_depots),
                "state": self.current_session.download_state.value,
                "timestamp": self.current_session.timestamp.isoformat(),
            }
        return None

    def _get_game_install_directory(self, dest_path: str, game_data: Dict) -> str:
        """
        Calcula o diretório de instalação específico do jogo com validações de segurança.

        Args:
            dest_path: Path da biblioteca Steam (validado)
            game_data: Dados do jogo com installdir (validado)

        Returns:
            Caminho completo do diretório de instalação do jogo ou string vazia em erro
        """
        try:
            import re

            # Validações de segurança
            if not dest_path or not isinstance(dest_path, str):
                logger.error("Invalid dest_path for install directory calculation")
                return ""

            if not game_data or not isinstance(game_data, dict):
                logger.error("Invalid game_data for install directory calculation")
                return ""

            appid = game_data.get("appid")
            if not appid:
                logger.error("Missing appid in game_data")
                return ""

            # Obter install_folder_name da mesma forma que DownloadDepotsTask
            game_name = game_data.get("game_name", "")
            safe_game_name_fallback = (
                re.sub(r"[^\w\s-]", "", str(game_name)).strip().replace(" ", "_")
            )
            install_folder_name = game_data.get("installdir", safe_game_name_fallback)

            if not install_folder_name:
                install_folder_name = f"App_{appid}"

            # Sanitização do nome do diretório
            install_folder_name = re.sub(r'[<>:"/\\|?*]', "_", str(install_folder_name))

            # Montar caminho: dest_path/steamapps/common/install_folder_name
            install_dir = os.path.join(
                dest_path, "steamapps", "common", install_folder_name
            )

            # Validação final do caminho
            install_dir = os.path.normpath(install_dir)
            if not install_dir.startswith(os.path.normpath(dest_path)):
                logger.error(f"Path traversal attempt detected: {install_dir}")
                return ""

            logger.debug(f"Calculated install directory: {install_dir}")
            return install_dir

        except Exception as e:
            logger.error(f"Error calculating install directory: {e}")
            return ""

    def _setup_task_connections(self):
        """Configura conexões com a task de download"""
        if self.download_task:
            self.download_task.progress.connect(self._handle_progress)
            self.download_task.progress_percentage.connect(self._handle_percentage)
            self.download_task.bytes_downloaded.connect(self._handle_bytes_downloaded)
            self.download_task.process_started.connect(self._on_process_started)
            self.download_task.depot_completed.connect(self._on_depot_completed)
            self.download_task.finished.connect(self._on_task_finished)
            self.download_task.cancelled.connect(
                self._on_task_cancelled
            )  # Nova conexão
            self.download_task.error.connect(self._handle_task_error)
            self.download_task.steamless_progress.connect(self._handle_steamless_progress)

    def _run_download_task(
        self, game_data: Dict[str, Any], selected_depots: list, dest_path: str
    ):
        """Executa task de download em thread separada"""
        try:
            if not self.download_task:
                raise ValueError("Download task not initialized")

            self.task_runner = TaskRunner()
            worker = self.task_runner.run(
                self.download_task.run, game_data, selected_depots, dest_path
            )
            # Conectar signals do worker para tratamento de erros
            if hasattr(worker, "error"):
                worker.error.connect(self._handle_task_error)
            # Nota: worker.completed não é conectado aqui porque a task já emite 'finished'
        except Exception as e:
            logger.error(f"Failed to run download task: {e}")
            self.download_error.emit(f"Failed to run download task: {e}")

    def _set_state(self, new_state: DownloadState):
        """Atualiza estado e emite signal"""
        self.download_state = new_state
        self.state_changed.emit(new_state.value)
        logger.debug(f"Download state changed to: {new_state.value}")

    def _terminate_process(self):
        """Terminate process with proper resource cleanup"""
        try:
            if self.current_process and self.current_process.is_running():
                # Tentar terminação gentil primeiro
                self.current_process.terminate()

                # Aguardar até 5 segundos
                try:
                    self.current_process.wait(timeout=5)
                except psutil.TimeoutExpired:
                    # Forçar kill se não responder
                    logger.warning("Process didn't terminate, forcing kill")
                    self.current_process.kill()
                    self.current_process.wait(timeout=2)

                logger.info("Process terminated successfully")
        except Exception as e:
            logger.error(f"Error terminating process: {e}")
        finally:
            # Explicitly close process handle to prevent leaks
            try:
                if self.current_process:
                    # Close the process handle
                    self.current_process = None
            except Exception as e:
                logger.warning(f"Error closing process handle: {e}")

    def _monitor_download(self):
        """Monitora estado do processo e download com race condition prevention"""
        try:
            if not self.current_process:
                return

            # Verificar se processo ainda existe e está rodando
            is_running = False
            try:
                if self.current_process:
                    is_running = self.current_process.is_running()
            except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                is_running = False

            if not is_running:
                # Processo terminou - verificar se foi esperado
                if self.download_state == DownloadState.DOWNLOADING:
                    # Se não estamos em finalização controlada, verificar terminação inesperada
                    if not self._task_finishing:
                        # Delay reduzido para melhor responsividade
                        QTimer.singleShot(1000, self._check_process_termination)
        except Exception as e:
            logger.error(f"Error monitoring download: {e}")

    def _check_process_termination(self):
        """Verifica se a terminação do processo foi inesperada após um delay"""
        try:
            # Se a task está finalizando ou não está mais em DOWNLOADING, ignorar
            if self._task_finishing or self.download_state != DownloadState.DOWNLOADING:
                return

            # Se o estado ainda está em DOWNLOADING após 2 segundos, é inesperado
            logger.warning("Process terminated unexpectedly")
            self._handle_unexpected_termination()
        except Exception as e:
            logger.error(f"Error checking process termination: {e}")

    def _handle_unexpected_termination(self):
        """Lida com terminação inesperada do processo"""
        self.monitor_timer.stop()
        self._set_state(DownloadState.CANCELLED)
        self.download_error.emit("Download process terminated unexpectedly")

    # Handlers de signals da task
    def _handle_progress(self, message: str):
        """Handle progress messages from task"""
        logger.debug(f"Download progress: {message}")
        self.download_progress.emit(0, message)  # Percentage será calculado depois

    def _handle_percentage(self, percentage: int):
        """Handle percentage updates"""
        self.download_progress.emit(percentage, "")

    def _handle_bytes_downloaded(self, downloaded_bytes: int, total_bytes: int):
        """Handle bytes downloaded updates"""
        self.download_bytes.emit(downloaded_bytes, total_bytes)

    def _handle_steamless_progress(self, message: str):
        """Handle Steamless progress messages"""
        logger.debug(f"Steamless progress: {message}")
        self.steamless_progress.emit(message)

    def _on_process_started(self, process):
        """Handle process start"""
        try:
            self.current_process = psutil.Process(process.pid)
            logger.debug(f"Process started with PID: {process.pid}")
        except Exception as e:
            logger.error(f"Error tracking process: {e}")

    def _on_depot_completed(self, depot_id: str):
        """Handle depot completion"""
        if self.current_session:
            self.current_session.completed_depots.append(depot_id)
            self.current_session.save()

            # Check if this was the last depot
            if len(self.current_session.completed_depots) == len(
                self.current_session.selected_depots
            ):
                # All depots completed - stop monitoring to avoid false positives during Steamless
                self.monitor_timer.stop()
                logger.debug("All depots completed, stopping process monitoring")

        self.depot_completed.emit(depot_id)
        logger.debug(f"Depot completed: {depot_id}")

    def _on_task_finished(self):
        """Handle task completion - novo método simplificado"""
        # Parar monitoramento imediatamente
        if hasattr(self, "monitor_timer") and self.monitor_timer:
            self.monitor_timer.stop()

        # Marcar que a task está finalizando
        self._task_finishing = True

        # Limpar referência do processo
        self.current_process = None

        # Se já foi cancelado, não fazer nada
        if self.download_state == DownloadState.CANCELLED:
            logger.info("Download task finished after cancellation")
            return

        # Se não foi cancelado, marcar como completado e emitir signal
        self._set_state(DownloadState.COMPLETED)
        if self.current_session:
            self.current_session.download_state = DownloadState.COMPLETED
            self.current_session.save()

            # Calcular caminho de instalação para Online-Fixes
            install_path = self._get_game_install_directory(
                self.current_session.dest_path, self.current_session.game_data
            )

            self.download_completed.emit(self.current_session.session_id, install_path)

        logger.debug("Download task finished successfully")

    def _on_task_cancelled(self):
        """Handle task cancellation - novo método"""
        self.monitor_timer.stop()

        # Marcar que a task está finalizando
        self._task_finishing = True

        # Limpar referência ao processo
        self.current_process = None

        # Mudar estado para cancelled
        self._set_state(DownloadState.CANCELLED)
        if self.current_session:
            self.current_session.download_state = DownloadState.CANCELLED
            self.current_session.save()

        # Emitir signal de cancelamento
        self.download_cancelled.emit()

        logger.info("Download task cancelled successfully")

    def _handle_task_error(self, error_message: str):
        """Handle task errors"""
        self.monitor_timer.stop()

        # Se o erro é relacionado ao cancelamento, emitir cancelled em vez de error
        if (
            "cancel" in error_message.lower()
            or self.download_state == DownloadState.CANCELLING
        ):
            self._set_state(DownloadState.CANCELLED)
            self.download_cancelled.emit()
        else:
            self._set_state(DownloadState.CANCELLED)
            self.download_error.emit(error_message)

        logger.error(f"Download task error: {error_message}")

    def cleanup(self):
        """
        Enhanced cleanup with proper resource management.

        Garante que:
        - Timer seja parado
        - Processos sejam terminados gracefulmente
        - Threads sejam limpas
        - Recursos sejam liberados
        - Process handles sejam fechados
        """
        try:
            logger.debug("Cleaning up DownloadManager resources...")

            # Parar timer de monitoramento
            if hasattr(self, "monitor_timer"):
                self.monitor_timer.stop()

            # Terminar processo ativo com cleanup completo
            if self.current_process:
                try:
                    if self.current_process.is_running():
                        self._terminate_process()
                    else:
                        # Even if not running, close the handle
                        self.current_process = None
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    logger.debug(f"Process already terminated: {e}")
                    self.current_process = None
                except Exception as e:
                    logger.error(f"Error in process cleanup: {e}")
                    self.current_process = None

            # Limpar threads ativas
            if hasattr(self, "_active_threads"):
                for thread in list(self._active_threads):
                    try:
                        if (
                            thread
                            and hasattr(thread, "isRunning")
                            and thread.isRunning()
                        ):
                            thread.quit()
                            if not thread.wait(2000):
                                thread.terminate()
                                thread.wait(1000)
                    except Exception as e:
                        logger.warning(f"Error cleaning up thread {thread}: {e}")
                    finally:
                        self._active_threads.discard(thread)

            # Clean up download task properly
            if self.download_task:
                try:
                    self.download_task.cleanup()
                except Exception as e:
                    logger.warning(f"Error cleaning up download task: {e}")
                finally:
                    self.download_task = None

            # Limpar task runner com force_cleanup
            if self.task_runner:
                try:
                    if hasattr(self.task_runner, "force_cleanup"):
                        self.task_runner.force_cleanup()
                        logger.debug("Used force_cleanup on download task runner")
                    else:
                        # Fallback para método antigo
                        if (
                            hasattr(self.task_runner, "thread")
                            and self.task_runner.thread
                        ):
                            thread = self.task_runner.thread
                            if thread.isRunning():
                                thread.quit()
                                thread.wait(3000)
                            # Limpar referência antes de deletar
                            self.task_runner.thread = None
                except Exception as e:
                    # Silenciar warning de deleção de C/C++ object - é normal no PyQt6
                    if "wrapped C/C++ object" not in str(e):
                        logger.warning(f"Error cleaning up task runner thread: {e}")
                finally:
                    self.task_runner = None

            # Limpar referências
            self.current_process = None
            self.current_session = None

            logger.debug("DownloadManager cleanup completed")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
