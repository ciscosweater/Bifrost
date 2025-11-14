import logging
from utils.logger import get_internationalized_logger
import os
import re
import shutil
import subprocess
import sys

import psutil

logger = get_internationalized_logger()

# A global variable is used here to pass the SLSsteam.so path from the
# moment it's found (before Steam is killed) to the moment it's needed
# (after Steam is killed).
_slssteam_so_path_cache = None

# Cache for Steam libraries to avoid repeated scans
_STEAM_LIBRARIES_CACHE = {}
_STEAM_LIBRARIES_CACHE_TTL = 60  # 1 minute cache for Steam libraries


def find_steam_install():
    """
    Attempts to find the Steam installation path based on the operating system.
    """
    if sys.platform == "win32":
        return _find_steam_windows()
    elif sys.platform == "linux":
        return _find_steam_linux()
    else:
        logger.warning(
            f"Automatic Steam path detection is not supported on this OS: {sys.platform}."
        )
        return None


def _find_steam_windows():
    """Finds Steam installation path on Windows via the registry."""
    try:
        import winreg

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
        winreg.CloseKey(key)
        logger.debug(f"Found Steam installation at: {steam_path}")
        return os.path.normpath(steam_path)
    except Exception:
        logger.debug("Failed to read Steam path from registry.")
        return None


def _find_steam_linux():
    """Finds Steam installation path on Linux by checking common locations."""
    home_dir = os.path.expanduser("~")
    potential_paths = [
        os.path.join(home_dir, ".steam", "steam"),
        os.path.join(home_dir, ".local", "share", "Steam"),
        os.path.join(
            home_dir, ".var", "app", "com.valvesoftware.Steam", "data", "Steam"
        ),
        os.path.join(home_dir, "snap", "steam", "common", ".steam", "steam"),
    ]

    for path in potential_paths:
        if os.path.isdir(os.path.join(path, "steamapps")):
            real_path = os.path.realpath(path)
            logger.debug(f"Found Steam installation at: {real_path} (from {path})")
            return real_path

    logger.debug("Could not find Steam installation in common Linux directories.")
    return None


def parse_library_folders(vdf_path):
    """
    Parses a libraryfolders.vdf file to find all Steam library paths.
    """
    library_paths = []
    try:
        with open(vdf_path, "r", encoding="utf-8") as f:
            content = f.read()
        matches = re.findall(r"^\s*\"(?:path|\d+)\"\s*\"(.*?)\"", content, re.MULTILINE)
        for path in matches:
            normalized_path = path.replace("\\\\", "\\")
            if os.path.isdir(os.path.join(normalized_path, "steamapps")):
                library_paths.append(normalized_path)
    except Exception as e:
        logger.error(f"Failed to parse libraryfolders.vdf: {e}")
    return library_paths


def get_steam_libraries(force_refresh: bool = False):
    """
    Finds all Steam library folders, resolving symbolic links to prevent duplicates.

    Args:
        force_refresh: If True, bypasses cache and forces a fresh scan
    """
    import time

    current_time = time.time()
    cache_key = "steam_libraries"

    # Check cache first (unless force_refresh)
    if not force_refresh and cache_key in _STEAM_LIBRARIES_CACHE:
        cached_libraries, cached_time = _STEAM_LIBRARIES_CACHE[cache_key]
        if current_time - cached_time < _STEAM_LIBRARIES_CACHE_TTL:
            logger.debug(
                f"Using cached Steam libraries: {len(cached_libraries)} libraries"
            )
            return cached_libraries

    steam_path = find_steam_install()
    if not steam_path:
        return []

    all_libraries = {os.path.realpath(steam_path)}
    vdf_path = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")

    if os.path.exists(vdf_path):
        additional_libraries = parse_library_folders(vdf_path)
        for lib_path in additional_libraries:
            all_libraries.add(os.path.realpath(lib_path))

    libraries_list = list(all_libraries)

    # Cache the result
    _STEAM_LIBRARIES_CACHE[cache_key] = (libraries_list, current_time)

    return libraries_list


def kill_steam_process():
    """
    Finds and terminates the 'steam' or 'steam.exe' process. On Linux, it
    also finds and caches the path to SLSsteam.so before killing the process.
    """
    global _slssteam_so_path_cache
    _slssteam_so_path_cache = None

    process_name = "steam.exe" if sys.platform == "win32" else "steam"
    steam_proc = next(
        (
            p
            for p in psutil.process_iter(["pid", "name"])
            if p.info["name"].lower() == process_name
        ),
        None,
    )

    if not steam_proc:
        logger.warning(f"{process_name} process not found.")
        return False

    if sys.platform == "linux":
        pid = steam_proc.pid
        maps_file = f"/proc/{pid}/maps"
        try:
            with open(maps_file, "r") as f:
                for line in f:
                    if "SLSsteam.so" in line:
                        parts = line.split()
                        if len(parts) > 5 and os.path.exists(parts[-1]):
                            _slssteam_so_path_cache = parts[-1]
                            logger.info(
                                f"Found and cached SLSsteam.so path: {_slssteam_so_path_cache}"
                            )
                            break
        except Exception as e:
            logger.error(f"Error reading process maps for SLSsteam.so: {e}")
    try:
        steam_proc.kill()
        steam_proc.wait(timeout=5)
        logger.info(f"Successfully terminated {process_name} (PID: {steam_proc.pid}).")
        return True
    except Exception as e:
        logger.error(f"Failed to terminate {process_name}: {e}")
        return False


def start_steam():
    """
    Launches the Steam client. On Linux, it uses a multi-step approach.
    Returns 'SUCCESS', 'FAILED', or 'NEEDS_USER_PATH'.
    """
    global _slssteam_so_path_cache
    logger.info("Attempting to start Steam...")

    try:
        if sys.platform == "win32":
            steam_path = find_steam_install()
            if not steam_path:
                return "FAILED"
            exe_path = os.path.join(steam_path, "steam.exe")
            if not os.path.exists(exe_path):
                return "FAILED"
            subprocess.Popen([exe_path])
            return "SUCCESS"

        elif sys.platform == "linux":

            def launch_with_audit(so_path):
                logger.info(f"Attempting to launch Steam with LD_AUDIT: {so_path}")

                # Check if SLSsteam.so architecture matches system
                try:
                    result = subprocess.run(
                        ["file", so_path], capture_output=True, text=True
                    )
                    if "ELF 32-bit" in result.stdout:
                        logger.warning(
                            "SLSsteam.so is 32-bit, this may cause issues on 64-bit systems"
                        )
                except (AttributeError, TypeError):
                    pass

                # Find the correct Steam installation path
                steam_install_path = find_steam_install()
                if steam_install_path:
                    steam_script = os.path.join(steam_install_path, "steam.sh")
                    if os.path.exists(steam_script):
                        logger.info(f"Using Steam script: {steam_script}")
                        env = os.environ.copy()
                        env["LD_AUDIT"] = so_path
                        # Use the steam.sh script instead of 'steam' command
                        subprocess.Popen([steam_script, "-no-cef-sandbox"], env=env)
                        return "SUCCESS"

                # Fallback to system steam
                env = os.environ.copy()
                env["LD_AUDIT"] = so_path
                subprocess.Popen(["steam"], env=env)
                return "SUCCESS"

            # 1. Use cached path if available
            if _slssteam_so_path_cache:
                result = launch_with_audit(_slssteam_so_path_cache)
                _slssteam_so_path_cache = None
                return result

            # 2. If no cache, check the default installation path
            default_path = os.path.expanduser("~/.local/share/SLSsteam/SLSsteam.so")
            if os.path.exists(default_path):
                return launch_with_audit(default_path)

            # 3. If neither works, signal UI to ask the user for the path
            logger.warning("SLSsteam.so not found in cache or default location.")
            return "NEEDS_USER_PATH"
        else:
            return "FAILED"
    except Exception as e:
        logger.error(f"Failed to execute Steam: {e}", exc_info=True)
        return "FAILED"


def start_steam_with_path(path):
    """
    Launches Steam using a user-provided path to SLSsteam.so.
    """
    if not path or not os.path.exists(path):
        logger.error(f"Provided path is invalid or does not exist: {path}")
        return False

    try:
        logger.info(f"Executing Steam with user-provided LD_AUDIT: {path}")

        # Check architecture
        try:
            result = subprocess.run(["file", path], capture_output=True, text=True)
            if "ELF 32-bit" in result.stdout:
                logger.warning(
                    "SLSsteam.so is 32-bit, this may cause issues on 64-bit systems"
                )
        except (AttributeError, TypeError):
            pass

        # Find the correct Steam installation
        steam_install_path = find_steam_install()
        if steam_install_path:
            steam_script = os.path.join(steam_install_path, "steam.sh")
            if os.path.exists(steam_script):
                logger.info(f"Using Steam script: {steam_script}")
                env = os.environ.copy()
                env["LD_AUDIT"] = path
                subprocess.Popen([steam_script, "-no-cef-sandbox"], env=env)
                return True

        # Fallback to system steam
        env = os.environ.copy()
        env["LD_AUDIT"] = path
        subprocess.Popen(["steam"], env=env)
        return True
    except Exception as e:
        logger.error(
            f"Failed to execute steam with provided path '{path}': {e}", exc_info=True
        )
        return False


def clear_steam_libraries_cache():
    """Clear the Steam libraries cache."""
    global _STEAM_LIBRARIES_CACHE
    _STEAM_LIBRARIES_CACHE.clear()
    logger.debug("Steam libraries cache cleared")


def run_dll_injector(steam_path):
    """
    Runs the DLLInjector.exe. This is a Windows-specific function.
    """
    if sys.platform != "win32":
        return False
    injector_path = os.path.join(steam_path, "DLLInjector.exe")
    if not os.path.exists(injector_path):
        return False
    try:
        subprocess.Popen([injector_path], creationflags=subprocess.CREATE_NO_WINDOW)
        return True
    except Exception:
        return False
