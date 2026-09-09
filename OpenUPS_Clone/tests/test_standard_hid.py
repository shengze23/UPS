from __future__ import annotations

import unittest

from openups.device import HIDDeviceInfo
from openups.standard_hid import StandardHIDOpenUPSClient, thermistor_temperature


class FakeStandardTransport:
    def __init__(self, reports: dict[int, bytes]) -> None:
        self.reports = reports
        self.calls: list[tuple[int, int]] = []
        self._open = False
        self.info = HIDDeviceInfo(
            path=r"\\?\hid#vid_04d8&pid_d004&col01",
            vendor_id=0x04D8,
            product_id=0xD004,
            usage_page=0x0084,
            usage=0x0004,
            input_report_length=4,
            output_report_length=0,
            feature_report_length=13,
        )

    @property
    def is_open(self) -> bool:
        return self._open

    @property
    def device_info(self):
        return self.info if self._open else None

    def open(self):
        self._open = True
        return self.info

    def get_feature_report(self, report_id: int, expected_length: int) -> bytes:
        self.calls.append((report_id, expected_length))
        return self.reports[report_id]

    def close(self) -> None:
        self._open = False


def reports(*, status: int = 0x0002, capacity: int = 50, runtime: int = 3932100):
    return {
        0x20: bytes.fromhex("20 81 05 06 00"),
        0x21: bytes.fromhex("21 01 00 05 00"),
        0x22: bytes.fromhex("22 02 00 00 00"),
        0x23: bytes.fromhex("23 f6 01"),
        0x30: bytes.fromhex("30 63 00 00 00"),
        0x40: bytes([0x40]) + status.to_bytes(2, "little"),
        0x52: bytes([0x52, capacity]),
        0x60: bytes([0x60]) + runtime.to_bytes(3, "little"),
    }


class StandardHIDClientTests(unittest.TestCase):
    def test_decodes_captured_usb_only_reports_without_any_write_api(self) -> None:
        transport = FakeStandardTransport(reports())
        snapshot = StandardHIDOpenUPSClient(transport).poll()

        self.assertTrue(snapshot.connected)
        self.assertTrue(snapshot.protocol_ready)
        self.assertEqual(snapshot.operating_mode, "USB powered")
        self.assertAlmostEqual(snapshot.vin, 0.07090, places=5)
        self.assertAlmostEqual(snapshot.vbat, 0.06, places=5)
        self.assertAlmostEqual(snapshot.vout, 0.02571, places=5)
        self.assertAlmostEqual(snapshot.discharge_current, 0.080565, places=6)
        self.assertAlmostEqual(snapshot.pcb_temperature, 23.97959, places=4)
        self.assertIsNone(snapshot.remaining_capacity)
        self.assertIsNone(snapshot.runtime_to_empty_min)
        self.assertEqual(
            [report_id for report_id, _length in transport.calls],
            [0x20, 0x21, 0x22, 0x23, 0x30, 0x40, 0x52, 0x60],
        )

    def test_battery_status_enables_capacity_and_runtime(self) -> None:
        battery_present_and_discharging = (1 << 15) | (1 << 11)
        snapshot = StandardHIDOpenUPSClient(
            FakeStandardTransport(
                reports(status=battery_present_and_discharging, capacity=73, runtime=3600)
            )
        ).poll()

        self.assertEqual(snapshot.operating_mode, "Battery powered")
        self.assertEqual(snapshot.remaining_capacity, 73.0)
        self.assertEqual(snapshot.runtime_to_empty_min, 60)
        self.assertTrue(snapshot.flags["battery_enabled"])

    def test_thermistor_interpolates_and_rejects_zero(self) -> None:
        self.assertIsNone(thermistor_temperature(0))
        self.assertEqual(thermistor_temperature(0x31), -40.0)
        self.assertEqual(thermistor_temperature(0x200), 25.0)
        self.assertEqual(thermistor_temperature(0x3CC), 125.0)


if __name__ == "__main__":
    unittest.main()
