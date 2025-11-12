import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QResizeEvent
from .theme import theme, Typography, BorderRadius, Spacing

# Import i18n
try:
    from utils.i18n import tr
except (ImportError, ModuleNotFoundError):
    def tr(context, text):
        return text

logger = logging.getLogger(__name__)

class ResponsiveLayout:
    """
    Responsive layout system that adapts to different screen sizes.
    """
    
    def __init__(self, parent_widget):
        self.parent = parent_widget
        self.breakpoints = {
            'mobile': 480,
            'tablet': 768,
            'desktop': 1024,
            'large': 1200
        }
        self.current_size_class = 'desktop'
        self.layouts = {}
        
    def get_size_class(self, width):
        """Determine size class based on width."""
        if width < self.breakpoints['mobile']:
            return 'mobile'
        elif width < self.breakpoints['tablet']:
            return 'tablet'
        elif width < self.breakpoints['desktop']:
            return 'desktop'
        else:
            return 'large'
            
    def update_layout(self, width):
        """Update layout based on screen size."""
        new_size_class = self.get_size_class(width)
        if new_size_class != self.current_size_class:
            self.current_size_class = new_size_class
            self._apply_responsive_changes()
            
    def _apply_responsive_changes(self):
        """Apply responsive changes based on current size class."""
        # Override in subclasses
        pass

class ResponsiveMainWindow(QWidget):
    """
    Main window with responsive design capabilities.
    """
    
    layout_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.responsive_layout = ResponsiveLayout(self)
        self._setup_responsive_ui()
        
    def _setup_responsive_ui(self):
        """Setup responsive UI components."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create responsive containers
        self._create_header()
        self._create_content()
        self._create_footer()
        
    def _create_header(self):
        """Create responsive header."""
        self.header_widget = ResponsiveHeader()
        self.main_layout.addWidget(self.header_widget)
        
    def _create_content(self):
        """Create responsive content area."""
        self.content_widget = ResponsiveContent()
        self.main_layout.addWidget(self.content_widget)
        
    def _create_footer(self):
        """Create responsive footer."""
        self.footer_widget = ResponsiveFooter()
        self.main_layout.addWidget(self.footer_widget)
        
    def resizeEvent(self, a0):
        """Handle resize events for responsive behavior."""
        super().resizeEvent(a0)
        if hasattr(a0, 'size'):
            new_size = a0.size()
            self.responsive_layout.update_layout(new_size.width())
            self.layout_changed.emit(self.responsive_layout.current_size_class)

class ResponsiveHeader(QWidget):
    """
    Responsive header component.
    """
    
    def __init__(self):
        super().__init__()
        self.setFixedHeight(60)
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup header UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title
        self.title_label = QLabel(tr("ResponsiveDesign", "ACCELA"))
        from .theme import theme, Typography
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.PRIMARY};
                {Typography.get_font_style(Typography.H2_SIZE, Typography.WEIGHT_BOLD)};
            }}
        """)
        layout.addWidget(self.title_label)
        
        layout.addStretch()
        
        # Controls (hidden on mobile)
        self.controls_widget = QWidget()
        controls_layout = QHBoxLayout(self.controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add control buttons here
        layout.addWidget(self.controls_widget)
        
    def apply_responsive_style(self, size_class):
        """Apply responsive styling."""
        from .theme import theme, Typography
        if size_class == 'mobile':
            self.title_label.setStyleSheet(f"""
                QLabel {{
                    color: {theme.colors.PRIMARY};
                    {Typography.get_font_style(Typography.H3_SIZE, Typography.WEIGHT_BOLD)};
                }}
            """)
            self.controls_widget.hide()
        else:
            self.title_label.setStyleSheet(f"""
                QLabel {{
                    color: {theme.colors.PRIMARY};
                    {Typography.get_font_style(Typography.H2_SIZE, Typography.WEIGHT_BOLD)};
                }}
            """)
            self.controls_widget.show()

class ResponsiveContent(QWidget):
    """
    Responsive content area with adaptive layout.
    """
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup content UI."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Drop zone area
        self.drop_zone = ResponsiveDropZone()
        self.main_layout.addWidget(self.drop_zone, 3)
        
        # Progress area
        self.progress_area = ResponsiveProgressArea()
        self.main_layout.addWidget(self.progress_area)
        
        # Game info area
        self.game_info = ResponsiveGameInfo()
        self.main_layout.addWidget(self.game_info)
        
        # Log area
        self.log_area = ResponsiveLogArea()
        self.main_layout.addWidget(self.log_area, 1)
        
    def apply_responsive_style(self, size_class):
        """Apply responsive styling."""
        self.drop_zone.apply_responsive_style(size_class)
        self.progress_area.apply_responsive_style(size_class)
        self.game_info.apply_responsive_style(size_class)
        self.log_area.apply_responsive_style(size_class)

class ResponsiveDropZone(QWidget):
    """
    Responsive drop zone for file uploads.
    """
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup drop zone UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Animation area
        self.animation_label = QLabel()
        self.animation_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.animation_label.setMinimumHeight(200)
        layout.addWidget(self.animation_label)
        
        # Text label
        self.text_label = QLabel(tr("ResponsiveDesign", "Drag and Drop ZIP file here"))
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        from .theme import theme, Typography
        self.text_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.PRIMARY};
                {Typography.get_font_style(Typography.H2_SIZE, Typography.WEIGHT_NORMAL)};
            }}
        """)
        layout.addWidget(self.text_label)
        
    def apply_responsive_style(self, size_class):
        """Apply responsive styling."""
        from .theme import theme, Typography
        if size_class == 'mobile':
            self.text_label.setStyleSheet(f"""
                QLabel {{
                    color: {theme.colors.PRIMARY};
                    {Typography.get_font_style(Typography.H3_SIZE, Typography.WEIGHT_NORMAL)};
                }}
            """)
            self.animation_label.setMinimumHeight(150)
        elif size_class == 'tablet':
            self.text_label.setStyleSheet(f"""
                QLabel {{
                    color: {theme.colors.PRIMARY};
                    {Typography.get_font_style(Typography.H3_SIZE + 1, Typography.WEIGHT_NORMAL)};
                }}
            """)
            self.animation_label.setMinimumHeight(175)
        else:  # desktop, large
            self.text_label.setStyleSheet(f"""
                QLabel {{
                    color: {theme.colors.PRIMARY};
                    {Typography.get_font_style(Typography.H2_SIZE, Typography.WEIGHT_NORMAL)};
                }}
            """)
            self.animation_label.setMinimumHeight(200)

class ResponsiveProgressArea(QWidget):
    """
    Responsive progress area.
    """
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup progress area UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # Progress bar
        self.progress_bar = QLabel()  # Placeholder for actual progress bar
        self.progress_bar.setStyleSheet(f"""
            QLabel {{
                background: {theme.colors.SURFACE_DARK};
                border: 1px solid {theme.colors.PRIMARY};
                {BorderRadius.get_border_radius(BorderRadius.MEDIUM)};
                height: 12px;
            }}
        """)
        layout.addWidget(self.progress_bar)
        
        # Speed label
        self.speed_label = QLabel("")
        self.speed_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.speed_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_SECONDARY};
                {Typography.get_font_style(Typography.BODY_SIZE)};
            }}
        """)
        layout.addWidget(self.speed_label)
        
    def apply_responsive_style(self, size_class):
        """Apply responsive styling."""
        if size_class == 'mobile':
            self.speed_label.setStyleSheet(f"""
                QLabel {{
                    color: {theme.colors.TEXT_SECONDARY};
                    {Typography.get_font_style(Typography.CAPTION_SIZE)};
                }}
            """)
        else:
            self.speed_label.setStyleSheet(f"""
                QLabel {{
                    color: {theme.colors.TEXT_SECONDARY};
                    {Typography.get_font_style(Typography.BODY_SIZE)};
                }}
            """)

class ResponsiveGameInfo(QWidget):
    """
    Responsive game information display.
    """
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup game info UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # Game image
        self.game_image = QLabel()
        self.game_image.setFixedSize(184, 69)
        self.game_image.setStyleSheet(f"""
            QLabel {{
                border: 1px solid {theme.colors.PRIMARY};
                {BorderRadius.get_border_radius(BorderRadius.SMALL)};
                background: {theme.colors.SURFACE};
            }}
        """)
        layout.addWidget(self.game_image)
        
        # Game info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(Spacing.XS)
        
        self.game_title = QLabel(tr("ResponsiveDesign", "Game Title"))
        self.game_title.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.PRIMARY};
                {Typography.get_font_style(Typography.H3_SIZE, Typography.WEIGHT_BOLD)};
            }}
        """)
        info_layout.addWidget(self.game_title)
        
        self.game_status = QLabel(tr("ResponsiveDesign", "Status"))
        self.game_status.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_SECONDARY};
                {Typography.get_font_style(Typography.BODY_SIZE)};
            }}
        """)
        info_layout.addWidget(self.game_status)
        
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
    def apply_responsive_style(self, size_class):
        """Apply responsive styling."""
        if size_class == 'mobile':
            self.game_image.setFixedSize(140, 52)
            self.game_title.setStyleSheet(f"""
                QLabel {{
                    color: {theme.colors.PRIMARY};
                    {Typography.get_font_style(Typography.BODY_SIZE, Typography.WEIGHT_BOLD)};
                }}
            """)
            self.game_status.setStyleSheet(f"""
                QLabel {{
                    color: {theme.colors.TEXT_SECONDARY};
                    {Typography.get_font_style(Typography.CAPTION_SIZE)};
                }}
            """)
        else:
            self.game_image.setFixedSize(184, 69)
            self.game_title.setStyleSheet(f"""
                QLabel {{
                    color: {theme.colors.PRIMARY};
                    {Typography.get_font_style(Typography.H3_SIZE, Typography.WEIGHT_BOLD)};
                }}
            """)
            self.game_status.setStyleSheet(f"""
                QLabel {{
                    color: {theme.colors.TEXT_SECONDARY};
                    {Typography.get_font_style(Typography.BODY_SIZE)};
                }}
            """)

class ResponsiveLogArea(QWidget):
    """
    Responsive log display area.
    """
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup log area UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # Log display
        self.log_display = QLabel(tr("ResponsiveDesign", "Log output will appear here..."))
        self.log_display.setStyleSheet(f"""
            QLabel {{
                background: {theme.colors.BACKGROUND};
                border: 1px solid {theme.colors.SURFACE_DARK};
                {BorderRadius.get_border_radius(BorderRadius.SMALL)};
                color: {theme.colors.PRIMARY};
                font-family: {Typography.get_font_family()};
                {Typography.get_font_style(Typography.CAPTION_SIZE)};
                {Spacing.get_padding(Spacing.MD)};
            }}
        """)
        self.log_display.setWordWrap(True)
        layout.addWidget(self.log_display)
        
    def apply_responsive_style(self, size_class):
        """Apply responsive styling."""
        if size_class == 'mobile':
            self.log_display.setStyleSheet(f"""
                QLabel {{
                    background: {theme.colors.BACKGROUND};
                    border: 1px solid {theme.colors.SURFACE_DARK};
                    {BorderRadius.get_border_radius(BorderRadius.SMALL)};
                    color: {theme.colors.PRIMARY};
                    font-family: {Typography.get_font_family()};
                    {Typography.get_font_style(Typography.CAPTION_SIZE - 2)};
                    {Spacing.get_padding(Spacing.SM)};
                }}
            """)
        else:
            self.log_display.setStyleSheet(f"""
                QLabel {{
                    background: {theme.colors.BACKGROUND};
                    border: 1px solid {theme.colors.SURFACE_DARK};
                    {BorderRadius.get_border_radius(BorderRadius.SMALL)};
                    color: {theme.colors.PRIMARY};
                    font-family: {Typography.get_font_family()};
                    {Typography.get_font_style(Typography.CAPTION_SIZE)};
                    {Spacing.get_padding(Spacing.MD)};
                }}
            """)

class ResponsiveFooter(QWidget):
    """
    Responsive footer component.
    """
    
    def __init__(self):
        super().__init__()
        self.setFixedHeight(30)
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup footer UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        
        # Status label
        self.status_label = QLabel(tr("ResponsiveDesign", "Ready"))
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_SECONDARY};
                {Typography.get_font_style(Typography.CAPTION_SIZE + 1)};
            }}
        """)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # Version info
        self.version_label = QLabel(tr("ResponsiveDesign", "v1.0"))
        self.version_label.setStyleSheet(f"""
            QLabel {{
                color: {theme.colors.TEXT_SECONDARY};
                {Typography.get_font_style(Typography.CAPTION_SIZE)};
            }}
        """)
        layout.addWidget(self.version_label)
        
    def apply_responsive_style(self, size_class):
        """Apply responsive styling."""
        if size_class == 'mobile':
            self.version_label.hide()
        else:
            self.version_label.show()