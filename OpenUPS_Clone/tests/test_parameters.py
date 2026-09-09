from __future__ import annotations

import unittest

from openups.parameters import PARAMETER_BY_NAME, validate_parameter_value


class ParameterTests(unittest.TestCase):
    def test_manual_units_are_recorded(self) -> None:
        self.assertEqual(PARAMETER_BY_NAME["OUT_VOLTAGE"].unit, "V")
        self.assertEqual(PARAMETER_BY_NAME["CHG_IBULK"].unit, "mA")

    def test_documented_output_range_is_checked(self) -> None:
        errors = validate_parameter_value(PARAMETER_BY_NAME["OUT_VOLTAGE"], 25)
        self.assertTrue(any("<= 24" in error for error in errors))

    def test_cell_count_is_integer_in_range(self) -> None:
        definition = PARAMETER_BY_NAME["CELLS"]
        self.assertTrue(any("whole number" in error for error in validate_parameter_value(definition, 2.5)))
        self.assertTrue(any(">= 1" in error for error in validate_parameter_value(definition, 0)))
        self.assertTrue(any("<= 6" in error for error in validate_parameter_value(definition, 7)))

    def test_all_parameters_remain_non_writable(self) -> None:
        self.assertTrue(all(not definition.writable for definition in PARAMETER_BY_NAME.values()))


if __name__ == "__main__":
    unittest.main()

