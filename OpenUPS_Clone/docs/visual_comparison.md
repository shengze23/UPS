# Visual comparison

References: figures 1-3 from both supplied OpenUPS software manuals. The 2014 manual in `Mini-Box.Com.zip` has the sharper screenshots and was used for proportions and label order.

| Region | Legacy reference | Clone | Remaining difference |
|---|---|---|---|
| Window | Fixed Windows desktop window | Fixed 790 x 835 logical-pixel window | Native title chrome varies by Windows version and DPI |
| Header | Power icon, capacity, RTE, VIN/VBAT/VOUT | Same information order and grouping | Clone uses a text power badge; Mini-Box artwork was not copied |
| Navigation | Status, Settings, Minimize button row | Same order and behavior | Focus/pressed rendering follows installed Qt Windows style |
| Status cells | Cell6 to Cell1, On/Bal columns | Same order and columns | Exact MFC checkbox metrics differ slightly |
| Status flags | Two legacy columns | Same labels/order in two columns | Some meanings remain unverified until protocol capture |
| Status metrics | Currents, temperature, state bytes, debug, power, log | Same plus input current and converter frequencies requested by the task | Field values unavailable without a verified profile |
| Settings | Wizard, individual parameter setup, transfers and state progress | Same hierarchy | Added explicit read-only labels/tooltips |
| Battery Wizard | Five inputs, result list, connection diagram | Same input structure and a conservative wiring reference | Calculated values and Apply are disabled because formulas are incomplete |

The layout uses Qt logical pixels and layouts instead of absolute child coordinates, so it should retain proportions at 100%, 125% and 150% Windows scaling. Final pixel matching must be checked on the target Windows host because macOS cannot render the Windows platform style or title bar faithfully.

Offscreen mock renders were inspected at scale factors 1.0, 1.25 and 1.5. No label, field, button, group-box border or footer text was clipped or overlapped at those scales.
