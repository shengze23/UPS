# OpenUPS Clone — Windows 11 test build

A clean-room Python/PySide6 replacement for the legacy Mini-Box OpenUPS Configuration application. Normal mode uses the board's vendor HID collection directly on Windows 11. It never loads `OpenUPSLib.dll`, never starts or modifies `OpenUPS.exe`, and contains no firmware-flashing path.

## Current safety boundary

Normal hardware mode opens the exact vendor collection (`04D8:D004`, usage `FF00:0001`, 32-byte input/output reports) and sends only the three periodic query frames recovered from the supplied 2014 library: `81`, `85`, and `83`, each padded to exactly 32 bytes. It accepts the corresponding `82`, `86`, and `84` responses. These requests read status, output power, clock, capacity, and runtime. An explicit allow-list rejects every other command.

Although HID uses an OUT transfer to request a response, these three commands are read-only at the OpenUPS protocol level. Parameter writes, sync, restore, reset, firmware flashing, and Battery Wizard Apply remain disabled because their complete address/unit map has not yet been verified on the user's board.

## First Windows 11 hardware test

1. In the Windows 7 VM menu, disconnect/eject the OpenUPS USB device from the VM so Windows 11 owns it. A USB device cannot be attached to the VM and host simultaneously.
2. Close the legacy OpenUPS GUI and any diagnostic script.
3. Extract this entire folder on Windows 11.
4. Double-click `RUN_FROM_SOURCE_WIN11.bat`. It creates/checks `.venv`, installs dependencies, and starts the GUI with HID logging visible.
5. The expected footer is `Connected - Windows 11 vendor HID telemetry (read-only)`, the title should show firmware `1.9`, and the console should repeat 32-byte `HID TX` / `HID RX` lines.

If it does not connect, keep the console open and send a screenshot of the entire console. `Access denied` normally means the USB device is still owned by the VM or another program. `Timed out` or `Wrong response ID` means the device opened but its reply framing needs to be adjusted from the captured log.

The `Settings` page being locked is intentional for this test build. Live status is enabled; configuration changes are not.

## Other run modes

Run from Command Prompt with visible HID bytes:

```powershell
py main.py --debug-hid
```

Use the limited standard Power Device collection as a fallback:

```powershell
py main.py --standard-hid --debug-hid
```

Use mock mode to inspect every screen without a board:

```powershell
py main.py --mock
```

## Tests

Tests never communicate with real hardware:

```powershell
py -m unittest discover -s tests -v
```

Coverage includes exact collection selection, the closed request allow-list, exact 32-byte request frames, response scaling, BCD/time parsing, malformed packets, reconnect behavior, mock telemetry, and default write denial.

## Windows onedir build

Double-click `BUILD_WIN11.bat`. It invokes PowerShell correctly even when started from Command Prompt. The expected artifact is:

```text
dist\OpenUPS-Clone\OpenUPS-Clone.exe
```

PyInstaller cannot cross-compile a Windows executable from macOS, so the final EXE must be built on Windows 11.

## Target-board acceptance checklist

- Device Manager shows both OpenUPS collections.
- The Windows 7 VM has released the USB device.
- Clone opens the `FF00:0001` / `col02` path.
- Debug logging shows only 32-byte requests beginning `81`, `85`, and `83`.
- Responses begin `82`, `86`, and `84`; firmware displays as `1.9`.
- Input/output/battery voltages, currents and temperature agree with trusted measurements.
- Unplug causes `Disconnected` without GUI freeze; replug recovers automatically.
- Original Mini-Box files remain unchanged.

## Project map

- `openups/vendor_telemetry.py`: allow-listed native vendor-HID polling and decode
- `openups/standard_hid.py`: limited collection-1 fallback and D004 conversions
- `openups/device.py`: strict collection discovery and exact-frame Windows transport
- `openups/models.py`: immutable telemetry model
- `openups/service.py`: poll/reconnect loop
- `openups/parameters.py`: manual-derived read-only parameter catalog
- `openups/safety.py`: disabled-by-default safe write transaction pipeline
- `gui/`: PySide6 window, pages, worker and wizard
- `docs/implementation_status.md`: verified/implemented/blocked feature matrix
