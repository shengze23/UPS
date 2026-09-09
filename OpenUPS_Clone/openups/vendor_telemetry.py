"""Native Windows 11 telemetry over the OpenUPS vendor HID collection.

The three request IDs and response layouts in this module were recovered from
the supplied 2014 ``OpenUPSLib.dll``.  They are the library's periodic status
queries; no parameter-write, reset, bootloader, or firmware command is present
here.  HID still uses an OUT report to ask for data, so "read-only" describes
the command semantics rather than the USB transfer direction.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .device import DeviceError, HIDDeviceInfo, WindowsHIDTransport
from .models import FLAG_NAMES, TelemetrySnapshot
from .standard_hid import thermistor_temperature


REPORT_LENGTH = 32

STATUS_REQUEST = 0x81
STATUS_RESPONSE = 0x82
TIME_REQUEST = 0x83
TIME_RESPONSE = 0x84
POWER_REQUEST = 0x85
POWER_RESPONSE = 0x86

# This is intentionally a closed allow-list.  Configuration commands recovered
# elsewhere in the legacy binary are not accepted by this module.
READ_ONLY_REQUESTS = frozenset((STATUS_REQUEST, TIME_REQUEST, POWER_REQUEST))

VIN_VOLTS_PER_COUNT = 0.03545
VOUT_VOLTS_PER_COUNT = 0.02571
VBAT_VOLTS_PER_COUNT = 0.00857
CHARGE_AMPS_PER_COUNT = 0.0008274
DISCHARGE_AMPS_PER_COUNT = 0.016113
INPUT_CONVERSION_EFFICIENCY = 0.9


class VendorTelemetryTransport(Protocol):
    @property
    def is_open(self) -> bool: ...

    @property
    def device_info(self) -> HIDDeviceInfo | None: ...

    def open(self) -> HIDDeviceInfo: ...

    def transact(self, outbound: bytes, response_length: int, timeout_ms: int) -> bytes: ...

    def close(self) -> None: ...


def _u16(report: bytes, offset: int) -> int:
    return int.from_bytes(report[offset : offset + 2], "little", signed=False)


def _u32(report: bytes, offset: int) -> int:
    return int.from_bytes(report[offset : offset + 4], "little", signed=False)


def _bcd(value: int, field: str) -> int:
    high, low = value >> 4, value & 0x0F
    if high > 9 or low > 9:
        raise DeviceError(f"Invalid BCD {field} byte 0x{value:02X}")
    return high * 10 + low


def build_read_request(command: int) -> bytes:
    """Build one exact 32-byte legacy polling request."""
    if command not in READ_ONLY_REQUESTS:
        raise DeviceError(f"Command 0x{command:02X} is not an approved read-only request")
    return bytes((command,)) + bytes(REPORT_LENGTH - 1)


def validate_response(report: bytes, expected_id: int) -> bytes:
    if len(report) != REPORT_LENGTH:
        raise DeviceError(
            f"Short/invalid response 0x{expected_id:02X}: "
            f"received {len(report)} bytes, expected {REPORT_LENGTH}"
        )
    if report[0] != expected_id:
        raise DeviceError(
            f"Wrong response ID: expected 0x{expected_id:02X}, got 0x{report[0]:02X}"
        )
    return report


@dataclass(frozen=True, slots=True)
class VendorStatus:
    vin: float
    vout: float
    vbat: float
    cells: tuple[float, ...]
    charge_current: float
    discharge_current: float
    input_current: float
    temperature: float | None
    firmware_major: int
    firmware_minor: int
    ups_state: int
    operating_mode: str
    status_bytes: tuple[int, int, int]


def parse_status_response(report: bytes) -> VendorStatus:
    report = validate_response(report, STATUS_RESPONSE)
    vin = _u16(report, 1) * VIN_VOLTS_PER_COUNT
    vout = _u16(report, 3) * VOUT_VOLTS_PER_COUNT
    vbat = _u16(report, 5) * VBAT_VOLTS_PER_COUNT
    cells = tuple(_u16(report, offset) * VBAT_VOLTS_PER_COUNT for offset in range(7, 19, 2))
    charge_current = _u16(report, 19) * CHARGE_AMPS_PER_COUNT
    load_current = _u16(report, 21) * DISCHARGE_AMPS_PER_COUNT

    status_bytes = (report[23], report[24], report[25])
    # OpenUPSLib.dll checks these two exact bits in this order.
    battery_powered = bool(report[24] & (1 << 6))
    line_powered = bool(report[24] & (1 << 5))
    if battery_powered:
        ups_state = 1
        operating_mode = "Battery powered"
        discharge_current = load_current
        input_current = 0.0
    elif line_powered:
        ups_state = 2
        operating_mode = "Line powered"
        discharge_current = 0.0
        charge_input = (
            (charge_current * vbat) / (vin * INPUT_CONVERSION_EFFICIENCY)
            if vin > 0.0
            else 0.0
        )
        input_current = load_current + charge_input
    else:
        ups_state = 3
        operating_mode = "USB powered"
        discharge_current = 0.0
        input_current = 0.0

    firmware = report[31]
    return VendorStatus(
        vin=vin,
        vout=vout,
        vbat=vbat,
        cells=cells,
        charge_current=charge_current,
        discharge_current=discharge_current,
        input_current=input_current,
        temperature=thermistor_temperature(_u16(report, 26)),
        firmware_major=firmware >> 4,
        firmware_minor=firmware & 0x0F,
        ups_state=ups_state,
        operating_mode=operating_mode,
        status_bytes=status_bytes,
    )


@dataclass(frozen=True, slots=True)
class VendorTime:
    board_time: datetime | None
    remaining_capacity: int
    runtime_to_empty_min: int | None


def parse_time_response(report: bytes) -> VendorTime:
    report = validate_response(report, TIME_RESPONSE)
    try:
        board_time = datetime(
            2000 + _bcd(report[2], "year"),
            _bcd(report[3], "month"),
            _bcd(report[4], "day"),
            _bcd(report[6], "hour"),
            _bcd(report[7], "minute"),
            _bcd(report[8], "second"),
        )
    except (DeviceError, ValueError):
        # An unset RTC must not hide otherwise valid power telemetry.
        board_time = None
    runtime = _u16(report, 16)
    return VendorTime(
        board_time=board_time,
        remaining_capacity=report[12],
        runtime_to_empty_min=None if runtime == 0xFFFF else runtime,
    )


def parse_power_response(report: bytes) -> float:
    report = validate_response(report, POWER_RESPONSE)
    return _u32(report, 1) * 1e-6


class VendorTelemetryOpenUPSClient:
    """Poll the verified legacy status requests, with no configuration writes."""

    def __init__(
        self,
        transport: VendorTelemetryTransport | None = None,
        *,
        timeout_ms: int = 500,
    ) -> None:
        self.transport = transport or WindowsHIDTransport()
        self.timeout_ms = timeout_ms

    @property
    def is_connected(self) -> bool:
        return self.transport.is_open

    def connect(self) -> None:
        if not self.transport.is_open:
            self.transport.open()

    def _query(self, request_id: int, response_id: int) -> bytes:
        response = self.transport.transact(
            build_read_request(request_id),
            response_length=REPORT_LENGTH,
            timeout_ms=self.timeout_ms,
        )
        return validate_response(response, response_id)

    def poll(self) -> TelemetrySnapshot:
        self.connect()
        status_report = self._query(STATUS_REQUEST, STATUS_RESPONSE)
        power_report = self._query(POWER_REQUEST, POWER_RESPONSE)
        time_report = self._query(TIME_REQUEST, TIME_RESPONSE)

        status = parse_status_response(status_report)
        time_values = parse_time_response(time_report)
        output_power = parse_power_response(power_report)
        info = self.transport.device_info

        flags = {name: None for name in FLAG_NAMES}
        flags.update(
            vin_enabled=status.ups_state == 2,
            battery_enabled=status.ups_state == 1,
            output_enabled=status.vout >= 0.5,
        )
        raw = (
            f"82:{status_report.hex()} 86:{power_report.hex()} 84:{time_report.hex()} "
            f"clock={time_values.board_time.isoformat(sep=' ') if time_values.board_time else 'unavailable'} "
            f"status={status.status_bytes[0]:02X}/{status.status_bytes[1]:02X}/"
            f"{status.status_bytes[2]:02X}"
        )
        return TelemetrySnapshot(
            connected=True,
            protocol_ready=True,
            connection_message="Connected - Windows 11 vendor HID telemetry (read-only)",
            device_path=info.path if info else None,
            firmware_major=status.firmware_major,
            firmware_minor=status.firmware_minor,
            operating_mode=status.operating_mode,
            vin=status.vin,
            vbat=status.vbat,
            vout=status.vout,
            cell_voltages=status.cells,
            charge_current=status.charge_current,
            discharge_current=status.discharge_current,
            input_current=status.input_current,
            pcb_temperature=status.temperature,
            output_power=output_power,
            ups_state=status.ups_state,
            remaining_capacity=float(time_values.remaining_capacity),
            runtime_to_empty_min=time_values.runtime_to_empty_min,
            flags=flags,
            raw_debug=raw,
        )

    def close(self) -> None:
        self.transport.close()
