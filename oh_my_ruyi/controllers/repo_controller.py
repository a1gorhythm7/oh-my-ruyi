from __future__ import annotations

import os
import signal
import sys

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal, QTimer
from ruyi.config import GlobalConfig
from ruyi.ruyipkg.composite_repo import CompositeRepo

from ..i18n import apply_qprocess_locale, _
from ..rich_output import RICH_TERMINAL_ENV, strip_terminal_controls
from ..workers import RepoInitWorker, RepoSyncWorker
from ..worker_manager import WorkerTaskRunner


class RepoController(QObject):
    """
    Controller for repository operations: init, sync, update, and news.
    Encapsulates QThread workers and QProcess executions.
    """

    # Init Signals
    init_started = Signal()
    init_finished = Signal(object)  # CompositeRepo
    init_failed = Signal(str)

    # Sync Signals
    sync_started = Signal()
    sync_finished = Signal(object)  # CompositeRepo
    sync_failed = Signal(str)

    # Update Signals
    update_started = Signal(str)
    update_output = Signal(bytes)
    update_finished = Signal(bool, str, str)  # success, message, details

    # News Signals
    news_started = Signal(str)
    news_output = Signal(bytes)
    news_finished = Signal(bool, str, str)  # success, message, details

    def __init__(self, parent=None):
        super().__init__(parent)
        self._runner = WorkerTaskRunner(self)
        self._worker = None

        # Update process
        self._update_process: QProcess | None = None
        self._update_cancel_requested = False
        self._update_output = bytearray()

        # News process
        self._news_process: QProcess | None = None
        self._news_cancel_requested = False
        self._news_output = bytearray()

        # Process kill timer
        self._kill_timer = QTimer(self)
        self._kill_timer.setSingleShot(True)
        self._kill_timer.setInterval(2000)
        self._kill_timer.timeout.connect(self._force_kill_processes)

    @property
    def is_busy(self) -> bool:
        return (
            self._worker is not None
            or self._update_process is not None
            or self._news_process is not None
        )

    # --- Workers (Init & Sync) ---

    def start_repo_init(self, config: GlobalConfig) -> None:
        if self.is_busy:
            return
        self.init_started.emit()
        self._worker = RepoInitWorker(config)
        self._worker.finished.connect(self._on_init_finished)
        self._worker.failed.connect(self._on_init_failed)
        self._runner.run_worker(self._worker)

    def _on_init_finished(self, mr: CompositeRepo) -> None:
        self._worker = None
        self.init_finished.emit(mr)

    def _on_init_failed(self, error: str) -> None:
        self._worker = None
        self.init_failed.emit(error)

    def start_repo_sync(self, config: GlobalConfig, mr: CompositeRepo) -> None:
        if self.is_busy:
            return
        self.sync_started.emit()
        self._worker = RepoSyncWorker(config, mr)
        self._worker.finished.connect(self._on_sync_finished)
        self._worker.failed.connect(self._on_sync_failed)
        self._runner.run_worker(self._worker)

    def _on_sync_finished(self, mr: CompositeRepo) -> None:
        self._worker = None
        self.sync_finished.emit(mr)

    def _on_sync_failed(self, error: str) -> None:
        self._worker = None
        self.sync_failed.emit(error)

    # --- QProcess (Update) ---

    def start_update(self, config_path: str, repo_id: str) -> bool:
        if self.is_busy:
            return False

        self._update_cancel_requested = False
        self._update_output.clear()

        process = QProcess(self)
        self._update_process = process
        process.setProgram(sys.executable)
        process.setArguments(
            [
                "-m",
                "oh_my_ruyi.repo_update_child",
                os.fspath(config_path),
                repo_id,
            ]
        )
        self._setup_process_env(process)

        process.readyReadStandardOutput.connect(self._read_update_output)
        process.finished.connect(
            lambda code, status, p=process: self._on_update_finished(p, code, status)
        )
        process.errorOccurred.connect(
            lambda error, p=process: self._on_update_error(p, error)
        )

        self.update_started.emit(repo_id)
        process.start()
        return True

    def _read_update_output(self) -> None:
        if self._update_process is None:
            return
        data = bytes(self._update_process.readAllStandardOutput())
        self._update_output.extend(data)
        self.update_output.emit(data)

    def _on_update_finished(self, process: QProcess, code: int, _status) -> None:
        if process != self._update_process:
            process.deleteLater()
            return
        self._kill_timer.stop()
        self._read_update_output()
        self._update_process = None
        process.deleteLater()

        if self._update_cancel_requested:
            self.update_finished.emit(False, _("Repository update cancelled."), "")
            return

        if code != 0:
            output = strip_terminal_controls(
                bytes(self._update_output).decode(errors="replace")
            ).strip()
            self.update_finished.emit(
                False,
                _("Repository update failed (exit code {code}).", code=code),
                output,
            )
            return

        self.update_finished.emit(True, "", "")

    def _on_update_error(self, process: QProcess, error: QProcess.ProcessError) -> None:
        if process != self._update_process:
            return
        if error == QProcess.ProcessError.FailedToStart:
            self.update_finished.emit(
                False, _("Failed to start the repository update process."), ""
            )

    def cancel_update(self) -> None:
        process = self._update_process
        if process is None or self._update_cancel_requested:
            return
        self._update_cancel_requested = True
        self._terminate_process(process)

    # --- QProcess (News) ---

    def start_news_action(self, config_path: str, repo_id: str, action: str) -> bool:
        if self.is_busy:
            return False

        self._news_cancel_requested = False
        self._news_output.clear()

        process = QProcess(self)
        self._news_process = process
        process.setProgram(sys.executable)
        process.setArguments(
            [
                "-m",
                "oh_my_ruyi.repo_news_child",
                os.fspath(config_path),
                repo_id,
                action,
            ]
        )
        self._setup_process_env(process)

        process.readyReadStandardOutput.connect(self._read_news_output)
        process.finished.connect(
            lambda code, status, p=process: self._on_news_finished(p, code, status)
        )
        process.errorOccurred.connect(
            lambda error, p=process: self._on_news_error(p, error)
        )

        self.news_started.emit(action)
        process.start()
        return True

    def _read_news_output(self) -> None:
        if self._news_process is None:
            return
        data = bytes(self._news_process.readAllStandardOutput())
        self._news_output.extend(data)
        self.news_output.emit(data)

    def _on_news_finished(self, process: QProcess, code: int, _status) -> None:
        if process != self._news_process:
            process.deleteLater()
            return
        self._kill_timer.stop()
        self._read_news_output()
        self._news_process = None
        process.deleteLater()

        if self._news_cancel_requested:
            self.news_finished.emit(False, _("Action cancelled."), "")
            return

        if code != 0:
            output = strip_terminal_controls(
                bytes(self._news_output).decode(errors="replace")
            ).strip()
            self.news_finished.emit(
                False,
                _("Action failed (exit code {code}).", code=code),
                output,
            )
            return

        self.news_finished.emit(True, "", "")

    def _on_news_error(self, process: QProcess, error: QProcess.ProcessError) -> None:
        if process != self._news_process:
            return
        if error == QProcess.ProcessError.FailedToStart:
            self.news_finished.emit(False, _("Failed to start the news process."), "")

    def cancel_news(self) -> None:
        process = self._news_process
        if process is None or self._news_cancel_requested:
            return
        self._news_cancel_requested = True
        self._terminate_process(process)

    # --- Helpers ---

    def _setup_process_env(self, process: QProcess) -> None:
        env = QProcessEnvironment.systemEnvironment()
        apply_qprocess_locale(env)
        env.remove("NO_COLOR")
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("RUYI_TELEMETRY_OPTOUT", "1")
        for key, value in RICH_TERMINAL_ENV.items():
            env.insert(key, value)
        process.setProcessEnvironment(env)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

    def _terminate_process(self, process: QProcess) -> None:
        pid = process.processId()
        if pid > 0 and hasattr(os, "killpg"):
            try:
                os.killpg(pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                process.terminate()
        else:
            process.terminate()
        self._kill_timer.start()

    def _force_kill_processes(self) -> None:
        for process in (self._update_process, self._news_process):
            if (
                process is not None
                and process.state() != QProcess.ProcessState.NotRunning
            ):
                process.kill()
