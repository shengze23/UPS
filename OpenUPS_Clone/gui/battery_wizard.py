from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


class BatteryWizardDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Battery Wizard - calculation disabled")
        self.setFixedSize(650, 480)
        root = QVBoxLayout(self)
        content = QHBoxLayout()
        root.addLayout(content, 1)

        form_box = QGroupBox("Battery setup")
        form = QFormLayout(form_box)
        self.chemistry = QComboBox()
        self.chemistry.addItems(("PbSO4", "LiFePO4", "LiPo"))
        self.capacity = QLineEdit("7000")
        self.nominal_voltage = QLineEdit("12.00")
        self.batteries = QLineEdit("2")
        self.measurement = QComboBox()
        self.measurement.addItems(("Individual", "Global"))
        form.addRow("Battery type:", self.chemistry)
        form.addRow("Capacity [mAh]:", self.capacity)
        form.addRow("Nominal voltage [V]:", self.nominal_voltage)
        form.addRow("Batteries / cells:", self.batteries)
        form.addRow("Measuring points:", self.measurement)
        self.result = QPlainTextEdit()
        self.result.setReadOnly(True)
        self.result.setPlainText(
            "CALCULATION NOT VERIFIED\n\n"
            "The manuals document example results but do not provide complete formulas "
            "for every chemistry and topology. Apply remains disabled until calculations "
            "are reproduced from captured legacy behavior and checked against the board."
        )
        form.addRow("Result:", self.result)
        content.addWidget(form_box, 3)

        diagram = QLabel(
            "J4.+\n\n"
            " |\n[ CELL 6 ]\n"
            " |---- J6.5\n"
            "[ CELL 5 ]\n"
            " |---- J6.4\n"
            "  ...\n"
            " |\nJ4.-\n\n"
            "Reference only - verify wiring\nagainst the hardware manual."
        )
        diagram.setStyleSheet("QLabel { background: white; border: 1px solid #aaa; padding: 18px; }")
        diagram.setMinimumWidth(225)
        content.addWidget(diagram, 2)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Apply (disabled)")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

