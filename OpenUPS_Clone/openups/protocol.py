from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .models import TelemetrySnapshot


class ProtocolError(RuntimeError):
    pass


class ProtocolUnavailableError(ProtocolError):
    pass


SUPPORTED_SCALARS: dict[str, tuple[str, int]] = {
    "u8": ("<B", 1),
    "s8": ("<b", 1),
    "u16le": ("<H", 2),
    "s16le": ("<h", 2),
    "u32le": ("<I", 4),
    "s32le": ("<i", 4),
    "f32le": ("<f", 4),
}


def parse_hex_frame(text: str) -> bytes:
    compact = "".join(text.replace("0x", "").split())
    if not compact:
        raise ProtocolError("A transaction frame cannot be empty")
    if len(compact) % 2:
        raise ProtocolError("Hex frame must contain complete bytes")
    try:
        return bytes.fromhex(compact)
    except ValueError as exc:
        raise ProtocolError(f"Invalid hex frame: {exc}") from exc


@dataclass(frozen=True, slots=True)
class FieldSpec:
    target: str
    kind: str
    offset: int
    scale: float = 1.0
    bit: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FieldSpec":
        return cls(
            target=str(data["target"]),
            kind=str(data.get("kind", "u8")),
            offset=int(data["offset"]),
            scale=float(data.get("scale", 1.0)),
            bit=None if data.get("bit") is None else int(data["bit"]),
        )


@dataclass(frozen=True, slots=True)
class ReadRequest:
    name: str
    tx: bytes
    response_length: int
    fields: tuple[FieldSpec, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReadRequest":
        return cls(
            name=str(data["name"]),
            tx=parse_hex_frame(str(data["tx_hex"])),
            response_length=int(data.get("response_length", 32)),
            fields=tuple(FieldSpec.from_dict(item) for item in data.get("fields", [])),
        )


@dataclass(frozen=True, slots=True)
class CommandProfile:
    profile_name: str
    source: str
    read_only: bool
    requests: tuple[ReadRequest, ...]

    @classmethod
    def load(cls, path: str | Path) -> "CommandProfile":
        profile_path = Path(path)
        data = json.loads(profile_path.read_text(encoding="utf-8"))
        profile = cls(
            profile_name=str(data["profile_name"]),
            source=str(data["source"]),
            read_only=bool(data.get("read_only", False)),
            requests=tuple(ReadRequest.from_dict(item) for item in data.get("requests", [])),
        )
        profile.validate()
        return profile

    def validate(self) -> None:
        if not self.read_only:
            raise ProtocolError("Only profiles explicitly marked read_only=true are accepted")
        if not self.source.strip():
            raise ProtocolError("Profile must identify the proven source of its bytes")
        if not self.requests:
            raise ProtocolError("Profile contains no read requests")
        for request in self.requests:
            if request.response_length <= 0 or request.response_length > 4096:
                raise ProtocolError(f"Invalid response length for {request.name}")
            for field in request.fields:
                _validate_field(field, request.response_length)


def _validate_field(field: FieldSpec, response_length: int) -> None:
    if field.kind not in SUPPORTED_SCALARS:
        raise ProtocolError(f"Unsupported field kind: {field.kind}")
    _, size = SUPPORTED_SCALARS[field.kind]
    if field.offset < 0 or field.offset + size > response_length:
        raise ProtocolError(f"Field {field.target} is outside its response")
    if field.bit is not None and not 0 <= field.bit <= 7:
        raise ProtocolError(f"Invalid bit for {field.target}: {field.bit}")


def decode_fields(payload: bytes, fields: Iterable[FieldSpec]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for field in fields:
        _validate_field(field, len(payload))
        fmt, _ = SUPPORTED_SCALARS[field.kind]
        raw = struct.unpack_from(fmt, payload, field.offset)[0]
        value: Any = bool((int(raw) >> field.bit) & 1) if field.bit is not None else raw * field.scale
        if field.bit is None and field.scale == 1.0 and field.kind not in {"f32le"}:
            value = int(value)
        values[field.target] = value
    return values


def apply_responses(
    base: TelemetrySnapshot,
    pairs: Iterable[tuple[ReadRequest, bytes]],
) -> TelemetrySnapshot:
    decoded: dict[str, Any] = {}
    debug: list[str] = []
    for request, response in pairs:
        if len(response) < request.response_length:
            raise ProtocolError(
                f"{request.name}: short response ({len(response)} < {request.response_length})"
            )
        response = response[: request.response_length]
        decoded.update(decode_fields(response, request.fields))
        debug.append(f"{request.name}: {response.hex(' ')}")
    decoded["raw_debug"] = " | ".join(debug)
    decoded["protocol_ready"] = True
    decoded["connection_message"] = "Connected"
    return base.with_values(decoded)

