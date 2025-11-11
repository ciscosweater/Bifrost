import logging
import os
from typing import List, Dict, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QMessageBox, QWidget, QFrame, QCheckBox, QTextEdit,
    QSplitter, QGroupBox, QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from ui.enhanced_widgets import EnhancedProgressBar
from ui.interactions import HoverButton, ModernFrame
from ui.theme import theme, Typography, Spacing, BorderRadius
from ui.custom_checkbox import CustomCheckBox
from utils.settings import get_font_setting
from core.game_manager import GameManager


logger = logging.getLogger(__name__)

class GameDeletionWorker(QThread):
    """Worker thread for deleting games without blocking the UI."""
    progress = pyqtSignal(int, str)  # progress, message
    game_deleted = pyqtSignal(str, bool, str)  # game_name, success, message
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)  # error_message
    
    def __init__(self, games_to_delete: List[Dict], delete_compatdata: bool = False):
        super().__init__()
        self.games_to_delete = games_to_delete
        self.delete_compatdata = delete_compatdata
        self._is_running = True
        self._current_game = None
        
        # Initial validation
        if not games_to_delete:
            raise ValueError("No games provided for deletion")
        
        logger.info(f"Starting deletion worker for {len(games_to_delete)} games")
    
    def run(self):
        """Execute game deletion in background with robust error handling."""
        total_games = len(self.games_to_delete)
        successful_deletions = 0
        failed_deletions = 0
        
        try:
            for i, game_info in enumerate(self.games_to_delete):
                if not self._is_running:
                    logger.info("Deletion worker stopped by user")
                    break
                
                # Validate game data before processing
                if not game_info or not isinstance(game_info, dict):
                    error_msg = f"Invalid game data at index {i}"
                    logger.error(error_msg)
                    self.game_deleted.emit("Unknown Game", False, error_msg)
                    failed_deletions += 1
                    continue
                
                game_name = game_info.get('name', 'Unknown Game')
                self._current_game = game_name
                
                # Validate essential fields
                if not game_info.get('appid'):
                    error_msg = f"Missing appid for game: {game_name}"
                    logger.error(error_msg)
                    self.game_deleted.emit(game_name, False, error_msg)
                    failed_deletions += 1
                    continue
                
                try:
                    # Update progress
                    progress_percent = int((i / total_games) * 100)
                    self.progress.emit(progress_percent, f"Deleting {game_name}...")
                    
                    logger.info(f"Deleting game {i+1}/{total_games}: {game_name}")
                    
                    # Delete game with implicit timeout
                    success, message = GameManager.delete_game(game_info, self.delete_compatdata)
                    
                    if success:
                        successful_deletions += 1
                        logger.info(f"Successfully deleted: {game_name}")
                    else:
                        failed_deletions += 1
                        logger.warning(f"Failed to delete {game_name}: {message}")
                    
                    self.game_deleted.emit(game_name, success, message)
                    
                    # Small pause to avoid system overload
                    self.msleep(100)  # 100ms between deletions
                    
                except Exception as e:
                    error_msg = f"Unexpected error deleting {game_name}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    self.game_deleted.emit(game_name, False, error_msg)
                    failed_deletions += 1
                    continue
            
            # Final progress
            self.progress.emit(100, f"Completed! {successful_deletions} successful, {failed_deletions} failed")
            
            # Final log
            logger.info(f"Deletion process completed: {successful_deletions} successful, {failed_deletions} failed")
            
        except Exception as e:
            error_msg = f"Critical error in deletion worker: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
        finally:
            self.finished.emit()
    
    def stop(self):
        """Safely stop the worker execution."""
        logger.info(f"Stopping deletion worker (current game: {self._current_game})")
        self._is_running = False
    
    def get_current_game(self) -> str:
        """Returns the name of the currently processed game."""
        return self._current_game or "None"

class GameDeletionDialog(QDialog):
    """Main dialog for ACCELA game deletion."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.games_list = []
        self.selected_games = []
        self.deletion_worker = None
        
        self.setWindowTitle("Uninstall ACCELA Games")
        self.setModal(True)
        self.setMinimumSize(800, 500)
        self.resize(850, 600)
        
        # Apply modern simplified theme to avoid conflicts
        self.setStyleSheet(f"""
            QDialog {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 {theme.colors.BACKGROUND}, stop:1 {theme.colors.SURFACE});
                border: 2px solid {theme.colors.PRIMARY};
                color: {theme.colors.TEXT_PRIMARY};
                border-radius: 8px;
            }}
            QLabel {{
                color: {theme.colors.TEXT_PRIMARY};
                font-weight: 500;
                padding: 2px;
                border: none;
                background: transparent;
            }}
            QTableWidget {{
                background-color: {theme.colors.BACKGROUND};
                color: {theme.colors.TEXT_PRIMARY};
                border: 1px solid {theme.colors.BORDER};
                gridline-color: {theme.colors.BORDER};
                selection-background-color: {theme.colors.PRIMARY};
                alternate-background-color: {theme.colors.SURFACE};
                {Typography.get_font_style(Typography.BODY_SIZE)};
                outline: none;
            }}
            QTableWidget::item {{
                padding: 8px 4px;
                border-bottom: 1px solid {theme.colors.BORDER};
            }}
            QTableWidget::item:selected {{
                background-color: {theme.colors.PRIMARY};
                color: {theme.colors.TEXT_ON_PRIMARY};
            }}
            QTableWidget::item:hover {{
                background-color: {theme.colors.SURFACE_LIGHT};
            }}
            QHeaderView::section {{
                background-color: {theme.colors.SURFACE};
                color: {theme.colors.TEXT_PRIMARY};
                padding: 6px 4px;
                border: 1px solid {theme.colors.BORDER};
                font-weight: bold;
                {Typography.get_font_style(Typography.CAPTION_SIZE)};
            }}
            QGroupBox {{
                color: {theme.colors.TEXT_PRIMARY};
                border: 1px solid {theme.colors.BORDER};
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 12px;
                font-weight: bold;
                background-color: {theme.colors.SURFACE};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px 0 6px;
                color: {theme.colors.PRIMARY};
            }}
            QTextEdit {{
                background-color: {theme.colors.SURFACE};
                color: {theme.colors.TEXT_PRIMARY};
                border: 1px solid {theme.colors.BORDER};
                padding: 8px;
                font-family: {Typography.get_font_family()};
                {Typography.get_font_style(Typography.CAPTION_SIZE)};
            }}
            QPushButton {{
                background-color: {theme.colors.SURFACE};
                color: {theme.colors.TEXT_PRIMARY};
                border: 1px solid {theme.colors.BORDER};
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                {Typography.get_font_style(Typography.CAPTION_SIZE)};
            }}
            QPushButton:hover {{
                background-color: {theme.colors.PRIMARY};
                color: {theme.colors.TEXT_ON_PRIMARY};
                border-color: {theme.colors.PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {theme.colors.PRIMARY_DARK};
            }}
            QPushButton:disabled {{
                background-color: {theme.colors.SURFACE_LIGHT};
                color: {theme.colors.TEXT_DISABLED};
                border-color: {theme.colors.BORDER};
            }}
        """)
        
        self._setup_ui()
        self._load_games()
    
    def _setup_ui(self):
        """Configura a interface do dialog."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        layout.setSpacing(Spacing.SM)
        
        # Header
        header_frame = self._create_header()
        layout.addWidget(header_frame)
        
        # Main content with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Games table (left)
        table_frame = self._create_games_table()
        splitter.addWidget(table_frame)
        
        # Details panel (right)
        details_frame = self._create_details_panel()
        splitter.addWidget(details_frame)
        
        splitter.setSizes([500, 300])
        
        # Action buttons
        buttons_frame = self._create_action_buttons()
        layout.addWidget(buttons_frame)
        
        # Progress bar (initially hidden)
        self.progress_frame = self._create_progress_frame()
        self.progress_frame.setVisible(False)
        layout.addWidget(self.progress_frame)
    
    def _create_header(self) -> QFrame:
        """Cria o header do dialog."""
        frame = ModernFrame()
        frame.setMaximumHeight(60)  # Altura adequada para header
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
        layout.setSpacing(Spacing.XS)
        
        title = QLabel("ACCELA Game Manager")
        selected_font = get_font_setting("selected_font", "TrixieCyrG-Plain Regular") or "TrixieCyrG-Plain Regular"
        title.setFont(QFont(selected_font, Typography.H3_SIZE, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {theme.colors.TEXT_ACCENT}; margin: 0; border: none; background: transparent;")
        layout.addWidget(title)
        
        subtitle = QLabel("Select and delete games downloaded by ACCELA")
        subtitle.setStyleSheet(f"color: {theme.colors.TEXT_SECONDARY}; {Typography.get_font_style(Typography.BODY_SIZE)}; margin: 0; border: none; background: transparent;")
        layout.addWidget(subtitle)
        
        return frame
    
    def _create_games_table(self) -> QFrame:
        """Cria a tabela de jogos."""
        frame = ModernFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(Spacing.SM, Spacing.XS, Spacing.SM, Spacing.XS)  # Margens adequadas
        layout.setSpacing(Spacing.XS)  # Spacing adequado
        
        # Table header
        header_label = QLabel("Installed Games")
        header_font = get_font_setting("selected_font", "TrixieCyrG-Plain Regular") or "TrixieCyrG-Plain Regular"
        header_label.setFont(QFont(header_font, Typography.BODY_SIZE, QFont.Weight.Bold))
        header_label.setStyleSheet(f"color: {theme.colors.TEXT_ACCENT}; margin: 0; margin-bottom: 6px; border: none; background: transparent;")
        layout.addWidget(header_label)
        
        # Games table
        self.games_table = QTableWidget()
        self.games_table.setColumnCount(4)
        self.games_table.setHorizontalHeaderLabels([
            "Select", "Game Name", "Size", "Location"
        ])
        
        # Configure vertical headers with safety check
        vertical_header = self.games_table.verticalHeader()
        if vertical_header is not None:
            vertical_header.setVisible(False)
            vertical_header.setDefaultSectionSize(40)

        # Configure table
        self.games_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.games_table.setAlternatingRowColors(True)
        self.games_table.setShowGrid(False)
        self.games_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.games_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.games_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.games_table.setMinimumHeight(250)  # Adequate table height
        
        # Configure columns correctly
        header = self.games_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Select
            self.games_table.setColumnWidth(0, 60)  # Largura fixa para checkbox (aumentada)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Game Name
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Size
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Location
            
            # Configurar header vertical
            vertical_header = self.games_table.verticalHeader()
            if vertical_header:
                vertical_header.setVisible(False)
                vertical_header.setDefaultSectionSize(40)  # Altura adequada para linhas
                vertical_header.setMinimumSectionSize(40)
        
        # Estilo da tabela melhorado
        self.games_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {theme.colors.BACKGROUND};
                color: {theme.colors.TEXT_PRIMARY};
                border: 1px solid {theme.colors.BORDER};
                gridline-color: {theme.colors.BORDER};
                selection-background-color: {theme.colors.PRIMARY};
                alternate-background-color: {theme.colors.SURFACE};
                {Typography.get_font_style(Typography.BODY_SIZE)};
                outline: none;
            }}
            QTableWidget::item {{
                padding: 8px 6px;
                border-bottom: 1px solid {theme.colors.BORDER};
                background-color: transparent;
            }}
            QTableWidget::item:selected {{
                background-color: {theme.colors.PRIMARY};
                color: {theme.colors.TEXT_ON_PRIMARY};
            }}
            QTableWidget::item:hover {{
                background-color: {theme.colors.SURFACE_LIGHT};
            }}
            QTableWidget::item:selected:hover {{
                background-color: {theme.colors.PRIMARY_LIGHT};
            }}
            QCheckBox {{
                border: 2px solid {theme.colors.BORDER};
                border-radius: 0px;
                background-color: {theme.colors.BACKGROUND};
                width: 20px;
                height: 20px;
                spacing: 0px;
                padding: 0px;
                margin: 0px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: none;
                background-color: transparent;
                margin: 0px;
                padding: 0px;
            }}
            QCheckBox::indicator:unchecked {{
                border: none;
                background-color: transparent;
            }}
            QCheckBox::indicator:checked {{
                background-color: {theme.colors.PRIMARY};
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEwIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDRMMy41IDdMOSAxIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
            }}
            QHeaderView::section {{
                background-color: {theme.colors.SURFACE};
                color: {theme.colors.TEXT_PRIMARY};
                padding: 10px 8px;
                border: 1px solid {theme.colors.BORDER};
                font-weight: bold;
                {Typography.get_font_style(Typography.BODY_SIZE)};
                text-align: center;
            }}
            QHeaderView::section:first {{
                background-color: {theme.colors.SURFACE};
                border-left: 1px solid {theme.colors.BORDER};
            }}
            QHeaderView::section:last {{
                border-right: 1px solid {theme.colors.BORDER};
            }}
        """)
        
        layout.addWidget(self.games_table)
        
        # Select all/none buttons
        select_layout = QHBoxLayout()
        select_layout.setContentsMargins(0, Spacing.XS, 0, 0)  # Margens adequadas
        select_layout.setSpacing(Spacing.SM)  # Adequate spacing between buttons
        
        self.select_all_btn = HoverButton("Select All")
        self.select_all_btn.clicked.connect(self._select_all_games)
        self.select_all_btn.setFixedHeight(30)  # Fixed height for consistency
        select_layout.addWidget(self.select_all_btn)
        
        self.select_none_btn = HoverButton("Select None")
        self.select_none_btn.clicked.connect(self._select_none_games)
        self.select_none_btn.setFixedHeight(30)  # Fixed height for consistency
        select_layout.addWidget(self.select_none_btn)
        
        select_layout.addStretch()
        layout.addLayout(select_layout)
        
        return frame
    
    def _create_details_panel(self) -> QFrame:
        """Cria o painel de detalhes do jogo selecionado."""
        frame = ModernFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(Spacing.SM, Spacing.XS, Spacing.SM, Spacing.XS)  # Margens adequadas
        layout.setSpacing(Spacing.XS)  # Spacing adequado
        
        # Details title
        details_title = QLabel("Game Details")
        details_font = get_font_setting("selected_font", "TrixieCyrG-Plain Regular") or "TrixieCyrG-Plain Regular"
        details_title.setFont(QFont(details_font, Typography.BODY_SIZE, QFont.Weight.Bold))
        details_title.setStyleSheet(f"color: {theme.colors.TEXT_ACCENT}; margin: 0; margin-bottom: 6px; border: none; background: transparent;")
        layout.addWidget(details_title)
        
        # Game info
        self.game_info_text = QTextEdit()
        self.game_info_text.setReadOnly(True)
        self.game_info_text.setMaximumHeight(140)  # Altura adequada para detalhes
        self.game_info_text.setMinimumHeight(100)  # Minimum height
        layout.addWidget(self.game_info_text)
        
        # Compatdata option
        compatdata_group = QGroupBox("Save Data Options")
        
        compatdata_layout = QVBoxLayout(compatdata_group)
        
        self.delete_compatdata_checkbox = CustomCheckBox("Delete save data (compatdata folder)")
        self.delete_compatdata_checkbox.setChecked(False)  # Default: preserve saves
        self.delete_compatdata_checkbox.setToolTip(
            "Check this box to delete the game's save data and configuration files.\n"
            "The compatdata folder contains:\n"
            "• Game saves and progress\n"
            "• Configuration files\n"
            "• Steam compatibility data\n"
            "\nIf unchecked, this data will be preserved for future use."
        )
        compatdata_layout.addWidget(self.delete_compatdata_checkbox)
        
        # Compatdata info label
        compatdata_info = QLabel("Uncheck to preserve save games in compatdata/APPID/")
        compatdata_info.setStyleSheet(f"color: {theme.colors.TEXT_SECONDARY}; font-style: italic; {Typography.get_font_style(Typography.CAPTION_SIZE)}; padding: {Spacing.XS}px;")
        compatdata_layout.addWidget(compatdata_info)
        
        layout.addWidget(compatdata_group)
        
        # Warning box
        warning_group = QGroupBox("Deletion Warning")
        
        warning_layout = QVBoxLayout(warning_group)
        
        warning_text = QLabel(
            "• This will permanently delete the game and all its files\n"
            "• Save games handling depends on your choice above\n"
            "• This action cannot be undone\n"
            "• Only ACCELA-downloaded games will be shown"
        )
        warning_text.setStyleSheet(f"color: {theme.colors.TEXT_PRIMARY}; padding: {Spacing.XS}px; {Typography.get_font_style(Typography.CAPTION_SIZE)};")
        warning_layout.addWidget(warning_text)
        
        layout.addWidget(warning_group)
        layout.addStretch()
        
        return frame
    
    def _create_action_buttons(self) -> QFrame:
        """Create action buttons."""
        frame = QFrame()
        frame.setMaximumHeight(45)  # Adequate height for buttons
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(Spacing.MD, Spacing.XS, Spacing.MD, Spacing.XS)  # Margens adequadas
        layout.setSpacing(Spacing.MD)  # Adequate spacing between buttons
        
        # Refresh button
        self.refresh_btn = HoverButton("Refresh List")
        self.refresh_btn.clicked.connect(self._load_games)
        self.refresh_btn.setFixedHeight(32)  # Fixed height for consistency
        layout.addWidget(self.refresh_btn)
        
        layout.addStretch()
        
        # Delete button
        self.delete_btn = HoverButton("Delete Selected Games")
        self.delete_btn.clicked.connect(self._start_deletion)
        self.delete_btn.setEnabled(False)
        self.delete_btn.setFixedHeight(32)  # Fixed height for consistency
        layout.addWidget(self.delete_btn)
        
        # Close button
        self.close_btn = HoverButton("Close")
        self.close_btn.clicked.connect(self.close)
        self.close_btn.setFixedHeight(32)  # Fixed height for consistency
        layout.addWidget(self.close_btn)
        
        return frame
    
    def _create_progress_frame(self) -> QFrame:
        """Create deletion progress frame."""
        frame = ModernFrame()
        frame.setMaximumHeight(70)  # Altura adequada para progresso
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)  # Margens adequadas
        layout.setSpacing(Spacing.SM)  # Spacing adequado
        
        # Progress label
        self.progress_label = QLabel("Preparing deletion...")
        self.progress_label.setStyleSheet(f"color: {theme.colors.TEXT_PRIMARY}; {Typography.get_font_style(Typography.BODY_SIZE)};")
        layout.addWidget(self.progress_label)
        
        # Progress bar
        self.progress_bar = EnhancedProgressBar()
        self.progress_bar.setMaximumHeight(18)  # Altura adequada
        layout.addWidget(self.progress_bar)
        
        # Cancel button
        self.cancel_btn = HoverButton("Cancel")
        self.cancel_btn.clicked.connect(self._cancel_deletion)
        self.cancel_btn.setFixedHeight(24)  # Fixed height for consistency
        layout.addWidget(self.cancel_btn)
        
        return frame
    
    def _load_games(self):
        """Carrega a lista de jogos ACCELA."""
        self.games_list = GameManager.scan_accela_games()
        self._populate_games_table()
        self._update_details_panel()
        
        logger.info(f"Loaded {len(self.games_list)} ACCELA games")
    
    def _populate_games_table(self):
        """Popula a tabela com os jogos encontrados."""
        self.games_table.setRowCount(len(self.games_list))
        
        for row, game in enumerate(self.games_list):
            # Standard simple checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(False)
            checkbox.stateChanged.connect(self._on_selection_changed)
            
            # Container simples para centralizar
            checkbox_container = QWidget()
            checkbox_container.setFixedSize(20, 20)
            container_layout = QHBoxLayout(checkbox_container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(0)
            checkbox.setFixedSize(20, 20)
            container_layout.addWidget(checkbox)
            container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            self.games_table.setCellWidget(row, 0, checkbox_container)
            
            # Game name (use display_name)
            name_item = QTableWidgetItem(game['display_name'])
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name_item.setToolTip(f"APPID: {game['appid']}\n{game['name']}\nDirectory: {game.get('installdir', 'N/A')}")  # Tooltip mais completo
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.games_table.setItem(row, 1, name_item)
            
            # Size (simplificado)
            size_text = game.get('size_formatted', 'Unknown')
            size_item = QTableWidgetItem(size_text)
            size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.games_table.setItem(row, 2, size_item)
            
            # Location - show more useful information
            library_path = game['library_path']
            # Tentar mostrar um caminho mais significativo (drive + pasta principal)
            if os.name == 'nt':  # Windows
                # Ex: "C:\Steam" ou "D:\Games\Steam"
                location_display = library_path
            else:  # Linux/Mac
                # Ex: "~/.steam/steam" ou "/home/user/.local/share/Steam"
                home = os.path.expanduser("~")
                if library_path.startswith(home):
                    location_display = library_path.replace(home, "~", 1)
                else:
                    location_display = library_path
            
            # Limit size for display
            if len(location_display) > 40:
                location_display = "..." + location_display[-37:]
            
            location_item = QTableWidgetItem(location_display)
            location_item.setFlags(location_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            location_item.setToolTip(f"Full path: {library_path}")  # Tooltip com path completo
            location_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.games_table.setItem(row, 3, location_item)
        
        # Connect row selection - remove itemSelectionChanged to avoid freezing
        self.games_table.cellClicked.connect(self._on_cell_clicked)
    
    def _on_cell_clicked(self, row: int, column: int):
        """Handle cell clicks - toggle checkbox and update details."""
        if 0 <= row < len(self.games_list):
            # Toggle checkbox if not clicking on checkbox column
            if column != 0:
                checkbox_container = self.games_table.cellWidget(row, 0)
                if checkbox_container:
                    checkbox = checkbox_container.findChild(QCheckBox)
                    if checkbox:
                        checkbox.setChecked(not checkbox.isChecked())
            
            # Update details panel
            self._update_details_panel(self.games_list[row])
    
    # Removido para evitar travamento - usando apenas cellClicked
    # def _on_table_selection_changed(self):
    #     """Handle table selection changes."""
    #     current_row = self.games_table.currentRow()
    #     if 0 <= current_row < len(self.games_list):
    #         self._update_details_panel(self.games_list[current_row])
    
    def _update_details_panel(self, game: Optional[Dict] = None):
        """Update details panel with game information."""
        if not game:
            self.game_info_text.setText("Select a game to view details...")
            return
        
        try:
            # Basic information without calculations that might freeze
            game_dir = game.get('game_dir', '')
            game_dir_exists = os.path.exists(game_dir) if game_dir else False
            
            details = f"""<b>Display Name:</b> {game.get('display_name', 'N/A')}<br>
<b>Original Name:</b> {game.get('name', 'N/A')}<br>
<b>APPID:</b> {game.get('appid', 'N/A')}<br>
<b>Install Directory:</b> {game.get('installdir', 'N/A')}<br>
<b>Size:</b> {game.get('size_formatted', 'N/A')}<br>
<b>Library:</b> {os.path.basename(game.get('library_path', 'N/A'))}<br>
<b>Game Directory:</b> {'Exists' if game_dir_exists else 'Not found'}<br><br>

<b>Files to be deleted:</b><br>
• {os.path.basename(game.get('acf_path', 'N/A'))}<br>
• {game.get('installdir', 'N/A')}/ (entire folder)<br><br>

<b>Save Data (compatdata):</b><br>
• Path: compatdata/{game.get('appid', 'N/A')}/<br>
• Action: Will be deleted if checked<br>
• Tip: Uncheck to preserve save games
"""
            
            self.game_info_text.setText(details)
        except Exception as e:
            logger.error(f"Error updating details panel: {e}")
            self.game_info_text.setText("Error loading game details.")
    
    def _on_selection_changed(self):
        """Update button state when selection changes."""
        selected_games = []
        
        for row in range(self.games_table.rowCount()):
            checkbox_container = self.games_table.cellWidget(row, 0)
            if checkbox_container:
                # Encontrar o checkbox dentro do container
                checkbox = checkbox_container.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    selected_games.append(self.games_list[row])
        
        self.selected_games = selected_games
        self.delete_btn.setEnabled(len(selected_games) > 0)
        self.delete_btn.setText(f"Delete Selected Games ({len(selected_games)})")
    
    def _select_all_games(self):
        """Seleciona todos os jogos."""
        for row in range(self.games_table.rowCount()):
            checkbox_container = self.games_table.cellWidget(row, 0)
            if checkbox_container:
                checkbox = checkbox_container.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(True)
    
    def _select_none_games(self):
        """Deseleciona todos os jogos."""
        for row in range(self.games_table.rowCount()):
            checkbox_container = self.games_table.cellWidget(row, 0)
            if checkbox_container:
                checkbox = checkbox_container.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)
    
    def _start_deletion(self):
        """Start deletion process."""
        if not self.selected_games:
            return
        
        # Confirm deletion
        game_names = [game['name'] for game in self.selected_games]
        # Removed size calculation to avoid freezing
        # total_size = sum(game['size_bytes'] for game in self.selected_games)
        delete_compatdata = self.delete_compatdata_checkbox.isChecked()
        
        # Calculate compatdata size if applicable (removed to avoid freezing)
        # compatdata_size = 0
        compatdata_games = []
        if delete_compatdata:
            for game in self.selected_games:
                compatdata_path = os.path.join(game['library_path'], 'steamapps', 'compatdata', game['appid'])
                if os.path.exists(compatdata_path):
                    # compatdata_size += GameManager._calculate_directory_size(compatdata_path)
                    compatdata_games.append(game['name'])
        
        confirm_msg = QMessageBox(self)
        confirm_msg.setWindowTitle("Confirm Deletion")
        confirm_msg.setIcon(QMessageBox.Icon.Warning)
        
        # Main message based on compatdata option
        if delete_compatdata:
            main_text = f"Are you sure you want to delete {len(self.selected_games)} game(s) INCLUDING SAVE DATA?"
            main_text += f"\n\nWARNING: This will permanently delete all save games and progress!"
        else:
            main_text = f"Are you sure you want to delete {len(self.selected_games)} game(s)?"
            main_text += f"\n\nSave games will be preserved."
        
        confirm_msg.setText(main_text)
        
        # Detailed text (without size calculation to avoid freezing)
        detailed_text = f"Games to delete:\n" + "\n".join(f"• {name}" for name in game_names)
        
        if delete_compatdata and compatdata_games:
            detailed_text += f"\n\nSave data to be deleted:\n" + "\n".join(f"• {name}" for name in compatdata_games)
        
        detailed_text += "\n\nThis action cannot be undone!"
        
        confirm_msg.setDetailedText(detailed_text)
        confirm_msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        confirm_msg.setDefaultButton(QMessageBox.StandardButton.No)
        
        if confirm_msg.exec() != QMessageBox.StandardButton.Yes:
            return
        
        # Start deletion
        self._start_deletion_worker()
    
    def _start_deletion_worker(self):
        """Start background deletion worker."""
        # Esconder elementos da UI normal
        self.games_table.setEnabled(False)
        self.delete_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.progress_frame.setVisible(True)
        
        # Get compatdata option
        delete_compatdata = self.delete_compatdata_checkbox.isChecked()
        
        # Criar e iniciar worker
        self.deletion_worker = GameDeletionWorker(self.selected_games, delete_compatdata)
        self.deletion_worker.progress.connect(self._on_deletion_progress)
        self.deletion_worker.game_deleted.connect(self._on_game_deleted)
        self.deletion_worker.finished.connect(self._on_deletion_finished)
        self.deletion_worker.start()
    
    def _on_deletion_progress(self, progress: int, message: str):
        """Update deletion progress."""
        self.progress_bar.setValue(progress)
        self.progress_label.setText(message)
    
    def _on_game_deleted(self, game_name: str, success: bool, message: str):
        """Handle result of game deletion."""
        if success:
            logger.info(f"Successfully deleted: {game_name}")
        else:
            logger.error(f"Failed to delete {game_name}: {message}")
    
    def _on_deletion_finished(self):
        """Handle end of deletion process."""
        self.deletion_worker = None
        
        # Mostrar resultado
        QMessageBox.information(
            self, 
            "Deletion Complete", 
            "Game deletion process has completed. Check the logs for details."
        )
        
        # Recarregar lista e resetar UI
        self._load_games()
        self.games_table.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.progress_frame.setVisible(False)
        self.progress_bar.setValue(0)
    
    def _cancel_deletion(self):
        """Cancel deletion process."""
        if self.deletion_worker:
            self.deletion_worker.stop()
            self.deletion_worker.wait()
            self.deletion_worker = None
        
        # Resetar UI
        self.games_table.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        self.progress_frame.setVisible(False)
        self.progress_bar.setValue(0)
    
    def closeEvent(self, a0):
        """Trata o evento de fechar o dialog."""
        if self.deletion_worker:
            self._cancel_deletion()
        super().closeEvent(a0)
