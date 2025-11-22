import logging
from utils.logger import get_internationalized_logger
import os
import shutil
import time
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import QThread, pyqtSignal

from . import steam_helpers

logger = get_internationalized_logger()

# Directory size cache with TTL (15 minutes for better performance)
_DIRECTORY_SIZE_CACHE = {}
_CACHE_TTL_SECONDS = 900  # 15 minutes
_MAX_CACHE_SIZE = 200  # Increased cache size

# Games scan cache to avoid duplicate calls
_GAMES_SCAN_CACHE = {}
_GAMES_SCAN_CACHE_TTL = 30  # 30 seconds cache for games scan


class DirectorySizeWorker(QThread):
    """Worker thread to calculate directory sizes without blocking UI."""

    size_calculated = pyqtSignal(int)

    def __init__(self, path: str):
        super().__init__()
        self.path = path

    def run(self):
        """Calculates directory size in background."""
        size = self._calculate_directory_size_optimized(self.path)
        self.size_calculated.emit(size)

    @staticmethod
    def _calculate_directory_size_optimized(path: str, max_depth: int = 20) -> int:
        """Calculates size using os.scandir with early termination and limits."""
        # Validate path before processing
        if not path or not isinstance(path, str):
            logger.debug("Invalid path provided for size calculation")
            return 0

        # Normalize path
        path = os.path.normpath(path)

        # Check cache first
        current_time = time.time()
        cache_key = path

        if cache_key in _DIRECTORY_SIZE_CACHE:
            cached_size, cached_time = _DIRECTORY_SIZE_CACHE[cache_key]
            if current_time - cached_time < _CACHE_TTL_SECONDS:
                logger.debug(
                    f"Using cached size for {os.path.basename(path)}: {cached_size} bytes"
                )
                return cached_size

        # Check if directory exists
        if not os.path.exists(path):
            logger.debug(f"Directory does not exist: {path}")
            _DIRECTORY_SIZE_CACHE[cache_key] = (
                0,
                current_time,
            )  # Cache negative result
            return 0

        if not os.path.isdir(path):
            logger.debug(f"Path is not a directory: {path}")
            return 0

        total_size = 0
        file_count = 0
        dir_count = 0
        large_files = 0

        # Performance limits to prevent excessive scanning
        MAX_FILES = 10000  # Limit files to prevent excessive scanning
        MAX_DIRS = 1000  # Limit directories to prevent excessive recursion
        SAMPLE_SIZE = 1000  # Sample size for estimation when limits hit

        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    # Early termination for file count limit
                    if file_count > MAX_FILES:
                        logger.warning(
                            f"Directory scan limit reached ({MAX_FILES} files): {path}"
                        )
                        # Estimate total size based on sample
                        if file_count > SAMPLE_SIZE:
                            avg_file_size = total_size / file_count
                            estimated_total = int(
                                avg_file_size * file_count * 1.2
                            )  # 20% buffer
                            logger.debug(
                                f"Estimated size for {os.path.basename(path)}: {GameManager._format_size(estimated_total)}"
                            )
                            _DIRECTORY_SIZE_CACHE[cache_key] = (
                                estimated_total,
                                current_time,
                            )
                            return estimated_total
                        break

                    try:
                        stat_info = entry.stat()

                        if entry.is_file():
                            # Check for very large file size
                            file_size = stat_info.st_size
                            if file_size > 1024 * 1024 * 1024:  # > 1GB
                                large_files += 1

                            total_size += file_size
                            file_count += 1

                        elif entry.is_dir() and max_depth > 0:
                            # Early termination for directory count limit
                            if dir_count > MAX_DIRS:
                                logger.warning(
                                    f"Directory recursion limit reached ({MAX_DIRS} dirs): {path}"
                                )
                                break

                            # Avoid recursion in system directories
                            dir_name = entry.name.lower()
                            if dir_name in [
                                "node_modules",
                                ".git",
                                "__pycache__",
                                "venv",
                                ".venv",
                                "target",
                                "build",
                                "dist",
                                ".vscode",
                                ".idea",
                            ]:
                                logger.debug(f"Skipping system directory: {entry.path}")
                                continue

                            # Skip hidden directories (performance optimization)
                            if dir_name.startswith("."):
                                logger.debug(f"Skipping hidden directory: {entry.path}")
                                continue

                            # Recursive call with depth limit
                            dir_size = (
                                DirectorySizeWorker._calculate_directory_size_optimized(
                                    entry.path, max_depth - 1
                                )
                            )
                            total_size += dir_size
                            dir_count += 1

                    except (OSError, IOError, PermissionError) as e:
                        logger.debug(f"Error accessing {entry.path}: {e}")
                        continue
                    except Exception as e:
                        logger.warning(f"Unexpected error processing {entry.path}: {e}")
                        continue

        except (OSError, IOError, PermissionError) as e:
            logger.error(f"Permission error scanning directory {path}: {e}")
            return 0
        except Exception as e:
            logger.error(
                f"Critical error calculating directory size for {path}: {e}",
                exc_info=True,
            )
            return 0

        # Cache the result
        _DIRECTORY_SIZE_CACHE[cache_key] = (total_size, current_time)

        # Clean old cache entries periodically
        if len(_DIRECTORY_SIZE_CACHE) > _MAX_CACHE_SIZE:
            DirectorySizeWorker._cleanup_size_cache()

        # Log statistics if it's a large directory
        if logger.isEnabledFor(logging.DEBUG) and (file_count > 100 or dir_count > 10):
            logger.debug(
                f"Directory stats for {os.path.basename(path)}: "
                f"{file_count} files, {dir_count} subdirs, {large_files} large files, "
                f"depth: {20 - max_depth}/20, total size: {GameManager._format_size(total_size)}"
            )

        return total_size

    @staticmethod
    def _cleanup_size_cache():
        """Remove expired entries from directory size cache with LRU fallback."""
        current_time = time.time()
        expired_keys = []

        # First remove expired entries
        for key, (_, cached_time) in _DIRECTORY_SIZE_CACHE.items():
            if current_time - cached_time > _CACHE_TTL_SECONDS:
                expired_keys.append(key)

        # If there are still many entries, remove the oldest ones (LRU)
        if len(_DIRECTORY_SIZE_CACHE) - len(expired_keys) > _MAX_CACHE_SIZE // 2:
            # Sort by time and remove the oldest ones
            sorted_items = sorted(_DIRECTORY_SIZE_CACHE.items(), key=lambda x: x[1][1])
            excess_count = (
                len(_DIRECTORY_SIZE_CACHE) - len(expired_keys) - (_MAX_CACHE_SIZE // 2)
            )

            for i in range(excess_count):
                if i < len(sorted_items):
                    expired_keys.append(sorted_items[i][0])

        # Remove expired/selected keys
        for key in expired_keys:
            if key in _DIRECTORY_SIZE_CACHE:
                del _DIRECTORY_SIZE_CACHE[key]

        if expired_keys:
            logger.debug(
                f"Cleaned {len(expired_keys)} entries from size cache "
                f"({len([k for k, (_, t) in _DIRECTORY_SIZE_CACHE.items() if current_time - t > _CACHE_TTL_SECONDS])} expired)"
            )


class GameManager:
    """
    Manages operations with games downloaded by Bifrost.
    Responsible for scanning, parsing, and safely deleting games.
    """

    @staticmethod
    def scan_bifrost_games(
        async_size_calculation: bool = True, force_refresh: bool = False
    ) -> List[Dict]:
        """
        Scans all Steam libraries for Bifrost games.

        Args:
            async_size_calculation: If True, calculates sizes asynchronously for better performance
            force_refresh: If True, bypasses cache and forces a fresh scan

        Returns:
            List of dictionaries with information about found games
        """
        current_time = time.time()
        cache_key = f"games_scan_{async_size_calculation}"

        # Check cache first (unless force_refresh)
        if not force_refresh and cache_key in _GAMES_SCAN_CACHE:
            cached_games, cached_time = _GAMES_SCAN_CACHE[cache_key]
            if current_time - cached_time < _GAMES_SCAN_CACHE_TTL:
                logger.debug(
                    f"Using cached games scan result: {len(cached_games)} games"
                )
                return cached_games

        games = []
        libraries = steam_helpers.get_steam_libraries()

        logger.debug(f"Scanning {len(libraries)} Steam libraries for Bifrost games")

        for library_path in libraries:
            steamapps_path = os.path.join(library_path, "steamapps")
            if not os.path.isdir(steamapps_path):
                logger.debug(f"steamapps directory not found in {library_path}")
                continue

            acf_files = GameManager._find_acf_files(steamapps_path)
            logger.debug(f"Found {len(acf_files)} ACF files in {library_path}")

            for acf_file in acf_files:
                try:
                    game_info = GameManager._parse_acf_file(acf_file)
                    if game_info and GameManager._is_bifrost_game(game_info):
                        # Extract appid from the ACF file path
                        acf_filename = os.path.basename(acf_file)
                        appid = None
                        if acf_filename.startswith(
                            "appmanifest_"
                        ) and acf_filename.endswith(".acf"):
                            appid = acf_filename[len("appmanifest_") : -len(".acf")]
                            game_info["appid"] = appid
                        else:
                            logger.warning(
                                f"Invalid ACF filename format: {acf_filename}"
                            )
                            continue

                        # Add display_name field (same as name for now)
                        game_info["display_name"] = game_info.get("name", "")

                        # Add library_path and acf_path
                        game_info["library_path"] = library_path
                        game_info["acf_path"] = acf_file

                        # Calculate game directory size
                        installdir = game_info.get("installdir", "")
                        if installdir:
                            game_dir = os.path.join(
                                library_path, "steamapps", "common", installdir
                            )

                            # Check if directory exists before calculating size
                            if os.path.exists(game_dir):
                                if async_size_calculation:
                                    # Async calculation for better performance
                                    size_bytes = DirectorySizeWorker._calculate_directory_size_optimized(
                                        game_dir
                                    )
                                else:
                                    # Sync calculation (fallback)
                                    size_bytes = DirectorySizeWorker._calculate_directory_size_optimized(
                                        game_dir
                                    )

                                game_info["size_formatted"] = GameManager._format_size(
                                    size_bytes
                                )
                                game_info["game_dir"] = game_dir
                            else:
                                logger.warning(f"Game directory not found: {game_dir}")
                                game_info["size_formatted"] = "0 B"
                                game_info["game_dir"] = game_dir
                        else:
                            game_info["size_formatted"] = "0 B"
                            game_info["game_dir"] = None

                        games.append(game_info)

                except Exception as e:
                    logger.error(f"Error processing ACF file {acf_file}: {e}")
                    continue

        logger.debug(f"Found {len(games)} Bifrost games")

        # Cache the result
        _GAMES_SCAN_CACHE[cache_key] = (games, current_time)

        return games

    @staticmethod
    def _find_acf_files(steamapps_path: str) -> List[str]:
        """Find all ACF files optimized with validations."""
        acf_files = []

        # Validate directory
        if not steamapps_path or not os.path.exists(steamapps_path):
            logger.error(f"Invalid steamapps path: {steamapps_path}")
            return []

        if not os.path.isdir(steamapps_path):
            logger.error(f"Path is not a directory: {steamapps_path}")
            return []

        try:
            with os.scandir(steamapps_path) as entries:
                for entry in entries:
                    try:
                        # Validate it's a valid ACF file
                        if (
                            entry.is_file()
                            and entry.name.startswith("appmanifest_")
                            and entry.name.endswith(".acf")
                        ):
                            # Validate name format (appmanifest_{appid}.acf)
                            name_parts = entry.name[:-4].split("_")  # Remove .acf
                            if len(name_parts) == 2 and name_parts[0] == "appmanifest":
                                appid_part = name_parts[1]
                                # Check if appid is numeric
                                if appid_part.isdigit():
                                    acf_files.append(entry.path)
                                else:
                                    logger.debug(
                                        f"Skipping ACF with invalid appid: {entry.name}"
                                    )
                            else:
                                logger.debug(
                                    f"Skipping ACF with invalid format: {entry.name}"
                                )

                    except (OSError, PermissionError) as e:
                        logger.debug(f"Error accessing {entry.name}: {e}")
                        continue

        except (OSError, PermissionError) as e:
            logger.error(f"Permission error scanning directory {steamapps_path}: {e}")
        except Exception as e:
            logger.error(
                f"Unexpected error scanning directory {steamapps_path}: {e}",
                exc_info=True,
            )

        logger.debug(f"Found {len(acf_files)} valid ACF files in {steamapps_path}")
        return acf_files

    @staticmethod
    def _parse_acf_file(acf_path: str) -> Optional[Dict]:
        """Parse Steam ACF file with robust validation."""
        try:
            # Validate file before reading
            if not os.path.exists(acf_path):
                logger.error(f"ACF file does not exist: {acf_path}")
                return None

            if not os.path.isfile(acf_path):
                logger.error(f"ACF path is not a file: {acf_path}")
                return None

            # Validate file size to avoid reading corrupted files
            file_size = os.path.getsize(acf_path)
            if file_size == 0:
                logger.warning(f"ACF file is empty: {acf_path}")
                return {}

            if file_size > 10 * 1024 * 1024:  # 10MB max
                logger.error(f"ACF file too large ({file_size} bytes): {acf_path}")
                return None

            # Use context manager for proper file handle cleanup
            try:
                with open(acf_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except (OSError, IOError) as e:
                logger.error(f"Failed to open ACF file {acf_path}: {e}")
                return None

            if not content.strip():
                logger.warning(f"ACF file is empty after reading: {acf_path}")
                return {}

            game_info = {}
            line_number = 0

            for line in content.split("\n"):
                line_number += 1
                line = line.strip()

                # Skip empty lines or comments
                if not line or line.startswith("//"):
                    continue

                # Parse key-value in Steam format (accepts tabs or spaces)
                if '"' in line and (
                    ("\t" in line and line.count("\t") >= 2)  # Tab format
                    or ("  " in line and line.count('"') >= 4)
                ):  # Space format
                    try:
                        # Remove tabs and extra spaces, then split by quotes
                        cleaned_line = line.replace("\t", " ").strip()
                        # Normalize multiple spaces to single space
                        while "  " in cleaned_line:
                            cleaned_line = cleaned_line.replace("  ", " ")

                        parts = cleaned_line.split('"')
                        if len(parts) >= 3:
                            key = parts[1].strip()
                            value = parts[3] if len(parts) > 3 else ""

                            # Validate key
                            if key and not key.isspace():
                                game_info[key] = value
                            else:
                                logger.debug(
                                    f"Invalid key on line {line_number} in {acf_path}"
                                )
                    except Exception as e:
                        logger.debug(
                            f"Error parsing line {line_number} in {acf_path}: {e}"
                        )
                        continue

            # Validate essential fields
            if not game_info:
                logger.warning(f"No valid data parsed from ACF: {acf_path}")
                return {}

            # Debug log with important fields
            if logger.isEnabledFor(logging.DEBUG):
                important_fields = ["appid", "name", "installdir", "SizeOnDisk"]
                found_fields = {
                    k: v for k, v in game_info.items() if k in important_fields
                }
                logger.debug(f"Parsed ACF {os.path.basename(acf_path)}: {found_fields}")

            return game_info

        except UnicodeDecodeError as e:
            logger.error(f"Encoding error reading ACF {acf_path}: {e}")
            return None
        except PermissionError as e:
            logger.error(f"Permission denied reading ACF {acf_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error parsing ACF {acf_path}: {e}", exc_info=True)
            return None

    @staticmethod
    def _is_bifrost_game(game_info: Dict) -> bool:
        """Check if the game is Bifrost with robust validations."""
        try:
            if not game_info or not isinstance(game_info, dict):
                logger.debug("Invalid game_info: not a dictionary or empty")
                return False

            # Bifrost games have specific characteristics:
            # 1. SizeOnDisk = 0 (because they're downloaded differently)
            # 2. Have valid installdir
            # 3. Have valid name
            size_on_disk = game_info.get("SizeOnDisk", "1")
            name = game_info.get("name", "").strip()
            installdir = game_info.get("installdir", "").strip()

            # More rigorous validations
            if not isinstance(size_on_disk, str):
                logger.debug(f"Invalid SizeOnDisk type: {type(size_on_disk)}")
                return False

            # Convert to string if necessary and clean
            try:
                size_on_disk_clean = str(size_on_disk).strip()
            except Exception:
                logger.debug("Failed to convert SizeOnDisk to string")
                return False

            # Validate name
            if not name or len(name) < 1:
                logger.debug("Invalid or empty game name")
                return False

            # Validate installdir
            if not installdir or len(installdir) < 1:
                logger.debug("Invalid or empty installdir")
                return False

            # Check if doesn't contain suspicious characters
            if ".." in installdir or "/" in installdir or "\\" in installdir:
                logger.debug(f"Suspicious characters in installdir: {installdir}")
                return False

            # Check if it's a valid Bifrost game
            is_bifrost = (
                size_on_disk_clean == "0"  # SizeOnDisk is exactly '0'
                and len(name) > 0  # Has a valid name
                and len(installdir) > 0  # Has a valid installdir
            )

            if is_bifrost:
                logger.debug(f"Valid Bifrost game detected: {name} ({installdir})")
            else:
                logger.debug(
                    f"Not an Bifrost game: {name} (SizeOnDisk: {size_on_disk_clean}, installdir: {installdir})"
                )

            return is_bifrost

        except Exception as e:
            logger.error(f"Error checking if game is Bifrost: {e}", exc_info=True)
            return False

    @staticmethod
    def delete_game(
        game_info: Dict, delete_compatdata: bool = False
    ) -> Tuple[bool, str]:
        """Delete Bifrost game safely with additional validations."""
        try:
            app_id = game_info.get("appid")
            library_path = game_info.get("library_path")
            installdir = game_info.get("installdir")

            # Robust input validation
            if not app_id or not app_id.isdigit():
                return False, "Invalid or missing app_id"
            if not library_path:
                return False, "Missing library_path"
            if not installdir:
                return False, "Missing installdir"
            if not os.path.exists(library_path):
                return False, f"Library path does not exist: {library_path}"

            # Enhanced path sanitization to prevent path traversal
            library_path = os.path.normpath(library_path)
            installdir = os.path.normpath(installdir).lstrip("/\\")

            # Strict security validations
            if (
                ".." in installdir
                or installdir.startswith("~")
                or "/" in installdir
                or "\\" in installdir
            ):
                return False, f"Invalid installdir format: {installdir}"

            # Only allow alphanumeric characters, spaces, hyphens, underscores, and dots
            import re

            if not re.match(r"^[a-zA-Z0-9\s\-_.]+$", installdir):
                return False, f"Invalid characters in installdir: {installdir}"

            # Build secure paths
            steamapps_path = os.path.join(library_path, "steamapps")
            common_path = os.path.join(steamapps_path, "common")
            game_dir = os.path.join(common_path, installdir)
            acf_path = game_info.get("acf_path")

            # Enhanced validation: ensure all paths are within expected directories
            try:
                # Validate library path exists and is accessible
                if not os.path.exists(library_path) or not os.path.isdir(library_path):
                    return False, f"Invalid library path: {library_path}"

                # Validate steamapps and common directories
                if not os.path.exists(steamapps_path):
                    return False, f"Steamapps directory not found: {steamapps_path}"

                if not os.path.exists(common_path):
                    return False, f"Common directory not found: {common_path}"

                # Validate game directory is within common directory
                common_real = os.path.realpath(common_path)
                game_real = os.path.realpath(game_dir)

                if (
                    not game_real.startswith(common_real + os.sep)
                    and game_real != common_real
                ):
                    return (
                        False,
                        f"Security violation: game directory outside expected path: {game_dir}",
                    )

                # Validate ACF file path if provided
                if acf_path:
                    acf_real = os.path.realpath(acf_path)
                    steamapps_real = os.path.realpath(steamapps_path)
                    if (
                        not acf_real.startswith(steamapps_real + os.sep)
                        and acf_real != steamapps_real
                    ):
                        return (
                            False,
                            f"Security violation: ACF file outside steamapps directory: {acf_path}",
                        )

            except (OSError, ValueError) as e:
                return False, f"Path validation failed: {str(e)}"

            # Confirm it's really an Bifrost game before deleting
            if acf_path and os.path.exists(acf_path):
                parsed_info = GameManager._parse_acf_file(acf_path)
                if not parsed_info or not GameManager._is_bifrost_game(parsed_info):
                    return False, "Security check: Game is not a valid Bifrost game"

            deleted_items = []
            errors = []

            # Delete game directory with additional validation
            if game_dir and os.path.exists(game_dir):
                try:
                    # Check if it's not a critical directory
                    if os.path.samefile(game_dir, common_path):
                        errors.append("Cannot delete common directory")
                    else:
                        shutil.rmtree(game_dir, ignore_errors=True)
                        deleted_items.append(f"Game directory: {game_dir}")
                        logger.debug(f"Deleted game directory: {game_dir}")
                except Exception as e:
                    errors.append(f"Failed to delete game directory: {e}")
            elif game_dir:
                logger.warning(f"Game directory not found: {game_dir}")

            # Delete ACF file
            if acf_path and os.path.exists(acf_path):
                try:
                    # Validate it's a valid ACF file
                    if not acf_path.endswith(".acf") or not os.path.basename(
                        acf_path
                    ).startswith("appmanifest_"):
                        errors.append("Invalid ACF file format")
                    else:
                        os.remove(acf_path)
                        deleted_items.append(f"ACF file: {acf_path}")
                        logger.info(f"Deleted ACF file: {acf_path}")
                except Exception as e:
                    errors.append(f"Failed to delete ACF file: {e}")
            elif acf_path:
                logger.warning(f"ACF file not found: {acf_path}")

            # Delete compatdata if requested (with enhanced validation)
            if delete_compatdata:
                # Validate app_id format to prevent path traversal
                if not app_id or not app_id.isdigit():
                    errors.append("Invalid app_id format for compatdata deletion")
                else:
                    compatdata_path = os.path.join(
                        library_path, "steamapps", "compatdata", app_id
                    )
                    if os.path.exists(compatdata_path):
                        try:
                            # Enhanced validation: ensure it's within compatdata directory
                            compatdata_base = os.path.join(
                                library_path, "steamapps", "compatdata"
                            )
                            compatdata_real = os.path.realpath(compatdata_path)
                            compatdata_base_real = os.path.realpath(compatdata_base)

                            # Strict path validation
                            if (
                                compatdata_real.startswith(
                                    compatdata_base_real + os.sep
                                )
                                or compatdata_real == compatdata_base_real
                            ) and os.path.basename(compatdata_real) == app_id:
                                shutil.rmtree(compatdata_path, ignore_errors=True)
                                deleted_items.append(f"Compatdata: {compatdata_path}")
                                logger.info(
                                    f"Deleted compatdata directory: {compatdata_path}"
                                )
                            else:
                                errors.append(
                                    "Compatdata directory validation failed - path traversal detected"
                                )
                        except (OSError, ValueError) as e:
                            errors.append(f"Failed to delete compatdata: {str(e)}")
                    else:
                        logger.info(
                            f"Compatdata directory not found: {compatdata_path}"
                        )

            # Operation result
            if errors:
                if deleted_items:
                    return (
                        False,
                        f"Partial success. Deleted: {', '.join(deleted_items)}. Errors: {'; '.join(errors)}",
                    )
                else:
                    return False, f"Deletion failed: {'; '.join(errors)}"
            else:
                logger.info(
                    f"Successfully deleted game {app_id}: {', '.join(deleted_items)}"
                )
                return (
                    True,
                    f"Game deleted successfully. Removed: {', '.join(deleted_items)}",
                )

        except Exception as e:
            logger.error(f"Critical error deleting game: {e}", exc_info=True)
            return False, f"Critical error: {str(e)}"

    @staticmethod
    def get_directory_size_async(path: str, callback) -> None:
        """Inicia cálculo de tamanho em thread separada."""
        worker = DirectorySizeWorker(path)
        worker.size_calculated.connect(callback)
        worker.start()

    @staticmethod
    def _calculate_directory_size(path: str) -> int:
        """Método legado - usar _calculate_directory_size_optimized."""
        return DirectorySizeWorker._calculate_directory_size_optimized(path)

    @staticmethod
    def validate_game_integrity(game_info: Dict) -> Tuple[bool, List[str]]:
        """
        Valida a integridade das informações do jogo.

        Returns:
            Tuple[bool, List[str]]: (é_valido, lista_de_erros)
        """
        errors = []

        # Validar campos obrigatórios
        required_fields = ["appid", "name", "installdir", "library_path", "acf_path"]
        for field in required_fields:
            if not game_info.get(field):
                errors.append(f"Missing required field: {field}")

        # Validar APPID
        appid = game_info.get("appid")
        if appid and not appid.isdigit():
            errors.append(f"Invalid APPID format: {appid}")

        # Validar paths
        library_path = game_info.get("library_path")
        if library_path and not os.path.exists(library_path):
            errors.append(f"Library path does not exist: {library_path}")

        acf_path = game_info.get("acf_path")
        if acf_path and not os.path.exists(acf_path):
            errors.append(f"ACF file does not exist: {acf_path}")

        game_dir = game_info.get("game_dir")
        if game_dir and not os.path.exists(game_dir):
            errors.append(f"Game directory does not exist: {game_dir}")

        return len(errors) == 0, errors

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Formata tamanho em bytes para formato legível."""
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size_float = float(size_bytes)
        while size_float >= 1024 and i < len(size_names) - 1:
            size_float /= 1024.0
            i += 1

        return f"{size_float:.1f} {size_names[i]}"

    @staticmethod
    def clear_games_cache():
        """Clear the games scan cache."""
        global _GAMES_SCAN_CACHE
        _GAMES_SCAN_CACHE.clear()
        logger.debug("Games scan cache cleared")
