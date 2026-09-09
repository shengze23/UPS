from __future__ import annotations

import argparse
import logging
import sys

from PySide6.QtWidgets import QApplication, QStyleFactory

from gui.main_window import MainWindow
from openups.client import MockOpenUPSClient, OpenUPSClient
from openups.device import WindowsHIDTransport
from openups.standard_hid import StandardHIDOpenUPSClient, StandardHIDTransport
from openups.vendor_telemetry import VendorTelemetryOpenUPSClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Clean-room OpenUPS configuration GUI")
    parser.add_argument("--mock", action="store_true", help="Use deterministic simulated telemetry")
    parser.add_argument(
        "--poll-ms",
        type=int,
        default=750,
        help="Polling interval in milliseconds (250-10000; default: 750)",
    )
    parser.add_argument(
        "--command-profile",
        help="Optional external vendor-collection read profile (advanced)",
    )
    parser.add_argument(
        "--standard-hid",
        action="store_true",
        help="Use the limited col01 Power Device reports instead of native col02 telemetry",
    )
    parser.add_argument("--debug-hid", action="store_true", help="Log exact HID TX/RX bytes")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug_hid else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = QApplication(sys.argv[:1])
    app.setApplicationName("OpenUPS Clone")
    app.setOrganizationName("OpenUPS Clone")
    if "Windows" in QStyleFactory.keys():
        app.setStyle("Windows")
    elif "Fusion" in QStyleFactory.keys():
        app.setStyle("Fusion")
    if args.mock:
        client = MockOpenUPSClient()
    elif args.command_profile:
        client = OpenUPSClient(
            WindowsHIDTransport(debug=args.debug_hid),
            command_profile=args.command_profile,
        )
    elif args.standard_hid:
        client = StandardHIDOpenUPSClient(
            StandardHIDTransport(debug=args.debug_hid),
        )
    else:
        client = VendorTelemetryOpenUPSClient(
            WindowsHIDTransport(debug=args.debug_hid),
        )
    window = MainWindow(
        client,
        poll_interval_ms=max(250, min(10_000, args.poll_ms)),
        mock_mode=args.mock,
    )
    window.show()
    window.start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
