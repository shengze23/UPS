from __future__ import annotations

import unittest

from openups.hid_descriptor import decode_report, parse_report_descriptor


# Application collection, report ID 1, one 16-bit feature value with usage
# Power Device:Voltage and exponent -2.
DESCRIPTOR = bytes.fromhex(
    "05 84 09 04 A1 01 "
    "85 01 09 30 15 00 26 FF 7F 35 00 46 FF 7F 55 0E "
    "75 10 95 01 B1 02 C0"
)


class DescriptorParserTests(unittest.TestCase):
    def test_parses_feature_field_and_collection_path(self) -> None:
        parsed = parse_report_descriptor(DESCRIPTOR)
        self.assertEqual(parsed.report_ids("feature"), (1,))
        field = parsed.fields_for("feature", 1)[0]
        self.assertEqual((field.usage.page, field.usage.usage), (0x84, 0x30))
        self.assertEqual(field.collection_path[0].usage, 0x04)
        self.assertEqual(field.bit_size, 16)
        self.assertEqual(field.unit_exponent, -2)
        self.assertEqual(parsed.expected_length("feature", 1), 3)

    def test_decodes_little_endian_value_and_exponent(self) -> None:
        parsed = parse_report_descriptor(DESCRIPTOR)
        values = decode_report(parsed, "feature", 1, b"\x01\xd2\x04")
        self.assertEqual(values[0].raw_value, 1234)
        self.assertAlmostEqual(values[0].scaled_value, 12.34)


if __name__ == "__main__":
    unittest.main()

