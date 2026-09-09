from __future__ import annotations

from dataclasses import dataclass, field, replace
from math import ceil
from typing import Iterable


class HIDDescriptorError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Usage:
    page: int
    usage: int

    def text(self) -> str:
        return f"{self.page:04X}:{self.usage:04X}"


@dataclass(frozen=True, slots=True)
class ReportField:
    report_type: str
    report_id: int
    bit_offset: int
    bit_size: int
    usage: Usage | None
    collection_path: tuple[Usage, ...]
    flags: int
    logical_minimum: int
    logical_maximum: int
    physical_minimum: int
    physical_maximum: int
    unit_exponent: int
    unit: int

    @property
    def is_constant(self) -> bool:
        return bool(self.flags & 0x01)

    @property
    def is_variable(self) -> bool:
        return bool(self.flags & 0x02)


@dataclass(frozen=True, slots=True)
class ReportValue:
    field: ReportField
    raw_value: int
    scaled_value: float


@dataclass(slots=True)
class ParsedReportDescriptor:
    fields: list[ReportField] = field(default_factory=list)

    def report_ids(self, report_type: str) -> tuple[int, ...]:
        return tuple(sorted({item.report_id for item in self.fields if item.report_type == report_type}))

    def fields_for(self, report_type: str, report_id: int) -> list[ReportField]:
        return [
            item
            for item in self.fields
            if item.report_type == report_type and item.report_id == report_id
        ]

    def expected_length(self, report_type: str, report_id: int) -> int:
        fields = self.fields_for(report_type, report_id)
        if not fields:
            return 0
        data_bits = max(item.bit_offset + item.bit_size for item in fields)
        return 1 + ceil(data_bits / 8)


@dataclass(slots=True)
class _GlobalState:
    usage_page: int = 0
    logical_minimum: int = 0
    logical_maximum: int = 0
    physical_minimum: int = 0
    physical_maximum: int = 0
    unit_exponent: int = 0
    unit: int = 0
    report_size: int = 0
    report_id: int = 0
    report_count: int = 0

    def copy(self) -> "_GlobalState":
        return replace(self)


@dataclass(slots=True)
class _LocalState:
    usages: list[Usage] = field(default_factory=list)
    usage_minimum: Usage | None = None
    usage_maximum: Usage | None = None

    def reset(self) -> None:
        self.usages.clear()
        self.usage_minimum = None
        self.usage_maximum = None

    def expanded_usages(self, count: int) -> list[Usage | None]:
        usages: list[Usage | None] = list(self.usages)
        if self.usage_minimum and self.usage_maximum:
            if self.usage_minimum.page == self.usage_maximum.page:
                span = self.usage_maximum.usage - self.usage_minimum.usage + 1
                if 0 < span <= 1024:
                    usages.extend(
                        Usage(self.usage_minimum.page, self.usage_minimum.usage + index)
                        for index in range(span)
                    )
        if not usages:
            return [None] * count
        if len(usages) < count:
            usages.extend([usages[-1]] * (count - len(usages)))
        return usages[:count]


def _unsigned(data: bytes) -> int:
    return int.from_bytes(data, "little", signed=False)


def _signed(data: bytes) -> int:
    return int.from_bytes(data, "little", signed=True)


def _usage(value: int, usage_page: int, byte_count: int) -> Usage:
    if byte_count > 2:
        return Usage((value >> 16) & 0xFFFF, value & 0xFFFF)
    return Usage(usage_page, value & 0xFFFF)


def _unit_exponent(value: int) -> int:
    nibble = value & 0x0F
    return nibble - 16 if nibble & 0x08 else nibble


def parse_report_descriptor(descriptor: bytes) -> ParsedReportDescriptor:
    parsed = ParsedReportDescriptor()
    globals_ = _GlobalState()
    global_stack: list[_GlobalState] = []
    locals_ = _LocalState()
    collection_stack: list[Usage] = []
    offsets: dict[tuple[str, int], int] = {}
    index = 0

    while index < len(descriptor):
        prefix = descriptor[index]
        index += 1
        if prefix == 0xFE:
            if index + 2 > len(descriptor):
                raise HIDDescriptorError("Truncated long item header")
            size = descriptor[index]
            index += 2  # size and long-item tag
            if index + size > len(descriptor):
                raise HIDDescriptorError("Truncated long item data")
            index += size
            continue

        size_code = prefix & 0x03
        size = 4 if size_code == 3 else size_code
        item_type = (prefix >> 2) & 0x03
        tag = (prefix >> 4) & 0x0F
        if index + size > len(descriptor):
            raise HIDDescriptorError("Truncated short item data")
        payload = descriptor[index : index + size]
        index += size
        unsigned = _unsigned(payload)

        if item_type == 1:  # Global
            if tag == 0:
                globals_.usage_page = unsigned
            elif tag == 1:
                globals_.logical_minimum = _signed(payload)
            elif tag == 2:
                globals_.logical_maximum = (
                    _signed(payload) if globals_.logical_minimum < 0 else unsigned
                )
            elif tag == 3:
                globals_.physical_minimum = _signed(payload)
            elif tag == 4:
                globals_.physical_maximum = (
                    _signed(payload) if globals_.physical_minimum < 0 else unsigned
                )
            elif tag == 5:
                globals_.unit_exponent = _unit_exponent(unsigned)
            elif tag == 6:
                globals_.unit = unsigned
            elif tag == 7:
                globals_.report_size = unsigned
            elif tag == 8:
                if unsigned == 0:
                    raise HIDDescriptorError("Report ID 0 is reserved")
                globals_.report_id = unsigned
            elif tag == 9:
                globals_.report_count = unsigned
            elif tag == 10:
                global_stack.append(globals_.copy())
            elif tag == 11:
                if not global_stack:
                    raise HIDDescriptorError("Global POP without PUSH")
                globals_ = global_stack.pop()
            continue

        if item_type == 2:  # Local
            if tag == 0:
                locals_.usages.append(_usage(unsigned, globals_.usage_page, size))
            elif tag == 1:
                locals_.usage_minimum = _usage(unsigned, globals_.usage_page, size)
            elif tag == 2:
                locals_.usage_maximum = _usage(unsigned, globals_.usage_page, size)
            continue

        if item_type != 0:  # Reserved
            continue

        if tag == 10:  # Collection
            usage = locals_.expanded_usages(1)[0]
            if usage is not None:
                collection_stack.append(usage)
            else:
                collection_stack.append(Usage(0, 0))
            locals_.reset()
            continue
        if tag == 12:  # End Collection
            if not collection_stack:
                raise HIDDescriptorError("END_COLLECTION without COLLECTION")
            collection_stack.pop()
            locals_.reset()
            continue

        report_type = {8: "input", 9: "output", 11: "feature"}.get(tag)
        if report_type is None:
            locals_.reset()
            continue
        if globals_.report_size < 0 or globals_.report_count < 0:
            raise HIDDescriptorError("Invalid negative report size/count")
        key = (report_type, globals_.report_id)
        bit_offset = offsets.get(key, 0)
        usages = locals_.expanded_usages(globals_.report_count)
        for field_index in range(globals_.report_count):
            parsed.fields.append(
                ReportField(
                    report_type=report_type,
                    report_id=globals_.report_id,
                    bit_offset=bit_offset + field_index * globals_.report_size,
                    bit_size=globals_.report_size,
                    usage=usages[field_index],
                    collection_path=tuple(collection_stack),
                    flags=unsigned,
                    logical_minimum=globals_.logical_minimum,
                    logical_maximum=globals_.logical_maximum,
                    physical_minimum=globals_.physical_minimum,
                    physical_maximum=globals_.physical_maximum,
                    unit_exponent=globals_.unit_exponent,
                    unit=globals_.unit,
                )
            )
        offsets[key] = bit_offset + globals_.report_count * globals_.report_size
        locals_.reset()

    if collection_stack:
        raise HIDDescriptorError("Unclosed collection in descriptor")
    return parsed


def _extract_bits(data: bytes, bit_offset: int, bit_size: int) -> int:
    if bit_size == 0:
        return 0
    if bit_offset < 0 or bit_size < 0 or bit_offset + bit_size > len(data) * 8:
        raise HIDDescriptorError("Report field extends beyond the supplied report")
    value = int.from_bytes(data, "little", signed=False)
    return (value >> bit_offset) & ((1 << bit_size) - 1)


def decode_report(
    parsed: ParsedReportDescriptor,
    report_type: str,
    report_id: int,
    report: bytes,
) -> list[ReportValue]:
    if not report:
        raise HIDDescriptorError("Empty HID report")
    if report_id and report[0] != report_id:
        raise HIDDescriptorError(
            f"Expected report ID {report_id:02X}, received {report[0]:02X}"
        )
    # HIDAPI includes the report-ID byte, including a zero byte for unnumbered
    # feature reports on platforms which support them.
    data = report[1:] if report[0] == report_id else report
    values: list[ReportValue] = []
    for item in parsed.fields_for(report_type, report_id):
        if item.is_constant:
            continue
        raw = _extract_bits(data, item.bit_offset, item.bit_size)
        if item.logical_minimum < 0 and item.bit_size and raw & (1 << (item.bit_size - 1)):
            raw -= 1 << item.bit_size
        scaled = float(raw)
        logical_span = item.logical_maximum - item.logical_minimum
        physical_span = item.physical_maximum - item.physical_minimum
        if logical_span and physical_span:
            scaled = (
                (raw - item.logical_minimum) * physical_span / logical_span
                + item.physical_minimum
            )
        scaled *= 10.0 ** item.unit_exponent
        values.append(ReportValue(item, raw, scaled))
    return values


def format_usage_path(path: Iterable[Usage]) -> str:
    return "/".join(item.text() for item in path)
