from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from .. import version_manager
from ..workers import (
    VersionActivationWorker,
    VersionCatalogWorker,
    VersionDeactivationWorker,
    VersionDeleteWorker,
    VersionDownloadWorker,
)
from ..worker_manager import WorkerTaskRunner


class VersionController(QObject):
    """
    Controller for version management operations: catalog fetching, downloading,
    activation, deactivation, and deletion.
    """

    # Catalog
    catalog_started = Signal()
    catalog_finished = Signal(object)  # tuple of stable/testing releases
    catalog_failed = Signal(str)

    # Download
    download_started = Signal()
    download_progress = Signal(int, int)  # bytes_downloaded, total_bytes
    download_finished = Signal(object)  # Path
    download_cancelled = Signal()
    download_failed = Signal(str)

    # Activation
    activation_started = Signal()
    activation_finished = Signal()
    activation_failed = Signal(str)

    # Deactivation
    deactivation_started = Signal()
    deactivation_finished = Signal()
    deactivation_failed = Signal(str)

    # Deletion
    deletion_started = Signal()
    deletion_finished = Signal(str)  # string representation of the deleted version
    deletion_failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._runner = WorkerTaskRunner(self)
        self._worker = None

    @property
    def is_busy(self) -> bool:
        return self._worker is not None

    def cancel_current_task(self) -> None:
        if isinstance(self._worker, VersionDownloadWorker):
            self._worker.request_cancel()

    # --- Catalog ---

    def start_catalog_fetch(self) -> None:
        if self.is_busy:
            return
        self.catalog_started.emit()
        self._worker = VersionCatalogWorker()
        self._worker.finished.connect(self._on_catalog_finished)
        self._worker.failed.connect(self._on_catalog_failed)
        self._runner.run_worker(self._worker)

    def _on_catalog_finished(
        self,
        catalog: tuple[
            list[version_manager.RuyiRelease], list[version_manager.RuyiRelease]
        ],
    ) -> None:
        self._worker = None
        self.catalog_finished.emit(catalog)

    def _on_catalog_failed(self, error: str) -> None:
        self._worker = None
        self.catalog_failed.emit(error)

    # --- Download ---

    def start_download(
        self,
        release: version_manager.RuyiRelease,
        directory: Path,
        download_url: str,
    ) -> None:
        if self.is_busy:
            return
        self.download_started.emit()
        self._worker = VersionDownloadWorker(release, directory, download_url)
        self._worker.progress.connect(self.download_progress.emit)
        self._worker.cancelled.connect(self._on_download_cancelled)
        self._worker.finished.connect(self._on_download_finished)
        self._worker.failed.connect(self._on_download_failed)
        self._runner.run_worker(self._worker)

    def _on_download_finished(self, path: Path) -> None:
        self._worker = None
        self.download_finished.emit(path)

    def _on_download_cancelled(self) -> None:
        self._worker = None
        self.download_cancelled.emit()

    def _on_download_failed(self, error: str) -> None:
        self._worker = None
        self.download_failed.emit(error)

    # --- Activation ---

    def start_activation(self, release_path: Path, link_path: Path) -> None:
        if self.is_busy:
            return
        self.activation_started.emit()
        self._worker = VersionActivationWorker(release_path, link_path)
        self._worker.finished.connect(self._on_activation_finished)
        self._worker.failed.connect(self._on_activation_failed)
        self._runner.run_worker(self._worker)

    def _on_activation_finished(self) -> None:
        self._worker = None
        self.activation_finished.emit()

    def _on_activation_failed(self, error: str) -> None:
        self._worker = None
        self.activation_failed.emit(error)

    # --- Deactivation ---

    def start_deactivation(self, link_path: Path) -> None:
        if self.is_busy:
            return
        self.deactivation_started.emit()
        self._worker = VersionDeactivationWorker(link_path)
        self._worker.finished.connect(self._on_deactivation_finished)
        self._worker.failed.connect(self._on_deactivation_failed)
        self._runner.run_worker(self._worker)

    def _on_deactivation_finished(self) -> None:
        self._worker = None
        self.deactivation_finished.emit()

    def _on_deactivation_failed(self, error: str) -> None:
        self._worker = None
        self.deactivation_failed.emit(error)

    # --- Deletion ---

    def start_deletion(self, release_path: Path, link_path: Path) -> None:
        if self.is_busy:
            return
        self.deletion_started.emit()
        self._worker = VersionDeleteWorker(release_path, link_path)
        self._worker.finished.connect(self._on_deletion_finished)
        self._worker.failed.connect(self._on_deletion_failed)
        self._runner.run_worker(self._worker)

    def _on_deletion_finished(self, version_str: str) -> None:
        self._worker = None
        self.deletion_finished.emit(version_str)

    def _on_deletion_failed(self, error: str) -> None:
        self._worker = None
        self.deletion_failed.emit(error)
