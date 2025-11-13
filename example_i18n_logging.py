#!/usr/bin/env python3
"""
Example demonstrating i18n logging system usage.
This file shows how to use the new i18n-enabled logging.
"""

import sys
import os

# Add project root to path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logger import get_i18n_logger, info_i18n
from utils.i18n import init_i18n
from PyQt6.QtWidgets import QApplication

def demo_i18n_logging():
    """Demonstrate i18n logging functionality."""
    
    app = QApplication(sys.argv)
    
    # Initialize i18n system
    init_i18n(app)
    
    # Get i18n logger with context
    logger = get_i18n_logger("demo", "Application")
    
    print("=== i18n Logging Demo ===")
    
    # These messages will be translated if the language is set to Portuguese
    info_i18n(logger, "Application starting...")
    info_i18n(logger, "Loaded {font_name} font", "DemoFont")
    info_i18n(logger, "Applied selected font: '{font_name}' with size {size}px", "DemoFont", 12)
    info_i18n(logger, "Zip file provided as argument: {zip_file}", "demo.zip")
    info_i18n(logger, "Main window displayed successfully.")
    info_i18n(logger, "Logging configured (simple_mode={simple_mode}, level={level}).", False, "INFO")
    info_i18n(logger, "Translation loaded for {language}", "pt_BR")
    info_i18n(logger, "Using .ts file directly: {ts_file}", "app_pt_BR.ts")
    info_i18n(logger, "Loaded {count} contexts from {ts_file}", 50, "app_pt_BR.ts")
    info_i18n(logger, "Using saved language preference: {language}", "pt_BR")
    info_i18n(logger, "Auto-detected language: {language}", "pt_BR")
    info_i18n(logger, "Starting zip processing task for: {zip_path}", "/path/to/file.zip")
    info_i18n(logger, "Found official install directory: {directory}", "/games/steam")
    info_i18n(logger, "Found game name from Steam API: {game_name}", "Demo Game")
    info_i18n(logger, "Transferred total game size: {size} bytes ({size_gb:.2f} GB)", 1073741824, 1.00)
    info_i18n(logger, "Zip processing task completed successfully.")
    info_i18n(logger, "OnlineFixesManager initialized")
    info_i18n(logger, "Checking for fixes for AppID: {appid}", 12345)
    info_i18n(logger, "Fix check completed for {appid}: Generic={generic}, Online={online}", 12345, True, False)
    info_i18n(logger, "Started fix download for AppID {appid}: {fix_type}", 12345, "Generic")
    info_i18n(logger, "Downloading {fix_type} fix from {download_url}", "Generic", "https://example.com/fix.zip")
    info_i18n(logger, "Successfully applied {fix_type} fix for AppID {appid}", "Generic", 12345)
    info_i18n(logger, "OnlineFixesManager cleanup completed")
    info_i18n(logger, "User agreed to restart Steam.")
    info_i18n(logger, "Game Manager dialog opened and closed")
    info_i18n(logger, "Backup dialog opened and closed")
    info_i18n(logger, "Font setting updated: selected_font={font}", "Arial")
    info_i18n(logger, "Restarting application to apply font settings...")
    info_i18n(logger, "Logging settings updated: level={level}, simple_mode={simple_mode}", "DEBUG", True)
    info_i18n(logger, "Running SLSsteam command: {command}", "/path/to/slssteam")
    info_i18n(logger, "Auto-enabled slssteam_mode after successful SLSsteam setup")
    info_i18n(logger, "Deleted game directory: {game_dir}", "/games/steam/app_12345")
    info_i18n(logger, "Deleted ACF file: {acf_path}", "/games/steam/appmanifest_12345.acf")
    info_i18n(logger, "Deleted compatdata directory: {compatdata_path}", "/games/steam/steamapps/compatdata/12345")
    info_i18n(logger, "Compatdata directory not found: {compatdata_path}", "/games/steam/steamapps/compatdata/12345")
    info_i18n(logger, "Successfully deleted game {app_id}: {items}", 12345, "game directory, ACF file")
    info_i18n(logger, "Created backup directory: {backup_dir}", "/backups/accela")
    info_i18n(logger, "Found {count} ACCELA stats files out of {total} total", 25, 100)
    info_i18n(logger, "{game_type} backup created successfully: {backup_path}", "Steam", "/backups/accela/steam_backup.zip")
    info_i18n(logger, "Backed up {count} files", 25)
    info_i18n(logger, "Created pre-restore backup: {backup_result}", "/backups/accela/pre_restore.zip")
    info_i18n(logger, "Backup restored successfully from: {backup_path}", "/backups/accela/steam_backup.zip")
    info_i18n(logger, "Backup deleted: {backup_path}", "/backups/accela/old_backup.zip")
    info_i18n(logger, "Download cancellation requested")
    info_i18n(logger, "Trying API fallback for app {app_id}", 12345)
    info_i18n(logger, "Found {count} API URLs for app {app_id}", 3, 12345)
    info_i18n(logger, "Cleaned up {count} old sessions", 5)
    info_i18n(logger, "Image cache initialized at: {cache_dir}", "/tmp/accela_cache")
    info_i18n(logger, "Emergency cleanup: removed {count} files, freed memory", 10)
    info_i18n(logger, "LRU eviction: removed {count} files, freed {size:.1f} MB", 5, 25.5)
    info_i18n(logger, "Cleared image cache: removed {count} files", 100)
    info_i18n(logger, "Wine detected: {wine_version}", "Wine 8.0")
    info_i18n(logger, "System performance optimized for Steamless")
    info_i18n(logger, "System performance restored to normal")
    info_i18n(logger, "Found and cached SLSsteam.so path: {path}", "/path/to/slssteam.so")
    info_i18n(logger, "Successfully terminated {process_name} (PID: {pid}).", "steam", 1234)
    info_i18n(logger, "Attempting to start Steam...")
    info_i18n(logger, "Attempting to launch Steam with LD_AUDIT: {so_path}", "/path/to/slssteam.so")
    info_i18n(logger, "Using Steam script: {steam_script}", "/usr/bin/steam")
    info_i18n(logger, "Executing Steam with user-provided LD_AUDIT: {path}", "/custom/path/slssteam.so")
    info_i18n(logger, "Starting cleanup for session {session_id}", "session_123")
    info_i18n(logger, "Cleanup completed: {files_removed} files, {dirs_removed} dirs removed", 10, 2)
    info_i18n(logger, "Removed partial file: {file_path}", "/tmp/partial_download.zip")
    
    print("\n=== Demo completed ===")
    print("These messages would be translated to Portuguese if the system language is set to pt_BR")
    print("To see the translation in action, run the main application with system language set to Portuguese")

if __name__ == "__main__":
    demo_i18n_logging()