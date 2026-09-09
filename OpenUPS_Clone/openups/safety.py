from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Callable, Mapping, Protocol


class WriteSafetyError(RuntimeError):
    pass


class ConfigurationAdapter(Protocol):
    def read_all(self) -> Mapping[str, float]: ...

    def write_values(self, changes: Mapping[str, float]) -> None: ...


@dataclass(frozen=True, slots=True)
class Change:
    name: str
    old_value: float
    new_value: float


@dataclass(frozen=True, slots=True)
class WriteResult:
    backup_path: Path
    changes: tuple[Change, ...]
    verified: bool


class SafeWriteCoordinator:
    """Reusable backup/diff/confirmation/readback pipeline.

    Production construction keeps allow_hardware_writes=False. This pipeline is
    unit-tested against a mock adapter but is not connected to GUI controls.
    """

    def __init__(self, *, allow_hardware_writes: bool = False, tolerance: float = 1e-6) -> None:
        self.allow_hardware_writes = allow_hardware_writes
        self.tolerance = tolerance

    def apply(
        self,
        adapter: ConfigurationAdapter,
        requested: Mapping[str, float],
        backup_directory: str | Path,
        confirm: Callable[[tuple[Change, ...]], bool],
        validate: Callable[[Mapping[str, float]], list[str]] | None = None,
    ) -> WriteResult:
        if not self.allow_hardware_writes:
            raise WriteSafetyError("Hardware writes are disabled in this read-only build")
        if not requested:
            raise WriteSafetyError("No configuration changes were requested")
        current = {name: float(value) for name, value in adapter.read_all().items()}
        backup_directory = Path(backup_directory)
        backup_directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        backup_path = backup_directory / f"openups-config-{stamp}.json"
        backup_path.write_text(
            json.dumps({"captured_at": stamp, "parameters": current}, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        missing = sorted(set(requested) - set(current))
        if missing:
            raise WriteSafetyError(f"Cannot change unknown parameters: {', '.join(missing)}")
        validation_errors = validate(requested) if validate is not None else []
        if validation_errors:
            raise WriteSafetyError("Validation failed: " + "; ".join(validation_errors))
        changes = tuple(
            Change(name, current[name], float(new_value))
            for name, new_value in sorted(requested.items())
            if abs(current[name] - float(new_value)) > self.tolerance
        )
        if not changes:
            raise WriteSafetyError("Requested configuration already matches the device")
        if not confirm(changes):
            raise WriteSafetyError("Write cancelled before any device data changed")
        try:
            adapter.write_values({change.name: change.new_value for change in changes})
        except Exception as exc:
            raise WriteSafetyError(
                f"Write failed after backup {backup_path}; device may be partially updated: {exc}"
            ) from exc
        observed = adapter.read_all()
        failed = [
            change.name
            for change in changes
            if change.name not in observed
            or abs(float(observed[change.name]) - change.new_value) > self.tolerance
        ]
        if failed:
            raise WriteSafetyError(
                "Readback verification failed for: " + ", ".join(sorted(failed))
            )
        return WriteResult(backup_path=backup_path, changes=changes, verified=True)
