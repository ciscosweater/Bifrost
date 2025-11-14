import logging
from utils.logger import get_internationalized_logger

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ui.theme import Spacing, theme

logger = get_internationalized_logger()


class CheckBoxWidget(QWidget):
    """Internal widget for drawing the checkbox"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._checked = False
        self.setFixedSize(20, 20)  # Increased size for better visualization
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        if self._checked != checked:
            self._checked = checked
            self.update()

    def paintEvent(self, a0):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw border
        pen = QPen(QColor(theme.colors.PRIMARY), 2)
        painter.setPen(pen)

        # Draw background
        if self._checked:
            brush = QBrush(QColor(theme.colors.PRIMARY))
            painter.setBrush(brush)
        else:
            brush = QBrush(QColor(theme.colors.BACKGROUND))
            painter.setBrush(brush)

        # Draw rounded rectangle (ajustado para 20x20)
        painter.drawRoundedRect(2, 2, 16, 16, 3, 3)

        # Draw checkmark if checked (ajustado para 20x20)
        if self._checked:
            painter.setPen(QPen(QColor(theme.colors.TEXT_ON_PRIMARY), 2))
            painter.drawLine(6, 10, 8, 12)
            painter.drawLine(8, 12, 13, 7)

        painter.end()


class CustomCheckBox(QWidget):
    """Custom checkbox with guaranteed visible checkmark"""

    stateChanged = pyqtSignal(int)

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._text = text

        # Setup layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.XS)

        # Checkbox
        self.checkbox_widget = CheckBoxWidget()
        layout.addWidget(self.checkbox_widget)

        # Label
        if text:
            self.label = QLabel(text)
            self.label.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(self.label)
        else:
            self.label = None

        layout.addStretch()
        self.setLayout(layout)

        # Ensure minimum size to avoid cutting
        if text:
            # If has text, don't limit size
            self.setMinimumHeight(20)
        else:
            # If no text, fixed size for table
            self.setMinimumSize(20, 20)
            self.setMaximumSize(20, 20)

    def isChecked(self):
        return self.checkbox_widget.isChecked()

    def setChecked(self, checked):
        old_checked = self.checkbox_widget.isChecked()
        self.checkbox_widget.setChecked(checked)
        if old_checked != checked:
            self.stateChanged.emit(1 if checked else 0)

    def mousePressEvent(self, a0):
        if a0 and a0.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self.isChecked())
            a0.accept()
        else:
            super().mousePressEvent(a0)

    def setText(self, text):
        """Update checkbox text"""
        if self.label:
            self.label.setText(text)
        else:
            # Create label if it doesn't exist
            self.label = QLabel(text)
            self.label.setCursor(Qt.CursorShape.PointingHandCursor)
            layout = self.layout()
            if layout:
                layout.addWidget(self.label)
        self._text = text

    def text(self):
        """Get checkbox text"""
        return self._text
