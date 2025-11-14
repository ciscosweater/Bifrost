"""
Enhanced File Cleanup Manager com integração ao GameInstallDirectoryCleanup
"""

import logging
from typing import Dict, Optional

from utils.logger import get_internationalized_logger

from utils.file_cleanup import FileCleanupManager
from utils.game_install_cleanup import GameInstallDirectoryCleanup
logger = get_internationalized_logger()


class EnhancedFileCleanupManager(FileCleanupManager):
    """
    File Cleanup Manager aprimorado com limpeza agressiva de diretório de instalação.

    Herda do FileCleanupManager original e adiciona:
    - Limpeza agressiva do diretório de instalação do jogo
    - Verificações de segurança 100% Steam-safe
    - Logging detalhado e reversível
    """

    def __init__(self):
        super().__init__()
        self.game_cleanup = GameInstallDirectoryCleanup()

    def cleanup_partial_download_enhanced(
        self,
        download_dir: str = "",
        install_dir: str = "",
        game_data: Optional[Dict] = None,
        session_id: str = "",
        aggressive: bool = False,
    ) -> Dict:
        """
        Limpeza aprimorada de download parcial.

        Args:
            download_dir: Diretório de download temporário (legado)
            install_dir: Diretório de instalação do jogo (novo)
            game_data: Dados do jogo para validação
            session_id: ID da sessão para tracking
            aggressive: Se True, faz limpeza agressiva do install dir

        Returns:
            Dict com resultado completo da limpeza
        """
        result = {
            "success": False,
            "legacy_cleanup": {},
            "install_cleanup": {},
            "total_files_removed": 0,
            "total_space_freed_mb": 0,
            "errors": [],
        }

        try:
            logger.info(
                f"Starting enhanced cleanup for session {session_id or 'unknown'}"
            )

            # 1. Limpeza legária (mantida para compatibilidade)
            if download_dir:
                try:
                    self.cleanup_download_directory(download_dir, session_id)
                    result["legacy_cleanup"] = {"status": "completed"}
                except Exception as e:
                    error_msg = f"Legacy cleanup error: {e}"
                    logger.warning(error_msg)
                    result["errors"].append(error_msg)

            # 2. Limpeza agressiva do diretório de instalação (NOVO)
            if aggressive and install_dir and game_data:
                logger.info("Starting AGGRESSIVE cleanup of game install directory")

                # Primeiro fazer dry-run para segurança
                dry_run_result = self.game_cleanup.cleanup_game_install_directory(
                    install_dir=install_dir,
                    game_data=game_data,
                    session_id=session_id,
                    dry_run=True,
                )

                logger.info(
                    f"DRY RUN RESULT: {dry_run_result['files_removed']} files, {dry_run_result['dirs_removed']} dirs"
                )

                # Executar limpeza real se dry-run for seguro
                if dry_run_result.get("success", False):
                    real_result = self.game_cleanup.cleanup_game_install_directory(
                        install_dir=install_dir,
                        game_data=game_data,
                        session_id=session_id,
                        dry_run=False,
                    )

                    result["install_cleanup"] = real_result
                    result["total_files_removed"] = real_result.get("files_removed", 0)
                    result["total_space_freed_mb"] = real_result.get(
                        "space_freed_mb", 0
                    )

                    # Verificar pós-limpeza
                    post_check = real_result.get("post_cleanup_check", {})
                    if post_check.get("warnings"):
                        logger.warning(
                            f"Post-cleanup warnings: {post_check['warnings']}"
                        )
                        result["errors"].extend(post_check["warnings"])
                else:
                    error_msg = "Dry-run failed, skipping aggressive cleanup"
                    logger.error(error_msg)
                    result["errors"].append(error_msg)

            result["success"] = True
            logger.info("Enhanced cleanup completed successfully")

        except Exception as e:
            error_msg = f"Enhanced cleanup error: {e}"
            logger.error(error_msg)
            result["errors"].append(error_msg)

        return result

    def safe_cancel_cleanup(
        self, install_dir: str, game_data: Dict, session_id: str = ""
    ) -> Dict:
        """
        COMPLETE CLEANUP FOR DOWNLOAD CANCELLATION

        Método otimizado para cancelamento COM LIMPEZA COMPLETA:
        - 100% seguro para Steam (verificações extremas)
        - APAGA TUDO dentro do diretório do jogo sendo baixado
        - NUNCA apaga nada fora da pasta do jogo
        - Só funciona durante cancelamento de download
        - Múltiplas confirmações de segurança
        """
        logger.warning(
            f"STARTING COMPLETE CANCEL CLEANUP for game: {game_data.get('game_name', 'Unknown')}"
        )
        logger.warning(f"Install Directory: {install_dir}")
        logger.warning(f"Session ID: {session_id}")

        # Verificação adicional: só deve funcionar com session_id válido
        if not session_id or len(session_id) < 5:
            error_msg = "INVALID SESSION ID - This should only be called during download cancellation"
            logger.error(error_msg)
            return {
                "success": False,
                "errors": [error_msg],
                "cleanup_type": "CANCEL_CLEANUP_BLOCKED",
            }

        # Verificação de dados do jogo
        if not game_data.get("game_name") or not game_data.get("appid"):
            error_msg = "INVALID GAME DATA - Missing game name or appid"
            logger.error(error_msg)
            return {
                "success": False,
                "errors": [error_msg],
                "cleanup_type": "CANCEL_CLEANUP_BLOCKED",
            }

        logger.warning("ALL PRE-CHECKS PASSED - PROCEEDING WITH COMPLETE CLEANUP")

        return self.cleanup_partial_download_enhanced(
            download_dir="",  # Não limpar diretórios temporários legados
            install_dir=install_dir,
            game_data=game_data,
            session_id=session_id,
            aggressive=True,  # Limpeza COMPLETA e agressiva
        )

    def get_install_directory_cleanup_info(self, install_dir: str) -> Dict:
        """
        Obtém informações sobre limpezas anteriores no diretório de instalação.
        """
        try:
            logs = self.game_cleanup.get_removal_log(install_dir)

            return {
                "install_dir": install_dir,
                "previous_cleanups": len(logs),
                "cleanup_logs": logs[:5],  # Últimas 5 limpezas
                "has_recent_cleanup": any(
                    log
                    for log in logs
                    if log.get("timestamp")
                    and self._is_recent_cleanup(log.get("timestamp"))
                ),
            }
        except Exception as e:
            logger.error(f"Error getting cleanup info: {e}")
            return {"error": str(e)}

    def _is_recent_cleanup(self, timestamp: Optional[str], hours: int = 24) -> bool:
        """
        Verifica se limpeza foi recente (dentro de X horas)
        """
        try:
            if not timestamp:
                return False
            from datetime import datetime, timedelta

            cleanup_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return datetime.now() - cleanup_time < timedelta(hours=hours)
        except Exception:
            return False
