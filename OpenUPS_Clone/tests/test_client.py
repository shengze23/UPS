from __future__ import annotations

import unittest

from openups.client import OpenUPSClient
from openups.device import HIDDeviceInfo
from openups.protocol import CommandProfile, FieldSpec, ReadRequest


class RecordingTransport:
    def __init__(self) -> None:
        self._open = False
        self.transactions = []
        self.info = HIDDeviceInfo(
            path="test-path",
            vendor_id=0x04D8,
            product_id=0xD004,
            usage_page=0xFF00,
            usage=0x0001,
            input_report_length=32,
            output_report_length=32,
        )

    @property
    def is_open(self):
        return self._open

    @property
    def device_info(self):
        return self.info if self._open else None

    def enumerate(self):
        return [self.info]

    def open(self):
        self._open = True
        return self.info

    def transact(self, outbound, response_length, timeout_ms):
        self.transactions.append((outbound, response_length, timeout_ms))
        response = bytearray(response_length)
        response[0:2] = (1234).to_bytes(2, "little")
        return bytes(response)

    def close(self):
        self._open = False


class ClientTests(unittest.TestCase):
    def test_no_profile_opens_collection_but_transmits_nothing(self) -> None:
        transport = RecordingTransport()
        snapshot = OpenUPSClient(transport).poll()
        self.assertTrue(snapshot.connected)
        self.assertFalse(snapshot.protocol_ready)
        self.assertEqual(transport.transactions, [])

    def test_verified_profile_frame_is_passed_through_exactly(self) -> None:
        transport = RecordingTransport()
        profile = CommandProfile(
            profile_name="test capture",
            source="unit-test working script",
            read_only=True,
            requests=(
                ReadRequest(
                    name="status",
                    tx=b"\x00\xa1\x02",
                    response_length=32,
                    fields=(FieldSpec("vin", "u16le", 0, 0.01),),
                ),
            ),
        )
        profile.validate()
        snapshot = OpenUPSClient(transport, command_profile=profile).poll()
        self.assertEqual(transport.transactions[0][0], b"\x00\xa1\x02")
        self.assertAlmostEqual(snapshot.vin, 12.34)
        self.assertTrue(snapshot.protocol_ready)


if __name__ == "__main__":
    unittest.main()

