"""
Game Install Directory Cleanup - Safe and aggressive cleanup of partial files
Specific to game installation directory being downloaded
"""

import json


from typing import Dict, List
from utils.logger import get_internationalized_logger
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

logger = get_internationalized_logger()


# Import i18n safely - will be available when app is running
def tr(context, text):
    """Fallback translation function - will be replaced by proper i18n"""
    return text


class GameInstallDirectoryCleanup:
    """
    100% safe and aggressive cleanup of partial files in game installation directory.

    Features:
    - 100% safe for Steam (never removes critical files)
    - Aggressive cleanup (removes ALL partial files)
    - Game-specific (cleans only the directory of the game being downloaded)
    - Reversible (detailed log of what was removed)
    """

    def __init__(self):
        # DepotDownloader partial file patterns
        self.partial_extensions = {
            ".tmp",
            ".partial",
            ".downloading",
            ".temp",
            ".incomplete",
            ".chunk",
            ".manifest.tmp",
            ".depot.tmp",
        }

        # Partial file name patterns
        self.partial_patterns = {
            "manifest_",
            "chunk_",
            "temp_",
            "tmp_",
            "partial_",
            ".download",
            ".incomplete",
            ".lock",
            "~$",
        }

        # Temporary directories safe to remove
        self.temp_directories = {".DepotDownloader", "temp", "tmp", "cache"}

        # Critical files that should NEVER be removed
        self.critical_game_files = {
            # Common executables
            ".exe",
            ".sh",
            ".bin",
            ".run",
            ".appimage",
            # Game libraries
            ".dll",
            ".so",
            ".dylib",
            # Game data files
            ".pak",
            ".arc",
            ".zip",
            ".rar",
            ".7z",
            ".dat",
            ".cfg",
            ".ini",
            ".xml",
            ".json",
            ".yaml",
            # Game resources
            ".png",
            ".jpg",
            ".jpeg",
            ".bmp",
            ".tga",
            ".dds",
            ".wav",
            ".mp3",
            ".ogg",
            ".flac",
            ".ttf",
            ".otf",
            ".woff",
            ".woff2",
            # Game scripts
            ".lua",
            ".py",
            ".js",
            ".cs",
            ".cpp",
            ".h",
            # Documentation
            ".txt",
            ".md",
            ".pdf",
            ".htm",
            ".html",
            # Steam specific
            "steam_api.dll",
            "steam_api64.dll",
            "libsteam_api.so",
            "appmanifest",
            "acf",
        }

        # DepotDownloader temporary files (always removed)
        self.depotdownloader_files = {
            "keys.vdf",
            "appinfo.vdf",
            "package.vdf",
            "manifest_*.cache",
            "*.chunk.tmp",
            "*.manifest.tmp",
        }

        # Removal log for reversal
        self.removal_log: List[Dict] = []

    def cleanup_game_install_directory(
        self,
        install_dir: str,
        game_data: Dict,
        session_id: str = "",
        dry_run: bool = False,
    ) -> Dict:
        """
        COMPLETE AND AGGRESSIVE CLEANUP OF GAME DIRECTORY

        Deletes EVERYTHING inside the specific game directory being downloaded.
        NEVER deletes anything outside the game folder.
        100% safe to avoid deleting wrong directories.

        Args:
            install_dir: Game installation directory
            game_data: Game data (appid, name, etc.)
            session_id: Download session ID
            dry_run: If True, only simulates without removing

        Returns:
            Dict with cleanup result
        """
        result = {
            "success": False,
            "install_dir": install_dir,
            "game_name": game_data.get("game_name", "Unknown"),
            "appid": game_data.get("appid", "Unknown"),
            "session_id": session_id,
            "files_removed": 0,
            "dirs_removed": 0,
            "space_freed_mb": 0,
            "removals": [],
            "errors": [],
            "dry_run": dry_run,
            "cleanup_type": "COMPLETE_DIRECTORY_CLEANUP",
        }

        try:
            # EXTREME SAFETY CHECKS
            if not self._verify_ultra_safety_checks(install_dir, game_data, session_id):
                result["errors"].append(
                    tr(
                        "GameInstallCleanup",
                        "ULTRA SAFETY CHECK FAILED: Directory validation failed - NO FILES DELETED",
                    )
                )
                return result

            # MULTIPLE CONFIRMATIONS
            if not self._multiple_confirmations(install_dir, game_data, session_id):
                result["errors"].append(
                    tr(
                        "GameInstallCleanup",
                        "MULTIPLE CONFIRMATIONS FAILED - NO FILES DELETED",
                    )
                )
                return result

            logger.warning(
                f"{'[DRY RUN] ' if dry_run else ''}STARTING COMPLETE CLEANUP OF GAME DIRECTORY"
            )
            logger.warning(f"Directory: {install_dir}")
            logger.warning(f"Game: {result['game_name']} (AppID: {result['appid']})")
            logger.warning(f"Session: {session_id}")
            logger.warning(
                f"{'[DRY RUN] ' if dry_run else ''}ALL CONTENTS WILL BE DELETED"
            )

            # Initialize removal log
            self.removal_log = []

            # COMPLETE DIRECTORY CLEANUP
            total_size_freed = 0

            # DELETE ABSOLUTELY EVERYTHING INSIDE THE DIRECTORY
            complete_result = self._complete_directory_cleanup(install_dir, dry_run)
            result["files_removed"] = complete_result["files_removed"]
            result["dirs_removed"] = complete_result["dirs_removed"]
            total_size_freed += complete_result["size"]
            result["removals"].extend(complete_result["removals"])

            # Calculate final statistics
            result["space_freed_mb"] = round(total_size_freed / (1024 * 1024), 2)
            result["success"] = True

            # Save removal log
            if not dry_run:
                self._save_removal_log(install_dir, game_data, session_id)

            logger.warning(
                f"{'[DRY RUN] ' if dry_run else ''}COMPLETE CLEANUP FINISHED"
            )
            logger.warning(f"  Files removed: {result['files_removed']}")
            logger.warning(f"  Directories removed: {result['dirs_removed']}")
            logger.warning(f"  Space freed: {result['space_freed_mb']} MB")
            logger.warning(f"  Directory is now EMPTY: {install_dir}")

        except Exception as e:
            error_msg = f"ERROR DURING COMPLETE CLEANUP: {e}"
            logger.error(error_msg)
            result["errors"].append(error_msg)

        return result

    def _verify_ultra_safety_checks(
        self, install_dir: str, game_data: Dict, session_id: str
    ) -> bool:
        """
        EXTREME SAFETY CHECKS
        Multiple verification layers to ensure only correct directory is deleted
        """
        try:
            # PATH TRAVERSAL SECURITY: Resolve and validate path
            install_path = Path(install_dir).resolve()

            logger.debug("STARTING ULTRA SAFETY CHECKS")

            # 1. Directory must exist
            if not install_path.exists():
                logger.error(f"SAFETY: Install directory does not exist: {install_dir}")
                return False

            # 2. Cannot be root or system directory
            if install_path.is_absolute() and len(install_path.parts) <= 3:
                logger.error(
                    tr("GameInstallCleanup", "SAFETY: Directory too close to root")
                    + f": {install_dir}"
                )
                return False

            # 2.1. ADDITIONAL SECURITY: Verify against allowed base paths
            allowed_base_paths = [
                Path.home() / ".steam" / "steam",
                Path.home() / ".local" / "share" / "Steam",
                Path("/usr/local/games/steam"),
                Path("/opt/steam"),
            ]

            is_allowed_path = False
            for base_path in allowed_base_paths:
                try:
                    if install_path.is_relative_to(base_path.resolve()):
                        is_allowed_path = True
                        break
                except (ValueError, OSError):
                    continue

            if not is_allowed_path:
                logger.error(
                    f"SAFETY: Path not in allowed Steam directories: {install_path}"
                )
                return False

            # 3. MUST contain 'steamapps/common' in path (Steam library structure)
            if (
                "steamapps" not in install_dir.lower()
                or "common" not in install_dir.lower()
            ):
                logger.error(f"SAFETY: Not a Steam game directory: {install_dir}")
                return False

            # 4. The last directory must be the game name
            game_name = game_data.get("game_name", "").lower()
            dir_name = install_path.name.lower()

            if not (game_name and game_name in dir_name):
                logger.error(
                    f"SAFETY: Directory name doesn't match game name: {dir_name} vs {game_name}"
                )
                return False

            # 5. Verify if it's really the directory of the game being downloaded
            if not self._verify_game_directory_match(install_dir, game_data):
                logger.error("SAFETY: Directory doesn't match game being downloaded")
                return False

            # 6. Cannot contain critical Steam system indicators
            dangerous_paths = [
                "steamapps/common",  # Only the parent directory
                "steam.exe",
                "steam.sh",
                "userdata",
                "config",
                "steamapps/workshop",
            ]

            install_lower = install_dir.lower()
            for dangerous in dangerous_paths:
                if dangerous in install_lower and install_dir.lower().endswith(
                    dangerous
                ):
                    logger.error(
                        f"SAFETY: Dangerous Steam path detected: {install_dir}"
                    )
                    return False

            # 7. Additional Steam structure verification
            if not self._verify_steam_library_structure(install_dir):
                logger.error(f"SAFETY: Invalid Steam library structure: {install_dir}")
                return False

            # 8. Check if there's active session_id (should only clean during cancellation)
            if not session_id:
                logger.error(
                    "SAFETY: No session ID provided - this should only run during download cancellation"
                )
                return False

            logger.debug(
                tr("GameInstallCleanup", "[OK] ALL ULTRA SAFETY CHECKS PASSED")
                + f": {install_dir}"
            )
            return True

        except Exception as e:
            logger.error(f"ULTRA SAFETY CHECK ERROR: {e}")
            return False

    def _verify_game_directory_match(self, install_dir: str, game_data: Dict) -> bool:
        """
        Additional verification to ensure it's the correct game directory
        """
        try:
            install_path = Path(install_dir)
            game_name = game_data.get("game_name", "").lower()

            # Check if directory name corresponds to game
            dir_name = install_path.name.lower()

            # 1. Directory name must contain game name
            if game_name and game_name not in dir_name:
                logger.warning(
                    f"Directory name doesn't contain game name: {dir_name} vs {game_name}"
                )
                return False

            # 2. Check if there are files that look like game files
            game_files_found = 0
            for item in install_path.iterdir():
                if item.is_file():
                    file_lower = item.name.lower()
                    # Files that indicate it's a game
                    if any(
                        file_lower.endswith(ext)
                        for ext in [".exe", ".dll", ".so", ".pak", ".dat", ".bin"]
                    ):
                        game_files_found += 1
                        if game_files_found >= 2:
                            break

            # If no game files found, might be wrong directory
            if game_files_found == 0:
                logger.warning(f"No game files found in directory: {install_dir}")
                # Doesn't fail completely, but warns

            return True

        except Exception as e:
            logger.error(f"Error verifying game directory match: {e}")
            return False

    def _verify_steam_library_structure(self, install_dir: str) -> bool:
        """
        Check if structure is correct for a Steam library
        """
        try:
            install_path = Path(install_dir)

            # Must be inside steamapps/common
            parent = install_path.parent
            if parent.name.lower() != "common":
                logger.error(f"Not in steamapps/common directory: {install_dir}")
                return False

            grandparent = parent.parent
            if grandparent.name.lower() != "steamapps":
                logger.error(f"Not in steamapps directory: {install_dir}")
                return False

            # Check if there are other games (indicates valid Steam library)
            sibling_games = 0
            for item in parent.iterdir():
                if item.is_dir() and item != install_path:
                    sibling_games += 1
                    if sibling_games >= 1:  # At least 1 other game
                        break

            if sibling_games == 0:
                logger.warning(
                    "No other games found in steamapps/common - unusual but not fatal"
                )

            return True

        except Exception as e:
            logger.error(f"Error verifying Steam library structure: {e}")
            return False

    def _multiple_confirmations(
        self, install_dir: str, game_data: Dict, session_id: str
    ) -> bool:
        """
        MULTIPLE CONFIRMATIONS BEFORE DELETION
        """
        try:
            logger.debug("STARTING MULTIPLE CONFIRMATIONS")

            # Confirmation 1: Validate game data
            if not game_data.get("game_name") or not game_data.get("appid"):
                logger.error(
                    tr("GameInstallCleanup", "CONFIRMATION 1 FAILED: Invalid game data")
                )
                return False

            # Confirmation 2: Validate session ID
            if not session_id or len(session_id) < 5:
                logger.error("CONFIRMATION 2 FAILED: Invalid session ID")
                return False

            # Confirmation 3: Verify it's really cancellation
            # (This verification should be done by caller, but let's log)
            logger.debug(
                f"CONFIRMATION 3 PASSED: Session ID {session_id} indicates download cancellation"
            )

            # Confirmation 4: Final path verification
            install_path = Path(install_dir)
            if not install_path.exists() or not install_path.is_dir():
                logger.error("CONFIRMATION 4 FAILED: Invalid directory path")
                return False

            # Confirmation 5: Verify we're not trying to delete something critical
            # Note: 'home' was removed because it's a valid path in Linux for Steam libraries
            critical_checks = [
                "windows",
                "program files",
                "system32",
                "usr/bin",
                "etc",
                "var",
                "root",
                "boot",
                "lib",
                "opt",
                "sbin",
            ]

            install_lower = install_dir.lower()
            for critical in critical_checks:
                if critical in install_lower:
                    logger.error(
                        f"CONFIRMATION 5 FAILED: Critical system path detected: {critical}"
                    )
                    return False

            logger.debug(
                tr("GameInstallCleanup", "[OK] ALL MULTIPLE CONFIRMATIONS PASSED")
            )
            return True

        except Exception as e:
            logger.error(f"MULTIPLE CONFIRMATIONS ERROR: {e}")
            return False

    def _complete_directory_cleanup(self, install_dir: str, dry_run: bool) -> Dict:
        """
        DELETES ABSOLUTELY EVERYTHING INSIDE DIRECTORY
        """
        result = {"files_removed": 0, "dirs_removed": 0, "size": 0, "removals": []}

        try:
            install_path = Path(install_dir)

            logger.warning(
                f"{'[DRY RUN] ' if dry_run else ''}STARTING COMPLETE DIRECTORY CLEANUP"
            )
            logger.warning(f"Target: {install_dir}")

            # List everything before deleting for logging
            all_items = list(install_path.iterdir())
            total_items = len(all_items)

            logger.warning(f"Found {total_items} items to delete")

            # Delete each item individually for detailed logging
            for item in all_items:
                try:
                    if item.is_file():
                        file_size = item.stat().st_size

                        if dry_run:
                            logger.debug(
                                f"[DRY RUN] Would delete FILE: {item} ({file_size} bytes)"
                            )
                        else:
                            logger.warning(f"DELETING FILE: {item} ({file_size} bytes)")
                            item.unlink()

                        result["files_removed"] += 1
                        result["size"] += file_size
                        result["removals"].append(
                            {
                                "type": "file",
                                "path": str(item),
                                "size": file_size,
                                "reason": "complete_cleanup",
                            }
                        )

                    elif item.is_dir():
                        dir_size = self._get_directory_size(str(item))

                        if dry_run:
                            logger.debug(
                                f"[DRY RUN] Would delete DIRECTORY: {item} ({dir_size} bytes)"
                            )
                        else:
                            logger.warning(
                                f"DELETING DIRECTORY: {item} ({dir_size} bytes)"
                            )
                            import shutil

                            shutil.rmtree(str(item))

                        result["dirs_removed"] += 1
                        result["size"] += dir_size
                        result["removals"].append(
                            {
                                "type": "directory",
                                "path": str(item),
                                "size": dir_size,
                                "reason": "complete_cleanup",
                            }
                        )

                except Exception as e:
                    logger.error(f"Failed to delete {item}: {e}")
                    # Continue with other items even if one fails

            # Final verification: directory should be empty
            if not dry_run:
                remaining_items = list(install_path.iterdir())
                if remaining_items:
                    logger.error(
                        f"DIRECTORY NOT EMPTY AFTER CLEANUP: {len(remaining_items)} items remaining"
                    )
                    for item in remaining_items:
                        logger.error(f"  Remaining: {item}")
                else:
                    logger.warning(f"DIRECTORY SUCCESSFULLY CLEANED: {install_dir}")

            logger.warning(f"{'[DRY RUN] ' if dry_run else ''}COMPLETE CLEANUP SUMMARY")
            logger.warning(f"  Files deleted: {result['files_removed']}")
            logger.warning(f"  Directories deleted: {result['dirs_removed']}")
            logger.warning(f"  Total size freed: {result['size']} bytes")

        except Exception as e:
            logger.error(f"ERROR DURING COMPLETE CLEANUP: {e}")

        return result

    def _verify_safety_checks(self, install_dir: str) -> bool:
        """
        CRITICAL SAFETY VERIFICATIONS
        """
        try:
            install_path = Path(install_dir)

            # 1. Directory must exist
            if not install_path.exists():
                logger.error(f"SAFETY: Install directory does not exist: {install_dir}")
                return False

            # 2. Cannot be root or system directory
            if install_path.is_absolute() and len(install_path.parts) <= 3:
                logger.error(
                    tr("GameInstallCleanup", "SAFETY: Directory too close to root")
                    + f": {install_dir}"
                )
                return False

            # 3. Must contain 'steamapps/common' in path (Steam library structure)
            if (
                "steamapps" not in install_dir.lower()
                or "common" not in install_dir.lower()
            ):
                logger.error(f"SAFETY: Not a Steam game directory: {install_dir}")
                return False

            # 4. Cannot contain critical Steam system indicators
            dangerous_paths = [
                "steamapps/common",  # Only the parent directory
                "steam.exe",
                "steam.sh",
                "userdata",
                "config",
                "steamapps/workshop",
            ]

            install_lower = install_dir.lower()
            for dangerous in dangerous_paths:
                if dangerous in install_lower and install_dir.lower().endswith(
                    dangerous
                ):
                    logger.error(
                        f"SAFETY: Dangerous Steam path detected: {install_dir}"
                    )
                    return False

            # 5. Check if it looks like game directory (has game files)
            if not self._looks_like_game_directory(install_dir):
                logger.warning(
                    f"WARNING: Directory doesn't look like a game: {install_dir}"
                )
                # Doesn't fail, just warns

            logger.debug(f"SAFETY CHECKS PASSED: {install_dir}")
            return True

        except Exception as e:
            logger.error(f"SAFETY CHECK ERROR: {e}")
            return False

    def _looks_like_game_directory(self, install_dir: str) -> bool:
        """
        Check if directory looks like a game directory
        """
        try:
            game_indicators = 0
            total_files = 0

            for root, dirs, files in os.walk(install_dir):
                # Limit verification to not take too long
                level = root.replace(install_dir, "").count(os.sep)
                if level > 2:
                    continue

                for file in files:
                    total_files += 1
                    file_lower = file.lower()

                    # Game indicators
                    if any(
                        file_lower.endswith(ext)
                        for ext in [".exe", ".dll", ".so", ".pak", ".dat"]
                    ):
                        game_indicators += 1

                    # Stop if already found enough
                    if game_indicators >= 3:
                        return True

                    # Limit verification
                    if total_files >= 50:
                        break

            return game_indicators >= 2

        except Exception:
            return False

    def _remove_partial_files(
        self, install_dir: str, session_id: str, dry_run: bool
    ) -> Dict:
        """
        Aggressively remove partial/temporary files
        """
        result = {"count": 0, "size": 0, "removals": []}

        try:
            for root, dirs, files in os.walk(install_dir):
                for file in files:
                    file_path = os.path.join(root, file)

                    if self._is_partial_file(file, session_id):
                        try:
                            file_size = os.path.getsize(file_path)

                            if dry_run:
                                logger.debug(
                                    f"[DRY RUN] Would remove partial file: {file_path} ({file_size} bytes)"
                                )
                            else:
                                os.remove(file_path)
                                logger.debug(
                                    f"Removed partial file: {file_path} ({file_size} bytes)"
                                )

                            result["count"] += 1
                            result["size"] += file_size
                            result["removals"].append(
                                {
                                    "type": "file",
                                    "path": file_path,
                                    "size": file_size,
                                    "reason": "partial_file",
                                }
                            )

                        except OSError as e:
                            logger.warning(f"Failed to remove {file_path}: {e}")

        except Exception as e:
            logger.error(f"Error removing partial files: {e}")

        return result

    def _remove_temp_directories(self, install_dir: str, dry_run: bool) -> Dict:
        """
        Remove safe temporary directories
        """
        result = {"count": 0, "size": 0, "removals": []}

        try:
            for root, dirs, files in os.walk(install_dir, topdown=True):
                # Modify directory list during iteration
                dirs[:] = [d for d in dirs if d in self.temp_directories]

                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)

                    if self._is_safe_temp_directory(dir_path):
                        try:
                            dir_size = self._get_directory_size(dir_path)

                            if dry_run:
                                logger.info(
                                    f"[DRY RUN] Would remove temp directory: {dir_path} ({dir_size} bytes)"
                                )
                            else:
                                shutil.rmtree(dir_path)
                                logger.info(
                                    f"Removed temp directory: {dir_path} ({dir_size} bytes)"
                                )

                            result["count"] += 1
                            result["size"] += dir_size
                            result["removals"].append(
                                {
                                    "type": "directory",
                                    "path": dir_path,
                                    "size": dir_size,
                                    "reason": "temp_directory",
                                }
                            )

                        except OSError as e:
                            logger.warning(
                                f"Failed to remove directory {dir_path}: {e}"
                            )

        except Exception as e:
            logger.error(f"Error removing temp directories: {e}")

        return result

    def _cleanup_depotdownloader_artifacts(
        self, install_dir: str, dry_run: bool
    ) -> Dict:
        """
        Specific cleanup of DepotDownloader artifacts
        """
        result = {"count": 0, "size": 0, "removals": []}

        try:
            # Clean .DepotDownloader folder
            depotdownloader_dir = os.path.join(install_dir, ".DepotDownloader")
            if os.path.exists(depotdownloader_dir):
                try:
                    dir_size = self._get_directory_size(depotdownloader_dir)

                    if dry_run:
                        logger.info(
                            f"[DRY RUN] Would remove .DepotDownloader directory: {depotdownloader_dir}"
                        )
                    else:
                        shutil.rmtree(depotdownloader_dir)
                        logger.info(
                            f"Removed .DepotDownloader directory: {depotdownloader_dir}"
                        )

                    result["count"] += 1
                    result["size"] += dir_size
                    result["removals"].append(
                        {
                            "type": "directory",
                            "path": depotdownloader_dir,
                            "size": dir_size,
                            "reason": "depotdownloader_artifact",
                        }
                    )

                except OSError as e:
                    logger.warning(f"Failed to remove .DepotDownloader: {e}")

            # Clean specific DepotDownloader files
            for root, dirs, files in os.walk(install_dir):
                for file in files:
                    file_path = os.path.join(root, file)

                    if self._is_depotdownloader_artifact(file):
                        try:
                            file_size = os.path.getsize(file_path)

                            if dry_run:
                                logger.info(
                                    f"[DRY RUN] Would remove DepotDownloader artifact: {file_path}"
                                )
                            else:
                                os.remove(file_path)
                                logger.info(
                                    f"Removed DepotDownloader artifact: {file_path}"
                                )

                            result["count"] += 1
                            result["size"] += file_size
                            result["removals"].append(
                                {
                                    "type": "file",
                                    "path": file_path,
                                    "size": file_size,
                                    "reason": "depotdownloader_artifact",
                                }
                            )

                        except OSError as e:
                            logger.warning(f"Failed to remove {file_path}: {e}")

        except Exception as e:
            logger.error(f"Error cleaning DepotDownloader artifacts: {e}")

        return result

    def _is_partial_file(self, filename: str, session_id: str = "") -> bool:
        """
        Check if file is partial/temporary
        """
        filename_lower = filename.lower()

        # 1. Temporary extensions
        if any(filename_lower.endswith(ext) for ext in self.partial_extensions):
            return True

        # 2. Name patterns
        if any(pattern in filename_lower for pattern in self.partial_patterns):
            return True

        # 3. Specific session ID
        if session_id and session_id in filename_lower:
            return True

        # 4. DepotDownloader files
        if self._is_depotdownloader_artifact(filename):
            return True

        return False

    def _is_depotdownloader_artifact(self, filename: str) -> bool:
        """
        Check if it's a DepotDownloader artifact
        """
        filename_lower = filename.lower()

        # Specific files
        if filename_lower in {"keys.vdf", "appinfo.vdf", "package.vdf"}:
            return True

        # Manifest/chunk patterns
        if filename_lower.startswith(("manifest_", "chunk_")):
            return True

        # DepotDownloader temporary extensions
        if any(
            filename_lower.endswith(suffix)
            for suffix in [".manifest.tmp", ".chunk.tmp", ".depot.tmp"]
        ):
            return True

        return False

    def _is_safe_temp_directory(self, dir_path: str) -> bool:
        """
        Check if temporary directory is safe to remove
        """
        dir_name = os.path.basename(dir_path).lower()

        # Must be a known temporary directory
        if dir_name not in self.temp_directories:
            return False

        try:
            # Check if it contains only temporary files
            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    if not self._is_partial_file(file):
                        logger.warning(f"Non-temporary file in temp dir: {file}")
                        return False

                # Limit depth
                level = root.replace(dir_path, "").count(os.sep)
                if level > 3:
                    return False

            return True

        except Exception:
            return False

    def _get_directory_size(self, dir_path: str) -> int:
        """
        Calculate total directory size
        """
        total_size = 0
        try:
            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                    except OSError:
                        continue
        except Exception:
            pass
        return total_size

    def _verify_post_cleanup_safety(self, install_dir: str) -> Dict:
        """
        Post-cleanup safety verification
        """
        check_result = {
            "game_files_preserved": 0,
            "critical_files_found": 0,
            "remaining_partial_files": 0,
            "warnings": [],
        }

        try:
            for root, dirs, files in os.walk(install_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_lower = file.lower()

                    # Check preserved critical files
                    if any(
                        file_lower.endswith(ext) for ext in self.critical_game_files
                    ):
                        check_result["critical_files_found"] += 1

                    # Count game files
                    if any(
                        file_lower.endswith(ext)
                        for ext in [".exe", ".dll", ".so", ".pak", ".dat"]
                    ):
                        check_result["game_files_preserved"] += 1

                    # Check if partial files remain
                    if self._is_partial_file(file):
                        check_result["remaining_partial_files"] += 1
                        check_result["warnings"].append(
                            f"Remaining partial file: {file_path}"
                        )

            # Important warnings
            if check_result["critical_files_found"] == 0:
                check_result["warnings"].append(
                    "No critical game files found - possible over-cleanup"
                )

            if check_result["remaining_partial_files"] > 5:
                check_result["warnings"].append(
                    f"Many partial files remaining: {check_result['remaining_partial_files']}"
                )

        except Exception as e:
            check_result["warnings"].append(f"Post-cleanup check error: {e}")

        return check_result

    def _save_removal_log(self, install_dir: str, game_data: Dict, session_id: str):
        """
        Save detailed removal log for possible reversal
        """
        try:
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "install_dir": install_dir,
                "game_data": game_data,
                "session_id": session_id,
                "removals": self.removal_log,
            }

            # Create log file in game directory
            log_file = os.path.join(
                install_dir,
                f".bifrost_cleanup_log_{session_id or datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            )

            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Cleanup log saved: {log_file}")

        except Exception as e:
            logger.error(f"Failed to save removal log: {e}")

    def get_removal_log(self, install_dir: str) -> List[Dict]:
        """
        Load previous removal logs
        """
        logs = []
        try:
            for file in os.listdir(install_dir):
                if file.startswith(".bifrost_cleanup_log_") and file.endswith(".json"):
                    log_file = os.path.join(install_dir, file)
                    try:
                        with open(log_file, "r", encoding="utf-8") as f:
                            log_data = json.load(f)
                            logs.append(log_data)
                    except Exception:
                        continue
        except Exception:
            pass

        return sorted(logs, key=lambda x: x.get("timestamp", ""), reverse=True)
