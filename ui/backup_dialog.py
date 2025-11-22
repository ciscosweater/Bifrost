import importlib.util
from utils.logger import get_internationalized_logger
import logging
import os
import sys
from typing import Any, Dict

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.interactions import HoverButton, ModernFrame
from ui.theme import BorderRadius, Spacing, Typography, theme

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# Import i18n
try:
    from utils.i18n import tr
except (ImportError, ModuleNotFoundError):

    def tr(context, text):
        return text


# Import BackupManager after path setup
backup_manager_path = os.path.join(project_root, "core", "backup_manager.py")
spec = importlib.util.spec_from_file_location("backup_manager", backup_manager_path)
if spec and spec.loader:
    backup_manager_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backup_manager_module)
    BackupManager = backup_manager_module.BackupManager
else:
    raise ImportError("Could not load BackupManager")

logger = get_internationalized_logger()


class BackupWorker(QThread):
    """Worker thread for backup operations to avoid UI freezing."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, operation: str, backup_manager, **kwargs):
        super().__init__()
        self.operation = operation
        self.backup_manager = backup_manager
        self.kwargs = kwargs

    def run(self):
        try:
            if self.operation == "create":
                self.progress.emit(tr("BackupDialog", "Creating backup..."))
                backup_path = self.backup_manager.create_backup(
                    self.kwargs.get("backup_name")
                )
                if backup_path:
                    self.finished.emit(
                        True,
                        tr("BackupDialog", "Backup created: {filename}").format(
                            filename=os.path.basename(backup_path)
                        ),
                    )
                else:
                    self.finished.emit(
                        False, tr("BackupDialog", "Failed to create backup")
                    )

            elif self.operation == "restore":
                self.progress.emit(tr("BackupDialog", "Restoring backup..."))
                success = self.backup_manager.restore_backup(self.kwargs["backup_path"])
                if success:
                    self.finished.emit(
                        True, tr("BackupDialog", "Backup restored successfully")
                    )
                else:
                    self.finished.emit(
                        False, tr("BackupDialog", "Failed to restore backup")
                    )

            elif self.operation == "delete":
                self.progress.emit(tr("BackupDialog", "Deleting backup..."))
                success = self.backup_manager.delete_backup(self.kwargs["backup_path"])
                if success:
                    self.finished.emit(
                        True, tr("BackupDialog", "Backup deleted successfully")
                    )
                else:
                    self.finished.emit(
                        False, tr("BackupDialog", "Failed to delete backup")
                    )

        except Exception as e:
            logger.error(f"Backup worker error: {e}")
            self.finished.emit(
                False, tr("BackupDialog", "Error: {error}").format(error=str(e))
            )


class BackupDialog(QDialog):
    """
    Dialog for managing Steam stats backups.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        if BackupManager is None:
            raise ImportError("BackupManager not available")
        self.backup_manager = BackupManager()
        self.worker = None
        self.setup_ui()
        self.refresh_backup_list()

    def _create_header(self) -> QFrame:
        """Cria o header do dialog."""
        frame = ModernFrame()
        frame.setMinimumHeight(60)
        frame.setMaximumHeight(80)

        frame.setStyleSheet(f"""
            QFrame {{
                background: {theme.colors.SURFACE};
                border: 2px solid {theme.colors.PRIMARY};
                {BorderRadius.get_border_radius(BorderRadius.MEDIUM)};
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        layout.setSpacing(Spacing.XS)

        title = QLabel(tr("BackupDialog", "Steam Stats Backup Manager"))
        title.setFont(
            QFont(Typography.get_font_family(), Typography.H1_SIZE, QFont.Weight.Bold)
        )
        title.setStyleSheet(f"""
            color: {theme.colors.TEXT_ACCENT};
            font-size: {Typography.H1_SIZE}px;
            font-weight: bold;
            margin: 0;
            border: none;
            background: transparent;
            padding: 2px;
        """)
        layout.addWidget(title)

        subtitle = QLabel(
            tr("BackupDialog", "Create, restore, and manage Steam stats backups")
        )
        subtitle.setStyleSheet(f"""
            color: {theme.colors.TEXT_SECONDARY};
            font-size: {Typography.H3_SIZE}px;
            margin: 0;
            border: none;
            background: transparent;
            padding: 2px;
        """)
        layout.addWidget(subtitle)

        return frame

    def setup_ui(self):
        self.setWindowTitle(tr("BackupDialog", "Backup/Restore Stats"))
        self.setFixedSize(900, 650)
        self.setModal(True)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        main_layout.setSpacing(Spacing.SM)

        # Header
        header_frame = self._create_header()
        main_layout.addWidget(header_frame)

        # Main content with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Backup list
        left_panel = QWidget()
        self.setup_backup_list_panel(
            left_panel.layout() if left_panel.layout() else QVBoxLayout(left_panel)
        )
        splitter.addWidget(left_panel)

        # Right panel - Actions and info
        right_panel = self.setup_actions_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([300, 600])  # More space for details
        main_layout.addWidget(splitter)

        # Progress section
        self.setup_progress_section(main_layout)

        # Buttons
        self.setup_buttons(main_layout)

        self.setLayout(main_layout)

        # Apply theme
        self.setStyleSheet(f"""
            QDialog {{
                background: {theme.colors.BACKGROUND};
                border: 2px solid {theme.colors.BORDER};
                {BorderRadius.get_border_radius(BorderRadius.MEDIUM)};
            }}
        """)

    def setup_backup_list_panel(self, parent_layout=None):
        """Setup backup list panel."""
        if parent_layout is None:
            panel = QFrame()
            layout = QVBoxLayout(panel)
        else:
            layout = parent_layout
            panel = None

        # Title
        list_title = QLabel(tr("BackupDialog", "Available Backups"))
        list_title.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_PRIMARY};
                {Typography.get_font_style(Typography.H3_SIZE)};
                font-weight: bold;
                padding: {Spacing.SM}px 0;
            }}
        """)
        layout.addWidget(list_title)

        # Backup list
        self.backup_list = QListWidget()
        self.backup_list.setStyleSheet(f"""
            QListWidget {{
                background: {theme.colors.SURFACE};
                border: 1px solid {theme.colors.BORDER};
                {BorderRadius.get_border_radius(BorderRadius.SMALL)};
                {Typography.get_font_style(Typography.BODY_SIZE)};
                padding: {Spacing.XS}px;
            }}
            QListWidget::item {{
                padding: {Spacing.SM}px;
                border-bottom: 1px solid {theme.colors.BORDER};
                color: {theme.colors.TEXT_PRIMARY};
            }}
            QListWidget::item:selected {{
                background: {theme.colors.PRIMARY};
                color: {theme.colors.TEXT_ON_PRIMARY};
            }}
            QListWidget::item:hover {{
                background: {theme.colors.SURFACE_LIGHT};
            }}
        """)
        self.backup_list.itemSelectionChanged.connect(self.on_backup_selected)
        layout.addWidget(self.backup_list)

        # Refresh button
        refresh_btn = HoverButton(tr("BackupDialog", "Refresh List"))
        refresh_btn.clicked.connect(self.refresh_backup_list)
        layout.addWidget(refresh_btn)

        return panel if panel else layout.parent()

    def setup_actions_panel(self):
        """Setup actions panel."""
        panel = QFrame()
        layout = QVBoxLayout(panel)

        # Title
        actions_title = QLabel(tr("BackupDialog", "Backup Information"))
        actions_title.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_PRIMARY};
                {Typography.get_font_style(Typography.H3_SIZE)};
                font-weight: bold;
                padding: {Spacing.SM}px 0;
            }}
        """)
        layout.addWidget(actions_title)

        # Backup info text - more space for details
        self.backup_info_text = QTextEdit()
        self.backup_info_text.setReadOnly(True)
        self.backup_info_text.setMinimumHeight(300)  # Even more space for details
        self.backup_info_text.setStyleSheet(f"""
            QTextEdit {{
                background: {theme.colors.SURFACE};
                border: 1px solid {theme.colors.BORDER};
                {BorderRadius.get_border_radius(BorderRadius.SMALL)};
                {Typography.get_font_style(Typography.BODY_SIZE)};
                color: {theme.colors.TEXT_PRIMARY};
                padding: {Spacing.SM}px;
            }}
        """)
        self.backup_info_text.setText(
            tr("BackupDialog", "Select a backup to view details")
        )
        layout.addWidget(self.backup_info_text)

        layout.addStretch()

        return panel

    def setup_progress_section(self, parent_layout):
        """Setup progress section."""
        progress_frame = ModernFrame()
        progress_layout = QVBoxLayout(progress_frame)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {theme.colors.BORDER};
                {BorderRadius.get_border_radius(BorderRadius.SMALL)};
                text-align: center;
                {Typography.get_font_style(Typography.CAPTION_SIZE)};
                color: {theme.colors.TEXT_PRIMARY};
            }}
            QProgressBar::chunk {{
                background: {theme.colors.PRIMARY};
                {BorderRadius.get_border_radius(BorderRadius.SMALL)};
            }}
        """)
        progress_layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_SECONDARY};
                {Typography.get_font_style(Typography.CAPTION_SIZE)};
                padding: {Spacing.XS}px;
            }}
        """)
        progress_layout.addWidget(self.status_label)

        parent_layout.addWidget(progress_frame)

    def setup_buttons(self, parent_layout):
        """Setup dialog buttons."""
        button_layout = QHBoxLayout()

        # Left side - backup actions
        actions_layout = QHBoxLayout()

        self.create_backup_btn = HoverButton(tr("BackupDialog", "Create New Backup"))
        self.create_backup_btn.clicked.connect(self.create_backup)
        self.create_backup_btn.setMaximumWidth(150)
        actions_layout.addWidget(self.create_backup_btn)

        actions_layout.addSpacing(Spacing.MD)

        self.restore_backup_btn = HoverButton(tr("BackupDialog", "Restore"))
        self.restore_backup_btn.clicked.connect(self.restore_backup)
        self.restore_backup_btn.setEnabled(False)
        self.restore_backup_btn.setMaximumWidth(80)
        actions_layout.addWidget(self.restore_backup_btn)

        self.delete_backup_btn = HoverButton(tr("BackupDialog", "Delete"))
        self.delete_backup_btn.clicked.connect(self.delete_backup)
        self.delete_backup_btn.setEnabled(False)
        self.delete_backup_btn.setMaximumWidth(80)
        actions_layout.addWidget(self.delete_backup_btn)

        button_layout.addLayout(actions_layout)
        button_layout.addStretch()

        # Right side - close button
        close_btn = HoverButton(tr("BackupDialog", "Close"))
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        parent_layout.addLayout(button_layout)

    def refresh_backup_list(self):
        """Refresh the backup list."""
        try:
            self.backup_list.clear()
            backups = self.backup_manager.list_backups()

            if not backups:
                item = QListWidgetItem(tr("BackupDialog", "No backups found"))
                item.setData(Qt.ItemDataRole.UserRole, None)
                self.backup_list.addItem(item)
                return

            for backup in backups:
                display_name = backup["name"]
                if backup["created_date"]:
                    display_name += (
                        f" ({backup['created_date'].strftime('%Y-%m-%d %H:%M')})"
                    )
                display_name += f" - {backup['formatted_size']}"

                item = QListWidgetItem(display_name)
                item.setData(Qt.ItemDataRole.UserRole, backup)
                self.backup_list.addItem(item)

        except Exception as e:
            logger.error(f"Error refreshing backup list: {e}")
            QMessageBox.critical(
                self,
                tr("BackupDialog", "Error"),
                tr("BackupDialog", "Failed to refresh backup list: {error}").format(
                    error=e
                ),
            )

    def on_backup_selected(self):
        """Handle backup selection."""
        selected_items = self.backup_list.selectedItems()
        has_selection = len(selected_items) > 0

        self.restore_backup_btn.setEnabled(has_selection)
        self.delete_backup_btn.setEnabled(has_selection)

        if has_selection:
            backup = selected_items[0].data(Qt.ItemDataRole.UserRole)
            if backup:
                self.show_backup_info(backup)
            else:
                self.backup_info_text.setText(tr("BackupDialog", "No backup selected"))
        else:
            self.backup_info_text.setText(
                tr("BackupDialog", "Select a backup to view details")
            )

    def show_backup_info(self, backup: Dict[str, Any]):
        """Show backup information."""
        try:
            info = self.backup_manager.get_backup_info(backup["path"])
            if info:
                # Header information
                info_text = tr("BackupDialog", "Backup Name: {name}\n").format(
                    name=backup["name"]
                )
                created_date = (
                    backup["created_date"].strftime("%Y-%m-%d %H:%M:%S")
                    if backup["created_date"]
                    else tr("BackupDialog", "Unknown")
                )
                info_text += tr("BackupDialog", "Created: {date}\n").format(
                    date=created_date
                )
                info_text += tr("BackupDialog", "File Path: {path}\n\n").format(
                    path=backup["path"]
                )

                # Games information
                info_text += tr("BackupDialog", "Games Information:\n")
                info_text += "-" * 40 + "\n"
                info_text += tr("BackupDialog", "Total Games: {count}\n").format(
                    count=len(info.get("games", []))
                )
                info_text += tr("BackupDialog", "Bifrost Games: {count}\n").format(
                    count=len(info.get("bifrost_games", []))
                )
                info_text += tr("BackupDialog", "Other Games: {count}\n\n").format(
                    count=len(info.get("non_bifrost_games", []))
                )

                # List Bifrost games
                if info.get("bifrost_games"):
                    info_text += tr("BackupDialog", "Bifrost Games in Backup:\n")
                    for i, game in enumerate(info["bifrost_games"], 1):
                        info_text += tr(
                            "BackupDialog", "{i:2d}. {name} (ID: {app_id})\n"
                        ).format(i=i, name=game["name"], app_id=game["app_id"])
                    info_text += "\n"

                # List non-Bifrost games if any
                if info.get("non_bifrost_games"):
                    info_text += tr("BackupDialog", "Other Games in Backup:\n")
                    for i, game in enumerate(info["non_bifrost_games"], 1):
                        info_text += tr(
                            "BackupDialog", "{i:2d}. {name} (ID: {app_id})\n"
                        ).format(i=i, name=game["name"], app_id=game["app_id"])
                    info_text += "\n"

                # Size information
                info_text += tr("BackupDialog", "Size Information:\n")
                info_text += "-" * 40 + "\n"
                info_text += tr("BackupDialog", "Archive Size: {size}\n").format(
                    size=backup["formatted_size"]
                )
                info_text += tr("BackupDialog", "Uncompressed Size: {size}\n").format(
                    size=self.backup_manager._format_file_size(info["total_size"])
                )
                if "compressed_size" in info:
                    info_text += tr("BackupDialog", "Compressed Size: {size}\n").format(
                        size=self.backup_manager._format_file_size(
                            info["compressed_size"]
                        )
                    )
                    if info["total_size"] > 0:
                        compression_ratio = (
                            1 - info["compressed_size"] / info["total_size"]
                        ) * 100
                        info_text += tr(
                            "BackupDialog", "Compression Ratio: {ratio:.1f}%\n"
                        ).format(ratio=compression_ratio)
                info_text += tr("BackupDialog", "Total Files: {count}\n\n").format(
                    count=info["total_files"]
                )

                # File details
                info_text += tr("BackupDialog", "File Details:\n")
                info_text += "-" * 40 + "\n"

                for i, file_info in enumerate(info["files"], 1):
                    info_text += tr("BackupDialog", "{i:2d}. {filename}\n").format(
                        i=i, filename=file_info["name"]
                    )
                    game_name = file_info.get(
                        "game_name", tr("BackupDialog", "Unknown")
                    )
                    info_text += tr("BackupDialog", "    Game: {game}\n").format(
                        game=game_name
                    )
                    info_text += tr("BackupDialog", "    Type: {type}\n").format(
                        type=file_info["type"]
                    )
                    info_text += tr(
                        "BackupDialog", "    Original Size: {size}\n"
                    ).format(
                        size=self.backup_manager._format_file_size(file_info["size"])
                    )
                    if "compressed_size" in file_info:
                        info_text += tr(
                            "BackupDialog", "    Compressed Size: {size}\n"
                        ).format(
                            size=self.backup_manager._format_file_size(
                                file_info["compressed_size"]
                            )
                        )
                        if file_info["size"] > 0:
                            file_compression = (
                                1 - file_info["compressed_size"] / file_info["size"]
                            ) * 100
                            info_text += tr(
                                "BackupDialog", "    Compression: {compression:.1f}%\n"
                            ).format(compression=file_compression)
                    info_text += "\n"

                # Additional information
                info_text += tr("BackupDialog", "Additional Information:\n")
                info_text += "-" * 40 + "\n"
                info_text += tr(
                    "BackupDialog", "Backup Directory: {directory}\n"
                ).format(directory=os.path.dirname(backup["path"]))

                # File type summary
                schema_files = [f for f in info["files"] if f["type"] == "Schema"]
                stats_files = [f for f in info["files"] if f["type"] == "Stats"]
                info_text += tr("BackupDialog", "Schema Files: {0}\n").format(
                    len(schema_files)
                )
                info_text += tr("BackupDialog", "Stats Files: {0}\n").format(
                    len(stats_files)
                )

                self.backup_info_text.setText(info_text)
            else:
                info_text = tr("BackupDialog", "Backup Name: {0}\n").format(
                    backup["name"]
                )
                info_text += tr("BackupDialog", "Created: {0}\n").format(
                    backup["created_date"].strftime("%Y-%m-%d %H:%M:%S")
                    if backup["created_date"]
                    else tr("BackupDialog", "Unknown")
                )
                info_text += tr("BackupDialog", "Archive Size: {0}\n").format(
                    backup["formatted_size"]
                )
                info_text += tr("BackupDialog", "File Path: {0}\n\n").format(
                    backup["path"]
                )
                info_text += tr(
                    "BackupDialog", "Unable to read detailed backup information"
                )
                self.backup_info_text.setText(info_text)

        except Exception as e:
            logger.error(f"Error showing backup info: {e}")
            self.backup_info_text.setText(
                tr("BackupDialog", "Error loading backup info: {0}").format(e)
            )

    def create_backup(self):
        """Create a new backup."""
        if self.worker and self.worker.isRunning():
            return

        # Check if Steam stats path exists
        if not self.backup_manager.get_steam_stats_path():
            QMessageBox.critical(
                self,
                tr("BackupDialog", "Error"),
                tr(
                    "BackupDialog",
                    "Steam stats directory not found. Please ensure Steam is installed and has been run at least once.",
                ),
            )
            return

        # Check if there are files to backup
        files = self.backup_manager.list_stats_files()
        if not files:
            QMessageBox.warning(
                self,
                tr("BackupDialog", "Warning"),
                tr(
                    "BackupDialog",
                    "No stats files found to backup. This is normal if you haven't played any games yet.",
                ),
            )
            return

        # Start backup worker
        self.worker = BackupWorker("create", self.backup_manager)
        self.worker.progress.connect(self.on_worker_progress)
        self.worker.finished.connect(self.on_worker_finished)

        self.set_ui_busy(True, tr("BackupDialog", "Creating backup..."))
        self.worker.start()

    def restore_backup(self):
        """Restore selected backup."""
        if self.worker and self.worker.isRunning():
            return

        selected_items = self.backup_list.selectedItems()
        if not selected_items:
            return

        backup = selected_items[0].data(Qt.ItemDataRole.UserRole)
        if not backup:
            return

        # Confirm restore
        reply = QMessageBox.question(
            self,
            tr("BackupDialog", "Confirm Restore"),
            tr(
                "BackupDialog",
                "Are you sure you want to restore backup '{0}'?\n\n"
                "This will replace your current stats files.\n"
                "A backup will be created automatically before restoring.",
            ).format(backup["name"]),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Start restore worker
        self.worker = BackupWorker(
            "restore", self.backup_manager, backup_path=backup["path"]
        )
        self.worker.progress.connect(self.on_worker_progress)
        self.worker.finished.connect(self.on_worker_finished)

        self.set_ui_busy(True, tr("BackupDialog", "Restoring backup..."))
        self.worker.start()

    def delete_backup(self):
        """Delete selected backup."""
        selected_items = self.backup_list.selectedItems()
        if not selected_items:
            return

        backup = selected_items[0].data(Qt.ItemDataRole.UserRole)
        if not backup:
            return

        # Confirm delete
        reply = QMessageBox.question(
            self,
            tr("BackupDialog", "Confirm Delete"),
            tr(
                "BackupDialog",
                "Are you sure you want to delete backup '{0}'?\n\n"
                "This action cannot be undone.",
            ).format(backup["name"]),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Start delete worker
        self.worker = BackupWorker(
            "delete", self.backup_manager, backup_path=backup["path"]
        )
        self.worker.progress.connect(self.on_worker_progress)
        self.worker.finished.connect(self.on_worker_finished)

        self.set_ui_busy(True, tr("BackupDialog", "Deleting backup..."))
        self.worker.start()

    def on_worker_progress(self, message: str):
        """Handle worker progress updates."""
        self.status_label.setText(message)
        QApplication.processEvents()

    def on_worker_finished(self, success: bool, message: str):
        """Handle worker completion."""
        self.set_ui_busy(False)

        if success:
            QMessageBox.information(self, tr("BackupDialog", "Success"), message)
            self.refresh_backup_list()
        else:
            QMessageBox.critical(self, tr("BackupDialog", "Error"), message)

    def set_ui_busy(self, busy: bool, message: str = ""):
        """Set UI busy state."""
        self.progress_bar.setVisible(busy)
        self.status_label.setText(message)

        # Enable/disable buttons
        self.create_backup_btn.setEnabled(not busy)
        has_selection = bool(self.backup_list.selectedItems())
        self.restore_backup_btn.setEnabled(not busy and has_selection)
        self.delete_backup_btn.setEnabled(not busy and has_selection)

        if busy:
            self.progress_bar.setRange(0, 0)  # Indeterminate progress
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
