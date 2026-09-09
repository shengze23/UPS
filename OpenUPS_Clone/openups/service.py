from __future__ import annotations

import threading
from typing import Callable, Protocol

from .client import disconnected_snapshot
from .models import TelemetrySnapshot


class PollableClient(Protocol):
    def poll(self) -> TelemetrySnapshot: ...

    def close(self) -> None: ...


class PollingLoop:
    """Transport-agnostic poll/reconnect loop, intended to run off the GUI thread."""

    def __init__(
        self,
        client: PollableClient,
        *,
        poll_interval_ms: int = 750,
        reconnect_interval_ms: int = 1500,
        on_snapshot: Callable[[TelemetrySnapshot], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        waiter: Callable[[float], bool] | None = None,
    ) -> None:
        self.client = client
        self.poll_interval_ms = max(250, min(10_000, int(poll_interval_ms)))
        self.reconnect_interval_ms = max(500, min(30_000, int(reconnect_interval_ms)))
        self.on_snapshot = on_snapshot or (lambda _snapshot: None)
        self.on_error = on_error or (lambda _message: None)
        self._stop = threading.Event()
        self._waiter = waiter or self._stop.wait

    def stop(self) -> None:
        self._stop.set()

    def run(self, *, max_cycles: int | None = None) -> None:
        cycles = 0
        try:
            while not self._stop.is_set() and (max_cycles is None or cycles < max_cycles):
                cycles += 1
                try:
                    snapshot = self.client.poll()
                    self.on_snapshot(snapshot)
                    delay_ms = self.poll_interval_ms
                except Exception as exc:
                    try:
                        self.client.close()
                    finally:
                        message = f"Disconnected: {exc}"
                        self.on_error(message)
                        self.on_snapshot(disconnected_snapshot(message))
                    delay_ms = self.reconnect_interval_ms
                if self._waiter(delay_ms / 1000.0):
                    break
        finally:
            self.client.close()

