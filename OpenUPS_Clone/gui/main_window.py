from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from openups.logging_service import CsvTelemetryLogger
from openups.models import TelemetrySnapshot
from openups.service import PollableClient
from .header import HeaderWidget
from .settings_page import SettingsPage
from .status_page import StatusPage
from .styles import LEGACY_QSS
from .worker import DeviceWorker


class MainWindow(QMainWindow):
    def __init__(
        self,
        client: PollableClient,
        *,
        poll_interval_ms: int = 750,
        mock_mode: bool = False,
    ) -> None:
        super().__init__()
        self.mock_mode = mock_mode
        self.setWindowTitle("OpenUPS Disconnected")
        self.setFixedSize(790, 835)
        self.setStyleSheet(LEGACY_QSS)
        self._last_snapshot = TelemetrySnapshot()
        self._csv_logger: CsvTelemetryLogger | None = None
        self._log_interval_seconds = 1
        self._last_logged_at: datetime | None = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 8, 10, 9)
        root.setSpacing(6)
        self.header = HeaderWidget()
        root.addWidget(self.header)

        nav = QHBoxLayout()
        nav.setSpacing(5)
        self.status_button = QPushButton("Status")
        self.settings_button = QPushButton("Settings")
        self.minimize_button = QPushButton("Minimize")
        for button in (self.status_button, self.settings_button):
            button.setCheckable(True)
            nav.addWidget(button, 1)
        nav.addWidget(self.minimize_button, 1)
        root.addLayout(nav)

        self.stack = QStackedWidget()
        self.status_page = StatusPage()
        self.settings_page = SettingsPage()
        self.stack.addWidget(self.status_page)
        self.stack.addWidget(self.settings_page)
        root.addWidget(self.stack, 1)

        footer = QHBoxLayout()
        self.connection_label = QLabel("Disconnected - searching for OpenUPS HID device")
        self.connection_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        footer.addWidget(self.connection_label, 1)
        self.poll_label = QLabel(f"Poll: {poll_interval_ms} ms")
        footer.addWidget(self.poll_label)
        root.addLayout(footer)

        self.status_button.clicked.connect(lambda: self._select_page(0))
        self.settings_button.clicked.connect(lambda: self._select_page(1))
        self.minimize_button.clicked.connect(self.showMinimized)
        self.status_page.logging_toggled.connect(self._set_logging)
        self._select_page(0)

        self.worker = DeviceWorker(client, poll_interval_ms, self)
        self.worker.snapshot_ready.connect(self.update_snapshot)
        self.worker.error.connect(self._show_error)

    def start(self) -> None:
        self.worker.start()

    def _select_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        self.status_button.setChecked(index == 0)
        self.settings_button.setChecked(index == 1)

    def update_snapshot(self, snapshot: TelemetrySnapshot) -> None:
        self._last_snapshot = snapshot
        self.header.update_snapshot(snapshot)
        self.status_page.update_snapshot(snapshot)
        self.connection_label.setText(snapshot.connection_message)
        if snapshot.connected:
            suffix = " [MOCK]" if self.mock_mode else ""
            title = f"OpenUPS Connected  v{snapshot.firmware_text}  {snapshot.operating_mode}{suffix}"
        else:
            title = "OpenUPS Disconnected"
        self.setWindowTitle(title)
        self._log_if_due(snapshot)

    def _show_error(self, message: str) -> None:
        self.connection_label.setText(message)

    def _set_logging(self, enabled: bool, interval_seconds: int) -> None:
        if not enabled:
            self._csv_logger = None
            self._last_logged_at = None
            return
        default_path = str(Path.cwd() / "upslog.csv")
        path, _filter = QFileDialog.getSaveFileName(
            self,
            "Save OpenUPS telemetry log",
            default_path,
            "CSV files (*.csv)",
        )
        if not path:
            self.status_page.log_button.blockSignals(True)
            self.status_page.log_button.setChecked(False)
            self.status_page.log_button.setText("Start")
            self.status_page.log_button.blockSignals(False)
            return
        self._csv_logger = CsvTelemetryLogger(path)
        self._log_interval_seconds = interval_seconds
        self._last_logged_at = None
        self._log_if_due(self._last_snapshot)

    def _log_if_due(self, snapshot: TelemetrySnapshot) -> None:
        if self._csv_logger is None or not snapshot.connected or not snapshot.protocol_ready:
            return
        now = datetime.now(timezone.utc)
        if self._last_logged_at is not None:
            elapsed = (now - self._last_logged_at).total_seconds()
            if elapsed < self._log_interval_seconds:
                return
        self._csv_logger.append(snapshot)
        self._last_logged_at = now

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API name
        self.worker.stop()
        super().closeEvent(event)
