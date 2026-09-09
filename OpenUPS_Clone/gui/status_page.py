from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from openups.models import FLAG_NAMES, TelemetrySnapshot


FLAG_LABELS = {
    "charge_low_rate": "CHG_LR",
    "charge_high_rate": "CHG_HR",
    "ldo_enabled": "LDO Enable",
    "power_supply_warning": "PSW",
    "charge_enabled": "Enable CHG",
    "vin_enabled": "Enable VIN",
    "battery_enabled": "Enable VBAT",
    "output_enabled": "Enable VOUT",
    "power_button": "Power button",
    "battery_led": "LED Bat",
    "comparator": "Comparator",
    "over_temperature": "OverTemperature",
    "good_cell_configuration": "GoodCellCfg",
    "should_start_charge": "ShouldStartCharge",
    "cell_overvoltage": "Cell overvoltage",
    "cell_undervoltage": "Cell undervoltage",
}


def _display(value: float | int | None, decimals: int = 3) -> str:
    if value is None:
        return "---"
    if isinstance(value, int):
        return f"{value:02X}"
    return f"{value:.{decimals}f}"


class StatusPage(QWidget):
    logging_toggled = Signal(bool, int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 7, 6, 6)
        status_box = QGroupBox("Status")
        root.addWidget(status_box, 1)
        grid = QGridLayout(status_box)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(5, 1)

        grid.addWidget(QLabel(""), 0, 0)
        grid.addWidget(QLabel("On"), 0, 2)
        grid.addWidget(QLabel("Bal"), 0, 3)
        self.cells: list[QLineEdit] = []
        self.cell_on: list[QCheckBox] = []
        self.cell_balancing: list[QCheckBox] = []
        for display_row, cell_index in enumerate(range(5, -1, -1), start=1):
            grid.addWidget(QLabel(f"Cell{cell_index + 1} Voltage:"), display_row, 0)
            field = self._field()
            self.cells.append(field)
            grid.addWidget(field, display_row, 1)
            on = QCheckBox()
            bal = QCheckBox()
            on.setEnabled(False)
            bal.setEnabled(False)
            self.cell_on.append(on)
            self.cell_balancing.append(bal)
            grid.addWidget(on, display_row, 2)
            grid.addWidget(bal, display_row, 3)

        self.flags: dict[str, QCheckBox] = {}
        for index, name in enumerate(FLAG_NAMES):
            checkbox = QCheckBox(FLAG_LABELS[name])
            checkbox.setEnabled(False)
            row = 1 + (index % 8)
            column = 4 + (index // 8) * 2
            grid.addWidget(checkbox, row, column, 1, 2)
            self.flags[name] = checkbox

        self.metric_fields: dict[str, QLineEdit] = {}
        metrics = (
            ("charge_current", "Charge current:", "[A]"),
            ("discharge_current", "Discharge current:", "[A]"),
            ("input_current", "Input current:", "[A]"),
            ("pcb_temperature", "Temperature:", "[deg C]"),
            ("ups_state", "UPS State:", ""),
            ("charger_state", "Charger State:", ""),
            ("output_state", "Out State:", ""),
            ("charge_frequency", "Charge frequency:", "[kHz]"),
            ("output_frequency", "Output frequency:", "[kHz]"),
            ("output_power", "Output power:", "[W]"),
        )
        start_row = 10
        for offset, (name, label, unit) in enumerate(metrics):
            row = start_row + offset
            grid.addWidget(QLabel(label), row, 0)
            field = self._field()
            self.metric_fields[name] = field
            grid.addWidget(field, row, 1)
            grid.addWidget(QLabel(unit), row, 2, 1, 2)

        debug_label = QLabel("Debug:")
        self.debug = self._field()
        grid.addWidget(debug_label, 14, 4)
        grid.addWidget(self.debug, 14, 5, 1, 2)

        log_box = QGroupBox("CSV Log")
        log_layout = QHBoxLayout(log_box)
        self.log_interval = QComboBox()
        for seconds in (1, 2, 5, 10, 30, 60):
            self.log_interval.addItem(str(seconds), seconds)
        log_layout.addWidget(self.log_interval)
        log_layout.addWidget(QLabel("sec"))
        self.log_button = QPushButton("Start")
        self.log_button.setCheckable(True)
        self.log_button.toggled.connect(self._toggle_log)
        log_layout.addWidget(self.log_button)
        grid.addWidget(log_box, 16, 4, 3, 3)
        grid.setRowStretch(19, 1)

    @staticmethod
    def _field() -> QLineEdit:
        field = QLineEdit("---")
        field.setReadOnly(True)
        field.setMaximumWidth(130)
        return field

    def _toggle_log(self, enabled: bool) -> None:
        self.log_button.setText("Stop" if enabled else "Start")
        self.logging_toggled.emit(enabled, int(self.log_interval.currentData()))

    def update_snapshot(self, snapshot: TelemetrySnapshot) -> None:
        # GUI rows are Cell6..Cell1, while the model tuple is Cell1..Cell6.
        for row_index, cell_index in enumerate(range(5, -1, -1)):
            self.cells[row_index].setText(_display(snapshot.cell_voltages[cell_index]))
            self.cell_on[row_index].setChecked(snapshot.cell_on[cell_index] is True)
            self.cell_balancing[row_index].setChecked(snapshot.cell_balancing[cell_index] is True)
        for name, checkbox in self.flags.items():
            checkbox.setChecked(snapshot.flags.get(name) is True)
        for name, field in self.metric_fields.items():
            value = getattr(snapshot, name)
            field.setText(_display(value, 2 if name == "output_power" else 3))
        self.debug.setText(snapshot.raw_debug or "---")

