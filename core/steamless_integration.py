import logging
import os
import subprocess
import shutil
import re
from pathlib import Path
from typing import List, Optional, Dict
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

class SteamlessIntegration(QObject):
    """
    Integration module for Steamless CLI to remove Steam DRM from downloaded games.
    Handles Wine execution on Linux and file management using a Temp/Output isolation workflow.
    """

    progress = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal(bool)

    def __init__(self, steamless_path: Optional[str] = None):
        super().__init__()
        self.steamless_path = steamless_path or os.path.join(os.getcwd(), "Steamless")
        self.wine_available = self._check_wine_availability()

    def _check_wine_availability(self) -> bool:
        try:
            result = subprocess.run(['wine', '--version'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info(f"Wine detected: {result.stdout.strip()}")

            # Check winepath availability
            try:
                winepath_result = subprocess.run(['winepath', '--version'],
                                               capture_output=True, text=True, timeout=5)
                if winepath_result.returncode == 0:
                    logger.info(f"Winepath detected: {winepath_result.stdout.strip()}")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.warning("Winepath not found, will use fallback conversion")

            return True
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"Wine not available: {e}")

        self.error.emit("Wine is not installed or not available. Cannot run Steamless CLI.")
        return False

    def find_game_executables(self, game_directory: str) -> List[str]:
        if not os.path.exists(game_directory):
            logger.error(f"Game directory not found: {game_directory}")
            return []

        exe_files = []
        game_name = os.path.basename(game_directory.rstrip('/'))

        logger.debug(f"Searching for executables in: {game_directory}")

        for root, dirs, files in os.walk(game_directory):
            for file in files:
                if file.lower().endswith('.exe'):
                    file_path = os.path.join(root, file)

                    # Skip uninstaller/setup/config files
                    if self._should_skip_exe(file, file_path):
                        continue

                    # Skip tiny files (<100KB)
                    try:
                        if os.path.getsize(file_path) < 100 * 1024:
                            continue
                    except OSError:
                        continue

                    exe_files.append({
                        'path': file_path,
                        'name': file,
                        'size': os.path.getsize(file_path),
                        'priority': self._calculate_exe_priority(file, game_name, os.path.getsize(file_path))
                    })

        # Sort by priority (higher first)
        exe_files.sort(key=lambda x: x['priority'], reverse=True)

        logger.info(f"Found {len(exe_files)} executable(s) in {game_directory}")

        # Return just the paths
        return [x['path'] for x in exe_files]

    def _should_skip_exe(self, filename: str, file_path: Optional[str] = None) -> bool:
        skip_patterns = [
            r'^unins.*\.exe$', r'^setup.*\.exe$', r'^config.*\.exe$',
            r'^updater.*\.exe$', r'^patch.*\.exe$', r'^redist.*\.exe$',
            r'^vcredist.*\.exe$', r'^dxsetup.*\.exe$', r'^physx.*\.exe$',
            r'^unitycrashhandler.*\.exe$'
        ]
        for pattern in skip_patterns:
            if re.match(pattern, filename.lower()):
                return True
        return False

    def _calculate_exe_priority(self, filename: str, game_name: str, file_size: int) -> int:
        filename_lower = filename.lower()
        game_name_lower = game_name.lower()
        priority = 0
        game_name_clean = ''.join(c for c in game_name_lower if c.isalnum())

        if filename_lower.startswith(game_name_clean): priority += 100
        elif game_name_clean in filename_lower: priority += 80

        if filename_lower in ['game.exe', 'main.exe', 'play.exe', 'start.exe']: priority += 50

        if file_size > 50 * 1024 * 1024: priority += 30
        elif file_size > 10 * 1024 * 1024: priority += 20

        if any(word in filename_lower for word in ['crash', 'handler', 'debug', 'unitycrash']): priority -= 50

        return max(0, priority)

    def process_game_with_steamless(self, game_directory: str) -> bool:
        """
        Orchestrates the Move -> Process -> Return workflow.
        LIMITS processing to the TOP 3 candidates to save time.
        """
        if not self.wine_available:
            self.error.emit("Wine unavailable.")
            return False

        if not os.path.exists(self.steamless_path):
            self.error.emit(f"Steamless dir missing: {self.steamless_path}")
            return False

        # 1. Find Files
        self.progress.emit("Scanning for executables...")
        all_exes = self.find_game_executables(game_directory)

        if not all_exes:
            self.error.emit("No valid executables found to process.")
            self.finished.emit(True)
            return True

        # --- OTIMIZAÇÃO: Pega apenas os 3 melhores candidatos ---
        target_exes = all_exes[:3]
        self.progress.emit(f"Found {len(all_exes)} exes. Processing top {len(target_exes)} candidates...")
        # --------------------------------------------------------

        # 2. Setup Temp Dirs
        temp_root = os.path.join(game_directory, "_bifrost_temp")
        input_dir = os.path.join(temp_root, "input")
        output_dir = os.path.join(temp_root, "output")

        # Clean slate
        if os.path.exists(temp_root):
            try: shutil.rmtree(temp_root)
            except: pass

        try:
            os.makedirs(input_dir, exist_ok=True)
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            self.error.emit(f"Failed to create temp dirs: {e}")
            return False

        # Store mapping:  temp_filename -> original_full_path
        file_map: Dict[str, str] = {}

        try:
            # 3. MOVE TO TEMP (Isolation)
            for idx, original_path in enumerate(target_exes):
                filename = os.path.basename(original_path)
                temp_filename = f"{idx}_{filename}"
                temp_path = os.path.join(input_dir, temp_filename)

                try:
                    shutil.move(original_path, temp_path)
                    file_map[temp_filename] = original_path
                except Exception as e:
                    logger.error(f"Failed to move {filename}: {e}")

            # 4. RUN STEAMLESS (Processing)
            success_count = 0

            for temp_filename, original_path in file_map.items():
                input_file = os.path.join(input_dir, temp_filename)

                self.progress.emit(f"Processing: {os.path.basename(original_path)}")

                # Run Steamless logic
                is_unpacked = self._run_steamless_core(input_file)

                if is_unpacked:
                    unpacked_file = f"{input_file}.unpacked.exe"

                    if os.path.exists(unpacked_file):
                        # Move validated unpacked file to OUTPUT
                        dest_output = os.path.join(output_dir, temp_filename)
                        shutil.move(unpacked_file, dest_output)
                        success_count += 1
                        self.progress.emit(f"  -> DRM Removed! (Queued)")


            # 5. RETURN TO ORIGIN (Restoration)
            self.progress.emit("Restoring files...")

            for temp_filename, origin_path in file_map.items():

                path_in_output = os.path.join(output_dir, temp_filename)
                path_in_input = os.path.join(input_dir, temp_filename)

                # CASE A: DRM was removed (File exists in OUTPUT)
                if os.path.exists(path_in_output):
                    # 1. Original (currently in input) becomes backup at origin
                    backup_path = f"{origin_path}.original.exe"
                    if os.path.exists(backup_path):
                        try: os.remove(backup_path)
                        except: pass

                    if os.path.exists(path_in_input):
                        shutil.move(path_in_input, backup_path)

                    # 2. Unpacked (from output) goes to origin as the new main exe
                    shutil.move(path_in_output, origin_path)
                    self.progress.emit(f"Patched: {os.path.basename(origin_path)}")

                # CASE B: No DRM or Failed (File is only in INPUT)
                elif os.path.exists(path_in_input):
                    # Just put it back exactly where it was
                    shutil.move(path_in_input, origin_path)

                else:
                    self.error.emit(f"CRITICAL: File lost: {temp_filename}")

            self.progress.emit(f"Steamless Complete. patched {success_count} files.")
            self.finished.emit(True)
            return True

        except Exception as e:
            logger.error(f"Steamless Process Failed: {e}", exc_info=True)
            self.error.emit(f"Steamless Critical Error: {str(e)}")

            # Emergency Restore
            self.progress.emit("Attempting emergency file restore...")
            try:
                for temp_name, orig_path in file_map.items():
                    inp = os.path.join(input_dir, temp_name)
                    if os.path.exists(inp) and not os.path.exists(orig_path):
                        shutil.move(inp, orig_path)
            except:
                pass
            self.finished.emit(False)
            return False

        finally:
            # 6. CLEANUP
            if os.path.exists(temp_root):
                try: shutil.rmtree(temp_root)
                except: pass

    def _convert_to_windows_path(self, linux_path: str) -> str:
        """
        Convert Linux path to Windows path using winepath.
        Falls back to manual conversion if winepath fails.
        """
        try:
            result = subprocess.run(
                ['winepath', '-w', linux_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError) as e:
            logger.warning(f"winepath failed: {e}, using manual conversion")

        # Fallback: Manual conversion: /home/user/game -> Z:\home\user\game
        return "Z:" + linux_path.replace("/", "\\")

    def _run_steamless_core(self, input_file_path: str) -> bool:
        """
        Runs the actual CLI command on a specific file.
        """
        try:
            windows_path = self._convert_to_windows_path(input_file_path)

            # --quiet removed for better debugging if needed, but kept minimal logic
            cmd = ['wine', 'Steamless.CLI.exe', '-f', windows_path]

            process = subprocess.Popen(
                cmd,
                cwd=self.steamless_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            unpacked_created = False

            if process.stdout:
                for line in iter(process.stdout.readline, ''):
                    if not line: break
                    line = line.strip()

                    if "steam stub" in line.lower() or "unpacked" in line.lower():
                        self.progress.emit(f"Steamless: {line}")

                    if "unpacked file saved" in line.lower() or "successfully unpacked" in line.lower():
                        unpacked_created = True

            process.wait()

            # Double check file existence
            expected_output = f"{input_file_path}.unpacked.exe"
            return os.path.exists(expected_output)

        except Exception as e:
            logger.error(f"Core execution error: {e}")
            return False
