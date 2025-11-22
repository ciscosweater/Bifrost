"""
from utils.logger import get_internationalized_logger
Application State Manager - Centralized state management for Bifrost
"""
import logging
from enum import Enum
from typing import Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal

logger = get_internationalized_logger()

class AppState(Enum):
    """Application states"""
    IDLE = "idle"
    PROCESSING_ZIP = "processing_zip"
    SELECTING_DEPOTS = "selecting_depots"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    POST_PROCESSING = "post_processing"

class StateManager(QObject):
    """Centralized state management for the application"""
    
    # Signals
    state_changed = pyqtSignal(AppState, AppState)  # old_state, new_state
    download_progress = pyqtSignal(int, str)  # percentage, message
    error_occurred = pyqtSignal(str)  # error_message
    
    def __init__(self):
        super().__init__()
        self._current_state = AppState.IDLE
        self._state_data: Dict[str, Any] = {}
        logger.info("StateManager initialized")
    
    @property
    def current_state(self) -> AppState:
        """Get current application state"""
        return self._current_state
    
    def set_state(self, new_state: AppState, data: Optional[Dict[str, Any]] = None):
        """Change application state with optional data"""
        if new_state == self._current_state:
            logger.debug(f"State already set to {new_state.value}")
            return
            
        old_state = self._current_state
        self._current_state = new_state
        
        # Update state data
        if data:
            self._state_data.update(data)
        
        logger.info(f"State changed: {old_state.value} → {new_state.value}")
        self.state_changed.emit(old_state, new_state)
    
    def get_state_data(self, key: str, default: Any = None) -> Any:
        """Get data associated with current state"""
        return self._state_data.get(key, default)
    
    def set_state_data(self, key: str, value: Any):
        """Set data associated with current state"""
        self._state_data[key] = value
    
    def clear_state_data(self):
        """Clear all state data"""
        self._state_data.clear()
    
    def is_downloading(self) -> bool:
        """Check if currently downloading"""
        return self._current_state in [AppState.DOWNLOADING, AppState.PAUSED]
    
    def can_cancel(self) -> bool:
        """Check if current operation can be cancelled"""
        return self._current_state in [AppState.DOWNLOADING, AppState.POST_PROCESSING]
    
    def can_pause(self) -> bool:
        """Check if download can be paused"""
        return self._current_state == AppState.DOWNLOADING
    
    def can_resume(self) -> bool:
        """Check if download can be resumed"""
        return self._current_state == AppState.PAUSED
    
    def reset_to_idle(self):
        """Reset to idle state and clear data"""
        self.set_state(AppState.IDLE)
        self.clear_state_data()
        logger.info("State reset to idle")