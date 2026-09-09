from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from openups.parameters import PARAMETER_BY_NAME, PARAMETERS
from .battery_wizard import BatteryWizardDialog


READ_ONLY_REASON = (
    "Live status is available, but editing is disabled: parameter indices, wire units, "
    "and write command framing for firmware 1.9 are not yet verified."
)


class SettingsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 7, 6, 6)
        wizard_button = QPushButton("Battery wizard")
        wizard_button.clicked.connect(self._show_wizard)
        root.addWidget(wizard_button)

        individual = QGroupBox("Individual parameter setup (read-only)")
        form = QFormLayout(individual)
        self.parameter = QComboBox()
        self.parameter.addItem("Select parameter ...", None)
        for definition in PARAMETERS:
            self.parameter.addItem(definition.name, definition.name)
        self.parameter.currentIndexChanged.connect(self._parameter_changed)
        self.current_value = QLineEdit("---")
        self.current_value.setReadOnly(True)
        self.edited_value = QLineEdit()
        self.edited_value.setEnabled(False)
        self.units = QLabel("[---]")
        value_row = QHBoxLayout()
        value_row.addWidget(self.current_value)
        value_row.addWidget(self.units)
        form.addRow("Parameter:", self.parameter)
        form.addRow("Current value:", value_row)
        form.addRow("Edited value:", self.edited_value)
        self.description = QPlainTextEdit()
        self.description.setReadOnly(True)
        self.description.setMaximumHeight(105)
        form.addRow("Description:", self.description)
        self.change_log = QLineEdit("Read-only phase: no staged changes")
        self.change_log.setReadOnly(True)
        form.addRow("Change log:", self.change_log)
        button_row = QHBoxLayout()
        self.read_button = QPushButton("Read selected parameter")
        self.stage_button = QPushButton("Stage edited parameter")
        for button in (self.read_button, self.stage_button):
            button.setEnabled(False)
            button.setToolTip(READ_ONLY_REASON)
            button_row.addWidget(button)
        form.addRow(button_row)
        self.sync_button = QPushButton("Sync all parameters to the OpenUPS")
        self.sync_button.setEnabled(False)
        self.sync_button.setToolTip(READ_ONLY_REASON)
        form.addRow(self.sync_button)
        root.addWidget(individual)

        transfer = QGroupBox("Configuration transfer")
        transfer_layout = QVBoxLayout(transfer)
        captions = (
            "All parameters: OpenUPS ===> File (settings.ini)",
            "All parameters: File ===> OpenUPS (settings.ini)",
            "Reset OpenUPS (full restart and reload parameters)",
        )
        for caption in captions:
            button = QPushButton(caption)
            button.setEnabled(False)
            button.setToolTip(READ_ONLY_REASON)
            transfer_layout.addWidget(button)
        state_row = QHBoxLayout()
        state_row.addWidget(QLabel("State:"))
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        state_row.addWidget(self.progress, 1)
        self.state = QLabel("READ-ONLY - telemetry only")
        state_row.addWidget(self.state)
        transfer_layout.addLayout(state_row)
        root.addWidget(transfer)
        root.addStretch(1)

    def _parameter_changed(self) -> None:
        name = self.parameter.currentData()
        if not name:
            self.units.setText("[---]")
            self.description.clear()
            return
        definition = PARAMETER_BY_NAME[name]
        self.units.setText(f"[{definition.unit}]")
        self.description.setPlainText(
            f"{definition.description}\n\nDocumented default: {definition.documented_default}.\n\n{READ_ONLY_REASON}"
        )

    def _show_wizard(self) -> None:
        BatteryWizardDialog(self).exec()
