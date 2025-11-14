import logging
from utils.logger import get_internationalized_logger
import os
import re
import shutil

from PyQt6.QtCore import QObject, pyqtSignal

logger = get_internationalized_logger()


class MergeFilesTask(QObject):
    progress = pyqtSignal(str)
    merge_complete = pyqtSignal(bool)

    def run(self, game_data, dest_path, slssteam_mode):
        self.progress.emit(f"Starting merge task. SLSsteam Mode: {slssteam_mode}")

        safe_game_name_fallback = (
            re.sub(r"[^\w\s-]", "", game_data.get("game_name", ""))
            .strip()
            .replace(" ", "_")
        )
        install_folder_name = game_data.get("installdir", safe_game_name_fallback)
        if not install_folder_name:
            install_folder_name = f"App_{game_data['appid']}"

        # Sanitize directory name to remove filesystem-invalid characters
        install_folder_name = re.sub(r'[<>:"/\\|?*]', "_", str(install_folder_name))

        merge_root = os.path.join(dest_path, "steamapps", "common", install_folder_name)

        os.makedirs(merge_root, exist_ok=True)
        self.progress.emit(f"Merge destination set to: {merge_root}")

        self._copy_depot_files(merge_root)

        self._create_acf_file(game_data, dest_path, install_folder_name)

        self._cleanup_source_dirs()
        self.merge_complete.emit(slssteam_mode)

    def _copy_depot_files(self, merge_root):
        depots_dir = os.path.join(os.getcwd(), "depots")
        if not os.path.isdir(depots_dir):
            self.progress.emit("No 'depots' directory found to merge.")
            return

        for depot_id in os.listdir(depots_dir):
            source_path = os.path.join(depots_dir, depot_id)
            if os.path.isdir(source_path):
                self.progress.emit(f"Merging files from depot {depot_id}...")
                try:
                    ignore_pattern = shutil.ignore_patterns(".DepotDownloader")
                    shutil.copytree(
                        source_path,
                        merge_root,
                        dirs_exist_ok=True,
                        ignore=ignore_pattern,
                    )
                except Exception as e:
                    self.progress.emit(f"Error merging depot {depot_id}: {e}")

    def _create_acf_file(self, game_data, steam_library_path, install_folder_name):
        self.progress.emit("Generating Steam .acf manifest file...")
        acf_path = os.path.join(
            steam_library_path, "steamapps", f"appmanifest_{game_data['appid']}.acf"
        )

        acf_content = f'''
"AppState"
{{
    "appid"         "{game_data["appid"]}"
    "Universe"       "1"
    "name"          "{game_data["game_name"]}"
    "StateFlags"    "4"
    "installdir"    "{install_folder_name}"
    "LastUpdated"   "0"
    "UpdateResult"  "0"
    "SizeOnDisk"    "0"
    "buildid"       "0"
    "LastOwner"     "0"
    "BytesToDownload"   "0"
    "BytesDownloaded"   "0"
    "AutoUpdateBehavior"   "0"
    "AllowOtherDownloadsWhileRunning"   "0"
    "ScheduledAutoUpdate"   "0"
}}
'''

        try:
            with open(acf_path, "w", encoding="utf-8") as f:
                f.write(acf_content)
            self.progress.emit(f"Created .acf file at {acf_path}")
        except IOError as e:
            self.progress.emit(f"Error creating .acf file: {e}")

    def _cleanup_source_dirs(self):
        self.progress.emit("Cleaning up temporary download directories...")
        for dirname in ["depots", "manifest"]:
            dir_path = os.path.join(os.getcwd(), dirname)
            if os.path.isdir(dir_path):
                try:
                    shutil.rmtree(dir_path)
                    self.progress.emit(f"Removed '{dirname}' directory.")
                except OSError as e:
                    self.progress.emit(f"Error removing '{dirname}' directory: {e}")
