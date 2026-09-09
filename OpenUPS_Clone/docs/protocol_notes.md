# Protocol notes

## Verified device selection

The supplied Windows diagnostics and task specification establish two collections under VID `04D8`, PID `D004`:

| Purpose | Usage page:usage | Input report | Output report | Handling |
|---|---:|---:|---:|---|
| Standard telemetry | `0084:0004` | 4 | 0 | Optional limited `GetFeature` fallback |
| Vendor telemetry/configuration | `FF00:0001` | 32 | 32 | Default; select explicitly |

`openups.device.select_configuration_collection` requires all six identity/capability values. It never accepts a VID/PID-only match.

## Verified transport behavior

The user's `connect_openups.py` proves that Python hidapi can open the device. The two Windows diagnostic scripts prove SetupAPI enumeration and capabilities. The clone combines these: SetupAPI discovers and validates the exact collection, then hidapi opens that exact path.

`WindowsHIDTransport.transact` sends exactly the supplied bytes. It does not add or remove a leading byte. It performs a timed read and treats timeout/short write as a disconnect-worthy error. SetupAPI end-of-list values `259` and the observed cleared value `0` are both handled, fixing the user's post-enumeration `WinError 0`.

## Recovered read-only vendor telemetry

Static analysis of the supplied original `OpenUPSLib.dll` establishes the legacy polling sequence and decoder. Each request below is the shown first byte followed by 31 zero bytes:

| Request | Response | Decoded data |
|---:|---:|---|
| `81` | `82` | firmware, VIN/VBAT/VOUT, six cells, currents, temperature, status |
| `85` | `86` | output power |
| `83` | `84` | BCD clock, remaining capacity, runtime-to-empty |

The response conversions implemented by `openups/vendor_telemetry.py` mirror constants and offsets in that DLL. No `A1`, `A3`, `A5`, `B1`, reset, or bootloader operation is implemented. The default application's request builder rejects any ID outside `81/83/85`.

## Verified standard telemetry

The user's descriptor probe captured a 628-byte report descriptor and all feature reports from a D004 revision 0003 board. Fallback mode (`--standard-hid`) opens `0084:0004` (`col01`) and calls only `get_feature_report` for:

- `20`: battery voltage;
- `21`: output voltage/current;
- `22`: input voltage/current;
- `23`: thermistor ADC;
- `30`: battery current;
- `40`: present-status bitmap;
- `52`: remaining capacity;
- `60`: runtime to empty.

The D004 voltage/current corrections and thermistor lookup are independently applied from the public NUT OpenUPS HID driver. Report `24` contains six cell fields but returns zero until certain vendor request codes are written, so the clone does not pretend those zeros are cell voltages.

## Still-missing configuration evidence

The DLL usage samples expose getters but not configuration operations, while the manuals contain parameter names without a complete packet/address/unit map. Therefore these facts remain unverified on the target board:

- parameter indices, raw units, read commands and write commands;
- reset command;
- `settings.ini` key ordering and wire conversion.

## Supplying verified reads

Other read-only logic can still be encoded in a reviewed JSON file that validates against `docs/command_profile.schema.json`. Every outbound `tx_hex` must include exactly what `hid.device.write(...)` receives. Launch with:

```powershell
py main.py --command-profile .\verified-openups-1.9-reads.json --debug-hid
```

The profile loader requires `read_only: true` and a non-empty `source` description. This label is a provenance safeguard, not a substitute for reviewing the commands.

## No firmware path

The flashing guide was inspected to understand the device context. The application implements no bootloader detection, firmware file handling, program/verify command, or flashing code.
