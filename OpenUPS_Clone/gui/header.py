from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from openups.models import TelemetrySnapshot


def _number(value: float | None, decimals: int = 2) -> str:
    return "---" if value is None else f"{value:.{decimals}f}"


class HeaderWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)

        brand = QFrame()
        brand.setFrameShape(QFrame.Shape.StyledPanel)
        brand_layout = QVBoxLayout(brand)
        brand_layout.setContentsMargins(7, 6, 7, 6)
        self.power_badge = QLabel("USB\nPOWERED")
        self.power_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.power_badge.setStyleSheet(
            "QLabel { background: white; border: 1px solid #aaa; font-weight: 700; color: #222; }"
        )
        self.power_badge.setMinimumSize(90, 70)
        brand_layout.addWidget(self.power_badge)
        layout.addWidget(brand)

        metrics = QWidget()
        metrics_layout = QVBoxLayout(metrics)
        metrics_layout.setContentsMargins(0, 1, 0, 0)
        top = QHBoxLayout()
        top.addStretch(1)
        top.addWidget(QLabel("Capacity:"))
        self.capacity = QLineEdit("---")
        self.capacity.setReadOnly(True)
        self.capacity.setFixedWidth(55)
        top.addWidget(self.capacity)
        top.addWidget(QLabel("%"))
        top.addSpacing(22)
        top.addWidget(QLabel("RTE:"))
        self.rte = QLineEdit("---")
        self.rte.setReadOnly(True)
        self.rte.setFixedWidth(70)
        top.addWidget(self.rte)
        top.addWidget(QLabel("hh:mm"))
        top.addStretch(1)
        metrics_layout.addLayout(top)

        voltage_row = QHBoxLayout()
        voltage_row.setSpacing(7)
        self.vin = self._voltage_group("Voltage IN")
        self.vbat = self._voltage_group("Voltage BAT")
        self.vout = self._voltage_group("Voltage OUT")
        for group, _field in (self.vin, self.vbat, self.vout):
            voltage_row.addWidget(group, 1)
        metrics_layout.addLayout(voltage_row)
        layout.addWidget(metrics, 1)

    @staticmethod
    def _voltage_group(title: str) -> tuple[QGroupBox, QLineEdit]:
        group = QGroupBox(title)
        group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        grid = QGridLayout(group)
        field = QLineEdit("---")
        field.setReadOnly(True)
        field.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(field, 0, 0)
        grid.addWidget(QLabel("[V]"), 0, 1)
        return group, field

    def update_snapshot(self, snapshot: TelemetrySnapshot) -> None:
        source = snapshot.operating_mode.upper().replace(" ", "\n")
        self.power_badge.setText(source if snapshot.connected else "NO DEVICE")
        self.capacity.setText(_number(snapshot.remaining_capacity, 0))
        self.rte.setText(snapshot.runtime_text)
        self.vin[1].setText(_number(snapshot.vin, 3))
        self.vbat[1].setText(_number(snapshot.vbat, 3))
        self.vout[1].setText(_number(snapshot.vout, 3))

