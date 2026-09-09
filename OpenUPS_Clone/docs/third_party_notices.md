# Third-party protocol data notice

`openups/standard_hid.py` uses D004 calibration constants and thermistor transfer-point data published in the Network UPS Tools OpenUPS HID subdriver:

- Source: <https://github.com/networkupstools/nut/blob/master/drivers/openups-hid.c>
- Relevant upstream author: Nicu Pavel (`npavel@mini-box.com`), 2012, with the other authors listed in the source header
- Upstream license: GNU General Public License, version 2 or later

The Python transport and report decoder in this project were independently written against the USB report descriptor and feature-report output captured from the user's physical board. No legacy Mini-Box binary or DLL is bundled or loaded.
