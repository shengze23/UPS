from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from typing import Any


FLAG_NAMES = (
    "charge_low_rate",
    "charge_high_rate",
    "ldo_enabled",
    "power_supply_warning",
    "charge_enabled",
    "vin_enabled",
    "battery_enabled",
    "output_enabled",
    "power_button",
    "battery_led",
    "comparator",
    "over_temperature",
    "good_cell_configuration",
    "should_start_charge",
    "cell_overvoltage",
    "cell_undervoltage",
)


@dataclass(frozen=True, slots=True)
class TelemetrySnapshot:
    connected: bool = False
    protocol_ready: bool = False
    connection_message: str = "Disconnected"
    device_path: str | None = None
    firmware_major: int | None = None
    firmware_minor: int | None = None
    firmware_build: str | None = None
    operating_mode: str = "Unknown"
    vin: float | None = None
    vbat: float | None = None
    vout: float | None = None
    cell_voltages: tuple[float | None, ...] = (None,) * 6
    cell_on: tuple[bool | None, ...] = (None,) * 6
    cell_balancing: tuple[bool | None, ...] = (None,) * 6
    charge_current: float | None = None
    discharge_current: float | None = None
    input_current: float | None = None
    pcb_temperature: float | None = None
    output_power: float | None = None
    ups_state: int | None = None
    charger_state: int | None = None
    output_state: int | None = None
    charge_frequency: float | None = None
    output_frequency: float | None = None
    remaining_capacity: float | None = None
    runtime_to_empty_min: int | None = None
    flags: dict[str, bool | None] = field(
        default_factory=lambda: {name: None for name in FLAG_NAMES}
    )
    raw_debug: str = ""
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def firmware_text(self) -> str:
        if self.firmware_major is None or self.firmware_minor is None:
            return "--"
        text = f"{self.firmware_major}.{self.firmware_minor}"
        return f"{text} {self.firmware_build}" if self.firmware_build else text

    @property
    def runtime_text(self) -> str:
        if self.runtime_to_empty_min is None or self.runtime_to_empty_min > 0xFFFF:
            return "---"
        hours, minutes = divmod(max(0, self.runtime_to_empty_min), 60)
        return f"{hours:02d}:{minutes:02d}"

    def with_values(self, values: dict[str, Any]) -> "TelemetrySnapshot":
        direct: dict[str, Any] = {}
        flags = dict(self.flags)
        cells = list(self.cell_voltages)
        cell_on = list(self.cell_on)
        cell_balancing = list(self.cell_balancing)
        for key, value in values.items():
            if key.startswith("flags."):
                flags[key.removeprefix("flags.")] = bool(value)
            elif key.startswith("cell_voltages."):
                cells[int(key.rsplit(".", 1)[1])] = float(value)
            elif key.startswith("cell_on."):
                cell_on[int(key.rsplit(".", 1)[1])] = bool(value)
            elif key.startswith("cell_balancing."):
                cell_balancing[int(key.rsplit(".", 1)[1])] = bool(value)
            elif key in self.__dataclass_fields__:
                direct[key] = value
        if "ups_state" in direct and "operating_mode" not in direct:
            direct["operating_mode"] = {
                1: "Battery powered",
                2: "Line powered",
                3: "USB powered",
            }.get(int(direct["ups_state"]), "Unknown")
        direct.update(
            flags=flags,
            cell_voltages=tuple(cells),
            cell_on=tuple(cell_on),
            cell_balancing=tuple(cell_balancing),
            captured_at=datetime.now(timezone.utc),
        )
        return replace(self, **direct)

    def as_json_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["captured_at"] = self.captured_at.isoformat()
        return data


def mock_snapshot(step: int = 0) -> TelemetrySnapshot:
    """Return deterministic, visibly changing data for GUI development."""
    phase = (step % 20) / 20.0
    cells = tuple(3.68 + phase * 0.03 + index * 0.004 for index in range(6))
    return TelemetrySnapshot(
        connected=True,
        protocol_ready=True,
        connection_message="Connected (mock device)",
        device_path="mock://openups/vendor-collection",
        firmware_major=1,
        firmware_minor=9,
        firmware_build="beta 2016_07_25",
        operating_mode="Line powered",
        vin=12.18 + phase * 0.08,
        vbat=sum(cells),
        vout=12.02,
        cell_voltages=cells,
        cell_on=(True,) * 6,
        cell_balancing=(False, False, False, False, step % 4 == 0, False),
        charge_current=0.74 + phase * 0.04,
        discharge_current=0.0,
        input_current=1.18,
        pcb_temperature=31.4 + phase,
        output_power=8.6 + phase,
        ups_state=2,
        charger_state=1,
        output_state=1,
        charge_frequency=333.0,
        output_frequency=300.0,
        remaining_capacity=82.0,
        runtime_to_empty_min=174,
        flags={
            name: name
            in {"charge_high_rate", "charge_enabled", "vin_enabled", "output_enabled", "comparator", "good_cell_configuration"}
            for name in FLAG_NAMES
        },
        raw_debug="02 01 01 00",
    )
