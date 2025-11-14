import logging
from utils.logger import get_internationalized_logger
from PyQt6.QtCore import QObject, QThread, pyqtSignal

logger = get_internationalized_logger()

class Worker(QObject):
    """
    A generic worker object that executes a given function in a separate thread.
    It emits signals to communicate results, errors, and completion status
    back to the main thread in a thread-safe manner.
    """
    finished = pyqtSignal(object)
    error = pyqtSignal(tuple)
    completed = pyqtSignal()

    def __init__(self, target_func, *args, **kwargs):
        super().__init__()
        self.target_func = target_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        """
        Executes the target function and handles the outcome.
        """
        func_name = self.target_func.__name__
        logger.debug(f"Worker starting execution of function: '{func_name}'")
        try:
            result = self.target_func(*self.args, **self.kwargs)
            self.finished.emit(result)
            logger.debug(f"Worker finished function '{func_name}' successfully.")
        except Exception as e:
            logger.error(f"An error occurred in worker function '{func_name}': {e}", exc_info=True)
            import traceback
            self.error.emit((type(e), e, traceback.format_exc()))
        finally:
            self.completed.emit()
            logger.debug(f"Worker completed task for function '{func_name}'.")


class TaskRunner:
    """
    Manages the execution of a function in a background QThread.
    This class now prevents its instances from being garbage collected
    while a task is running.
    """
    # --- MODIFICATION START ---
    # Class attribute to hold references to active runner instances.
    _active_runners = []
    # --- MODIFICATION END ---

    def __init__(self):
        self.thread = None
        self.worker = None

    def run(self, target_func, *args, **kwargs):
        """
        Creates and starts a new thread to run the given function.
        """
        self.thread = QThread()
        self.worker = Worker(target_func, *args, **kwargs)
        self.worker.moveToThread(self.thread)

        # Connect signals and slots
        self.thread.started.connect(self.worker.run)
        self.worker.completed.connect(self.thread.quit)
        self.worker.completed.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._cleanup)

        # --- MODIFICATION START ---
        # Connect the cleanup slot to remove the runner from the active list
        # once the task is complete.
        # Note: _cleanup is already connected to thread.finished above
        # --- MODIFICATION END ---

        # Start the thread
        self.thread.start()
        logger.debug(f"Task for function '{target_func.__name__}' has been started in a new thread.")

        # --- MODIFICATION START ---
        # Add this instance to the class-level list to prevent it from
        # being garbage collected while the thread is running.
        TaskRunner._active_runners.append(self)
        # --- MODIFICATION END ---

        return self.worker

    def _cleanup(self):
        """
        A slot that runs on task completion to remove this TaskRunner
        instance from the active list, allowing it to be garbage collected.
        """
        func_name = "unknown"
        if self.worker and hasattr(self.worker, 'target_func'):
            func_name = self.worker.target_func.__name__
        logger.debug(f"Cleaning up TaskRunner instance for '{func_name}'.")
        
        # Ensure thread is properly stopped before cleanup
        if self.thread and self.thread.isRunning():
            logger.warning(f"Thread still running for '{func_name}', forcing quit...")
            self.thread.quit()
            if not self.thread.wait(1000):
                logger.warning(f"Thread did not quit for '{func_name}', terminating...")
                self.thread.terminate()
                self.thread.wait(500)
        
        # Remove from active runners list
        if self in TaskRunner._active_runners:
            TaskRunner._active_runners.remove(self)
        
        # Clear references
        self.thread = None
        self.worker = None
    
    def force_cleanup(self):
        """
        Force cleanup of the TaskRunner and its thread.
        This method should be called when we need to ensure immediate cleanup.
        """
        func_name = "unknown"
        if self.worker and hasattr(self.worker, 'target_func'):
            func_name = self.worker.target_func.__name__
        
        logger.debug(f"Force cleaning up TaskRunner instance for '{func_name}'.")
        
        try:
            # Stop thread if running
            if self.thread and self.thread.isRunning():
                logger.warning(f"Force stopping thread for '{func_name}'...")
                self.thread.quit()
                if not self.thread.wait(1000):
                    logger.warning(f"Thread did not quit gracefully for '{func_name}', terminating...")
                    self.thread.terminate()
                    self.thread.wait(500)
            
            # Remove from active runners
            if self in TaskRunner._active_runners:
                TaskRunner._active_runners.remove(self)
                
        except Exception as e:
            logger.warning(f"Error during force cleanup of TaskRunner: {e}")
        finally:
            # Always clear references
            self.thread = None
            self.worker = None
