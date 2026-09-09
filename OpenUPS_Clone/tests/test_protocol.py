from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from openups.models import TelemetrySnapshot
from openups.protocol import (
    CommandProfile,
    FieldSpec,
    ProtocolError,
    ReadRequest,
    apply_responses,
    decode_fields,
    parse_hex_frame,
)


class ProtocolTests(unittest.TestCase):
    def test_hex_frame_is_exact_and_not_padded(self) -> None:
        self.assertEqual(parse_hex_frame("00 A1 02"), b"\x00\xa1\x02")

    def test_decode_scaling_and_flag_bit(self) -> None:
        payload = bytes((0xD2, 0x04, 0b00010000))
        values = decode_fields(
            payload,
            (
                FieldSpec("vin", "u16le", 0, 0.01),
                FieldSpec("flags.output_enabled", "u8", 2, bit=4),
            ),
        )
        self.assertAlmostEqual(values["vin"], 12.34)
        self.assertTrue(values["flags.output_enabled"])

    def test_short_packet_is_rejected(self) -> None:
        request = ReadRequest("status", b"\x00\x01", 4, ())
        with self.assertRaisesRegex(ProtocolError, "short response"):
            apply_responses(TelemetrySnapshot(connected=True), [(request, b"\x00\x01")])

    def test_out_of_bounds_field_is_rejected(self) -> None:
        with self.assertRaisesRegex(ProtocolError, "outside"):
            decode_fields(b"\x00", (FieldSpec("vin", "u16le", 0),))

    def test_profile_must_be_explicitly_read_only(self) -> None:
        data = {
            "profile_name": "captured reads",
            "source": "user working script",
            "read_only": False,
            "requests": [{"name": "x", "tx_hex": "00", "fields": []}],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ProtocolError, "read_only"):
                CommandProfile.load(path)


if __name__ == "__main__":
    unittest.main()

