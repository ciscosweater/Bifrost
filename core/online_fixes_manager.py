"""
Online Fixes Manager - Sistema de verificação e aplicação de Online-Fixes
Baseado na documentação do LuaTools Steam Plugin
"""

import logging
import os
import urllib.parse
import zipfile
from datetime import datetime
from utils.i18n import tr
from typing import Any, Dict, List

import requests
from PyQt6.QtCore import QMutex, QMutexLocker, QObject, QThread, pyqtSignal

from utils.logger import get_internationalized_logger

logger = get_internationalized_logger()


class FixDownloadState:
    """Gerencia estado de download de fixes"""

    def __init__(self):
        self.status = "idle"  # idle, queued, downloading, extracting, done, failed
        self.bytes_read = 0
        self.total_bytes = 0
        self.error = None
        self.progress_message = ""

    def to_dict(self):
        return {
            "status": self.status,
            "bytesRead": self.bytes_read,
            "totalBytes": self.total_bytes,
            "error": self.error,
            "progressMessage": self.progress_message,
        }


class OnlineFixesManager(QObject):
    """
    Gerencia verificação, download e aplicação de Online-Fixes para jogos Steam
    Baseado na arquitetura do LuaTools Steam Plugin
    """

    # Signals principais
    fix_check_started = pyqtSignal(int)  # appid
    fix_check_completed = pyqtSignal(dict)  # resultado da verificação
    fix_download_progress = pyqtSignal(int, str)  # percentagem, mensagem
    fix_applied = pyqtSignal(int, str)  # appid, tipo do fix
    fix_error = pyqtSignal(str)  # mensagem de erro

    # Signals de estado
    fix_check_progress = pyqtSignal(str)  # mensagem de progresso da verificação

    def __init__(self):
        super().__init__()

        # HTTP Client com timeout configurado e otimizações
        self.http_client = requests.Session()

        # Configurar headers para melhor performance
        self.http_client.headers.update(
            {
                "User-Agent": "ACCELA-OnlineFixes/1.0",
                "Accept": "application/octet-stream",
                "Accept-Encoding": "gzip, deflate",
            }
        )

        # Headers para melhor performance
        self.http_client.headers.update(
            {
                "User-Agent": "ACCELA-OnlineFixes/1.0",
                "Accept": "application/octet-stream",
                "Accept-Encoding": "gzip, deflate",
            }
        )

        # Lock para thread safety (apenas para check, download usa QThread)
        self._fix_check_mutex = QMutex()

        # URLs permitidas (allowlist)
        self.allowed_domains = ["github.com", "raw.githubusercontent.com"]

        logger.debug("OnlineFixesManager initialized")

    def check_for_fixes(self, appid: int, game_name: str = "") -> Dict[str, Any]:
        """
        Verifica disponibilidade de fixes para um AppID específico

        Args:
            appid: ID do aplicativo Steam
            game_name: Nome do jogo (opcional)

        Returns:
            Dict com resultado da verificação
        """
        with QMutexLocker(self._fix_check_mutex):
            try:
                # Validação de entrada
                # Converter para int se for string ou float
                if isinstance(appid, str):
                    try:
                        appid = int(appid)
                    except ValueError:
                        raise ValueError(f"Invalid AppID format: {appid}")
                elif isinstance(appid, float):
                    if not appid.is_integer():
                        raise ValueError(f"AppID must be integer, got float: {appid}")
                    appid = int(appid)

                if not isinstance(appid, int) or appid <= 0 or appid > 99999999:
                    raise ValueError(
                        f"Invalid AppID: {appid} (type: {type(appid)}, must be between 1 and 99999999)"
                    )

                logger.debug(f"Checking for fixes for AppID: {appid}")
                self.fix_check_started.emit(appid)

                # Estrutura do resultado
                result = {
                    "appid": appid,
                    "gameName": game_name,
                    "genericFix": {"status": 0, "available": False, "url": None},
                    "onlineFix": {"status": 0, "available": False, "url": None},
                }

                # Emitir progresso
                self.fix_check_progress.emit(f"{tr('OnlineFixes', 'Fetching game name for')} {appid}...")

                # Obter nome do jogo se não fornecido
                if not game_name:
                    game_name = self._get_game_name_from_steam(appid)
                    result["gameName"] = game_name

                # Verificar Generic Fix
                self.fix_check_progress.emit(f"{tr('OnlineFixes', 'Checking generic fix for')} {game_name}...")
                result["genericFix"] = self._check_generic_fix(appid)

                # Verificar Online-Fix
                self.fix_check_progress.emit(f"{tr('OnlineFixes', 'Checking online-fix for')} {game_name}...")
                result["onlineFix"] = self._check_online_fix(appid)

                logger.debug(
                    f"{tr('OnlineFixes', 'Fix check completed for')} {appid}: Generic={result['genericFix']['available']}, Online={result['onlineFix']['available']}"
                )
                self.fix_check_completed.emit(result)

                return result

            except Exception as e:
                error_msg = f"Error checking fixes for {appid}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self.fix_error.emit(error_msg)

                # Retornar resultado de erro
                return {
                    "appid": appid,
                    "gameName": game_name,
                    "error": error_msg,
                    "genericFix": {"status": 0, "available": False, "url": None},
                    "onlineFix": {"status": 0, "available": False, "url": None},
                }

    def _get_game_name_from_steam(self, appid: int) -> str:
        """Obtém nome do jogo da Steam Store API"""
        try:
            url = "https://store.steampowered.com/api/appdetails"
            params = {"appids": appid}

            response = self.http_client.get(url, params=params, timeout=5)
            response.raise_for_status()

            data = response.json()
            if str(appid) in data and data[str(appid)]["success"]:
                return data[str(appid)]["data"]["name"]

            return f"App_{appid}"

        except Exception as e:
            logger.warning(f"Failed to get game name for {appid}: {e}")
            return f"App_{appid}"

    def _check_generic_fix(self, appid: int) -> Dict[str, Any]:
        """Verifica disponibilidade de Generic Fix"""
        try:
            generic_url = f"https://github.com/ShayneVi/Bypasses/releases/download/v1.0/{appid}.zip"

            # Validar URL
            if not self._is_url_allowed(generic_url):
                logger.warning(f"Generic fix URL not allowed: {generic_url}")
                return {"status": 403, "available": False, "url": None}

            # Usar HEAD request com timeout menor para verificação rápida
            response = self.http_client.head(
                generic_url, timeout=5, allow_redirects=True
            )
            logger.debug(f"Generic fix check for {appid} -> {response.status_code}")

            if response.status_code == 200:
                return {
                    "status": response.status_code,
                    "available": True,
                    "url": generic_url,
                }
            else:
                return {"status": response.status_code, "available": False, "url": None}

        except Exception as e:
            logger.warning(f"Generic fix check failed for {appid}: {e}")
            return {"status": 0, "available": False, "url": None}

    def _check_online_fix(self, appid: int) -> Dict[str, Any]:
        """Verifica disponibilidade de Online-Fix (múltiplas fontes)"""
        online_urls = [
            f"https://github.com/ShayneVi/OnlineFix1/releases/download/fixes/{appid}.zip",
            f"https://github.com/ShayneVi/OnlineFix2/releases/download/fixes/{appid}.zip",
        ]

        result = {"status": 0, "available": False, "url": None}

        for online_url in online_urls:
            try:
                # Validar URL
                if not self._is_url_allowed(online_url):
                    logger.warning(f"Online-fix URL not allowed: {online_url}")
                    continue

                # Usar timeout menor para verificação mais rápida
                response = self.http_client.head(
                    online_url, timeout=5, allow_redirects=True
                )
                logger.debug(
                    f"Online-fix check ({online_url}) for {appid} -> {response.status_code}"
                )

                if response.status_code == 200:
                    result["status"] = response.status_code
                    result["available"] = True
                    result["url"] = online_url
                    break
                elif result["status"] == 0:
                    # Armazenar primeiro status não-200
                    result["status"] = response.status_code

            except Exception as e:
                logger.warning(f"Online-fix check failed for {online_url}: {e}")
                if result["status"] == 0:
                    result["status"] = 0

        return result

    def _is_url_allowed(self, url: str) -> bool:
        """Verifica se URL está na allowlist"""
        try:
            parsed = urllib.parse.urlparse(url)
            return parsed.netloc.lower() in self.allowed_domains
        except Exception as e:
            logger.warning(f"URL parsing failed for {url}: {e}")
            return False

    def apply_fix(
        self,
        appid: int,
        download_url: str,
        install_path: str,
        fix_type: str = "",
        game_name: str = "",
    ) -> bool:
        """
        Inicia download e aplicação de um fix

        Args:
            appid: ID do aplicativo
            download_url: URL para download do fix
            install_path: Caminho de instalação do jogo
            fix_type: Tipo do fix ('generic' ou 'online')
            game_name: Nome do jogo

        Returns:
            bool: True se iniciado com sucesso
        """
        try:
            # Validações
            if not isinstance(appid, int) or appid <= 0:
                raise ValueError(f"Invalid AppID: {appid}")

            if not download_url or not isinstance(download_url, str):
                raise ValueError("Invalid download URL")

            if not install_path or not isinstance(install_path, str):
                raise ValueError("Invalid install path")

            # Sanitização e validação do caminho
            install_path = os.path.normpath(install_path)
            if not install_path or ".." in install_path:
                raise ValueError(
                    f"Invalid install path (directory traversal): {install_path}"
                )

            if not os.path.exists(install_path):
                raise ValueError(f"Install path does not exist: {install_path}")

            if not os.path.isdir(install_path):
                raise ValueError(f"Install path is not a directory: {install_path}")

            if not self._is_url_allowed(download_url):
                raise ValueError(f"URL not allowed: {download_url}")

            # Validação adicional do tipo de fix
            if fix_type not in ["generic", "online", ""]:
                raise ValueError(f"Invalid fix type: {fix_type}")

            # Criar worker thread PyQt6 para melhor compatibilidade
            class FixWorkerThread(QThread):
                def __init__(
                    self,
                    manager,
                    appid,
                    download_url,
                    install_path,
                    fix_type,
                    game_name,
                ):
                    super().__init__()
                    self.manager = manager
                    self.appid = appid
                    self.download_url = download_url
                    self.install_path = install_path
                    self.fix_type = fix_type
                    self.game_name = game_name

                def run(self):
                    try:
                        self.manager._download_and_extract_fix_worker(
                            self.appid,
                            self.download_url,
                            self.install_path,
                            self.fix_type,
                            self.game_name,
                        )
                    except Exception as e:
                        error_msg = f"Fix worker thread error: {str(e)}"
                        logger.error(error_msg, exc_info=True)
                        try:
                            self.manager.fix_error.emit(error_msg)
                        except (AttributeError, TypeError):
                            pass

            # Iniciar worker thread
            worker = FixWorkerThread(
                self, appid, download_url, install_path, fix_type, game_name
            )
            worker.start()

            logger.debug(f"Started fix download for AppID {appid}: {fix_type}")
            return True

        except Exception as e:
            error_msg = f"Failed to start fix download: {str(e)}"
            logger.error(error_msg, exc_info=True)
            try:
                self.fix_error.emit(error_msg)
            except (AttributeError, TypeError):
                pass
            return False

    def _download_and_extract_fix_worker(
        self,
        appid: int,
        download_url: str,
        install_path: str,
        fix_type: str,
        game_name: str,
    ):
        """Worker function para download e extração de fix"""
        dest_zip = None
        try:
            # Emitir progresso inicial
            try:
                self.fix_download_progress.emit(0, f"Downloading {fix_type} fix...")
            except Exception as emit_error:
                logger.warning(f"Failed to emit progress signal: {emit_error}")

            # Caminho do arquivo ZIP temporário com validação de segurança
            parent_dir = os.path.dirname(install_path)
            if not parent_dir or not os.path.exists(parent_dir):
                raise ValueError(
                    f"Invalid parent directory for temp files: {parent_dir}"
                )

            temp_dir = os.path.join(parent_dir, "temp")
            temp_dir = os.path.normpath(temp_dir)
            if not temp_dir.startswith(parent_dir):
                raise ValueError(
                    f"Path traversal attempt in temp directory: {temp_dir}"
                )

            os.makedirs(temp_dir, exist_ok=True)
            dest_zip = os.path.join(temp_dir, f"fix_{appid}.zip")

            # Limpar arquivo temporário existente
            if os.path.exists(dest_zip):
                os.remove(dest_zip)

            # Download do arquivo com validações
            logger.info(f"Downloading {fix_type} fix from {download_url}")

            response = self.http_client.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            total = int(response.headers.get("Content-Length", 0))

            # Validar tamanho máximo (50MB)
            max_size = 50 * 1024 * 1024  # 50MB
            if total > max_size:
                raise ValueError(
                    f"Fix file too large: {total} bytes (max: {max_size} bytes)"
                )

            downloaded = 0
            last_progress_emit = 0
            with open(dest_zip, "wb") as f:
                # Usar chunk size maior para melhor performance
                for chunk in response.iter_content(chunk_size=65536):  # 64KB chunks
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Atualizar progresso (menos frequente para melhor performance)
                        if total > 0:
                            percentage = int((downloaded / total) * 100)
                            # Emitir progresso apenas a cada 5% para reduzir overhead
                            if (
                                percentage - last_progress_emit >= 5
                                or percentage == 100
                            ):
                                try:
                                    self.fix_download_progress.emit(
                                        percentage, f"Downloading {fix_type} fix..."
                                    )
                                    last_progress_emit = percentage
                                except Exception as emit_error:
                                    logger.warning(
                                        f"Failed to emit progress signal: {emit_error}"
                                    )

            # Extração do arquivo
            try:
                self.fix_download_progress.emit(100, "Extracting files...")
            except Exception as emit_error:
                logger.warning(f"Failed to emit progress signal: {emit_error}")

            extracted_files = self._extract_fix_zip(dest_zip, install_path, appid)

            # Criar log de instalação
            self._create_install_log(
                appid, install_path, fix_type, download_url, game_name, extracted_files
            )

            # Limpar arquivo temporário
            try:
                if dest_zip and os.path.exists(dest_zip):
                    os.remove(dest_zip)
            except Exception as e:
                logger.warning(f"Failed to remove temp file {dest_zip}: {e}")

            # Emitir sucesso
            try:
                self.fix_download_progress.emit(
                    100, f"{fix_type.title()} fix applied successfully!"
                )
                self.fix_applied.emit(appid, fix_type)
            except Exception as emit_error:
                logger.warning(f"Failed to emit completion signals: {emit_error}")

            logger.info(f"Successfully applied {fix_type} fix for AppID {appid}")

        except Exception as e:
            error_msg = f"Failed to apply fix for AppID {appid}: {str(e)}"
            logger.error(error_msg, exc_info=True)

            # Limpar arquivo temporário em caso de erro
            try:
                if dest_zip and os.path.exists(dest_zip):
                    os.remove(dest_zip)
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp file: {cleanup_error}")

            try:
                self.fix_error.emit(error_msg)
            except Exception as emit_error:
                logger.error(f"Failed to emit error signal: {emit_error}")

    def _extract_fix_zip(
        self, zip_path: str, install_path: str, appid: int
    ) -> List[str]:
        """Extrai arquivo ZIP de fix com detecção inteligente de estrutura e segurança"""
        extracted_files = []

        try:
            # Validar arquivo ZIP antes de extrair
            if not os.path.exists(zip_path):
                raise FileNotFoundError(f"ZIP file not found: {zip_path}")

            # Validar tamanho do arquivo
            file_size = os.path.getsize(zip_path)
            max_size = 50 * 1024 * 1024  # 50MB
            if file_size > max_size:
                raise ValueError(f"ZIP file too large: {file_size} bytes")

            with zipfile.ZipFile(zip_path, "r") as zf:
                # Verificar se há arquivos maliciosos (path traversal)
                all_names = zf.namelist()
                for name in all_names:
                    # Detectar tentativas de path traversal
                    if ".." in name or name.startswith("/") or "\\" in name:
                        raise ValueError(f"Suspicious file path in ZIP: {name}")

                    # Verificar tamanho total da extração
                    info = zf.getinfo(name)
                    if info.file_size > max_size:
                        raise ValueError(
                            f"File too large in ZIP: {name} ({info.file_size} bytes)"
                        )

                all_names = zf.namelist()
                appid_folder = str(appid) + "/"

                # Obter apenas entradas de nível superior
                top_level_entries = set()
                for name in all_names:
                    parts = name.split("/")
                    if parts[0]:
                        top_level_entries.add(parts[0])

                # Verificar se há exatamente uma entrada de nível superior que é a pasta do appid
                if (
                    len(top_level_entries) == 1
                    and appid_folder.rstrip("/") in top_level_entries
                ):
                    # Extrair conteúdo da pasta appid, não a pasta em si
                    logger.info(
                        f"Found single folder {appid} in zip, extracting its contents"
                    )

                    for member in zf.namelist():
                        if member.startswith(appid_folder) and member != appid_folder:
                            # Remover prefixo da pasta appid do caminho
                            target_path = member[len(appid_folder) :]
                            if target_path:
                                source = zf.open(member)
                                target = os.path.join(install_path, target_path)

                                # Criar diretórios se necessário
                                os.makedirs(os.path.dirname(target), exist_ok=True)

                                # Escrever arquivo ou criar diretório
                                if not member.endswith("/"):
                                    with open(target, "wb") as f:
                                        f.write(source.read())
                                    # Rastrear arquivo (usar barras para consistência)
                                    extracted_files.append(
                                        target_path.replace("\\", "/")
                                    )
                                source.close()
                else:
                    # Extração normal - extrair todo conteúdo para pasta do jogo
                    logger.info(f"Extracting all zip contents to {install_path}")

                    for member in zf.namelist():
                        if not member.endswith("/"):
                            zf.extract(member, install_path)
                            # Rastrear arquivo (usar barras para consistência)
                            extracted_files.append(member.replace("\\", "/"))

            logger.info(f"Extracted {len(extracted_files)} files from fix")
            return extracted_files

        except Exception as e:
            logger.error(f"Failed to extract fix zip: {e}")
            raise

    def _create_install_log(
        self,
        appid: int,
        install_path: str,
        fix_type: str,
        download_url: str,
        game_name: str,
        extracted_files: List[str],
    ):
        """Cria log de instalação do fix"""
        try:
            log_file_path = os.path.join(install_path, f"accela-fix-log-{appid}.log")

            with open(log_file_path, "w", encoding="utf-8") as f:
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Game: {game_name} ({appid})\n")
                f.write(f"Fix Type: {fix_type.title()}-Fix\n")
                f.write(f"Download URL: {download_url}\n")
                f.write("Files:\n")
                for file_path in extracted_files:
                    f.write(f"{file_path}\n")

            logger.info(f"Created install log: {log_file_path}")

        except Exception as e:
            logger.warning(f"Failed to create install log: {e}")

    def cleanup(self):
        """Limpa recursos do gerenciador"""
        try:
            self.http_client.close()
            logger.info("OnlineFixesManager cleanup completed")
        except Exception as e:
            logger.error(f"Error during OnlineFixesManager cleanup: {e}")
