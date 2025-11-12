import logging
import os
import sys
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QListWidget, QListWidgetItem, QProgressBar, QTextEdit,
    QFrame, QMessageBox, QSplitter, QWidget, QGroupBox,
    QScrollArea, QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from ui.interactions import ModernFrame, HoverButton, AnimatedLabel
from ui.theme import theme, BorderRadius, Spacing, Typography

# Import BackupManager after path setup  
import importlib.util
backup_manager_path = os.path.join(project_root, "core", "backup_manager.py")
spec = importlib.util.spec_from_file_location("backup_manager", backup_manager_path)
if spec and spec.loader:
    backup_manager_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backup_manager_module)
    BackupManager = backup_manager_module.BackupManager
else:
    raise ImportError("Could not load BackupManager")

logger = logging.getLogger(__name__)


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
                self.progress.emit("Creating backup...")
                backup_path = self.backup_manager.create_backup(self.kwargs.get('backup_name'))
                if backup_path:
                    self.finished.emit(True, f"Backup created: {os.path.basename(backup_path)}")
                else:
                    self.finished.emit(False, "Failed to create backup")
                    
            elif self.operation == "restore":
                self.progress.emit("Restoring backup...")
                success = self.backup_manager.restore_backup(self.kwargs['backup_path'])
                if success:
                    self.finished.emit(True, "Backup restored successfully")
                else:
                    self.finished.emit(False, "Failed to restore backup")
                    
            elif self.operation == "delete":
                self.progress.emit("Deleting backup...")
                success = self.backup_manager.delete_backup(self.kwargs['backup_path'])
                if success:
                    self.finished.emit(True, "Backup deleted successfully")
                else:
                    self.finished.emit(False, "Failed to delete backup")
                    
        except Exception as e:
            logger.error(f"Backup worker error: {e}")
            self.finished.emit(False, f"Error: {str(e)}")


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
        
    def setup_ui(self):
        self.setWindowTitle("Backup/Restore Stats")
        self.setFixedSize(900, 650)
        self.setModal(True)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(Spacing.LG, Spacing.LG, Spacing.LG, Spacing.LG)
        main_layout.setSpacing(Spacing.MD)
        
        # Title
        title_label = QLabel("Steam Stats Backup Manager")
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_ACCENT};
                {Typography.get_font_style(Typography.H2_SIZE)};
                font-weight: bold;
                padding: {Spacing.SM}px 0;
            }}
        """)
        main_layout.addWidget(title_label)
        
        # Status section
        self.setup_status_section(main_layout)
        
        # Main content with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Backup list
        left_panel = QWidget()
        self.setup_backup_list_panel(left_panel.layout() if left_panel.layout() else QVBoxLayout(left_panel))
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
    
    def setup_status_section(self, parent_layout):
        """Setup status information section."""
        status_frame = ModernFrame()
        status_layout = QVBoxLayout(status_frame)
        
        # Steam stats path
        stats_path = self.backup_manager.get_steam_stats_path()
        if stats_path:
            path_label = QLabel(f"Stats Path: {stats_path}")
            path_label.setStyleSheet(f"""
                QLabel {{
                    color: {theme.colors.TEXT_SECONDARY};
                    {Typography.get_font_style(Typography.BODY_SIZE)};
                    padding: {Spacing.XS}px;
                }}
            """)
            status_layout.addWidget(path_label)
            
            # Count files
            files_count = len(self.backup_manager.list_stats_files())
            count_label = QLabel(f"Stats Files: {files_count}")
            count_label.setStyleSheet(f"""
                QLabel {{
                    color: {theme.colors.TEXT_SECONDARY};
                    {Typography.get_font_style(Typography.BODY_SIZE)};
                    padding: {Spacing.XS}px;
                }}
            """)
            status_layout.addWidget(count_label)
        else:
            error_label = QLabel("❌ Steam installation not found or stats directory missing")
            error_label.setStyleSheet(f"""
                QLabel {{
                    color: {theme.colors.ERROR};
                    {Typography.get_font_style(Typography.BODY_SIZE)};
                    font-weight: bold;
                    padding: {Spacing.XS}px;
                }}
            """)
            status_layout.addWidget(error_label)
        
        parent_layout.addWidget(status_frame)
    
    def setup_backup_list_panel(self, parent_layout=None):
        """Setup backup list panel."""
        if parent_layout is None:
            panel = QFrame()
            layout = QVBoxLayout(panel)
        else:
            layout = parent_layout
            panel = None
        
        # Title
        list_title = QLabel("Available Backups")
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
        refresh_btn = HoverButton("Refresh List")
        refresh_btn.clicked.connect(self.refresh_backup_list)
        layout.addWidget(refresh_btn)
        
        return panel if panel else layout.parent()
    
    def setup_actions_panel(self):
        """Setup actions panel."""
        panel = QFrame()
        layout = QVBoxLayout(panel)
        
        # Title
        actions_title = QLabel("Backup Information")
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
        self.backup_info_text.setText("Select a backup to view details")
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
        
        self.create_backup_btn = HoverButton("Create New Backup")
        self.create_backup_btn.clicked.connect(self.create_backup)
        self.create_backup_btn.setMaximumWidth(150)
        actions_layout.addWidget(self.create_backup_btn)
        
        actions_layout.addSpacing(Spacing.MD)
        
        self.restore_backup_btn = HoverButton("Restore")
        self.restore_backup_btn.clicked.connect(self.restore_backup)
        self.restore_backup_btn.setEnabled(False)
        self.restore_backup_btn.setMaximumWidth(80)
        actions_layout.addWidget(self.restore_backup_btn)
        
        self.delete_backup_btn = HoverButton("Delete")
        self.delete_backup_btn.clicked.connect(self.delete_backup)
        self.delete_backup_btn.setEnabled(False)
        self.delete_backup_btn.setMaximumWidth(80)
        actions_layout.addWidget(self.delete_backup_btn)
        
        button_layout.addLayout(actions_layout)
        button_layout.addStretch()
        
        # Right side - close button
        close_btn = HoverButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        parent_layout.addLayout(button_layout)
    
    def refresh_backup_list(self):
        """Refresh the backup list."""
        try:
            self.backup_list.clear()
            backups = self.backup_manager.list_backups()
            
            if not backups:
                item = QListWidgetItem("No backups found")
                item.setData(Qt.ItemDataRole.UserRole, None)
                self.backup_list.addItem(item)
                return
            
            for backup in backups:
                display_name = backup['name']
                if backup['created_date']:
                    display_name += f" ({backup['created_date'].strftime('%Y-%m-%d %H:%M')})"
                display_name += f" - {backup['formatted_size']}"
                
                item = QListWidgetItem(display_name)
                item.setData(Qt.ItemDataRole.UserRole, backup)
                self.backup_list.addItem(item)
                
        except Exception as e:
            logger.error(f"Error refreshing backup list: {e}")
            QMessageBox.critical(self, "Error", f"Failed to refresh backup list: {e}")
    
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
                self.backup_info_text.setText("No backup selected")
        else:
            self.backup_info_text.setText("Select a backup to view details")
    
    def show_backup_info(self, backup: Dict[str, Any]):
        """Show backup information."""
        try:
            info = self.backup_manager.get_backup_info(backup['path'])
            if info:
                # Header information
                info_text = f"Backup Name: {backup['name']}\n"
                info_text += f"Created: {backup['created_date'].strftime('%Y-%m-%d %H:%M:%S') if backup['created_date'] else 'Unknown'}\n"
                info_text += f"File Path: {backup['path']}\n\n"
                
                # Games information
                info_text += "Games Information:\n"
                info_text += "-" * 40 + "\n"
                info_text += f"Total Games: {len(info.get('games', []))}\n"
                info_text += f"ACCELA Games: {len(info.get('accela_games', []))}\n"
                info_text += f"Other Games: {len(info.get('non_accela_games', []))}\n\n"
                
                # List ACCELA games
                if info.get('accela_games'):
                    info_text += "ACCELA Games in Backup:\n"
                    for i, game in enumerate(info['accela_games'], 1):
                        info_text += f"{i:2d}. {game['name']} (ID: {game['app_id']})\n"
                    info_text += "\n"
                
                # List non-ACCELA games if any
                if info.get('non_accela_games'):
                    info_text += "Other Games in Backup:\n"
                    for i, game in enumerate(info['non_accela_games'], 1):
                        info_text += f"{i:2d}. {game['name']} (ID: {game['app_id']})\n"
                    info_text += "\n"
                
                # Size information
                info_text += "Size Information:\n"
                info_text += "-" * 40 + "\n"
                info_text += f"Archive Size: {backup['formatted_size']}\n"
                info_text += f"Uncompressed Size: {self.backup_manager._format_file_size(info['total_size'])}\n"
                if 'compressed_size' in info:
                    info_text += f"Compressed Size: {self.backup_manager._format_file_size(info['compressed_size'])}\n"
                    if info['total_size'] > 0:
                        compression_ratio = (1 - info['compressed_size'] / info['total_size']) * 100
                        info_text += f"Compression Ratio: {compression_ratio:.1f}%\n"
                info_text += f"Total Files: {info['total_files']}\n\n"
                
                # File details
                info_text += "File Details:\n"
                info_text += "-" * 40 + "\n"
                
                for i, file_info in enumerate(info['files'], 1):
                    info_text += f"{i:2d}. {file_info['name']}\n"
                    info_text += f"    Game: {file_info.get('game_name', 'Unknown')}\n"
                    info_text += f"    Type: {file_info['type']}\n"
                    info_text += f"    Original Size: {self.backup_manager._format_file_size(file_info['size'])}\n"
                    if 'compressed_size' in file_info:
                        info_text += f"    Compressed Size: {self.backup_manager._format_file_size(file_info['compressed_size'])}\n"
                        if file_info['size'] > 0:
                            file_compression = (1 - file_info['compressed_size'] / file_info['size']) * 100
                            info_text += f"    Compression: {file_compression:.1f}%\n"
                    info_text += "\n"
                
                # Additional information
                info_text += "Additional Information:\n"
                info_text += "-" * 40 + "\n"
                info_text += f"Backup Directory: {os.path.dirname(backup['path'])}\n"
                
                # File type summary
                schema_files = [f for f in info['files'] if f['type'] == 'Schema']
                stats_files = [f for f in info['files'] if f['type'] == 'Stats']
                info_text += f"Schema Files: {len(schema_files)}\n"
                info_text += f"Stats Files: {len(stats_files)}\n"
                
                self.backup_info_text.setText(info_text)
            else:
                info_text = f"Backup Name: {backup['name']}\n"
                info_text += f"Created: {backup['created_date'].strftime('%Y-%m-%d %H:%M:%S') if backup['created_date'] else 'Unknown'}\n"
                info_text += f"Archive Size: {backup['formatted_size']}\n"
                info_text += f"File Path: {backup['path']}\n\n"
                info_text += "Unable to read detailed backup information"
                self.backup_info_text.setText(info_text)
                
        except Exception as e:
            logger.error(f"Error showing backup info: {e}")
            self.backup_info_text.setText(f"Error loading backup info: {e}")
    
    def create_backup(self):
        """Create a new backup."""
        if self.worker and self.worker.isRunning():
            return
        
        # Check if Steam stats path exists
        if not self.backup_manager.get_steam_stats_path():
            QMessageBox.critical(self, "Error", "Steam stats directory not found. Please ensure Steam is installed and has been run at least once.")
            return
        
        # Check if there are files to backup
        files = self.backup_manager.list_stats_files()
        if not files:
            QMessageBox.warning(self, "Warning", "No stats files found to backup. This is normal if you haven't played any games yet.")
            return
        
        # Start backup worker
        self.worker = BackupWorker("create", self.backup_manager)
        self.worker.progress.connect(self.on_worker_progress)
        self.worker.finished.connect(self.on_worker_finished)
        
        self.set_ui_busy(True, "Creating backup...")
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
            "Confirm Restore",
            f"Are you sure you want to restore backup '{backup['name']}'?\n\n"
            "This will replace your current stats files.\n"
            "A backup will be created automatically before restoring.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Start restore worker
        self.worker = BackupWorker("restore", self.backup_manager, backup_path=backup['path'])
        self.worker.progress.connect(self.on_worker_progress)
        self.worker.finished.connect(self.on_worker_finished)
        
        self.set_ui_busy(True, "Restoring backup...")
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
            "Confirm Delete",
            f"Are you sure you want to delete backup '{backup['name']}'?\n\n"
            "This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Start delete worker
        self.worker = BackupWorker("delete", self.backup_manager, backup_path=backup['path'])
        self.worker.progress.connect(self.on_worker_progress)
        self.worker.finished.connect(self.on_worker_finished)
        
        self.set_ui_busy(True, "Deleting backup...")
        self.worker.start()
    
    def on_worker_progress(self, message: str):
        """Handle worker progress updates."""
        self.status_label.setText(message)
        QApplication.processEvents()
    
    def on_worker_finished(self, success: bool, message: str):
        """Handle worker completion."""
        self.set_ui_busy(False)
        
        if success:
            QMessageBox.information(self, "Success", message)
            self.refresh_backup_list()
        else:
            QMessageBox.critical(self, "Error", message)
    
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