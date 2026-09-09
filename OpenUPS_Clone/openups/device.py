from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import logging
import os
from typing import Protocol, Sequence


VENDOR_ID = 0x04D8
PRODUCT_ID = 0xD004
CONFIG_USAGE_PAGE = 0xFF00
CONFIG_USAGE = 0x0001
CONFIG_INPUT_REPORT_LENGTH = 32
CONFIG_OUTPUT_REPORT_LENGTH = 32

LOGGER = logging.getLogger(__name__)


class DeviceError(RuntimeError):
    pass


class DeviceNotFoundError(DeviceError):
    pass


class TransportUnavailableError(DeviceError):
    pass


@dataclass(frozen=True, slots=True)
class HIDDeviceInfo:
    path: str
    vendor_id: int
    product_id: int
    usage_page: int
    usage: int
    input_report_length: int
    output_report_length: int
    feature_report_length: int = 0
    manufacturer: str = ""
    product: str = ""
    serial_number: str = ""

    @property
    def is_configuration_collection(self) -> bool:
        return (
            self.vendor_id == VENDOR_ID
            and self.product_id == PRODUCT_ID
            and self.usage_page == CONFIG_USAGE_PAGE
            and self.usage == CONFIG_USAGE
            and self.input_report_length == CONFIG_INPUT_REPORT_LENGTH
            and self.output_report_length == CONFIG_OUTPUT_REPORT_LENGTH
        )


def select_configuration_collection(devices: Sequence[HIDDeviceInfo]) -> HIDDeviceInfo:
    matches = [device for device in devices if device.is_configuration_collection]
    if not matches:
        descriptions = ", ".join(
            f"{d.usage_page:04X}:{d.usage:04X} in={d.input_report_length} out={d.output_report_length}"
            for d in devices
            if d.vendor_id == VENDOR_ID and d.product_id == PRODUCT_ID
        )
        detail = f" Matching VID/PID collections: {descriptions}." if descriptions else ""
        raise DeviceNotFoundError(
            "OpenUPS vendor configuration collection FF00:0001 with 32/32 reports was not found."
            + detail
        )
    if len(matches) > 1:
        LOGGER.warning("Multiple valid OpenUPS configuration collections found; using %s", matches[0].path)
    return matches[0]


class HIDTransport(Protocol):
    @property
    def is_open(self) -> bool: ...

    @property
    def device_info(self) -> HIDDeviceInfo | None: ...

    def enumerate(self) -> list[HIDDeviceInfo]: ...

    def open(self) -> HIDDeviceInfo: ...

    def transact(self, outbound: bytes, response_length: int, timeout_ms: int) -> bytes: ...

    def close(self) -> None: ...


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("InterfaceClassGuid", GUID),
        ("Flags", wintypes.DWORD),
        ("Reserved", ctypes.c_void_p),
    ]


class HIDD_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Size", wintypes.ULONG),
        ("VendorID", wintypes.USHORT),
        ("ProductID", wintypes.USHORT),
        ("VersionNumber", wintypes.USHORT),
    ]


class HIDP_CAPS(ctypes.Structure):
    _fields_ = [
        ("Usage", wintypes.USHORT),
        ("UsagePage", wintypes.USHORT),
        ("InputReportByteLength", wintypes.USHORT),
        ("OutputReportByteLength", wintypes.USHORT),
        ("FeatureReportByteLength", wintypes.USHORT),
        ("Reserved", wintypes.USHORT * 17),
        ("NumberLinkCollectionNodes", wintypes.USHORT),
        ("NumberInputButtonCaps", wintypes.USHORT),
        ("NumberInputValueCaps", wintypes.USHORT),
        ("NumberInputDataIndices", wintypes.USHORT),
        ("NumberOutputButtonCaps", wintypes.USHORT),
        ("NumberOutputValueCaps", wintypes.USHORT),
        ("NumberOutputDataIndices", wintypes.USHORT),
        ("NumberFeatureButtonCaps", wintypes.USHORT),
        ("NumberFeatureValueCaps", wintypes.USHORT),
        ("NumberFeatureDataIndices", wintypes.USHORT),
    ]


class _WindowsDiscovery:
    DIGCF_PRESENT = 0x00000002
    DIGCF_DEVICEINTERFACE = 0x00000010
    FILE_SHARE_READ = 0x00000001
    FILE_SHARE_WRITE = 0x00000002
    OPEN_EXISTING = 3
    ERROR_NO_MORE_ITEMS = 259

    def __init__(self) -> None:
        if os.name != "nt":
            raise TransportUnavailableError("Windows HID discovery is only available on Windows")
        self.setupapi = ctypes.WinDLL("setupapi", use_last_error=True)
        self.hid = ctypes.WinDLL("hid", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.invalid_handle = ctypes.c_void_p(-1).value
        self._declare_functions()

    def _declare_functions(self) -> None:
        self.hid.HidD_GetHidGuid.argtypes = [ctypes.POINTER(GUID)]
        self.hid.HidD_GetAttributes.argtypes = [wintypes.HANDLE, ctypes.POINTER(HIDD_ATTRIBUTES)]
        self.hid.HidD_GetAttributes.restype = wintypes.BOOLEAN
        for function in (
            self.hid.HidD_GetManufacturerString,
            self.hid.HidD_GetProductString,
            self.hid.HidD_GetSerialNumberString,
        ):
            function.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.ULONG]
            function.restype = wintypes.BOOLEAN
        self.hid.HidD_GetPreparsedData.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p)]
        self.hid.HidD_GetPreparsedData.restype = wintypes.BOOLEAN
        self.hid.HidD_FreePreparsedData.argtypes = [ctypes.c_void_p]
        self.hid.HidP_GetCaps.argtypes = [ctypes.c_void_p, ctypes.POINTER(HIDP_CAPS)]
        self.hid.HidP_GetCaps.restype = ctypes.c_long
        self.setupapi.SetupDiGetClassDevsW.argtypes = [
            ctypes.POINTER(GUID), wintypes.LPCWSTR, wintypes.HWND, wintypes.DWORD
        ]
        self.setupapi.SetupDiGetClassDevsW.restype = wintypes.HANDLE
        self.setupapi.SetupDiEnumDeviceInterfaces.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            ctypes.POINTER(GUID),
            wintypes.DWORD,
            ctypes.POINTER(SP_DEVICE_INTERFACE_DATA),
        ]
        self.setupapi.SetupDiEnumDeviceInterfaces.restype = wintypes.BOOL
        self.setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(SP_DEVICE_INTERFACE_DATA),
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.c_void_p,
        ]
        self.setupapi.SetupDiGetDeviceInterfaceDetailW.restype = wintypes.BOOL
        self.setupapi.SetupDiDestroyDeviceInfoList.argtypes = [wintypes.HANDLE]
        self.kernel32.CreateFileW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        self.kernel32.CreateFileW.restype = wintypes.HANDLE
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    def _path_for(self, info_set: int, interface: SP_DEVICE_INTERFACE_DATA) -> str:
        required = wintypes.DWORD()
        self.setupapi.SetupDiGetDeviceInterfaceDetailW(
            info_set, ctypes.byref(interface), None, 0, ctypes.byref(required), None
        )
        if not required.value:
            raise ctypes.WinError(ctypes.get_last_error())
        buffer = ctypes.create_string_buffer(required.value)
        ctypes.c_ulong.from_buffer(buffer).value = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
        if not self.setupapi.SetupDiGetDeviceInterfaceDetailW(
            info_set,
            ctypes.byref(interface),
            buffer,
            required.value,
            ctypes.byref(required),
            None,
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        return ctypes.wstring_at(ctypes.addressof(buffer) + 4)

    @staticmethod
    def _hid_string(function: object, handle: int) -> str:
        buffer = ctypes.create_unicode_buffer(256)
        return buffer.value if function(handle, buffer, ctypes.sizeof(buffer)) else ""

    def enumerate(self) -> list[HIDDeviceInfo]:
        guid = GUID()
        self.hid.HidD_GetHidGuid(ctypes.byref(guid))
        info_set = self.setupapi.SetupDiGetClassDevsW(
            ctypes.byref(guid), None, None, self.DIGCF_PRESENT | self.DIGCF_DEVICEINTERFACE
        )
        if info_set == self.invalid_handle:
            raise ctypes.WinError(ctypes.get_last_error())
        devices: list[HIDDeviceInfo] = []
        try:
            index = 0
            while True:
                interface = SP_DEVICE_INTERFACE_DATA()
                interface.cbSize = ctypes.sizeof(interface)
                ctypes.set_last_error(0)
                if not self.setupapi.SetupDiEnumDeviceInterfaces(
                    info_set, None, ctypes.byref(guid), index, ctypes.byref(interface)
                ):
                    error = ctypes.get_last_error()
                    # A few Windows/Python combinations have been observed to
                    # return FALSE with a cleared last-error value at the end of
                    # the SetupAPI list.  Once enumeration has begun, both 0 and
                    # ERROR_NO_MORE_ITEMS mean that there is no next interface.
                    # This is the exact condition that made the diagnostic tool
                    # print a spurious ``WinError 0`` after listing both OpenUPS
                    # collections on the user's Windows 11 machine.
                    if error in (0, self.ERROR_NO_MORE_ITEMS):
                        break
                    raise ctypes.WinError(error)
                index += 1
                path = self._path_for(info_set, interface)
                handle = self.kernel32.CreateFileW(
                    path,
                    0,
                    self.FILE_SHARE_READ | self.FILE_SHARE_WRITE,
                    None,
                    self.OPEN_EXISTING,
                    0,
                    None,
                )
                if handle == self.invalid_handle:
                    continue
                try:
                    attributes = HIDD_ATTRIBUTES()
                    attributes.Size = ctypes.sizeof(attributes)
                    if not self.hid.HidD_GetAttributes(handle, ctypes.byref(attributes)):
                        continue
                    preparsed = ctypes.c_void_p()
                    caps = HIDP_CAPS()
                    if not self.hid.HidD_GetPreparsedData(handle, ctypes.byref(preparsed)):
                        continue
                    try:
                        if self.hid.HidP_GetCaps(preparsed, ctypes.byref(caps)) < 0:
                            continue
                    finally:
                        self.hid.HidD_FreePreparsedData(preparsed)
                    devices.append(
                        HIDDeviceInfo(
                            path=path,
                            vendor_id=attributes.VendorID,
                            product_id=attributes.ProductID,
                            usage_page=caps.UsagePage,
                            usage=caps.Usage,
                            input_report_length=caps.InputReportByteLength,
                            output_report_length=caps.OutputReportByteLength,
                            feature_report_length=caps.FeatureReportByteLength,
                            manufacturer=self._hid_string(self.hid.HidD_GetManufacturerString, handle),
                            product=self._hid_string(self.hid.HidD_GetProductString, handle),
                            serial_number=self._hid_string(self.hid.HidD_GetSerialNumberString, handle),
                        )
                    )
                finally:
                    self.kernel32.CloseHandle(handle)
        finally:
            self.setupapi.SetupDiDestroyDeviceInfoList(info_set)
        return devices


class WindowsHIDTransport:
    """Exact-frame HID transport for the vendor-defined OpenUPS collection.

    This class deliberately never adds/removes a report-ID byte or pads a frame. A
    verified command profile must provide the exact bytes accepted by the working
    Windows script.
    """

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

    def enumerate(self) -> list[HIDDeviceInfo]:
        return _WindowsDiscovery().enumerate()

    def _load_hid(self):
        if self._hid_module is None:
            try:
                import hid  # type: ignore
            except ImportError as exc:
                raise TransportUnavailableError(
                    "hidapi is required: py -m pip install hidapi"
                ) from exc
            self._hid_module = hid
        return self._hid_module

    @staticmethod
    def _normalized_path(path: str | bytes) -> str:
        if isinstance(path, bytes):
            path = path.decode("utf-8", errors="replace")
        return path.lower().replace("/", "\\")

    def _find_hidapi_path(self, selected: HIDDeviceInfo) -> str | bytes:
        hid = self._load_hid()
        desired = self._normalized_path(selected.path)
        for item in hid.enumerate(VENDOR_ID, PRODUCT_ID):
            candidate = item.get("path", b"")
            if self._normalized_path(candidate) == desired:
                return candidate
        raise DeviceNotFoundError("Selected collection disappeared before it could be opened")

    def open(self) -> HIDDeviceInfo:
        if os.name != "nt":
            raise TransportUnavailableError("Real OpenUPS access requires Windows; use --mock for UI preview")
        self.close()
        selected = select_configuration_collection(self.enumerate())
        hid = self._load_hid()
        handle = hid.device()
        try:
            handle.open_path(self._find_hidapi_path(selected))
        except Exception:
            handle.close()
            raise
        self._handle = handle
        self._device_info = selected
        LOGGER.info("Opened OpenUPS configuration collection: %s", selected.path)
        return selected

    def transact(self, outbound: bytes, response_length: int = 32, timeout_ms: int = 350) -> bytes:
        if self._handle is None:
            raise DeviceError("Transport is not open")
        if not outbound:
            raise DeviceError("Refusing to send an empty HID frame")
        if self.debug:
            LOGGER.debug("HID TX (%d): %s", len(outbound), outbound.hex(" "))
        written = self._handle.write(outbound)
        if written != len(outbound):
            raise DeviceError(f"Short HID write: {written} of {len(outbound)} bytes")
        received = bytes(self._handle.read(response_length, timeout_ms))
        if self.debug:
            LOGGER.debug("HID RX (%d): %s", len(received), received.hex(" "))
        if not received:
            raise DeviceError(f"Timed out waiting {timeout_ms} ms for HID response")
        return received

    def close(self) -> None:
        handle, self._handle = self._handle, None
        self._device_info = None
        if handle is not None:
            try:
                handle.close()
            except Exception:
                LOGGER.exception("Failed to close HID handle cleanly")
