# Implementation status

Status as of 2026-09-05.

| Feature | Evidence | Implementation | Status |
|---|---|---|---|
| Detect VID/PID | Windows diagnostics and descriptor probe | hidapi enumeration | Validated on user's D004 board |
| Select collection 2 for telemetry | Usage `FF00:0001`, 32/32 reports | Exact usage/page/length selection and `open_path` | Implemented; target-board run pending |
| Collection 1 fallback | Usage `0084:0004`, feature length 13 | `--standard-hid` | Implemented from user's probe |
| Exact HID path open | Existing hidapi access plus diagnostic paths | hidapi `open_path` after capability match | Implemented, needs board validation |
| Report-ID/framing | Static analysis of supplied 2014 DLL | Exact 32-byte `81/85/83` requests | Implemented; target-board run pending |
| Vendor status decode | Static analysis of supplied DLL parser/constants | `82/86/84` bounds-checked decode | Implemented and unit-tested |
| Standard telemetry reads | User's 628-byte HID descriptor and feature-report capture | `GetFeature` reports `20/21/22/23/30/40/52/60` | Implemented, read-only |
| Electrical/temperature scaling | Public NUT D004 subdriver plus captured descriptor | D004 correction factors and thermistor interpolation | Implemented; board measurement comparison pending |
| Capacity/runtime | HID reports `52/60` and status `40` | Suppresses firmware placeholders when battery absent | Implemented |
| Standard status | HID report `40` | AC/battery/charge/discharge/low/replacement decode | Implemented |
| Firmware version | Byte 31 nibbles in vendor `82` response | Displays major/minor | Implemented and unit-tested |
| Background polling | Prompt | `QThread` plus transport-agnostic loop | Implemented |
| Automatic reconnect | Prompt | Close-on-error and retry loop | Implemented and mock-tested |
| Raw HID logs | Prompt | Python logging behind `--debug-hid` | Implemented |
| Status GUI | Manual screenshot | Header, six cells, currents, states, flags, frequencies, power and CSV log | Implemented with mock data |
| Settings GUI | Manual screenshot | Parameter list/descriptions and transfer controls | Implemented read-only |
| Parameter list | 2019 hardware manual pages 8-12 | Names, units, descriptions and defaults | Implemented |
| Parameter reads | Complete address/unit map missing | Controls disabled | Blocked pending per-operation capture |
| Writes and reset | Command/index/unit map missing | GUI disabled; generic safety pipeline mock-tested | Intentionally blocked |
| Battery Wizard | Manual examples but incomplete formulas | Reference dialog; Apply disabled | Intentionally blocked |
| CSV logging | Software manual and binary header string | User-selected path, configurable interval | Implemented |
| PyInstaller onedir | Prompt | Windows spec and PowerShell build script | Spec built successfully on macOS; Windows build still required |
| Actual Windows/board acceptance | User verified both collections and Win7 legacy operation | Checklist and one-click batch launcher in README | Updated Win11 vendor build ready; live run pending |

The read-only safety posture is part of the implementation, not a missing UI state: no hardware write, reset, or firmware code is reachable.
