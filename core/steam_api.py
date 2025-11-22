import json
from utils.logger import get_internationalized_logger
import logging
import os
import subprocess
import sys
import tempfile
import time
from functools import wraps
from typing import Any, Dict

import requests

logger = get_internationalized_logger()


# --- Configuration ---
class SteamAPIConfig:
    """Centralized configuration for Steam API settings"""

    # Cache settings
    CACHE_DIR = "api_cache"
    CACHE_EXPIRATION_SECONDS = 21600  # 6 hours - more responsive cache
    MAX_CACHE_SIZE_MB = 50  # Limit cache size

    # Network settings
    DEFAULT_TIMEOUT = 15  # seconds
    MAX_RETRIES = 3
    RETRY_BACKOFF_FACTOR = 2.0

    # Performance settings
    MAX_CONCURRENT_REQUESTS = 5
    CONNECTION_POOL_SIZE = 10


def retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    exceptions: tuple = (requests.exceptions.RequestException,),
):
    """Enhanced decorator for retry with exponential backoff and jitter."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        # Add jitter to prevent thundering herd
                        base_wait = backoff_factor**attempt
                        jitter = base_wait * 0.1 * (0.5 + (hash(str(args)) % 100) / 100)
                        wait_time = base_wait + jitter

                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed, "
                            f"retry in {wait_time:.2f}s: {type(e).__name__}: {e}"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}"
                        )
            raise (
                last_exception
                if last_exception is not None
                else Exception("All attempts failed")
            )

        return wrapper

    return decorator


def get_depot_info_from_api(app_id):
    """
    Fetches depot and app info for a given app_id using a multi-tiered approach.

    Returns:
        dict: A dictionary containing 'depots' and 'installdir'.
              Returns an empty dict on failure.
    """
    os.makedirs(SteamAPIConfig.CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(SteamAPIConfig.CACHE_DIR, f"{app_id}_depot_details.json")

    if os.path.exists(cache_file):
        try:
            file_age = time.time() - os.path.getmtime(cache_file)
            if file_age < SteamAPIConfig.CACHE_EXPIRATION_SECONDS:
                logger.debug(
                    f"Loading app details for AppID: {app_id} from local cache."
                )
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(
                f"Could not read cache file {cache_file}. Fetching fresh data. Error: {e}"
            )

    logger.debug(
        f"Attempting to fetch app info for AppID {app_id} using steam.client (priority)..."
    )
    api_data = _fetch_with_steam_client(app_id)

    if not api_data or not api_data.get("depots"):
        logger.warning(
            f"steam.client method failed for AppID {app_id}. Falling back to public Web API."
        )
        api_data = _fetch_with_web_api(app_id)

    # Total game size is already calculated in _fetch_with_steam_client()
    # No need for additional depot size fetching

    # Cache the successful response
    if api_data and api_data.get("depots"):
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(api_data, f, indent=2)
            logger.debug(f"Cached API response for AppID: {app_id}")
            _cleanup_cache_if_needed()
        except (IOError, TypeError) as e:
            logger.warning(f"Failed to cache API response for AppID {app_id}: {e}")

    return api_data


def _fetch_with_steam_client(app_id):
    """
    Uses the steam.client library to get product info, including installdir.
    """
    try:
        from steam.client import SteamClient
    except ImportError:
        logger.warning(
            "`steam[client]` package not found. Skipping steam.client fetch method."
        )
        return {}

    script_content = f"""
import json, sys
from steam.client import SteamClient
try:
    client = SteamClient()
    client.anonymous_login()
    if not client.logged_on:
        sys.stderr.write("Failed to anonymously login to Steam.\\n")
        sys.exit(1)
    result = client.get_product_info(apps=[{app_id}], timeout=30)
    client.logout()
    print(json.dumps(result))
except Exception as e:
    sys.stderr.write(f"An exception occurred: {{e}}\\n")
    sys.exit(1)
"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as temp_file:
        temp_file.write(script_content)
        temp_script_path = temp_file.name

    api_data = {}
    raw_stdout = ""
    try:
        python_executable = sys.executable
        result = subprocess.run(
            [python_executable, temp_script_path],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            encoding="utf-8",
        )
        raw_stdout = result.stdout.strip()

        if result.returncode != 0:
            logger.error(
                f"steam.client subprocess failed. Stderr: {result.stderr.strip()}"
            )
            return {}

        data = json.loads(raw_stdout)
        app_data = data.get("apps", {}).get(str(app_id), {})

        depot_info = {}
        installdir = None
        game_name = None
        total_game_size = 0

        if app_data:
            installdir = app_data.get("config", {}).get("installdir")
            game_name = app_data.get("name") or app_data.get("common", {}).get("name")
            depots = app_data.get("depots", {})

            # Calcular tamanho total do jogo a partir dos depots
            total_game_size = 0
            for depot_id, depot_data in depots.items():
                if not isinstance(depot_data, dict):
                    continue
                config = depot_data.get("config", {})

                # Extrair tamanho do depot se disponível nos manifests
                depot_size = 0
                if "manifests" in depot_data and "public" in depot_data["manifests"]:
                    depot_size = int(depot_data["manifests"]["public"].get("size", 0))
                    total_game_size += depot_size

                depot_info[depot_id] = {
                    "name": depot_data.get("name", f"Depot {depot_id}"),
                    "oslist": config.get("oslist"),
                    "language": config.get("language"),
                    "steamdeck": config.get("steamdeck") == "1",
                    "size": depot_size,
                }

        api_data = {
            "depots": depot_info,
            "installdir": installdir,
            "game_name": game_name,
            "total_game_size": total_game_size,
        }

    except Exception as e:
        logger.error(
            f"An unexpected error occurred in _fetch_with_steam_client: {e}",
            exc_info=True,
        )
    finally:
        os.unlink(temp_script_path)

    return api_data


@retry(
    max_attempts=SteamAPIConfig.MAX_RETRIES,
    backoff_factor=SteamAPIConfig.RETRY_BACKOFF_FACTOR,
    exceptions=(requests.exceptions.Timeout, requests.exceptions.ConnectionError),
)
def _fetch_with_web_api(app_id: str) -> Dict[str, Any]:
    """
    Fetches data from the public Steam store API as a fallback.
    Implements retry with exponential backoff and configurable timeout.
    """
    url = "https://store.steampowered.com/api/appdetails"
    params = {"appids": app_id}
    headers = {
        "User-Agent": "Bifrost-Client/1.0",
        "Accept": "application/json",
        "Connection": "close",
    }

    try:
        response = requests.get(
            url, params=params, timeout=SteamAPIConfig.DEFAULT_TIMEOUT, headers=headers
        )
        response.raise_for_status()
        data = response.json()
        return _parse_web_api_response(app_id, data)
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching data from Web API for AppID {app_id}")
        raise
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error with Web API for AppID {app_id}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Web API request error for AppID {app_id}: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response from Web API for AppID {app_id}: {e}")
        return {}


def _parse_web_api_response(app_id, data):
    """
    Parses the JSON data from the public Web API.
    """
    depot_info = {}
    installdir = None
    game_name = None
    app_data_wrapper = data.get(str(app_id))

    if app_data_wrapper and app_data_wrapper.get("success"):
        app_data = app_data_wrapper.get("data", {})
        installdir = app_data.get("install_dir")
        game_name = app_data.get("name")
        depots = app_data.get("depots", {})
        for depot_id, depot_data in depots.items():
            if not isinstance(depot_data, dict):
                continue
            depot_info[depot_id] = {
                "name": depot_data.get("name", f"Depot {depot_id}"),
                "oslist": None,
                "language": None,
                "steamdeck": False,
            }

    return {
        "depots": depot_info,
        "installdir": installdir,
        "game_name": game_name,
        "total_game_size": 0,
    }


def _cleanup_cache_if_needed():
    """Clean up cache if it exceeds size limit"""
    try:
        total_size = 0
        cache_files = []

        if not os.path.exists(SteamAPIConfig.CACHE_DIR):
            return

        total_size = 0
        for filename in os.listdir(SteamAPIConfig.CACHE_DIR):
            filepath = os.path.join(SteamAPIConfig.CACHE_DIR, filename)
            if os.path.isfile(filepath):
                size = os.path.getsize(filepath)
                mtime = os.path.getmtime(filepath)
                cache_files.append((filepath, size, mtime))
                total_size += size

        # Convert to MB
        total_size_mb = total_size / (1024 * 1024)

        if total_size_mb <= SteamAPIConfig.MAX_CACHE_SIZE_MB:
            return

        # Sort by modification time (oldest first)
        cache_files.sort(key=lambda x: x[2])

        # Remove oldest files until under limit
        target_size = SteamAPIConfig.MAX_CACHE_SIZE_MB * 0.8 * 1024 * 1024  # 80% of max
        current_size = total_size

        removed_count = 0
        for filepath, size, mtime in cache_files:
            if current_size <= target_size:
                break

            try:
                os.remove(filepath)
                current_size -= size
                removed_count += 1
                logger.debug(f"Removed old cache file: {os.path.basename(filepath)}")
            except Exception as e:
                logger.warning(f"Error removing cache file {filepath}: {e}")

        if removed_count > 0:
            logger.info(
                f"API cache cleanup: removed {removed_count} files, freed {(total_size - current_size) / (1024 * 1024):.1f} MB"
            )

    except Exception as e:
        logger.error(f"Error during API cache cleanup: {e}")


def get_depot_sizes_from_manifests(app_id, depots):
    """
    Attempts to get depot sizes by downloading and analyzing manifests.

    Args:
        app_id: Steam App ID
        depots: Dictionary of depot information

    Returns:
        dict: Mapping of depot_id to size in bytes (0 if unavailable)
    """
    depot_sizes = {}
    logger.debug(f"Getting depot sizes for AppID {app_id} with {len(depots)} depots")

    try:
        from steam.client import SteamClient

        logger.debug("Steam client library available for depot size fetching")
    except ImportError:
        logger.warning("`steam[client]` package not found. Cannot fetch depot sizes.")
        return depot_sizes

    script_content = f"""
import json, sys, os
from steam.client import SteamClient
try:
    client = SteamClient()
    client.anonymous_login()
    if not client.logged_on:
        sys.stderr.write("Failed to anonymously login to Steam.\\n")
        sys.exit(1)

    depot_sizes = {{}}
    depots_data = {json.dumps(depots)}

    # Get product info which contains depot manifests
    app_id = {app_id}
    product_info = client.get_product_info([app_id])

    sys.stderr.write(f"Product info structure: {{product_info}}\\n")

    if product_info and 'apps' in product_info:
        apps = product_info['apps']
        sys.stderr.write(f"Available apps: {{list(apps.keys())}}\\n")

        if str(app_id) in apps:
            app_data = apps[str(app_id)]

            if 'depots' in app_data:
                app_depots = app_data['depots']
                sys.stderr.write(f"Found {{len(app_depots)}} depots\\n")

                for depot_id in depots_data.keys():
                    try:
                        if depot_id in app_depots:
                            depot_data = app_depots[depot_id]
                            if 'manifests' in depot_data and 'public' in depot_data['manifests']:
                                depot_size = depot_data['manifests']['public'].get('size', 0)
                                depot_sizes[depot_id] = int(depot_size)
                                sys.stderr.write(f"Depot {{depot_id}}: {{depot_size}} bytes\\n")
                            else:
                                depot_sizes[depot_id] = 0
                                sys.stderr.write(f"Depot {{depot_id}}: no public manifest\\n")
                        else:
                            depot_sizes[depot_id] = 0
                            sys.stderr.write(f"Depot {{depot_id}}: not found\\n")
                    except Exception as e:
                        sys.stderr.write(f"Error getting size for depot {{depot_id}}: {{e}}\\n")
                        depot_sizes[depot_id] = 0
            else:
                sys.stderr.write("No depots found in app data\\n")
        else:
            sys.stderr.write(f"AppID {{app_id}} not found in apps\\n")
    else:
        sys.stderr.write("No apps found in product info\\n")

    client.logout()
    print(json.dumps(depot_sizes))

except Exception as e:
    sys.stderr.write(f"Script error: {{e}}\\n")
    sys.exit(1)
"""

    logger.debug(
        f"Executing Steam client script to get depot sizes for {len(depots)} depots"
    )
    try:
        import subprocess
        import tempfile

        # Create temporary script file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as temp_script:
            temp_script.write(script_content)
            temp_script_path = temp_script.name

        try:
            python_executable = sys.executable
            result = subprocess.run(
                [python_executable, temp_script_path],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
                encoding="utf-8",
            )

            logger.debug(f"Depot size script return code: {result.returncode}")
            logger.debug(f"Depot size script stdout: {result.stdout}")
            logger.debug(f"Depot size script stderr: {result.stderr}")

            if result.returncode == 0:
                try:
                    depot_sizes = json.loads(result.stdout.strip())
                    logger.debug(
                        f"Successfully retrieved sizes for {len([s for s in depot_sizes.values() if s > 0])} depots"
                    )
                    logger.debug(f"Depot sizes: {depot_sizes}")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse depot sizes JSON: {e}")
                    logger.debug(f"Raw output: {result.stdout}")
            else:
                logger.error(
                    f"Depot size script failed with return code {result.returncode}"
                )
                logger.error(f"Error output: {result.stderr}")
        except Exception as e:
            logger.error(f"Failed to get depot sizes: {e}")
        finally:
            # Clean up temporary script
            try:
                os.unlink(temp_script_path)
            except (AttributeError, TypeError):
                pass

    except Exception as e:
        logger.error(f"Failed to get depot sizes: {e}")

    logger.debug(f"Final depot sizes dict: {depot_sizes}")
    return depot_sizes
