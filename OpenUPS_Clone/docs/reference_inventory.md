# Reference inventory

Inventory date: 2026-07-28. Originals were read in place and were not modified. SHA-256 hashes provide a later integrity check.

| Reference | Relevant contents | SHA-256 |
|---|---|---|
| `CODEX_OPENUPS_CLONE_PROMPT.md` | Scope, device identity, safety and acceptance criteria | `ef90a2c9d5ba55768dc7e6e44454e2c5ece47a46883136adbaf0f8efede0c4f2` |
| `PWR-OpenUPS-software-manual.pdf` | Eight pages; Status, Settings and Battery Wizard screenshots | `6e1449ec8f6b66d561aff4b4a519c3b0bac74867ad40668186c91f48af0588bb` |
| `PWR-OpenUPS-hardware-manual (1).pdf` | Twelve pages; electrical limits, wiring, modes and parameter names/defaults | `1c5698c13442367d3b81b8e9e2e462b534899ef5787533055ccc65e6a0ee04ee` |
| `PWR-OpenUPS-flashing-guide.pdf` | One page; programmer/bootloader procedure, inspected only | `456fa06f66f9b7a9580595cd937c6f542b1ddce04e7fb8540dc5d30c8946e974` |
| `Mini-Box.Com.zip` | 59 entries, including legacy binaries, two manuals, skin assets and public DLL usage samples | `198f4fce1b72d8fc1b428259bee0ac83527699e5288d7f7d83c92a25dd50e96f` |
| `check_openups.py` | hidapi enumeration only; no command packets | `364749007f1d41126782c1a16bc4a45f00d056123ac6067147c36eadf89d98f0` |
| `connect_openups.py` | Opens by VID/PID and passively reads; no command packets and no collection selection | `1e0ece091c07fd0995482144e8bb126d277036e3fe69ea41d89f52d39b9cd9d3` |
| `openups_exact_open_test.py` | SetupAPI/HID collection descriptions and Windows open-mode testing | `a90c209c6636422237ec1a43d12e8662488602dda3b52d4683a780b129995ef3` |
| `openups_hid_diagnostic.py` | SetupAPI/HID enumeration and capabilities | `dfa7b679a6c762067630e2711f2df441b37892361a0692b076d0564275e27936` |
| `openups_standard_hid_probe.txt` | User's D004 revision 0003 descriptor, feature reports and input reports | `369cdcd84784e863579188845d5fbb4838d32d506c4a525409f926e452673a53` |

The ZIP's public C++, C# and Visual Basic examples call `OpenUPSLib.dll` getters. They expose value names and polling guidance but not raw HID request bytes, report framing, response offsets or parameter wire encodings. The legacy DLL and EXE are not included in the new project and are never loaded by it.

Public D004 calibration and thermistor data used by the standard telemetry path are attributed separately in `docs/third_party_notices.md`.
