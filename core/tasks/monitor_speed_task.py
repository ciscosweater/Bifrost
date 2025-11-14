import logging
from utils.logger import get_internationalized_logger
import time
import psutil
from PyQt6.QtCore import QObject, pyqtSignal

# Import i18n
try:
    from utils.i18n import tr
except (ImportError, ModuleNotFoundError):

    def tr(context, text):
        return text

logger = get_internationalized_logger()

class SpeedMonitorTask(QObject):
    """
    A dedicated class for the speed monitoring task. This allows it to run
    continuously and emit signals at a regular interval.
    """
    speed_update = pyqtSignal(str)
    
    def __init__(self, interval=1):
        super().__init__()
        self.interval = interval
        self._is_running = True

    def run(self):
        """
        TASK: Periodically checks network I/O to calculate and report download speed.
        Runs in a loop until stopped.
        """
        logger.debug("Speed monitor task starting.")
        try:
            last_bytes = psutil.net_io_counters().bytes_recv
        except Exception as e:
            logger.error(f"Could not initialize psutil for speed monitoring: {e}")
            return

        while self._is_running:
            time.sleep(self.interval)
            if not self._is_running:
                break
            try:
                current_bytes = psutil.net_io_counters().bytes_recv
                speed = (current_bytes - last_bytes) / self.interval
                last_bytes = current_bytes
                self.speed_update.emit(f"{tr('MinimalDownloadWidget', 'Download Speed')}: {self._format_speed(speed)}")
            except Exception as e:
                logger.warning(f"Error during speed update loop: {e}")
                self.stop()

        logger.debug("Speed monitor task finished.")

    def _format_speed(self, speed_bps):
        """Formats bytes per second into a human-readable string."""
        if speed_bps < 1024: return f"{speed_bps:.2f} B/s"
        if speed_bps < 1024**2: return f"{(speed_bps / 1024):.2f} KB/s"
        return f"{(speed_bps / 1024**2):.2f} MB/s"

    def stop(self):
        """Signals the task to stop its loop and exit."""
        logger.debug("Stop signal received by speed monitor.")
        self._is_running = False
