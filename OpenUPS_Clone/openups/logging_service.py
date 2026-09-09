from __future__ import annotations

import csv
from pathlib import Path
from threading import Lock

from .models import TelemetrySnapshot


CSV_COLUMNS = (
    "timestamp",
    "ups_state",
    "vin_v",
    "vout_v",
    "charger_state",
    "vbat_v",
    "charge_current_a",
    "discharge_current_a",
    "input_current_a",
    "cell1_v",
    "cell2_v",
    "cell3_v",
    "cell4_v",
    "cell5_v",
    "cell6_v",
    "temperature_c",
    "capacity_percent",
    "rte_minutes",
    "output_power_w",
)


class CsvTelemetryLogger:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = Lock()

    def append(self, snapshot: TelemetrySnapshot) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        row = [
            snapshot.captured_at.isoformat(),
            snapshot.ups_state,
            snapshot.vin,
            snapshot.vout,
            snapshot.charger_state,
            snapshot.vbat,
            snapshot.charge_current,
            snapshot.discharge_current,
            snapshot.input_current,
            *snapshot.cell_voltages,
            snapshot.pcb_temperature,
            snapshot.remaining_capacity,
            snapshot.runtime_to_empty_min,
            snapshot.output_power,
        ]
        with self._lock:
            create_header = not self.path.exists() or self.path.stat().st_size == 0
            with self.path.open("a", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                if create_header:
                    writer.writerow(CSV_COLUMNS)
                writer.writerow(row)

