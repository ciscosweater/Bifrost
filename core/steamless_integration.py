import os
import re
import shutil
import subprocess
from typing import List, Optional

import psutil
from PyQt6.QtCore import QObject, pyqtSignal
from utils.logger import get_internationalized_logger

logger = get_internationalized_logger("Steamless")


class SteamlessIntegration(QObject):
    """
    Integration module for Steamless CLI to remove Steam DRM from downloaded games.
    Handles Wine execution on Linux and file management.
    """

    progress = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal(bool)

    def __init__(
        self, steamless_path: Optional[str] = None, performance_mode: bool = True
    ):
        super().__init__()
        self.steamless_path = steamless_path or os.path.join(os.getcwd(), "Steamless")
        self.wine_available = self._check_wine_availability()
        self.original_process_priority = None
        self.performance_mode = performance_mode

    def _check_wine_availability(self) -> bool:
        """Check if Wine is installed and available."""
        try:
            result = subprocess.run(
                ["wine", "--version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                logger.info(f"Wine detected: {result.stdout.strip()}")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"Wine not available: {e}")

        self.error.emit(
            "Wine is not installed or not available. Cannot run Steamless CLI."
        )
        return False

    def _check_disk_performance(self, path: str) -> dict:
        """Check disk performance metrics for optimization suggestions."""
        try:
            disk_usage = shutil.disk_usage(path)
            disk_free_gb = disk_usage.free / (1024**3)

            # Check if using SSD (simplified check)
            try:
                stat = os.statvfs(path)
                # This is a simplified check - real SSD detection is more complex
                is_likely_ssd = (
                    stat.f_bsize > 4096
                )  # Larger block size might indicate SSD
            except (AttributeError, TypeError):
                is_likely_ssd = False

            return {
                "free_space_gb": disk_free_gb,
                "is_likely_ssd": is_likely_ssd,
                "low_space_warning": disk_free_gb < 5,  # Less than 5GB
                "performance_tips": [],
            }
        except Exception as e:
            logger.warning(f"Could not check disk performance: {e}")
            return {"performance_tips": ["Could not analyze disk performance"]}

    def find_game_executables(self, game_directory: str) -> List[dict]:
        """
        Find all executable files in the game directory and subdirectories.
        Returns a list of .exe files sorted by priority.
        """
        if not os.path.exists(game_directory):
            logger.error(f"Game directory not found: {game_directory}")
            return []

        exe_files = []
        game_name = os.path.basename(game_directory.rstrip("/"))

        # Walk through all subdirectories
        logger.debug(f"Searching for executables in: {game_directory}")
        all_files_found = []

        for root, dirs, files in os.walk(game_directory):
            logger.debug(f"Scanning directory: {root} - Found {len(files)} files")
            all_files_found.extend(files)

            for file in files:
                if file.lower().endswith(".exe"):
                    file_path = os.path.join(root, file)
                    logger.debug(f"Found executable: {file_path}")

                    # Skip system/uninstaller files
                    if self._should_skip_exe(file, file_path):
                        logger.debug(f"Skipping executable (name filtered): {file}")
                        continue

                    # Get file size for priority calculation
                    try:
                        file_size = os.path.getsize(file_path)
                    except OSError:
                        file_size = 0

                    # Skip very small files (likely utilities) - but allow main game executables
                    if file_size < 100 * 1024:  # < 100KB
                        logger.debug(
                            f"Skipping executable (size filtered): {file} ({file_size} bytes)"
                        )
                        continue

                    # Get file size for priority calculation
                    try:
                        file_size = os.path.getsize(file_path)
                    except OSError:
                        file_size = 0

                    exe_files.append(
                        {
                            "path": file_path,
                            "name": file,
                            "size": file_size,
                            "priority": self._calculate_exe_priority(
                                file, game_name, file_size
                            ),
                        }
                    )
                else:
                    # Log non-exe files for debugging
                    if file.lower().endswith((".dll", ".so", ".bin")):
                        logger.debug(f"Found binary file: {file}")

        # Log summary of what was found
        exe_count = len([f for f in all_files_found if f.lower().endswith(".exe")])
        logger.debug(
            f"Directory scan complete. Total files: {len(all_files_found)}, EXE files: {exe_count}, After filtering: {len(exe_files)}"
        )

        if exe_count == 0:
            logger.warning(f"No .exe files found in {game_directory}")
            logger.debug(f"First 10 files found: {all_files_found[:10]}")
        elif len(exe_files) == 0:
            logger.warning(f"Found {exe_count} .exe files but all were filtered out")
            for root, dirs, files in os.walk(game_directory):
                for file in files:
                    if file.lower().endswith(".exe"):
                        logger.debug(f"Filtered EXE: {os.path.join(root, file)}")

        # Sort by priority (higher first)
        exe_files.sort(key=lambda x: x["priority"], reverse=True)

        if len(exe_files) == 0:
            logger.warning(f"No executables found in {game_directory}")
        else:
            logger.debug(f"Found {len(exe_files)} executable(s) in {game_directory}")
            for exe in exe_files[:3]:  # Log top 3 candidates only in debug
                logger.debug(
                    f"  - {exe['name']} ({exe['size']} bytes, priority: {exe['priority']})"
                )

        return exe_files  # Return full dictionaries with path, name, size, priority

    def _should_skip_exe(self, filename: str, file_path: Optional[str] = None) -> bool:
        """Check if an executable should be skipped based on name patterns."""
        skip_patterns = [
            r"^unins.*\.exe$",  # uninstallers
            r"^setup.*\.exe$",  # installers
            r"^config.*\.exe$",  # configuration tools
            r"^launcher.*\.exe$",  # launchers (usually not the main game)
            r"^updater.*\.exe$",  # updaters
            r"^patch.*\.exe$",  # patches
            r"^redist.*\.exe$",  # redistributables
            r"^vcredist.*\.exe$",  # Visual C++ redistributables
            r"^dxsetup.*\.exe$",  # DirectX setup
            r"^physx.*\.exe$",  # PhysX installers
        ]

        filename_lower = filename.lower()
        for pattern in skip_patterns:
            if re.match(pattern, filename_lower):
                return True

        # Skip very small files (likely utilities) - but allow main game executables
        try:
            # Use full path if available, otherwise assume it's a relative path
            path_to_check = file_path if file_path else filename
            file_size = os.path.getsize(path_to_check)
            # Only skip if smaller than 100KB AND not matching game name patterns
            if file_size < 100 * 1024:  # < 100KB
                return True
        except OSError:
            # Only skip if we can't get the file size AND it's not a likely main executable
            # Main game executables should exist, so this might be a broken symlink
            if file_path is None:
                return True
            # If we have a full path but can't read it, log but don't skip (might be permission issue)
            logger.debug(f"Cannot read file size for {filename}, but not skipping")
            return False

        return False

    def _calculate_exe_priority(
        self, filename: str, game_name: str, file_size: int
    ) -> int:
        """Calculate priority score for an executable file."""
        filename_lower = filename.lower()
        game_name_lower = game_name.lower()

        priority = 0

        # High priority: exact match with game name (remove spaces and special chars)
        game_name_clean = "".join(c for c in game_name_lower if c.isalnum())
        game_name_with_spaces = game_name_lower.replace(" ", "")

        if filename_lower.startswith(game_name_clean):
            priority += 100
        elif filename_lower.startswith(game_name_with_spaces):
            priority += 90
        elif game_name_clean in filename_lower:
            priority += 80  # Partial match still gets good priority
        elif game_name_with_spaces in filename_lower:
            priority += 70

        # Medium priority: common main executable names
        main_exe_patterns = ["game.exe", "main.exe", "play.exe", "start.exe"]
        if filename_lower in main_exe_patterns:
            priority += 50

        # Bonus for larger files (likely the main game)
        if file_size > 50 * 1024 * 1024:  # > 50MB
            priority += 30
        elif file_size > 10 * 1024 * 1024:  # > 10MB
            priority += 20
        elif file_size > 5 * 1024 * 1024:  # > 5MB
            priority += 10

        # Penalty for common non-game executables
        if any(
            word in filename_lower for word in ["editor", "tool", "config", "settings"]
        ):
            priority -= 20

        # High penalty for crash handlers and utilities
        if any(
            word in filename_lower
            for word in ["crash", "handler", "debug", "unitycrash"]
        ):
            priority -= 50

        return max(0, priority)

    def process_game_with_steamless(self, game_directory: str) -> bool:
        """
        Main method to process a game directory with Steamless.
        Returns True if successful, False otherwise.
        """
        if not self.wine_available:
            self.error.emit("Wine is not available for Steamless execution.")
            return False

        if not os.path.exists(self.steamless_path):
            self.error.emit(f"Steamless directory not found: {self.steamless_path}")
            return False

        steamless_cli = os.path.join(self.steamless_path, "Steamless.CLI.exe")
        if not os.path.exists(steamless_cli):
            self.error.emit(f"Steamless.CLI.exe not found: {steamless_cli}")
            return False

        # Check disk performance for optimization tips
        disk_info = self._check_disk_performance(game_directory)
        if disk_info.get("low_space_warning"):
            self.progress.emit(
                "[!] Low disk space detected - this may slow down Steamless"
            )
        if not disk_info.get("is_likely_ssd", True):
            self.progress.emit(
                "[TIP] Using SSD would significantly improve Steamless performance"
            )

        # Clean temporary files for better performance
        if self.performance_mode:
            self._cleanup_temp_files(game_directory)

        self.progress.emit("Searching for game executables...")
        exe_files = self.find_game_executables(game_directory)

        if not exe_files:
            self.error.emit("No suitable game executables found.")
            return False

        # Try executables in order of priority until one works
        max_attempts = min(3, len(exe_files))  # Try up to 3 executables

        for i in range(max_attempts):
            exe_info = exe_files[i]
            target_exe = exe_info["path"]
            exe_name = exe_info["name"]
            priority = exe_info["priority"]

            self.progress.emit(
                f"Attempt {i + 1}/{max_attempts}: Processing {exe_name} (priority: {priority})"
            )

            if self._run_steamless_on_exe(target_exe):
                self.progress.emit(f"Successfully processed: {exe_name}")
                return True
            else:
                self.progress.emit(f"Failed to process {exe_name}, trying next...")
                continue

        # If all attempts failed
        self.error.emit(f"Failed to process all {max_attempts} executable(s).")
        return False

    def _optimize_system_performance(self):
        """Optimize system performance for Steamless execution."""
        try:
            current_process = psutil.Process()
            self.original_process_priority = current_process.nice()
            # Unix-like systems
            current_process.nice(-5)  # Higher priority

            # Optimize memory usage
            if self.performance_mode:
                # Force garbage collection
                import gc

                gc.collect()

                # Check available memory
                memory = psutil.virtual_memory()
                if memory.percent > 80:
                    self.progress.emit(
                        "[!] High memory usage detected - consider closing other applications"
                    )

            logger.info("System performance optimized for Steamless")
        except Exception as e:
            logger.warning(f"Could not optimize system performance: {e}")

    def _restore_system_performance(self):
        """Restore original system performance settings."""
        try:
            if self.original_process_priority is not None:
                current_process = psutil.Process()
                current_process.nice(self.original_process_priority)
                logger.info("System performance restored to normal")
        except Exception as e:
            logger.warning(f"Could not restore system performance: {e}")

    def _run_steamless_on_exe(self, exe_path: str) -> bool:
        """Run Steamless CLI on a specific executable."""
        try:
            # Optimize system for performance
            self._optimize_system_performance()
            # Convert Linux path to Windows path for Wine
            windows_path = self._convert_to_windows_path(exe_path)
            if not windows_path:
                return False

            steamless_dir = self.steamless_path

            # Prepare Wine command with optimization flags
            cmd = [
                "wine",
                "Steamless.CLI.exe",
                "-f",
                windows_path,
                "--quiet",  # Reduce debug output for better performance
                "--realign",  # Realign sections for better file structure
                "--recalcchecksum",  # Ensure proper PE checksum
            ]

            # Add experimental features for maximum performance if enabled
            if self.performance_mode:
                cmd.append("--exp")  # Use experimental features for better speed

            self.progress.emit(f"Running Steamless (optimized): {' '.join(cmd)}")

            # Run Steamless CLI with optimized process settings
            process = subprocess.Popen(
                cmd,
                cwd=steamless_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                bufsize=0,  # Unbuffered output for faster processing
                preexec_fn=os.setsid
                if hasattr(os, "setsid")
                else None,  # Process group isolation
            )

            # Monitor output
            has_drm = False
            unpacked_created = False

            if process.stdout:
                for line in iter(process.stdout.readline, ""):
                    if not line:
                        break

                    line = line.strip()
                    self.progress.emit(f"Steamless: {line}")

                    # Check for DRM detection
                    if (
                        "steam stub" in line.lower()
                        or "drift" in line.lower()
                        or "steamstub" in line.lower()
                        or "packed with" in line.lower()
                    ):
                        has_drm = True

                    # Check for unpacked file creation
                    if (
                        "unpacked file saved to disk" in line.lower()
                        or "unpacked file saved as" in line.lower()
                        or "successfully unpacked file" in line.lower()
                        or ("unpacked" in line.lower() and ".exe" in line.lower())
                    ):
                        unpacked_created = True

            process.wait()

            if process.returncode != 0:
                self.error.emit(
                    f"Steamless failed with exit code: {process.returncode}"
                )
                return False

            if not has_drm:
                self.progress.emit("No Steam DRM detected in executable.")
                self.finished.emit(True)
                return True

            # Check if unpacked file was actually created (more reliable than output parsing)
            # Steamless creates: original.exe.unpacked.exe (keeps the .exe)
            unpacked_exe = f"{exe_path}.unpacked.exe"
            actual_unpacked_created = os.path.exists(unpacked_exe)

            if actual_unpacked_created:
                self.progress.emit(
                    f"Unpacked file detected: {os.path.basename(unpacked_exe)}"
                )
                return self._handle_unpacked_files(exe_path)
            else:
                if unpacked_created:
                    self.progress.emit(
                        "Steamless output indicated unpacked file was created, but file not found."
                    )
                else:
                    self.progress.emit(
                        "Steamless completed but no unpacked file was created."
                    )
                self.finished.emit(True)
                return True

        except Exception as e:
            logger.error(f"Error running Steamless: {e}", exc_info=True)
            self.error.emit(f"Error running Steamless: {str(e)}")
            return False
        finally:
            # Always restore system performance
            self._restore_system_performance()

    def _convert_to_windows_path(self, linux_path: str) -> Optional[str]:
        """Convert Linux path to Windows path format for Wine."""
        try:
            # Use winepath to convert the path
            result = subprocess.run(
                ["winepath", "-w", linux_path],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                windows_path = result.stdout.strip()
                logger.debug(f"Converted path: {linux_path} -> {windows_path}")
                return windows_path
            else:
                logger.error(f"Failed to convert path: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"Error converting path: {e}")
            return None

    def _cleanup_temp_files(self, directory: str):
        """Clean up temporary files that might slow down processing."""
        try:
            temp_patterns = ["*.tmp", "*.temp", "~*.*", ".DS_Store", "Thumbs.db"]
            cleaned_count = 0

            for pattern in temp_patterns:
                import glob

                for temp_file in glob.glob(
                    os.path.join(directory, "**", pattern), recursive=True
                ):
                    try:
                        os.remove(temp_file)
                        cleaned_count += 1
                    except (AttributeError, TypeError):
                        pass

            if cleaned_count > 0:
                self.progress.emit(
                    f"Cleaned {cleaned_count} temporary files for better performance"
                )
        except Exception as e:
            logger.debug(f"Could not clean temp files: {e}")

    def _handle_unpacked_files(self, original_exe: str) -> bool:
        """Handle the renaming of files after successful Steamless processing."""
        try:
            # Steamless creates: original.exe.unpacked.exe (keeps the .exe)
            unpacked_exe = f"{original_exe}.unpacked.exe"
            original_backup = f"{original_exe}.original.exe"

            if os.path.exists(unpacked_exe):
                # Rename original to .original
                if os.path.exists(original_backup):
                    logger.warning(f"Backup file already exists: {original_backup}")
                    os.remove(original_backup)

                shutil.move(original_exe, original_backup)
                self.progress.emit(
                    f"Renamed original: {os.path.basename(original_exe)} -> {os.path.basename(original_backup)}"
                )

                # Rename unpacked to original name
                shutil.move(unpacked_exe, original_exe)
                self.progress.emit(
                    f"Renamed unpacked: {os.path.basename(unpacked_exe)} -> {os.path.basename(original_exe)}"
                )

                self.progress.emit("Steam DRM successfully removed!")
                self.finished.emit(True)
                return True
            else:
                self.progress.emit(
                    "Unpacked file not found. DRM may not have been present or removable."
                )
                self.finished.emit(True)
                return True

        except Exception as e:
            logger.error(f"Error handling unpacked files: {e}", exc_info=True)
            self.error.emit(f"Error handling unpacked files: {str(e)}")
            return False
