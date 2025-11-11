"""
Directory Utilities - Optimized functions for directory operations
"""
import os
import logging
from typing import List, Generator, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class DirectoryUtils:
    """Optimized utilities for directory operations"""
    
    @staticmethod
    def safe_scandir(directory: str, pattern: Optional[str] = None) -> Generator[os.DirEntry, None, None]:
        """
        Optimized version of os.scandir with error handling and filtering
        
        Args:
            directory: Directory to scan
            pattern: Optional pattern to filter names (supports * and ?)
            
        Yields:
            os.DirEntry objects
        """
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if pattern is None or DirectoryUtils._matches_pattern(entry.name, pattern):
                        yield entry
        except (OSError, PermissionError) as e:
            logger.warning(f"Error scanning directory {directory}: {e}")
    
    @staticmethod
    def _matches_pattern(filename: str, pattern: str) -> bool:
        """Simple pattern matching (supports * and ?)"""
        import fnmatch
        return fnmatch.fnmatch(filename.lower(), pattern.lower())
    
    @staticmethod
    def find_files_by_extension(directory: str, extensions: List[str]) -> List[str]:
        """
        Find files by extension in optimized way
        
        Args:
            directory: Directory to search
            extensions: List of extensions (ex: ['.txt', '.json'])
            
        Returns:
            List of full paths of found files
        """
        if not extensions:
            return []
            
        extensions = [ext.lower() for ext in extensions]
        found_files = []
        
        for entry in DirectoryUtils.safe_scandir(directory):
            if entry.is_file():
                if any(entry.name.lower().endswith(ext) for ext in extensions):
                    found_files.append(entry.path)
        
        return found_files
    
    @staticmethod
    def find_files_by_pattern(directory: str, pattern: str) -> List[str]:
        """
        Encontra arquivos por padrão de forma otimizada
        
        Args:
            directory: Diretório para buscar
            pattern: Padrão (ex: '*.acf', 'appmanifest_*')
            
        Returns:
            Lista de caminhos completos dos arquivos encontrados
        """
        found_files = []
        
        for entry in DirectoryUtils.safe_scandir(directory, pattern):
            if entry.is_file():
                found_files.append(entry.path)
        
        return found_files
    
    @staticmethod
    def get_directory_size_fast(directory: str) -> int:
        """
        Calcula tamanho do diretório de forma otimizada usando os.scandir
        
        Args:
            directory: Diretório para calcular tamanho
            
        Returns:
            Tamanho total em bytes
        """
        total_size = 0
        
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    try:
                        if entry.is_file():
                            total_size += entry.stat().st_size
                        elif entry.is_dir():
                            total_size += DirectoryUtils.get_directory_size_fast(entry.path)
                    except (OSError, PermissionError):
                        continue
        except (OSError, PermissionError):
            pass
        
        return total_size
    
    @staticmethod
    def is_directory_empty(directory: str) -> bool:
        """
        Verifica se diretório está vazio de forma otimizada
        
        Args:
            directory: Diretório para verificar
            
        Returns:
            True se estiver vazio, False caso contrário
        """
        try:
            with os.scandir(directory) as entries:
                return not any(True for _ in entries)
        except (OSError, PermissionError):
            return False
    
    @staticmethod
    def remove_empty_directories(root_dir: str) -> int:
        """
        Remove diretórios vazios recursivamente de forma otimizada
        
        Args:
            root_dir: Diretório raiz para limpeza
            
        Returns:
            Número de diretórios removidos
        """
        removed_count = 0
        
        try:
            # Walk from bottom to top
            for dirpath, dirnames, _ in os.walk(root_dir, topdown=False):
                for dirname in dirnames:
                    full_path = os.path.join(dirpath, dirname)
                    if DirectoryUtils.is_directory_empty(full_path):
                        try:
                            os.rmdir(full_path)
                            removed_count += 1
                            logger.debug(f"Removed empty directory: {full_path}")
                        except OSError as e:
                            logger.warning(f"Failed to remove empty directory {full_path}: {e}")
        except (OSError, PermissionError) as e:
            logger.error(f"Error during empty directory cleanup: {e}")
        
        return removed_count
    
    @staticmethod
    def count_files_by_type(directory: str) -> dict:
        """
        Conta arquivos por tipo de forma otimizada
        
        Args:
            directory: Diretório para analisar
            
        Returns:
            Dicionário com contagem por extensão
        """
        file_counts = {}
        
        for entry in DirectoryUtils.safe_scandir(directory):
            if entry.is_file():
                ext = Path(entry.name).suffix.lower()
                if ext:
                    file_counts[ext] = file_counts.get(ext, 0) + 1
                else:
                    file_counts['no_extension'] = file_counts.get('no_extension', 0) + 1
            elif entry.is_dir():
                # Recursively count in subdirectories
                subdir_counts = DirectoryUtils.count_files_by_type(entry.path)
                for ext, count in subdir_counts.items():
                    file_counts[ext] = file_counts.get(ext, 0) + count
        
        return file_counts