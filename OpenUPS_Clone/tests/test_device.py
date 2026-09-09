from __future__ import annotations

import unittest

from openups.device import (
    DeviceNotFoundError,
    HIDDeviceInfo,
    select_configuration_collection,
)


def device(usage_page: int, usage: int, input_length: int, output_length: int) -> HIDDeviceInfo:
    return HIDDeviceInfo(
        path=f"path-{usage_page:04x}-{usage:04x}",
        vendor_id=0x04D8,
        product_id=0xD004,
        usage_page=usage_page,
        usage=usage,
        input_report_length=input_length,
        output_report_length=output_length,
    )


class DeviceSelectionTests(unittest.TestCase):
    def test_selects_vendor_collection_not_battery_collection(self) -> None:
        battery = device(0x0084, 0x0004, 4, 0)
        vendor = device(0xFF00, 0x0001, 32, 32)
        self.assertEqual(select_configuration_collection([battery, vendor]), vendor)

    def test_rejects_vid_pid_only_match(self) -> None:
        with self.assertRaises(DeviceNotFoundError):
            select_configuration_collection([device(0x0084, 0x0004, 4, 0)])

    def test_rejects_wrong_report_lengths(self) -> None:
        with self.assertRaises(DeviceNotFoundError):
            select_configuration_collection([device(0xFF00, 0x0001, 33, 33)])


if __name__ == "__main__":
    unittest.main()

