from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from openups.safety import SafeWriteCoordinator, WriteSafetyError


class MockConfiguration:
    def __init__(self) -> None:
        self.values = {"OUT_VOLTAGE": 12.0, "CELLS": 2.0}
        self.writes = 0

    def read_all(self):
        return dict(self.values)

    def write_values(self, changes):
        self.writes += 1
        self.values.update(changes)


class BrokenReadbackConfiguration(MockConfiguration):
    def write_values(self, changes):
        self.writes += 1


class SafetyTests(unittest.TestCase):
    def test_default_gate_prevents_any_read_or_write(self) -> None:
        adapter = MockConfiguration()
        with self.assertRaisesRegex(WriteSafetyError, "disabled"):
            SafeWriteCoordinator().apply(adapter, {"OUT_VOLTAGE": 13}, ".", lambda _diff: True)
        self.assertEqual(adapter.writes, 0)

    def test_enabled_mock_pipeline_backs_up_confirms_writes_and_verifies(self) -> None:
        adapter = MockConfiguration()
        seen_diff = []
        with tempfile.TemporaryDirectory() as directory:
            result = SafeWriteCoordinator(allow_hardware_writes=True).apply(
                adapter,
                {"OUT_VOLTAGE": 13.0},
                directory,
                lambda diff: not seen_diff.extend(diff),
            )
            self.assertTrue(result.verified)
            self.assertTrue(Path(result.backup_path).exists())
            self.assertEqual(adapter.values["OUT_VOLTAGE"], 13.0)
            self.assertEqual(seen_diff[0].old_value, 12.0)

    def test_mock_readback_failure_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(WriteSafetyError, "Readback verification failed"):
                SafeWriteCoordinator(allow_hardware_writes=True).apply(
                    BrokenReadbackConfiguration(),
                    {"OUT_VOLTAGE": 13.0},
                    directory,
                    lambda _diff: True,
                )

    def test_validation_runs_after_backup_and_before_write(self) -> None:
        adapter = MockConfiguration()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(WriteSafetyError, "Validation failed"):
                SafeWriteCoordinator(allow_hardware_writes=True).apply(
                    adapter,
                    {"OUT_VOLTAGE": 30.0},
                    directory,
                    lambda _diff: True,
                    validate=lambda _changes: ["OUT_VOLTAGE exceeds 24 V"],
                )
            self.assertEqual(adapter.writes, 0)
            self.assertEqual(len(list(Path(directory).glob("*.json"))), 1)


if __name__ == "__main__":
    unittest.main()
