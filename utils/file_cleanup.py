"""
File Cleanup Manager - Cleanup of partial and temporary files
"""

import logging
import os
from typing import List, Optional

from utils.logger import get_internationalized_logger



class FileCleanupManager:
    """Manages cleanup of temporary and partial files"""

    def __init__(self):
        self.temp_extensions = [
            ".tmp",
            ".partial",
            ".downloading",
            ".temp",
            ".incomplete",
        ]
        self.temp_files = ["keys.vdf", "manifest", "appinfo.vdf"]
        self.temp_directories = ["temp", "cache", "tmp"]
        # Additional patterns for DepotDownloaderMod files
        self.depotdownloader_patterns = [
            # Files that can be created during download
            "*.tmp",
            "*.partial",
            "*.downloading",
            # Temporary manifest files
            "manifest_*.depot",
            "*.manifest.tmp",
            # Steam chunk files
            "*.chunk",
            "*.chunk.tmp",
            # Lock patterns
            "*.lock",
            "*.download",
            "~$*",
        ]

    def _is_partial_file(self, filename: str, session_id: Optional[str] = None) -> bool:
        """Check if a file is partial/temporary"""
        filename_lower = filename.lower()

        # Check temporary extensions
        for ext in self.temp_extensions:
            if filename_lower.endswith(ext):
                return True

        # Check known temporary files
        for temp_file in self.temp_files:
            if temp_file in filename_lower:
                return True

        # Check if contains session ID (if provided)
        if session_id and session_id in filename:
            return True

        # Check DepotDownloaderMod patterns
        import fnmatch

        for pattern in self.depotdownloader_patterns:
            if fnmatch.fnmatch(filename_lower, pattern.lower()):
                return True

        return False

    def cleanup_session(self, session_id: Optional[str] = None) -> dict:
        """Clean temporary files from a specific session or general"""
        try:
            logger.info(f"Starting cleanup for session {session_id or 'unknown'}")

            cleaned_files = []
            cleaned_dirs = []
            errors = []

            # Clean current directory
            current_dir = os.getcwd()
            self._cleanup_directory_recursive(
                current_dir, session_id, cleaned_files, cleaned_dirs, errors
            )

            # Clean known temporary directories
            self._cleanup_temp_directories(
                session_id, cleaned_files, cleaned_dirs, errors
            )

            result = {
                "files_removed": len(cleaned_files),
                "dirs_removed": len(cleaned_dirs),
                "files": cleaned_files,
                "dirs": cleaned_dirs,
                "errors": errors,
            }

            logger.info(
                f"Cleanup completed: {result['files_removed']} files, {result['dirs_removed']} dirs removed"
            )
            return result

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return {
                "files_removed": 0,
                "dirs_removed": 0,
                "files": [],
                "dirs": [],
                "errors": [str(e)],
            }

    def _cleanup_directory_recursive(
        self,
        directory: str,
        session_id: Optional[str],
        cleaned_files: List[str],
        cleaned_dirs: List[str],
        errors: List[str],
    ) -> None:
        """Clean directory recursively"""
        try:
            with os.scandir(directory) as entries:
                files_to_remove = []
                subdirs = []

                # First pass: identify files and subdirectories
                for entry in entries:
                    if entry.is_file():
                        if self._is_partial_file(entry.name, session_id):
                            files_to_remove.append(entry.path)
                    elif entry.is_dir():
                        subdirs.append(entry.path)

                # Remover arquivos parciais
                for file_path in files_to_remove:
                    try:
                        os.remove(file_path)
                        logger.info(f"Removed partial file: {file_path}")
                        cleaned_files.append(file_path)
                    except OSError as e:
                        logger.warning(f"Failed to remove {file_path}: {e}")
                        errors.append(f"Failed to remove {file_path}: {e}")

                # Processar subdiretórios recursivamente
                for subdir in subdirs:
                    self._cleanup_directory_recursive(
                        subdir, session_id, cleaned_files, cleaned_dirs, errors
                    )
                    # Tentar remover diretório se estiver vazio
                    try:
                        if os.path.isdir(subdir) and not os.listdir(subdir):
                            os.rmdir(subdir)
                            logger.info(f"Removed empty directory: {subdir}")
                            cleaned_dirs.append(subdir)
                    except OSError:
                        pass  # Diretório não está vazio

        except (OSError, PermissionError) as e:
            logger.warning(f"Permission error accessing {directory}: {e}")
            errors.append(f"Permission error accessing {directory}: {e}")
        except Exception as e:
            logger.error(f"Error cleaning directory {directory}: {e}")
            errors.append(f"Error cleaning directory {directory}: {e}")

    def _cleanup_temp_directories(
        self,
        session_id: Optional[str],
        cleaned_files: List[str],
        cleaned_dirs: List[str],
        errors: List[str],
    ) -> None:
        """Limpa diretórios temporários conhecidos"""
        try:
            base_dirs = [
                os.getcwd(),
                os.path.expanduser("~/.cache"),
                "/tmp" if os.name != "nt" else os.environ.get("TEMP", ""),
            ]

            for base_dir in base_dirs:
                if not base_dir or not os.path.exists(base_dir):
                    continue

                for temp_dir in self.temp_directories:
                    temp_path = os.path.join(base_dir, temp_dir)
                    if os.path.exists(temp_path):
                        self._cleanup_directory_recursive(
                            temp_path, session_id, cleaned_files, cleaned_dirs, errors
                        )

        except Exception as e:
            logger.error(f"Error cleaning temp directories: {e}")
            errors.append(f"Error cleaning temp directories: {e}")

    def cleanup_download_directory(
        self, download_dir: str, session_id: Optional[str] = None
    ) -> dict:
        """Limpa diretório de download específico"""
        try:
            if not os.path.exists(download_dir):
                return {
                    "files_removed": 0,
                    "dirs_removed": 0,
                    "files": [],
                    "dirs": [],
                    "errors": [],
                }

            cleaned_files = []
            cleaned_dirs = []
            errors = []

            self._cleanup_directory_recursive(
                download_dir, session_id, cleaned_files, cleaned_dirs, errors
            )

            return {
                "files_removed": len(cleaned_files),
                "dirs_removed": len(cleaned_dirs),
                "files": cleaned_files,
                "dirs": cleaned_dirs,
                "errors": errors,
            }

        except Exception as e:
            logger.error(f"Error cleaning download directory {download_dir}: {e}")
            return {
                "files_removed": 0,
                "dirs_removed": 0,
                "files": [],
                "dirs": [],
                "errors": [str(e)],
            }
