from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParameterDefinition:
    name: str
    unit: str
    description: str
    documented_default: str
    minimum: float | None = None
    maximum: float | None = None
    integer_only: bool = False
    writable: bool = False


def _p(
    name: str,
    unit: str,
    description: str,
    default: str,
    minimum: float | None = None,
    maximum: float | None = None,
    integer_only: bool = False,
) -> ParameterDefinition:
    return ParameterDefinition(name, unit, description, default, minimum, maximum, integer_only)


# Names, units, and defaults are transcribed from the supplied 2019 hardware manual.
# No byte index or wire encoding is assigned because those were not supplied.
PARAMETERS = (
    _p("OPENUPSMODE", "enum", "Auto-restart behavior when input power is present.", "0", 0, 1, True),
    _p("UPS_CONFIG", "bitfield", "Enable/disable output, charge, balance, filtering, and pulse modules.", "all enabled", 0, 127, True),
    _p("UPS_INIT_DELAY_TOUT", "s", "Initial delay before starting the UPS.", "1", 0),
    _p("UPS_VIN_MAX_SHUTDOWN", "V", "Input overvoltage shutdown threshold.", "35"),
    _p("UPS_VIN_MIN_START", "V", "Input voltage threshold for start/use of VIN.", "11"),
    _p("UPS_VIN_MIN_STOP", "V", "Input voltage threshold for switching to battery.", "6"),
    _p("UPS_VCELL_MIN_START", "V", "Minimum battery/cell threshold for battery start.", "11.7"),
    _p("UPS_VCELL_MIN_STOP", "V", "Battery undervoltage shutdown threshold.", "11.4"),
    _p("UPS_VBAT_UVP_OFF_TOUT", "s", "Undervoltage debounce before shutdown.", "5", 0),
    _p("UPS_HARDOFF_TOUT", "s", "Grace period after motherboard shutdown pulse.", "60", 0),
    _p("UPS_SWITCHOVER_VBAT_TOUT", "ms", "Hold time before switching back from battery.", "1000", 0),
    _p("UPS_SWITCHOVER_VIN_TOUT", "ms", "Hold time before switching back from VIN.", "1", 0),
    _p("DCHG_IMAX", "mA", "Maximum allowed discharge current.", "10000", 0),
    _p("CAPACITY", "mAh", "Battery capacity for fuel-gauge calculations.", "7000", 1),
    _p("CHG_BAT_TYPE", "enum", "Battery chemistry: 0 PbSO4, 1 LiFePO4, 2 LiPo.", "0", 0, 2, True),
    _p("CHG_VCOND", "V", "Conditioning/pre-charge voltage.", "11.2", 0),
    _p("CHG_ICOND", "mA", "Conditioning/pre-charge current.", "100", 0, 3000),
    _p("CHG_TCOND", "s", "Conditioning/pre-charge time.", "30", 0),
    _p("CHG_IBULK", "mA", "Fast-charge current limit.", "1750", 0, 3000),
    _p("CHG_BULK_STOP_VOLTAGE", "V/cell", "Maximum bulk-charge voltage.", "14.1", 0),
    _p("CHG_HYSTERESIS", "V/cell", "Charge overvoltage allowance.", "0.1", 0),
    _p("CHG_START_VOLTAGE", "V/cell", "Charge-start / PbSO4 float voltage.", "13.5", 0),
    _p("CHG_IMIN", "mA", "End-of-charge current threshold.", "290", 0, 3000),
    _p("CHG_IFLOAT", "mA", "PbSO4 float-charge current limit.", "100", 0, 3000),
    _p("CHG_GLOBAL_TOUT", "min", "Global charge timeout.", "1260", 0),
    _p("CHG_TOPPING_TIMER", "s", "Lithium topping-charge resting period.", "1800", 0),
    _p("CHG_TEMP_PCB", "deg C", "PCB temperature for charge-current limiting.", "60"),
    _p("CHG_ILIMIT_TEMP_PCB", "mA", "Charge-current reduction step when hot.", "50", 0, 3000),
    _p("CHG_FREQUENCY", "kHz", "Charger converter working frequency.", "333", 0),
    _p("CELLS", "pcs", "Number of configured cells.", "1", 1, 6, True),
    _p("BAL_VCELL_MIN", "V", "Minimum cell voltage at which balancing is allowed.", "3", 0, 4.2),
    _p("BAL_VCELL_DIFF_START", "V", "Cell difference that starts balancing.", "0.07", 0),
    _p("BAL_VCELL_DIFF_STOP", "V", "Cell difference that stops balancing.", "0.04", 0),
    _p("OUT_VOLTAGE", "V", "Regulated output voltage.", "12", 5, 24),
    _p("OUT_FREQUENCY", "kHz", "Output converter working frequency.", "300", 0),
    _p("OUT_MAX_REGULATOR_STEP", "count", "Maximum output regulation step count.", "100", 0, 255, True),
    _p("MOB_ONOFF_TOUT", "ms", "Motherboard power-switch pulse duration.", "500", 0),
    _p("POUT_LO", "W", "Low output-power threshold for motherboard sensing.", "2", 0),
    _p("POUT_HI", "W", "High output-power threshold for motherboard sensing.", "6", 0),
    _p("OCV_SOC0", "V", "Open-circuit voltage for 0% initial SOC.", "11.8"),
    _p("OCV_SOC10", "V", "Open-circuit voltage for 10% initial SOC.", "11.9"),
    _p("OCV_SOC25", "V", "Open-circuit voltage for 25% initial SOC.", "12.0"),
    _p("OCV_SOC50", "V", "Open-circuit voltage for 50% initial SOC.", "12.3"),
    _p("OCV_SOC75", "V", "Open-circuit voltage for 75% initial SOC.", "12.6"),
    _p("OCV_SOC100", "V", "Open-circuit voltage for 100% initial SOC.", "12.8"),
    _p("WRITE_COUNT", "cycles", "Flash write count (read-only).", "read from device", 0, None, True),
)

PARAMETER_BY_NAME = {parameter.name: parameter for parameter in PARAMETERS}


def validate_parameter_value(definition: ParameterDefinition, value: float) -> list[str]:
    errors: list[str] = []
    if definition.integer_only and not float(value).is_integer():
        errors.append(f"{definition.name} requires a whole number")
    if definition.minimum is not None and value < definition.minimum:
        errors.append(f"{definition.name} must be >= {definition.minimum:g} {definition.unit}")
    if definition.maximum is not None and value > definition.maximum:
        errors.append(f"{definition.name} must be <= {definition.maximum:g} {definition.unit}")
    if not definition.writable:
        errors.append("Hardware writes are disabled until the wire index/encoding is verified")
    return errors

