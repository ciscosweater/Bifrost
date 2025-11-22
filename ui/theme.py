"""
Bifrost Design System - Centralized styling and design constants
Provides unified color palette, typography, spacing, and component styles
"""

from PyQt6.QtGui import QColor


class Colors:
    """Centralized color palette for Bifrost application"""

    # Primary colors (Steam-inspired theme)
    PRIMARY = "#66C0F4"  # Steam blue accent
    PRIMARY_LIGHT = "#8BD5FF"  # Hover states (lighter)
    PRIMARY_DARK = "#4BA3CF"  # Pressed states
    PRIMARY_VARIANT = "#5AB5E8"  # Alternative primary

    # Secondary colors
    SECONDARY = "#1B2838"  # Steam dark blue
    SECONDARY_LIGHT = "#2A3F54"  # Secondary hover (lighter)
    SECONDARY_DARK = "#0F1A22"  # Secondary pressed

    # Status colors
    SUCCESS = "#A3CF64"  # Success states (Steam green)
    SUCCESS_LIGHT = "#B8D97F"  # Success hover
    SUCCESS_DARK = "#8BB04A"  # Success pressed

    WARNING = "#C0A06C"  # Warning states (keep existing)
    WARNING_LIGHT = "#D0B07C"  # Warning hover
    WARNING_DARK = "#B0905C"  # Warning pressed

    ERROR = "#E84D45"  # Error states (Steam red)
    ERROR_LIGHT = "#FF6B64"  # Error hover
    ERROR_DARK = "#C73632"  # Error pressed

    # Neutral colors
    BACKGROUND = "#1B2838"  # Steam dark blue background
    SURFACE = "#171A21"  # Steam surface color
    SURFACE_LIGHT = "#1E2A38"  # Hover surfaces
    SURFACE_DARK = "#0F141A"  # Dark surfaces

    # Border colors
    BORDER = "#2A3F54"  # Subtle borders
    BORDER_LIGHT = "#3B5368"  # Light borders
    BORDER_DARK = "#1A2B3C"  # Dark borders

    # Text colors
    TEXT_PRIMARY = "#C7D5E0"  # Main text (Steam light blue-gray)
    TEXT_SECONDARY = "#8C9AA8"  # Secondary text
    TEXT_DISABLED = "#5C6B78"  # Disabled text
    TEXT_ON_PRIMARY = "#FFFFFF"  # Text on primary backgrounds
    TEXT_ACCENT = "#66C0F4"  # Accent text (Steam blue)

    # Overlay colors
    OVERLAY = "rgba(27, 40, 56, 0.8)"  # Modal overlay (Steam blue)
    OVERLAY_LIGHT = "rgba(27, 40, 56, 0.6)"  # Light overlay

    # Glassmorphism colors (simplified for PyQt6 compatibility)
    GLASS_SURFACE = "#171A21"
    GLASS_BORDER = "#2A3F54"

    @staticmethod
    def get_qcolor(color_hex: str) -> QColor:
        """Convert hex color to QColor"""
        return QColor(color_hex)


class Typography:
    """Unified typography system"""

    # Font sizes (versão compacta)
    H1_SIZE = 18  # Títulos principais
    H2_SIZE = 14  # Cabeçalhos de seção
    H3_SIZE = 12  # Subtítulos
    BODY_SIZE = 10  # Texto comum
    CAPTION_SIZE = 10  # Legendas / texto pequeno

    # Font weights
    WEIGHT_LIGHT = "light"
    WEIGHT_NORMAL = "normal"
    WEIGHT_BOLD = "bold"

    # Font family
    PRIMARY_FONT = "MotivaSansRegular"
    FALLBACK_FONT = "Arial"

    @staticmethod
    def get_font_style(size: int, weight: str = "normal") -> str:
        """Generate font style string"""
        return f"font-size: {size}px; font-weight: {weight};"

    @staticmethod
    def get_font_family() -> str:
        """Get font family string with fallback"""
        return "Motiva Sans"


class Spacing:
    """Consistent spacing system"""

    XS = 4  # Icon padding, tiny gaps
    SM = 8  # Button padding, small gaps
    MD = 16  # Component spacing
    LG = 24  # Section spacing
    XL = 32  # Page margins
    XXL = 48  # Large section breaks

    @staticmethod
    def get_margin(size: int) -> str:
        """Generate margin string"""
        return f"margin: {size}px;"

    @staticmethod
    def get_padding(size: int, horizontal: int | None = None) -> str:
        """Generate padding string"""
        if horizontal is not None:
            return f"padding: {size}px {horizontal}px;"
        return f"padding: {size}px;"

    @staticmethod
    def get_spacing_all(size: int) -> str:
        """Generate margin and padding string"""
        return f"margin: {size}px; padding: {size}px;"


class BorderRadius:
    """Consistent border radius system"""

    NONE = 0
    SMALL = 0
    MEDIUM = 0
    LARGE = 0
    XLARGE = 0
    ROUND = 0

    @staticmethod
    def get_border_radius(radius: int) -> str:
        """Generate border radius string"""
        return f"border-radius: {radius}px;"


class Shadows:
    """Shadow system for depth"""

    NONE = "none"
    SUBTLE = "0 1px 3px rgba(0, 0, 0, 0.2)"
    MEDIUM = "0 4px 6px rgba(0, 0, 0, 0.3)"
    LARGE = "0 8px 16px rgba(0, 0, 0, 0.4)"
    GLOW = f"0 0 20px {Colors.PRIMARY}40"  # Steam blue glow


class Animations:
    """Animation constants"""

    DURATION_FAST = "0.15s"
    DURATION_NORMAL = "0.2s"
    DURATION_SLOW = "0.3s"

    EASING_EASE = "ease"
    EASING_EASE_IN = "ease-in"
    EASING_EASE_OUT = "ease-out"
    EASING_EASE_IN_OUT = "ease-in-out"


class ComponentStyles:
    """Pre-defined component styles"""

    # Modern card style
    CARD = f"""
        QFrame {{
            background: {Colors.SURFACE};
            border: 1px solid {Colors.GLASS_BORDER};
            {BorderRadius.get_border_radius(BorderRadius.LARGE)};
            {Spacing.get_padding(Spacing.MD)};
        }}
        QFrame:hover {{
            background: {Colors.SURFACE_LIGHT};
            border: 1px solid {Colors.BORDER_LIGHT};
        }}
    """

    # Primary button style
    PRIMARY_BUTTON = f"""
        QPushButton {{
            background: {Colors.PRIMARY};
            border: 1px solid {Colors.PRIMARY_DARK};
            color: {Colors.TEXT_ON_PRIMARY};
            {Typography.get_font_style(Typography.BODY_SIZE, Typography.WEIGHT_BOLD)};
            {Spacing.get_padding(Spacing.SM, Spacing.MD)};
            {BorderRadius.get_border_radius(BorderRadius.MEDIUM)};
        }}
        QPushButton:hover {{
            background: {Colors.PRIMARY_LIGHT};
            border: 1px solid {Colors.PRIMARY};
        }}
        QPushButton:pressed {{
            background: {Colors.PRIMARY_DARK};
            border: 1px solid {Colors.PRIMARY_DARK};
        }}
        QPushButton:disabled {{
            background: {Colors.SURFACE};
            color: {Colors.TEXT_DISABLED};
            border: 1px solid {Colors.BORDER};
        }}
    """

    # Secondary button style
    SECONDARY_BUTTON = f"""
        QPushButton {{
            background: transparent;
            border: 1px solid {Colors.PRIMARY};
            color: {Colors.PRIMARY};
            {Typography.get_font_style(Typography.BODY_SIZE)};
            {Spacing.get_padding(Spacing.SM, Spacing.MD)};
            {BorderRadius.get_border_radius(BorderRadius.MEDIUM)};
        }}
        QPushButton:hover {{
            background: {Colors.PRIMARY};
            color: {Colors.TEXT_ON_PRIMARY};
        }}
        QPushButton:pressed {{
            background: {Colors.PRIMARY_DARK};
            border-color: {Colors.PRIMARY_DARK};
        }}
    """

    # Enhanced progress bar
    PROGRESS_BAR = f"""
        QProgressBar {{
            max-height: 18px;
            border: 1px solid {Colors.BORDER};
            text-align: center;
            color: {Colors.TEXT_PRIMARY};
            {Typography.get_font_style(Typography.CAPTION_SIZE, Typography.WEIGHT_BOLD)};
            background: {Colors.SURFACE};
            {BorderRadius.get_border_radius(BorderRadius.SMALL)};
            {Spacing.get_padding(1)};
        }}
        QProgressBar::chunk {{
            background: {Colors.PRIMARY};
            {BorderRadius.get_border_radius(BorderRadius.SMALL)};
        }}
    """

    # Status indicator
    STATUS_INDICATOR = {
        "ready": f"background: {Colors.SUCCESS}; color: {Colors.TEXT_ON_PRIMARY};",
        "processing": f"background: {Colors.SECONDARY}; color: {Colors.TEXT_ON_PRIMARY};",
        "error": f"background: {Colors.ERROR}; color: {Colors.TEXT_ON_PRIMARY};",
        "warning": f"background: {Colors.WARNING}; color: {Colors.TEXT_ON_PRIMARY};",
    }

    @staticmethod
    def get_status_indicator_style(status: str) -> str:
        """Get status indicator style"""
        status_style = ComponentStyles.STATUS_INDICATOR.get(
            status, ComponentStyles.STATUS_INDICATOR["ready"]
        )
        base_style = f"""
            QLabel {{
                {status_style};
                {BorderRadius.get_border_radius(BorderRadius.LARGE)};
                {Spacing.get_padding(Spacing.XS, Spacing.SM)};
                {Typography.get_font_style(Typography.CAPTION_SIZE)};
            }}
        """
        return base_style


class Theme:
    """Main theme class that combines all design elements"""

    def __init__(self):
        self.colors = Colors()
        self.typography = Typography()
        self.spacing = Spacing()
        self.border_radius = BorderRadius()
        self.shadows = Shadows()
        self.animations = Animations()
        self.components = ComponentStyles()

    def apply_theme_to_app(self, app):
        """Apply theme to QApplication"""
        app.setStyleSheet(f"""
            QMainWindow {{
                background: {Colors.BACKGROUND};
                color: {Colors.TEXT_PRIMARY};
            }}

            QWidget {{
                background: transparent;
                color: {Colors.TEXT_PRIMARY};
            }}

            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-size: {Typography.BODY_SIZE}px;
                font-weight: 400;
            }}

            QLineEdit, QTextEdit {{
                background: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                color: {Colors.TEXT_PRIMARY};
                {BorderRadius.get_border_radius(BorderRadius.MEDIUM)};
                {Spacing.get_padding(Spacing.SM)};
            }}

            QLineEdit:focus, QTextEdit:focus {{
                border: 1px solid {Colors.PRIMARY};
            }}
        """)

    def get_dialog_stylesheet(self) -> str:
        """Get stylesheet for dialogs"""
        return f"""
            QDialog {{
                background: {Colors.BACKGROUND};
                color: {Colors.TEXT_PRIMARY};
                {BorderRadius.get_border_radius(BorderRadius.LARGE)};
            }}

            QFrame {{
                background: {Colors.SURFACE};
                border: 1px solid {Colors.BORDER};
                {BorderRadius.get_border_radius(BorderRadius.MEDIUM)};
            }}

            QPushButton {{
                background: {Colors.SURFACE};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                {BorderRadius.get_border_radius(BorderRadius.MEDIUM)};
                {Spacing.get_padding(Spacing.SM, Spacing.MD)};
                font-weight: bold;
            }}

            QPushButton:hover {{
                background: {Colors.SURFACE_LIGHT};
                border: 1px solid {Colors.PRIMARY};
            }}

            QPushButton:pressed {{
                background: {Colors.SURFACE_DARK};
            }}

            QPushButton:disabled {{
                background: {Colors.SURFACE_DARK};
                color: {Colors.TEXT_DISABLED};
                border: 1px solid {Colors.BORDER_DARK};
            }}
        """


# Global theme instance
theme = Theme()
