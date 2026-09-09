from __future__ import annotations

import unittest

from openups.device import DeviceError, HIDDeviceInfo
from openups.vendor_telemetry import (
    POWER_REQUEST,
    STATUS_REQUEST,
    TIME_REQUEST,
    VendorTelemetryOpenUPSClient,
    build_read_request,
    parse_status_response,
    parse_time_response,
)


def status_response(*, line_powered: bool = True) -> bytes:
    report = bytearray(32)
    report[0] = 0x82
    report[1:3] = (400).to_bytes(2, "little")
    report[3:5] = (468).to_bytes(2, "little")
    report[5:7] = (1400).to_bytes(2, "little")
    for index, raw in enumerate((400, 401, 402, 403, 0, 0)):
        offset = 7 + index * 2
        report[offset : offset + 2] = raw.to_bytes(2, "little")
    report[19:21] = (1000).to_bytes(2, "little")
    report[21:23] = (50).to_bytes(2, "little")
    report[24] = 1 << (5 if line_powered else 6)
    report[26:28] = (0x200).to_bytes(2, "little")
    report[31] = 0x19
    return bytes(report)


def power_response() -> bytes:
    report = bytearray(32)
    report[0] = 0x86
    report[1:5] = (8_600_000).to_bytes(4, "little")
    return bytes(report)


def time_response(*, runtime: int = 123) -> bytes:
    report = bytearray(32)
    report[0] = 0x84
    report[2:5] = bytes((0x26, 0x09, 0x05))
    report[6:9] = bytes((0x14, 0x23, 0x45))
    report[12] = 73
    report[16:18] = runtime.to_bytes(2, "little")
    return bytes(report)


class FakeVendorTransport:
    def __init__(self) -> None:
        self._open = False
        self.calls: list[tuple[bytes, int, int]] = []
        self.responses = {
            STATUS_REQUEST: status_response(),
            POWER_REQUEST: power_response(),
            TIME_REQUEST: time_response(),
        }
        self.info = HIDDeviceInfo(
            path=r"\\?\hid#vid_04d8&pid_d004&col02",
            vendor_id=0x04D8,
            product_id=0xD004,
            usage_page=0xFF00,
            usage=0x0001,
            input_report_length=32,
            output_report_length=32,
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

    def transact(self, outbound: bytes, response_length: int, timeout_ms: int) -> bytes:
        self.calls.append((outbound, response_length, timeout_ms))
        return self.responses[outbound[0]]

    def close(self) -> None:
        self._open = False


class VendorTelemetryTests(unittest.TestCase):
    def test_only_three_allowlisted_requests_can_be_built(self) -> None:
        for command in (STATUS_REQUEST, POWER_REQUEST, TIME_REQUEST):
            frame = build_read_request(command)
            self.assertEqual(len(frame), 32)
            self.assertEqual(frame, bytes((command,)) + bytes(31))
        with self.assertRaises(DeviceError):
            build_read_request(0xA3)

    def test_decodes_status_scaling_state_temperature_and_firmware(self) -> None:
        status = parse_status_response(status_response())
        self.assertAlmostEqual(status.vin, 14.18)
        self.assertAlmostEqual(status.vout, 468 * 0.02571)
        self.assertAlmostEqual(status.vbat, 11.998)
        self.assertAlmostEqual(status.cells[0], 3.428)
        self.assertEqual(status.cells[-2:], (0.0, 0.0))
        self.assertAlmostEqual(status.charge_current, 0.8274)
        self.assertAlmostEqual(status.discharge_current, 0.0)
        self.assertAlmostEqual(
            status.input_current,
            50 * 0.016113 + (0.8274 * 11.998) / (14.18 * 0.9),
        )
        self.assertEqual(status.temperature, 25.0)
        self.assertEqual((status.firmware_major, status.firmware_minor), (1, 9))
        self.assertEqual(status.ups_state, 2)

    def test_decodes_time_capacity_and_unknown_runtime(self) -> None:
        parsed = parse_time_response(time_response(runtime=0xFFFF))
        self.assertEqual(parsed.board_time.isoformat(), "2026-09-05T14:23:45")
        self.assertEqual(parsed.remaining_capacity, 73)
        self.assertIsNone(parsed.runtime_to_empty_min)

    def test_invalid_rtc_does_not_discard_capacity(self) -> None:
        report = bytearray(time_response())
        report[3] = 0
        parsed = parse_time_response(bytes(report))
        self.assertIsNone(parsed.board_time)
        self.assertEqual(parsed.remaining_capacity, 73)

    def test_poll_sends_exact_legacy_read_sequence(self) -> None:
        transport = FakeVendorTransport()
        snapshot = VendorTelemetryOpenUPSClient(transport).poll()
        self.assertTrue(snapshot.connected)
        self.assertTrue(snapshot.protocol_ready)
        self.assertEqual(snapshot.firmware_text, "1.9")
        self.assertEqual(snapshot.remaining_capacity, 73.0)
        self.assertEqual(snapshot.runtime_to_empty_min, 123)
        self.assertAlmostEqual(snapshot.output_power, 8.6)
        self.assertEqual([call[0][0] for call in transport.calls], [0x81, 0x85, 0x83])
        self.assertTrue(all(len(call[0]) == 32 for call in transport.calls))
        self.assertTrue(all(call[1] == 32 for call in transport.calls))

    def test_rejects_wrong_or_short_response(self) -> None:
        with self.assertRaises(DeviceError):
            parse_status_response(bytes((0x82, 0x00)))
        with self.assertRaises(DeviceError):
            parse_status_response(bytes((0x84,)) + bytes(31))


if __name__ == "__main__":
    unittest.main()
