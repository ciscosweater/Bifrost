"""
Download Session - Data model for download state persistence
"""

import json
import logging
import os

from utils.logger import get_internationalized_logger
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
logger = get_internationalized_logger()


class DownloadState(Enum):
    """Possible states of a download"""

    IDLE = "idle"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class DownloadSession:
    """Stores persistent download state"""

    session_id: str
    game_data: Dict[str, Any]
    selected_depots: List[str]
    current_depot_index: int
    completed_depots: List[str]
    download_state: DownloadState
    timestamp: datetime
    dest_path: str = ""
    total_size: int = 0
    downloaded_size: int = 0
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dictionary"""
        return {
            "session_id": self.session_id,
            "game_data": self.game_data,
            "selected_depots": self.selected_depots,
            "current_depot_index": self.current_depot_index,
            "completed_depots": self.completed_depots,
            "download_state": self.download_state.value,
            "timestamp": self.timestamp.isoformat(),
            "dest_path": self.dest_path,
            "total_size": self.total_size,
            "downloaded_size": self.downloaded_size,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DownloadSession":
        """Create instance from dictionary"""
        return cls(
            session_id=data["session_id"],
            game_data=data["game_data"],
            selected_depots=data["selected_depots"],
            current_depot_index=data["current_depot_index"],
            completed_depots=data["completed_depots"],
            download_state=DownloadState(data["download_state"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            dest_path=data.get("dest_path", ""),
            total_size=data.get("total_size", 0),
            downloaded_size=data.get("downloaded_size", 0),
            error_message=data.get("error_message", ""),
        )

    def save(self):
        """Save session to file"""
        try:
            sessions = DownloadSession.load_all_sessions()
            sessions[self.session_id] = self.to_dict()

            # Ensure directory exists
            os.makedirs("data/sessions", exist_ok=True)

            with open("data/sessions/download_sessions.json", "w") as f:
                json.dump(sessions, f, indent=2)

            logger.debug(f"Session {self.session_id} saved successfully")

        except Exception as e:
            logger.error(f"Failed to save session {self.session_id}: {e}")

    @classmethod
    def load_session(cls, session_id: str) -> Optional["DownloadSession"]:
        """Load specific session"""
        try:
            sessions = cls.load_all_sessions()
            if session_id in sessions:
                return cls.from_dict(sessions[session_id])
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
        return None

    @classmethod
    def load_all_sessions(cls) -> Dict[str, Dict[str, Any]]:
        """Load all sessions"""
        try:
            if os.path.exists("data/sessions/download_sessions.json"):
                with open("data/sessions/download_sessions.json", "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load sessions: {e}")
        return {}

    @classmethod
    def delete_session(cls, session_id: str):
        """Remove saved session"""
        try:
            sessions = cls.load_all_sessions()
            if session_id in sessions:
                del sessions[session_id]

                os.makedirs("data/sessions", exist_ok=True)
                with open("data/sessions/download_sessions.json", "w") as f:
                    json.dump(sessions, f, indent=2)

                logger.debug(f"Session {session_id} deleted")
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")

    @classmethod
    def cleanup_old_sessions(cls, days: int = 7):
        """Remove old sessions (default: 7 days)"""
        try:
            sessions = cls.load_all_sessions()
            cutoff_date = datetime.now().timestamp() - (days * 24 * 3600)

            to_delete = []
            for session_id, session_data in sessions.items():
                session_timestamp = datetime.fromisoformat(
                    session_data["timestamp"]
                ).timestamp()
                if session_timestamp < cutoff_date:
                    to_delete.append(session_id)

            for session_id in to_delete:
                cls.delete_session(session_id)

            if to_delete:
                logger.debug(f"Cleaned up {len(to_delete)} old sessions")

        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {e}")

    def get_progress_percentage(self) -> float:
        """Calcula porcentagem de progresso"""
        if not self.selected_depots:
            return 0.0

        completed = len(self.completed_depots)
        total = len(self.selected_depots)

        if total == 0:
            return 0.0

        return (completed / total) * 100.0

    def get_current_depot(self) -> Optional[str]:
        """Retorna depot atual sendo baixado"""
        if 0 <= self.current_depot_index < len(self.selected_depots):
            return self.selected_depots[self.current_depot_index]
        return None

    def is_completed(self) -> bool:
        """Verifica se download está completo"""
        return self.download_state == DownloadState.COMPLETED and len(
            self.completed_depots
        ) == len(self.selected_depots)

    def can_resume(self) -> bool:
        """Verifica se download pode ser retomado"""
        return self.download_state in [
            DownloadState.PAUSED,
            DownloadState.CANCELLED,
        ] and len(self.completed_depots) < len(self.selected_depots)

    def calculate_total_size(self, depot_sizes: Dict[str, int]) -> int:
        """Calcula tamanho total baseado nos tamanhos dos depots selecionados"""
        total = 0
        for depot_id in self.selected_depots:
            total += depot_sizes.get(depot_id, 0)
        self.total_size = total
        return total

    def get_formatted_size(self, size_bytes: int) -> str:
        """Formata tamanho em bytes para exibição"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def get_summary(self) -> Dict[str, Any]:
        """Retorna resumo da sessão"""
        return {
            "session_id": self.session_id,
            "game_name": self.game_data.get("name", "Unknown"),
            "progress": self.get_progress_percentage(),
            "current_depot": self.get_current_depot(),
            "completed_depots": len(self.completed_depots),
            "total_depots": len(self.selected_depots),
            "state": self.download_state.value,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "can_resume": self.can_resume(),
            "total_size": self.total_size,
            "total_size_formatted": self.get_formatted_size(self.total_size),
            "downloaded_size": self.downloaded_size,
            "downloaded_size_formatted": self.get_formatted_size(self.downloaded_size),
        }
