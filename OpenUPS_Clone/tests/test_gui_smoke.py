from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication

    from gui.main_window import MainWindow
    from openups.client import MockOpenUPSClient
except ImportError:
    QApplication = None


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
class GuiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_mock_snapshot_populates_gui_and_writes_stay_disabled(self) -> None:
        client = MockOpenUPSClient()
        window = MainWindow(client, mock_mode=True)
        window.update_snapshot(client.poll())
        self.assertIn("Connected", window.windowTitle())
        self.assertEqual(window.header.vin[1].text(), "12.180")
        self.assertFalse(window.settings_page.sync_button.isEnabled())
        window.close()


if __name__ == "__main__":
    unittest.main()

