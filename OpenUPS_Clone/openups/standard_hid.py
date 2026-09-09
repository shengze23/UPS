"""Read-only OpenUPS telemetry from the USB Power Device collection.

The D004 firmware exposes measurements through HID feature reports on usage
0084:0004 (the Windows battery collection).  This module only calls
``get_feature_report``; it has no HID write or feature-report send operation.

Electrical correction factors and the thermistor transfer points are based on
the public Network UPS Tools OpenUPS HID subdriver by Mini-Box contributor Nicu
Pavel.  The report layout itself is also verified against the 628-byte report
descriptor captured from the user's D004 revision 0003 board.
"""
from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Protocol

from .device import DeviceError, DeviceNotFoundError, HIDDeviceInfo, PRODUCT_ID, VENDOR_ID
from .models import FLAG_NAMES, TelemetrySnapshot


LOGGER = logging.getLogger(__name__)

BATTERY_USAGE_PAGE = 0x0084
BATTERY_USAGE = 0x0004

# D004 correction factors.  HID voltage/current fields first normalize to the
# descriptor's 10^-2 units, then the OpenUPS driver applies its board-specific
# divider/current-sense correction.
VIN_VOLTS_PER_COUNT = 0.03545
VOUT_VOLTS_PER_COUNT = 0.02571
VBAT_VOLTS_PER_COUNT = 0.01
INPUT_AMPS_PER_COUNT = 0.0008274
OUTPUT_AMPS_PER_COUNT = 0.016113
BATTERY_AMPS_PER_COUNT = 0.01

# ADC transfer points for -40, -35, ... 125 deg C.
THERMISTOR_ADC_POINTS = (
    0x031, 0x040, 0x053, 0x068, 0x082, 0x0A0, 0x0C3, 0x0E9,
    0x113, 0x13F, 0x16E, 0x19F, 0x1CF, 0x200, 0x22F, 0x25C,
    0x286, 0x2AE, 0x2D3, 0x2F4, 0x312, 0x32D, 0x345, 0x35A,
    0x36D, 0x37E, 0x38C, 0x399, 0x3A5, 0x3AF, 0x3B7, 0x3BF,
    0x3C6, 0x3CC,
)


class StandardHIDTransportProtocol(Protocol):
    @property
    def is_open(self) -> bool: ...

    @property
    def device_info(self) -> HIDDeviceInfo | None: ...

    def open(self) -> HIDDeviceInfo: ...

    def get_feature_report(self, report_id: int, expected_length: int) -> bytes: ...

    def close(self) -> None: ...


def thermistor_temperature(adc_count: int) -> float | None:
    """Convert the OpenUPS thermistor ADC count using linear interpolation."""
    if adc_count <= 0:
        return None
    if adc_count <= THERMISTOR_ADC_POINTS[0]:
        return -40.0
    if adc_count >= THERMISTOR_ADC_POINTS[-1]:
        return 125.0
    for upper_index, upper_count in enumerate(THERMISTOR_ADC_POINTS[1:], start=1):
        if adc_count <= upper_count:
            lower_count = THERMISTOR_ADC_POINTS[upper_index - 1]
            lower_temperature = -40.0 + (upper_index - 1) * 5.0
            fraction = (adc_count - lower_count) / (upper_count - lower_count)
            return lower_temperature + fraction * 5.0
    return None


def _path_text(path: str | bytes) -> str:
    if isinstance(path, bytes):
        return path.decode("utf-8", errors="replace")
    return path


class StandardHIDTransport:
    """HIDAPI transport exposing read-only feature-report access."""

    def __init__(self, *, debug: bool = False, hid_module=None) -> None:
        self.debug = debug
        self._hid_module = hid_module
        self._handle = None
        self._device_info: HIDDeviceInfo | None = None

    @property
    def is_open(self) -> bool:
        return self._handle is not None

    @property
    def device_info(self) -> HIDDeviceInfo | None:
        return self._device_info

    def _load_hid(self):
        if self._hid_module is None:
            try:
                import hid  # type: ignore
            except ImportError as exc:
                raise DeviceError("hidapi is required: py -m pip install hidapi") from exc
            self._hid_module = hid
        return self._hid_module

    def _candidates(self) -> list[dict]:
        hid = self._load_hid()
        return [
            item
            for item in hid.enumerate(VENDOR_ID, PRODUCT_ID)
            if int(item.get("usage_page") or 0) == BATTERY_USAGE_PAGE
            and int(item.get("usage") or 0) == BATTERY_USAGE
        ]

    def open(self) -> HIDDeviceInfo:
        self.close()
        candidates = self._candidates()
        if not candidates:
            raise DeviceNotFoundError(
                "OpenUPS standard HID battery collection 0084:0004 was not found"
            )
        selected = candidates[0]
        hid = self._load_hid()
        handle = hid.device()
        try:
            handle.open_path(selected["path"])
        except Exception:
            handle.close()
            raise
        info = HIDDeviceInfo(
            path=_path_text(selected["path"]),
            vendor_id=VENDOR_ID,
            product_id=PRODUCT_ID,
            usage_page=BATTERY_USAGE_PAGE,
            usage=BATTERY_USAGE,
            input_report_length=4,
            output_report_length=0,
            feature_report_length=13,
            manufacturer=str(selected.get("manufacturer_string") or ""),
            product=str(selected.get("product_string") or ""),
            serial_number=str(selected.get("serial_number") or ""),
        )
        self._handle = handle
        self._device_info = info
        LOGGER.info("Opened OpenUPS standard HID collection (read-only): %s", info.path)
        return info

    def get_feature_report(self, report_id: int, expected_length: int) -> bytes:
        if self._handle is None:
            raise DeviceError("Standard HID transport is not open")
        # The captured collection advertises a maximum feature length of 13.
        # HIDAPI returns the report's actual length, including its report ID.
        report = bytes(self._handle.get_feature_report(report_id, max(13, expected_length)))
        if len(report) < expected_length:
            raise DeviceError(
                f"Short feature report 0x{report_id:02X}: "
                f"{len(report)} of at least {expected_length} bytes"
            )
        if report[0] != report_id:
            raise DeviceError(
                f"Wrong feature report ID: expected 0x{report_id:02X}, got 0x{report[0]:02X}"
            )
        if self.debug:
            LOGGER.debug("HID GET FEATURE 0x%02X RX: %s", report_id, report.hex(" "))
        return report

    def close(self) -> None:
        handle, self._handle = self._handle, None
        self._device_info = None
        if handle is not None:
            try:
                handle.close()
            except Exception:
                LOGGER.exception("Failed to close standard HID handle cleanly")


@dataclass(frozen=True, slots=True)
class StandardStatus:
    raw: int
    below_capacity_limit: bool
    runtime_limit_expired: bool
    charging: bool
    discharging: bool
    conditioning: bool
    need_replacement: bool
    ac_present: bool
    battery_present: bool


def _status(raw: int) -> StandardStatus:
    return StandardStatus(
        raw=raw,
        below_capacity_limit=bool(raw & (1 << 8)),
        runtime_limit_expired=bool(raw & (1 << 9)),
        charging=bool(raw & (1 << 10)),
        discharging=bool(raw & (1 << 11)),
        conditioning=bool(raw & (1 << 12)),
        need_replacement=bool(raw & (1 << 13)),
        ac_present=bool(raw & (1 << 14)),
        battery_present=bool(raw & (1 << 15)),
    )


def _u16(report: bytes, offset: int) -> int:
    return int.from_bytes(report[offset : offset + 2], "little", signed=False)


def _u24(report: bytes, offset: int) -> int:
    return int.from_bytes(report[offset : offset + 3], "little", signed=False)


class StandardHIDOpenUPSClient:
    """Poll the verified D004 standard reports without sending anything."""

    REPORT_LENGTHS = {
        0x20: 5,  # battery voltage
        0x21: 5,  # output voltage/current
        0x22: 5,  # input voltage/current
        0x23: 3,  # thermistor ADC
        0x30: 5,  # battery current
        0x40: 3,  # present-status bitmap
        0x52: 2,  # remaining capacity
        0x60: 4,  # run time to empty, seconds
    }

    def __init__(self, transport: StandardHIDTransportProtocol | None = None) -> None:
        self.transport = transport or StandardHIDTransport()

    @property
    def is_connected(self) -> bool:
        return self.transport.is_open

    def connect(self) -> None:
        if not self.transport.is_open:
            self.transport.open()

    def poll(self) -> TelemetrySnapshot:
        self.connect()
        reports = {
            report_id: self.transport.get_feature_report(report_id, length)
            for report_id, length in self.REPORT_LENGTHS.items()
        }
        status = _status(_u16(reports[0x40], 1))
        vin = _u16(reports[0x22], 1) * VIN_VOLTS_PER_COUNT
        input_current = _u16(reports[0x22], 3) * INPUT_AMPS_PER_COUNT
        vout = _u16(reports[0x21], 1) * VOUT_VOLTS_PER_COUNT
        output_current = _u16(reports[0x21], 3) * OUTPUT_AMPS_PER_COUNT
        vbat = _u16(reports[0x20], 3) * VBAT_VOLTS_PER_COUNT
        battery_current = _u16(reports[0x30], 3) * BATTERY_AMPS_PER_COUNT
        capacity_raw = reports[0x52][1]
        runtime_seconds = _u24(reports[0x60], 1)

        if status.ac_present:
            mode = "Line powered"
            ups_state = 2
        elif status.battery_present:
            mode = "Battery powered"
            ups_state = 1
        else:
            mode = "USB powered"
            ups_state = 3

        flags = {name: None for name in FLAG_NAMES}
        flags.update(
            power_supply_warning=(status.below_capacity_limit or status.runtime_limit_expired),
            charge_enabled=status.charging,
            vin_enabled=status.ac_present,
            battery_enabled=status.battery_present,
        )
        exact_status = (
            f"status=0x{status.raw:04X} "
            f"AC={int(status.ac_present)} BAT={int(status.battery_present)} "
            f"CHG={int(status.charging)} DIS={int(status.discharging)} "
            f"LOW={int(status.below_capacity_limit)} REPLACE={int(status.need_replacement)}"
        )
        raw_reports = " ".join(
            f"{report_id:02X}:{reports[report_id].hex()}" for report_id in self.REPORT_LENGTHS
        )
        info = self.transport.device_info
        return TelemetrySnapshot(
            connected=True,
            protocol_ready=True,
            connection_message="Connected - standard HID telemetry (read-only; settings locked)",
            device_path=info.path if info else None,
            operating_mode=mode,
            vin=vin,
            vbat=vbat,
            vout=vout,
            charge_current=battery_current,
            discharge_current=output_current,
            input_current=input_current,
            pcb_temperature=thermistor_temperature(_u16(reports[0x23], 1)),
            output_power=vout * output_current,
            ups_state=ups_state,
            charger_state=1 if status.charging else 0,
            output_state=1 if vout >= 0.5 else 0,
            # Firmware returns 50%/unknown runtime as placeholders when no
            # battery is present.  Do not present those as real measurements.
            remaining_capacity=float(capacity_raw) if status.battery_present else None,
            runtime_to_empty_min=(
                int(round(runtime_seconds / 60.0))
                if status.battery_present and runtime_seconds <= 0xFFFF
                else None
            ),
            flags=flags,
            raw_debug=f"{exact_status}; {raw_reports}",
        )

    def close(self) -> None:
        self.transport.close()
