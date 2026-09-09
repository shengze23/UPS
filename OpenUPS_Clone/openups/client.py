from __future__ import annotations

from dataclasses import replace
import logging
from pathlib import Path

from .device import HIDTransport, WindowsHIDTransport
from .models import TelemetrySnapshot, mock_snapshot
from .protocol import CommandProfile, apply_responses


LOGGER = logging.getLogger(__name__)


class OpenUPSClient:
    def __init__(
        self,
        transport: HIDTransport | None = None,
        *,
        command_profile: CommandProfile | str | Path | None = None,
        timeout_ms: int = 350,
    ) -> None:
        self.transport = transport or WindowsHIDTransport()
        if isinstance(command_profile, (str, Path)):
            command_profile = CommandProfile.load(command_profile)
        elif command_profile is not None:
            command_profile.validate()
        self.command_profile = command_profile
        self.timeout_ms = timeout_ms

    @property
    def is_connected(self) -> bool:
        return self.transport.is_open

    def connect(self) -> None:
        if not self.transport.is_open:
            self.transport.open()

    def poll(self) -> TelemetrySnapshot:
        self.connect()
        info = self.transport.device_info
        base = TelemetrySnapshot(
            connected=True,
            protocol_ready=False,
            connection_message="Connected - telemetry profile not loaded",
            device_path=info.path if info else None,
            operating_mode="Unknown",
        )
        if self.command_profile is None:
            return base
        pairs = []
        for request in self.command_profile.requests:
            response = self.transport.transact(
                request.tx,
                response_length=request.response_length,
                timeout_ms=self.timeout_ms,
            )
            pairs.append((request, response))
        return apply_responses(base, pairs)

    def close(self) -> None:
        self.transport.close()


class MockOpenUPSClient:
    def __init__(self) -> None:
        self._connected = False
        self._step = 0

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        self._connected = True

    def poll(self) -> TelemetrySnapshot:
        self.connect()
        snapshot = mock_snapshot(self._step)
        self._step += 1
        return snapshot

    def close(self) -> None:
        self._connected = False


def disconnected_snapshot(message: str) -> TelemetrySnapshot:
    return replace(TelemetrySnapshot(), connection_message=message)
