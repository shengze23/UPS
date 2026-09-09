from __future__ import annotations

import unittest

from openups.client import MockOpenUPSClient


class MockDeviceTests(unittest.TestCase):
    def test_mock_produces_live_complete_snapshot(self) -> None:
        client = MockOpenUPSClient()
        first = client.poll()
        second = client.poll()
        self.assertTrue(first.connected)
        self.assertTrue(first.protocol_ready)
        self.assertEqual(len(first.cell_voltages), 6)
        self.assertNotEqual(first.vin, second.vin)


if __name__ == "__main__":
    unittest.main()

