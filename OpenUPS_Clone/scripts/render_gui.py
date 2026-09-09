from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from gui.battery_wizard import BatteryWizardDialog
from gui.main_window import MainWindow
from openups.client import MockOpenUPSClient


def main() -> int:
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "tmp/gui/openups-clone-status.png")
    mode = sys.argv[2] if len(sys.argv) > 2 else "status"
    output.parent.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    window = MainWindow(MockOpenUPSClient(), mock_mode=True)
    window.update_snapshot(MockOpenUPSClient().poll())
    target = window
    if mode == "settings":
        window._select_page(1)
    elif mode == "wizard":
        target = BatteryWizardDialog()
    elif mode != "status":
        raise ValueError("mode must be status, settings, or wizard")
    target.show()

    def capture() -> None:
        pixmap = target.grab()
        if not pixmap.save(str(output)):
            raise RuntimeError(f"Failed to save {output}")
        app.quit()

    QTimer.singleShot(300, capture)
    app.exec()
    print(output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
