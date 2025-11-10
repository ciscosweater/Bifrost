import os
import logging
import shutil
import time
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal

from . import steam_helpers

logger = logging.getLogger(__name__)

# Directory size cache with TTL (15 minutes for better performance)
_DIRECTORY_SIZE_CACHE = {}
_CACHE_TTL_SECONDS = 900  # 15 minutes
_MAX_CACHE_SIZE = 200  # Increased cache size

class DirectorySizeWorker(QThread):
    """Worker thread para calcular tamanho de diretórios sem bloquear UI."""
    size_calculated = pyqtSignal(int)
    
    def __init__(self, path: str):
        super().__init__()
        self.path = path
    
    def run(self):
        """Calcula tamanho do diretório em background."""
        size = self._calculate_directory_size_optimized(self.path)
        self.size_calculated.emit(size)
    
    @staticmethod
    def _calculate_directory_size_optimized(path: str, max_depth: int = 3) -> int:
        """Calcula tamanho usando os.scandir com cache e otimizações avançadas."""
        # Validar path antes de processar
        if not path or not isinstance(path, str):
            logger.debug("Invalid path provided for size calculation")
            return 0
        
        # Normalizar path
        path = os.path.normpath(path)
        
        # Check cache first
        current_time = time.time()
        cache_key = path
        
        if cache_key in _DIRECTORY_SIZE_CACHE:
            cached_size, cached_time = _DIRECTORY_SIZE_CACHE[cache_key]
            if current_time - cached_time < _CACHE_TTL_SECONDS:
                logger.debug(f"Using cached size for {os.path.basename(path)}: {cached_size} bytes")
                return cached_size
        
        # Verificar se o diretório existe
        if not os.path.exists(path):
            logger.debug(f"Directory does not exist: {path}")
            _DIRECTORY_SIZE_CACHE[cache_key] = (0, current_time)  # Cache negative result
            return 0
        
        if not os.path.isdir(path):
            logger.debug(f"Path is not a directory: {path}")
            return 0
        
        total_size = 0
        file_count = 0
        dir_count = 0
        large_files = 0
        
        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    # Limitar número de arquivos para evitar travamento em diretórios muito grandes
                    if file_count > 2000:  # Aumentado para 2000 para melhor precisão
                        logger.warning(f"File count limit reached for {path}, calculation may be incomplete")
                        break
                        
                    try:
                        stat_info = entry.stat()
                        
                        if entry.is_file():
                            # Verificar tamanho de arquivo muito grande
                            file_size = stat_info.st_size
                            if file_size > 1024 * 1024 * 1024:  # > 1GB
                                large_files += 1
                            
                            total_size += file_size
                            file_count += 1
                            
                        elif entry.is_dir() and max_depth > 0:
                            # Evitar recursão em diretórios de sistema
                            dir_name = entry.name.lower()
                            if dir_name in ['node_modules', '.git', '__pycache__', 'venv', '.venv']:
                                logger.debug(f"Skipping system directory: {entry.path}")
                                continue
                            
                            # Recursive call com depth limit
                            dir_size = DirectorySizeWorker._calculate_directory_size_optimized(
                                entry.path, max_depth - 1
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
            logger.error(f"Critical error calculating directory size for {path}: {e}", exc_info=True)
            return 0
        
        # Cache the result
        _DIRECTORY_SIZE_CACHE[cache_key] = (total_size, current_time)
        
        # Clean old cache entries periodically
        if len(_DIRECTORY_SIZE_CACHE) > _MAX_CACHE_SIZE:
            DirectorySizeWorker._cleanup_size_cache()
        
        # Log estatísticas se for um diretório grande
        if logger.isEnabledFor(logging.DEBUG) and (file_count > 100 or dir_count > 10):
            logger.debug(f"Directory stats for {os.path.basename(path)}: "
                        f"{file_count} files, {dir_count} subdirs, {large_files} large files, "
                        f"total size: {GameManager._format_size(total_size)}")
        
        return total_size
    
    @staticmethod
    def _cleanup_size_cache():
        """Remove expired entries from directory size cache com LRU fallback."""
        current_time = time.time()
        expired_keys = []
        
        # Primeiro remover entradas expiradas
        for key, (_, cached_time) in _DIRECTORY_SIZE_CACHE.items():
            if current_time - cached_time > _CACHE_TTL_SECONDS:
                expired_keys.append(key)
        
        # Se ainda houver muitas entradas, remover as mais antigas (LRU)
        if len(_DIRECTORY_SIZE_CACHE) - len(expired_keys) > _MAX_CACHE_SIZE // 2:
            # Ordenar por tempo e remover as mais antigas
            sorted_items = sorted(_DIRECTORY_SIZE_CACHE.items(), key=lambda x: x[1][1])
            excess_count = len(_DIRECTORY_SIZE_CACHE) - len(expired_keys) - (_MAX_CACHE_SIZE // 2)
            
            for i in range(excess_count):
                if i < len(sorted_items):
                    expired_keys.append(sorted_items[i][0])
        
        # Remover as chaves expiradas/selecionadas
        for key in expired_keys:
            if key in _DIRECTORY_SIZE_CACHE:
                del _DIRECTORY_SIZE_CACHE[key]
        
        if expired_keys:
            logger.debug(f"Cleaned {len(expired_keys)} entries from size cache "
                        f"({len([k for k, (_, t) in _DIRECTORY_SIZE_CACHE.items() if current_time - t > _CACHE_TTL_SECONDS])} expired)")

class GameManager:
    """
    Gerencia operações com jogos baixados pelo ACCELA.
    Responsável por escanear, parsear e deletar jogos com segurança.
    """
    
    @staticmethod
    def scan_accela_games(async_size_calculation: bool = True) -> List[Dict]:
        """
        Escaneia todas as bibliotecas Steam em busca de jogos ACCELA.

        Args:
            async_size_calculation: Se True, calcula tamanhos de forma assíncrona para melhor performance

        Returns:
            Lista de dicionários com informações dos jogos encontrados
        """
        games = []
        libraries = steam_helpers.get_steam_libraries()
        
        logger.info(f"Scanning {len(libraries)} Steam libraries for ACCELA games")

        for library_path in libraries:
            steamapps_path = os.path.join(library_path, 'steamapps')
            if not os.path.isdir(steamapps_path):
                logger.debug(f"steamapps directory not found in {library_path}")
                continue

            acf_files = GameManager._find_acf_files(steamapps_path)
            logger.debug(f"Found {len(acf_files)} ACF files in {library_path}")

            for acf_file in acf_files:
                try:
                    game_info = GameManager._parse_acf_file(acf_file)
                    if game_info and GameManager._is_accela_game(game_info):
                        # Extract appid from the ACF file path
                        acf_filename = os.path.basename(acf_file)
                        appid = None
                        if acf_filename.startswith('appmanifest_') and acf_filename.endswith('.acf'):
                            appid = acf_filename[len('appmanifest_'):-len('.acf')]
                            game_info['appid'] = appid
                        else:
                            logger.warning(f"Invalid ACF filename format: {acf_filename}")
                            continue

                        # Add display_name field (same as name for now)
                        game_info['display_name'] = game_info.get('name', '')

                        # Add library_path and acf_path
                        game_info['library_path'] = library_path
                        game_info['acf_path'] = acf_file

                        # Calcular tamanho do diretório do jogo
                        installdir = game_info.get('installdir', '')
                        if installdir:
                            game_dir = os.path.join(library_path, 'steamapps', 'common', installdir)
                            
                            # Verificar se o diretório existe antes de calcular tamanho
                            if os.path.exists(game_dir):
                                if async_size_calculation:
                                    # Cálculo assíncrono para melhor performance
                                    size_bytes = DirectorySizeWorker._calculate_directory_size_optimized(game_dir)
                                else:
                                    # Cálculo síncrono (fallback)
                                    size_bytes = DirectorySizeWorker._calculate_directory_size_optimized(game_dir)
                                
                                game_info['size_formatted'] = GameManager._format_size(size_bytes)
                                game_info['game_dir'] = game_dir
                            else:
                                logger.warning(f"Game directory not found: {game_dir}")
                                game_info['size_formatted'] = "0 B"
                                game_info['game_dir'] = game_dir
                        else:
                            game_info['size_formatted'] = "0 B"
                            game_info['game_dir'] = None

                        games.append(game_info)
                        
                except Exception as e:
                    logger.error(f"Error processing ACF file {acf_file}: {e}")
                    continue

        logger.info(f"Found {len(games)} ACCELA games")
        return games
    
    @staticmethod
    def _find_acf_files(steamapps_path: str) -> List[str]:
        """Encontra todos os arquivos ACF de forma otimizada com validações."""
        acf_files = []
        
        # Validar diretório
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
                        # Validar que é um arquivo ACF válido
                        if (entry.is_file() and 
                            entry.name.startswith('appmanifest_') and 
                            entry.name.endswith('.acf')):
                            
                            # Validar formato do nome (appmanifest_{appid}.acf)
                            name_parts = entry.name[:-4].split('_')  # Remove .acf
                            if len(name_parts) == 2 and name_parts[0] == 'appmanifest':
                                appid_part = name_parts[1]
                                # Verificar se appid é numérico
                                if appid_part.isdigit():
                                    acf_files.append(entry.path)
                                else:
                                    logger.debug(f"Skipping ACF with invalid appid: {entry.name}")
                            else:
                                logger.debug(f"Skipping ACF with invalid format: {entry.name}")
                                
                    except (OSError, PermissionError) as e:
                        logger.debug(f"Error accessing {entry.name}: {e}")
                        continue
                        
        except (OSError, PermissionError) as e:
            logger.error(f"Permission error scanning directory {steamapps_path}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error scanning directory {steamapps_path}: {e}", exc_info=True)
        
        logger.debug(f"Found {len(acf_files)} valid ACF files in {steamapps_path}")
        return acf_files
    
    @staticmethod
    def _parse_acf_file(acf_path: str) -> Optional[Dict]:
        """Parseia arquivo ACF do Steam com validação robusta."""
        try:
            # Validar arquivo antes de ler
            if not os.path.exists(acf_path):
                logger.error(f"ACF file does not exist: {acf_path}")
                return None
            
            if not os.path.isfile(acf_path):
                logger.error(f"ACF path is not a file: {acf_path}")
                return None
            
            # Validar tamanho do arquivo para evitar ler arquivos corrompidos
            file_size = os.path.getsize(acf_path)
            if file_size == 0:
                logger.warning(f"ACF file is empty: {acf_path}")
                return {}
            
            if file_size > 10 * 1024 * 1024:  # 10MB max
                logger.error(f"ACF file too large ({file_size} bytes): {acf_path}")
                return None
            
            with open(acf_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            if not content.strip():
                logger.warning(f"ACF file is empty after reading: {acf_path}")
                return {}
                
            game_info = {}
            line_number = 0
            
            for line in content.split('\n'):
                line_number += 1
                line = line.strip()
                
                # Pular linhas vazias ou comentários
                if not line or line.startswith('//'):
                    continue
                
                # Parse de chave-valor no formato do Steam (aceita tabs ou espaços)
                if ('"' in line and 
                    (('\t' in line and line.count('\t') >= 2) or  # Formato com tabs
                     ('  ' in line and line.count('"') >= 4))):   # Formato com espaços
                    try:
                        # Remove tabs e espaços extras, depois split por quotes
                        cleaned_line = line.replace('\t', ' ').strip()
                        # Normalizar múltiplos espaços para um único espaço
                        while '  ' in cleaned_line:
                            cleaned_line = cleaned_line.replace('  ', ' ')
                        
                        parts = cleaned_line.split('"')
                        if len(parts) >= 3:
                            key = parts[1].strip()
                            value = parts[3] if len(parts) > 3 else ''
                            
                            # Validar chave
                            if key and not key.isspace():
                                game_info[key] = value
                            else:
                                logger.debug(f"Invalid key on line {line_number} in {acf_path}")
                    except Exception as e:
                        logger.debug(f"Error parsing line {line_number} in {acf_path}: {e}")
                        continue
            
            # Validar campos essenciais
            if not game_info:
                logger.warning(f"No valid data parsed from ACF: {acf_path}")
                return {}
            
            # Log de debug com campos importantes
            if logger.isEnabledFor(logging.DEBUG):
                important_fields = ['appid', 'name', 'installdir', 'SizeOnDisk']
                found_fields = {k: v for k, v in game_info.items() if k in important_fields}
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
    def _is_accela_game(game_info: Dict) -> bool:
        """Verifica se o jogo é do ACCELA com validações robustas."""
        try:
            if not game_info or not isinstance(game_info, dict):
                logger.debug("Invalid game_info: not a dictionary or empty")
                return False
            
            # ACCELA games have specific characteristics:
            # 1. SizeOnDisk = 0 (because they're downloaded differently)
            # 2. Have valid installdir
            # 3. Have valid name
            size_on_disk = game_info.get('SizeOnDisk', '1')
            name = game_info.get('name', '').strip()
            installdir = game_info.get('installdir', '').strip()
            
            # Validações mais rigorosas
            if not isinstance(size_on_disk, str):
                logger.debug(f"Invalid SizeOnDisk type: {type(size_on_disk)}")
                return False
            
            # Converter para string se necessário e limpar
            try:
                size_on_disk_clean = str(size_on_disk).strip()
            except Exception:
                logger.debug("Failed to convert SizeOnDisk to string")
                return False
            
            # Validar nome
            if not name or len(name) < 1:
                logger.debug("Invalid or empty game name")
                return False
            
            # Validar installdir
            if not installdir or len(installdir) < 1:
                logger.debug("Invalid or empty installdir")
                return False
            
            # Verificar se não contém caracteres suspeitos
            if '..' in installdir or '/' in installdir or '\\' in installdir:
                logger.debug(f"Suspicious characters in installdir: {installdir}")
                return False
            
            # Check if it's a valid ACCELA game
            is_accela = (
                size_on_disk_clean == '0' and  # SizeOnDisk is exactly '0'
                len(name) > 0 and               # Has a valid name
                len(installdir) > 0            # Has a valid installdir
            )
            
            if is_accela:
                logger.debug(f"Valid ACCELA game detected: {name} ({installdir})")
            else:
                logger.debug(f"Not an ACCELA game: {name} (SizeOnDisk: {size_on_disk_clean}, installdir: {installdir})")
            
            return is_accela
            
        except Exception as e:
            logger.error(f"Error checking if game is ACCELA: {e}", exc_info=True)
            return False
    
    @staticmethod
    def delete_game(game_info: Dict, delete_compatdata: bool = False) -> Tuple[bool, str]:
        """Deleta jogo ACCELA com segurança e validações adicionais."""
        try:
            app_id = game_info.get('appid')
            library_path = game_info.get('library_path')
            installdir = game_info.get('installdir')
            
            # Validação robusta de entrada
            if not app_id or not app_id.isdigit():
                return False, "Invalid or missing app_id"
            if not library_path:
                return False, "Missing library_path"
            if not installdir:
                return False, "Missing installdir"
            if not os.path.exists(library_path):
                return False, f"Library path does not exist: {library_path}"
            
            # Sanitização de paths para prevenir path traversal
            library_path = os.path.normpath(library_path)
            installdir = os.path.normpath(installdir).lstrip('/\\')
            
            # Validações de segurança adicionais
            if '..' in installdir or installdir.startswith('~'):
                return False, f"Invalid installdir format: {installdir}"
            
            # Construir paths seguros
            steamapps_path = os.path.join(library_path, 'steamapps')
            common_path = os.path.join(steamapps_path, 'common')
            game_dir = os.path.join(common_path, installdir)
            acf_path = game_info.get('acf_path')
            
            # Validar que estamos dentro dos diretórios esperados
            try:
                if common_path and os.path.exists(common_path):
                    common_real = os.path.realpath(common_path)
                    game_real = os.path.realpath(game_dir)
                    if not game_real.startswith(common_real):
                        return False, f"Security violation: game directory outside expected path: {game_dir}"
            except Exception:
                return False, "Failed to validate directory paths"
            
            # Confirmar que é realmente um jogo ACCELA antes de deletar
            if acf_path and os.path.exists(acf_path):
                parsed_info = GameManager._parse_acf_file(acf_path)
                if not parsed_info or not GameManager._is_accela_game(parsed_info):
                    return False, "Security check: Game is not a valid ACCELA game"
            
            deleted_items = []
            errors = []
            
            # Deletar diretório do jogo com validação adicional
            if game_dir and os.path.exists(game_dir):
                try:
                    # Verificar se não é um diretório crítico
                    if os.path.samefile(game_dir, common_path):
                        errors.append("Cannot delete common directory")
                    else:
                        shutil.rmtree(game_dir, ignore_errors=True)
                        deleted_items.append(f"Game directory: {game_dir}")
                        logger.info(f"Deleted game directory: {game_dir}")
                except Exception as e:
                    errors.append(f"Failed to delete game directory: {e}")
            elif game_dir:
                logger.warning(f"Game directory not found: {game_dir}")
            
            # Deletar arquivo ACF
            if acf_path and os.path.exists(acf_path):
                try:
                    # Validar que é um arquivo ACF válido
                    if not acf_path.endswith('.acf') or not os.path.basename(acf_path).startswith('appmanifest_'):
                        errors.append("Invalid ACF file format")
                    else:
                        os.remove(acf_path)
                        deleted_items.append(f"ACF file: {acf_path}")
                        logger.info(f"Deleted ACF file: {acf_path}")
                except Exception as e:
                    errors.append(f"Failed to delete ACF file: {e}")
            elif acf_path:
                logger.warning(f"ACF file not found: {acf_path}")
            
            # Deletar compatdata se solicitado (com validação)
            if delete_compatdata:
                compatdata_path = os.path.join(library_path, 'steamapps', 'compatdata', app_id)
                if os.path.exists(compatdata_path):
                    try:
                        # Validar que está dentro de compatdata
                        compatdata_base = os.path.join(library_path, 'steamapps', 'compatdata')
                        compatdata_real = os.path.realpath(compatdata_path)
                        compatdata_base_real = os.path.realpath(compatdata_base)
                        
                        if compatdata_real.startswith(compatdata_base_real):
                            shutil.rmtree(compatdata_path, ignore_errors=True)
                            deleted_items.append(f"Compatdata: {compatdata_path}")
                            logger.info(f"Deleted compatdata directory: {compatdata_path}")
                        else:
                            errors.append("Compatdata directory validation failed")
                    except Exception as e:
                        errors.append(f"Failed to delete compatdata: {e}")
                else:
                    logger.info(f"Compatdata directory not found: {compatdata_path}")
            
            # Resultado da operação
            if errors:
                if deleted_items:
                    return False, f"Partial success. Deleted: {', '.join(deleted_items)}. Errors: {'; '.join(errors)}"
                else:
                    return False, f"Deletion failed: {'; '.join(errors)}"
            else:
                logger.info(f"Successfully deleted game {app_id}: {', '.join(deleted_items)}")
                return True, f"Game deleted successfully. Removed: {', '.join(deleted_items)}"
                
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
        required_fields = ['appid', 'name', 'installdir', 'library_path', 'acf_path']
        for field in required_fields:
            if not game_info.get(field):
                errors.append(f"Missing required field: {field}")
        
        # Validar APPID
        appid = game_info.get('appid')
        if appid and not appid.isdigit():
            errors.append(f"Invalid APPID format: {appid}")
        
        # Validar paths
        library_path = game_info.get('library_path')
        if library_path and not os.path.exists(library_path):
            errors.append(f"Library path does not exist: {library_path}")
        
        acf_path = game_info.get('acf_path')
        if acf_path and not os.path.exists(acf_path):
            errors.append(f"ACF file does not exist: {acf_path}")
        
        game_dir = game_info.get('game_dir')
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