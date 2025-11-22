import logging
from utils.logger import get_internationalized_logger
import os
import zipfile
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.game_manager import GameManager
from core.steam_helpers import find_steam_install

logger = get_internationalized_logger()


class BackupManager:
    """
    Gerencia backup e restore dos arquivos de stats da Steam (appcache/stats).
    """

    def __init__(self):
        # Get project root directory (where main.py is located)
        current_dir = os.path.dirname(__file__)
        project_root = os.path.dirname(current_dir)
        self.backup_dir = os.path.join(project_root, "backups")
        self._ensure_backup_dir()

    def _ensure_backup_dir(self):
        """Garante que o diretório de backups exista."""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            logger.debug(f"Created backup directory: {self.backup_dir}")

    def get_steam_stats_path(self) -> Optional[str]:
        """
        Encontra o caminho da pasta appcache/stats da Steam.

        Returns:
            Caminho completo para a pasta stats ou None se não encontrada
        """
        steam_path = find_steam_install()
        if not steam_path:
            logger.error("Steam installation not found")
            return None

        stats_path = os.path.join(steam_path, "appcache", "stats")
        if not os.path.exists(stats_path):
            logger.error(f"Stats directory not found: {stats_path}")
            return None

        return stats_path

    def list_stats_files(self, bifrost_only: bool = True) -> List[str]:
        """
        Lista os arquivos de stats na pasta appcache/stats.

        Args:
            bifrost_only: Se True, inclui apenas stats de jogos Bifrost

        Returns:
            Lista de caminhos completos dos arquivos .bin
        """
        stats_path = self.get_steam_stats_path()
        if not stats_path:
            return []

        try:
            all_files = []
            for file in os.listdir(stats_path):
                if file.endswith(".bin"):
                    all_files.append(os.path.join(stats_path, file))

            if not bifrost_only:
                return sorted(all_files)

            # Filter for Bifrost games only
            bifrost_files = []
            bifrost_games = GameManager.scan_bifrost_games()
            bifrost_app_ids = {str(game.get("appid", "")) for game in bifrost_games}

            for file_path in all_files:
                filename = os.path.basename(file_path)
                # Stats files have patterns like:
                # UserGameStatsSchema_{appID}.bin
                # UserGameStats_{userID}_{appID}.bin
                app_id = ""

                if "UserGameStatsSchema_" in filename:
                    # Extract from UserGameStatsSchema_{appID}.bin
                    parts = filename.replace("UserGameStatsSchema_", "").replace(
                        ".bin", ""
                    )
                    app_id = parts
                elif "UserGameStats_" in filename:
                    # Extract from UserGameStats_{userID}_{appID}.bin
                    parts = filename.replace("UserGameStats_", "").replace(".bin", "")
                    parts = parts.split("_")
                    if len(parts) >= 2:
                        app_id = parts[-1]  # Last part is the appID

                if app_id in bifrost_app_ids:
                    bifrost_files.append(file_path)
                    logger.debug(
                        f"Bifrost stats file found: {filename} (AppID: {app_id})"
                    )
                else:
                    logger.debug(
                        f"Skipping non-Bifrost stats file: {filename} (AppID: {app_id})"
                    )

            logger.debug(
                f"Found {len(bifrost_files)} Bifrost stats files out of {len(all_files)} total"
            )
            return sorted(bifrost_files)

        except Exception as e:
            logger.error(f"Error listing stats files: {e}")
            return []

    def create_backup(
        self, backup_name: Optional[str] = None, bifrost_only: bool = True
    ) -> Optional[str]:
        """
        Cria um backup compactado dos arquivos de stats.

        Args:
            backup_name: Nome opcional para o backup (gerado automaticamente se None)
            bifrost_only: Se True, inclui apenas stats de jogos Bifrost

        Returns:
            Caminho completo do arquivo ZIP criado ou None em caso de erro
        """
        stats_path = self.get_steam_stats_path()
        if not stats_path:
            return None

        # Gerar nome do backup se não fornecido
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = "bifrost_stats_backup" if bifrost_only else "steam_stats_backup"
            backup_name = f"{prefix}_{timestamp}"

        # Garantir extensão .zip
        if not backup_name.endswith(".zip"):
            backup_name += ".zip"

        backup_path = os.path.join(self.backup_dir, backup_name)

        try:
            # Verificar se já existe
            if os.path.exists(backup_path):
                logger.warning(f"Backup file already exists: {backup_path}")
                return None

            # Criar backup ZIP
            with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                stats_files = self.list_stats_files(bifrost_only=bifrost_only)

                if not stats_files:
                    game_type = "Bifrost" if bifrost_only else "Steam"
                    logger.warning(
                        f"No {game_type.lower()} stats files found to backup"
                    )
                    return None

                for file_path in stats_files:
                    # Adicionar arquivo ao ZIP com caminho relativo
                    arcname = os.path.relpath(file_path, os.path.dirname(stats_path))
                    zipf.write(file_path, arcname)
                    logger.debug(f"Added to backup: {arcname}")

            game_type = "Bifrost" if bifrost_only else "Steam"
            logger.info(f"{game_type} backup created successfully: {backup_path}")
            logger.info(f"Backed up {len(stats_files)} files")
            return backup_path

        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            # Limpar arquivo parcial se existir
            if os.path.exists(backup_path):
                os.remove(backup_path)
            return None

    def list_backups(self) -> List[Dict[str, Any]]:
        """
        Lista todos os backups disponíveis.

        Returns:
            Lista de dicionários com informações dos backups
        """
        backups = []

        try:
            for file in os.listdir(self.backup_dir):
                if file.endswith(".zip"):
                    file_path = os.path.join(self.backup_dir, file)
                    stat = os.stat(file_path)

                    # Extrair timestamp do nome do arquivo
                    timestamp_str = (
                        file.replace("steam_stats_backup_", "")
                        .replace("bifrost_stats_backup_", "")
                        .replace("pre_restore_", "")
                        .replace(".zip", "")
                    )
                    created_date = None

                    try:
                        if timestamp_str.replace("_", "").isdigit():
                            created_date = datetime.strptime(
                                timestamp_str, "%Y%m%d_%H%M%S"
                            )
                    except (AttributeError, TypeError):
                        pass

                    backups.append(
                        {
                            "name": file,
                            "path": file_path,
                            "size": stat.st_size,
                            "created": stat.st_ctime,
                            "created_date": created_date,
                            "formatted_size": self._format_file_size(stat.st_size),
                        }
                    )

            # Ordenar por data de criação (mais recente primeiro)
            backups.sort(key=lambda x: x["created"], reverse=True)

        except Exception as e:
            logger.error(f"Error listing backups: {e}")

        return backups

    def restore_backup(
        self, backup_path: str, create_backup_first: bool = True
    ) -> bool:
        """
        Restaura os arquivos de stats a partir de um backup.

        Args:
            backup_path: Caminho completo do arquivo ZIP de backup
            create_backup_first: Se True, cria um backup antes de restaurar

        Returns:
            True se restaurado com sucesso, False caso contrário
        """
        # Validações de segurança
        if not os.path.exists(backup_path):
            logger.error(f"Backup file not found: {backup_path}")
            return False

        if not backup_path.endswith(".zip"):
            logger.error(f"Invalid backup file: {backup_path}")
            return False

        # Verificar se está no diretório de backups
        if not os.path.abspath(backup_path).startswith(
            os.path.abspath(self.backup_dir)
        ):
            logger.error(f"Backup file outside backup directory: {backup_path}")
            return False

        stats_path = self.get_steam_stats_path()
        if not stats_path:
            return False

        try:
            # Criar backup automático antes de restaurar
            if create_backup_first:
                pre_restore_backup = (
                    f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                backup_result = self.create_backup(pre_restore_backup)
                if not backup_result:
                    logger.warning("Failed to create pre-restore backup")
                else:
                    logger.info(f"Created pre-restore backup: {backup_result}")

            # Extrair backup
            with zipfile.ZipFile(backup_path, "r") as zipf:
                # Validar conteúdo do ZIP
                file_list = zipf.namelist()
                if not any(file.endswith(".bin") for file in file_list):
                    logger.error("No .bin files found in backup")
                    return False

                # Extrair arquivos
                for file_info in zipf.infolist():
                    if file_info.filename.endswith(".bin"):
                        # Extrair para pasta stats
                        target_path = os.path.join(
                            stats_path, os.path.basename(file_info.filename)
                        )

                        # Validação de segurança adicional
                        if not target_path.startswith(stats_path):
                            logger.error(
                                f"Invalid file path in backup: {file_info.filename}"
                            )
                            return False

                        zipf.extract(file_info, stats_path)
                        logger.debug(
                            f"Restored: {os.path.basename(file_info.filename)}"
                        )

            logger.info(f"Backup restored successfully from: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return False

    def delete_backup(self, backup_path: str) -> bool:
        """
        Exclui um arquivo de backup.

        Args:
            backup_path: Caminho completo do arquivo ZIP

        Returns:
            True se excluído com sucesso, False caso contrário
        """
        # Validações de segurança
        if not os.path.exists(backup_path):
            logger.error(f"Backup file not found: {backup_path}")
            return False

        if not backup_path.endswith(".zip"):
            logger.error(f"Invalid backup file: {backup_path}")
            return False

        # Verificar se está no diretório de backups
        if not os.path.abspath(backup_path).startswith(
            os.path.abspath(self.backup_dir)
        ):
            logger.error(f"Backup file outside backup directory: {backup_path}")
            return False

        try:
            os.remove(backup_path)
            logger.info(f"Backup deleted: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting backup: {e}")
            return False

    def _format_file_size(self, size_bytes: int) -> str:
        """
        Formata tamanho do arquivo para exibição.

        Args:
            size_bytes: Tamanho em bytes

        Returns:
            String formatada (KB, MB, GB)
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def get_backup_info(self, backup_path: str) -> Optional[Dict[str, Any]]:
        """
        Obtém informações detalhadas de um backup.

        Args:
            backup_path: Caminho completo do arquivo ZIP

        Returns:
            Dicionário com informações ou None em caso de erro
        """
        if not os.path.exists(backup_path):
            return None

        try:
            with zipfile.ZipFile(backup_path, "r") as zipf:
                file_list = zipf.namelist()
                bin_files = [f for f in file_list if f.endswith(".bin")]

                # Get Bifrost games for reference
                bifrost_games = GameManager.scan_bifrost_games()
                bifrost_game_dict = {
                    str(game.get("appid", "")): game for game in bifrost_games
                }

                # Extrair informações dos arquivos
                file_info = []
                game_app_ids = set()

                for file_name in bin_files:
                    info = zipf.getinfo(file_name)
                    filename = os.path.basename(file_name)

                    # Extract AppID using the same logic as list_stats_files
                    app_id = ""
                    if "UserGameStatsSchema_" in filename:
                        parts = filename.replace("UserGameStatsSchema_", "").replace(
                            ".bin", ""
                        )
                        app_id = parts
                    elif "UserGameStats_" in filename:
                        parts = filename.replace("UserGameStats_", "").replace(
                            ".bin", ""
                        )
                        parts = parts.split("_")
                        if len(parts) >= 2:
                            app_id = parts[-1]

                    if app_id:
                        game_app_ids.add(app_id)

                    # Determine file type and game info
                    file_type = "Schema" if "schema" in filename.lower() else "Stats"
                    game_name = "Unknown"

                    if app_id in bifrost_game_dict:
                        game_name = bifrost_game_dict[app_id].get("name", "Unknown")

                    file_info.append(
                        {
                            "name": filename,
                            "size": info.file_size,
                            "compressed_size": info.compress_size,
                            "type": file_type,
                            "app_id": app_id,
                            "game_name": game_name,
                            "is_bifrost": app_id in bifrost_game_dict,
                        }
                    )

                # Get unique games in backup
                games_in_backup = []
                for app_id in game_app_ids:
                    if app_id in bifrost_game_dict:
                        games_in_backup.append(
                            {
                                "app_id": app_id,
                                "name": bifrost_game_dict[app_id].get("name", "Unknown"),
                                "is_bifrost": True,
                            }
                        )
                    else:
                        games_in_backup.append(
                            {
                                "app_id": app_id,
                                "name": f"Game {app_id}",
                                "is_bifrost": False,
                            }
                        )

                return {
                    "total_files": len(bin_files),
                    "files": file_info,
                    "total_size": sum(f["size"] for f in file_info),
                    "compressed_size": sum(f["compressed_size"] for f in file_info),
                    "games": games_in_backup,
                    "bifrost_games": [g for g in games_in_backup if g["is_bifrost"]],
                    "non_bifrost_games": [
                        g for g in games_in_backup if not g["is_bifrost"]
                    ],
                }

        except Exception as e:
            logger.error(f"Error getting backup info: {e}")
            return None
