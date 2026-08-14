"""Unified concurrency using QThreadPool."""

from typing import Any, Callable, Optional
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
import traceback


class TaskSignals(QObject):
    """Signals for a background task."""

    finished = Signal(object)
    error = Signal(str)
    progress = Signal(int, str)


class BaseTask(QRunnable):
    """A runnable task that executes in a background thread."""

    def __init__(self, fn: Callable, *args: Any, **kwargs: Any):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = TaskSignals()
        self.is_cancelled = False
        self.setAutoDelete(True)

    @Slot()
    def run(self) -> None:
        if self.is_cancelled:
            return
        try:
            import inspect

            kwargs = dict(self.kwargs)
            try:
                sig = inspect.signature(self.fn)
                if "task" in sig.parameters and "task" not in kwargs:
                    kwargs["task"] = self
                elif (
                    "cancel_checker" in sig.parameters
                    and "cancel_checker" not in kwargs
                ):
                    kwargs["cancel_checker"] = lambda: self.is_cancelled
            except (ValueError, TypeError):
                pass

            result = self.fn(*self.args, **kwargs)
            if not self.is_cancelled:
                self.signals.finished.emit(result)
        except Exception as e:
            if not self.is_cancelled:
                self.signals.error.emit(str(e) + "\n" + traceback.format_exc())

    def cancel(self) -> None:
        self.is_cancelled = True


class TaskRunner(QObject):
    """Manages the thread pool and task lifecycle."""

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.pool = QThreadPool.globalInstance()
        self.active_tasks: list[BaseTask] = []

    def submit(self, task: BaseTask) -> None:
        self.active_tasks.append(task)
        task.signals.finished.connect(lambda _: self._remove_task(task))
        task.signals.error.connect(lambda _: self._remove_task(task))
        self.pool.start(task)

    def _remove_task(self, task: BaseTask) -> None:
        if task in self.active_tasks:
            self.active_tasks.remove(task)

    def cancel_all(self) -> None:
        for task in self.active_tasks:
            task.cancel()
