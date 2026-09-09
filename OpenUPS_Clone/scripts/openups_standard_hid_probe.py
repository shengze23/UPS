"""Read-only descriptor and report probe for the OpenUPS battery collection.

This script calls only HID descriptor, GetFeature, and GetInputReport operations.
It contains no output-report write, feature-report send, reset, or flash path.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from openups.hid_descriptor import (  # noqa: E402
    HIDDescriptorError,
    decode_report,
    format_usage_path,
    parse_report_descriptor,
)


VID = 0x04D8
PID = 0xD004
BATTERY_USAGE_PAGE = 0x0084
BATTERY_USAGE = 0x0004


def _normalized(path: str | bytes) -> str:
    if isinstance(path, bytes):
        path = path.decode("utf-8", errors="replace")
    return path.lower().replace("/", "\\")


def _hex_lines(data: bytes, width: int = 16) -> str:
    return "\n".join(
        f"  {offset:04X}: {data[offset:offset + width].hex(' ')}"
        for offset in range(0, len(data), width)
    )


def _usage_text(field) -> str:
    usage = field.usage.text() if field.usage else "----:----"
    path = format_usage_path(field.collection_path)
    return f"usage={usage} path={path or '<root>'}"


def main() -> int:
    try:
        import hid
    except ImportError:
        print("ERROR: hidapi is not installed in this Python environment")
        return 2

    candidates = [
        item
        for item in hid.enumerate(VID, PID)
        if int(item.get("usage_page") or 0) == BATTERY_USAGE_PAGE
        and int(item.get("usage") or 0) == BATTERY_USAGE
    ]
    if not candidates:
        print("ERROR: OpenUPS battery collection 0084:0004 was not found")
        return 1
    selected = candidates[0]
    print("READ-ONLY OpenUPS standard HID probe")
    print(f"VID:PID       = {VID:04X}:{PID:04X}")
    print(f"Usage         = {BATTERY_USAGE_PAGE:04X}:{BATTERY_USAGE:04X}")
    print(f"Manufacturer  = {selected.get('manufacturer_string')!r}")
    print(f"Product       = {selected.get('product_string')!r}")
    print(f"Serial        = {selected.get('serial_number')!r}")
    print(f"Path          = {_normalized(selected['path'])}")

    device = hid.device()
    try:
        device.open_path(selected["path"])
        descriptor = bytes(device.get_report_descriptor())
        print(f"\nReport descriptor ({len(descriptor)} bytes):")
        print(_hex_lines(descriptor))
        parsed = parse_report_descriptor(descriptor)

        grouped = defaultdict(list)
        for field in parsed.fields:
            grouped[(field.report_type, field.report_id)].append(field)
        print("\nParsed report fields:")
        for (report_type, report_id), fields in sorted(grouped.items()):
            expected = parsed.expected_length(report_type, report_id)
            print(f"\n[{report_type.upper()} report_id=0x{report_id:02X} expected_len={expected}]")
            for field in fields:
                kind = "CONST" if field.is_constant else ("VAR" if field.is_variable else "ARRAY")
                print(
                    f"  bit={field.bit_offset:3d}+{field.bit_size:<2d} {kind:<5s} "
                    f"{_usage_text(field)} logical={field.logical_minimum}..{field.logical_maximum} "
                    f"physical={field.physical_minimum}..{field.physical_maximum} "
                    f"unit_exp={field.unit_exponent} unit=0x{field.unit:X}"
                )

        print("\nFeature reports (GetFeature only):")
        for report_id in parsed.report_ids("feature"):
            length = max(13, parsed.expected_length("feature", report_id))
            try:
                report = bytes(device.get_feature_report(report_id, length))
                print(f"\nFEATURE 0x{report_id:02X} ({len(report)} bytes): {report.hex(' ')}")
                for value in decode_report(parsed, "feature", report_id, report):
                    print(
                        f"  {_usage_text(value.field)} raw={value.raw_value} "
                        f"scaled={value.scaled_value:.8g}"
                    )
            except Exception as exc:
                print(f"\nFEATURE 0x{report_id:02X}: READ FAILED: {exc}")

        print("\nInput reports (GetInputReport only):")
        for report_id in parsed.report_ids("input"):
            length = max(4, parsed.expected_length("input", report_id))
            try:
                report = bytes(device.get_input_report(report_id, length))
                print(f"\nINPUT 0x{report_id:02X} ({len(report)} bytes): {report.hex(' ')}")
                for value in decode_report(parsed, "input", report_id, report):
                    print(
                        f"  {_usage_text(value.field)} raw={value.raw_value} "
                        f"scaled={value.scaled_value:.8g}"
                    )
            except Exception as exc:
                print(f"\nINPUT 0x{report_id:02X}: READ FAILED: {exc}")
    except HIDDescriptorError as exc:
        print(f"ERROR parsing HID descriptor/report: {exc}")
        return 3
    except Exception as exc:
        print(f"ERROR reading OpenUPS standard HID data: {exc}")
        return 4
    finally:
        device.close()

    print("\nProbe complete. No HID write operation was called.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

