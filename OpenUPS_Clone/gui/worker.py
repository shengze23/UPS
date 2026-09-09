from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from openups.models import TelemetrySnapshot
from openups.service import PollableClient, PollingLoop


class DeviceWorker(QThread):
    snapshot_ready = Signal(object)
    error = Signal(str)

    def __init__(self, client: PollableClient, poll_interval_ms: int, parent=None) -> None:
        super().__init__(parent)
        self.loop = PollingLoop(
            client,
            poll_interval_ms=poll_interval_ms,
            on_snapshot=self._emit_snapshot,
            on_error=self.error.emit,
        )

    def _emit_snapshot(self, snapshot: TelemetrySnapshot) -> None:
        self.snapshot_ready.emit(snapshot)

    def run(self) -> None:
        self.loop.run()

    def stop(self) -> None:
        self.loop.stop()
        self.wait(2000)

