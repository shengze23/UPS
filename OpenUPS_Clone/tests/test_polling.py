from __future__ import annotations

import unittest

from openups.models import mock_snapshot
from openups.service import PollingLoop


class FlakyClient:
    def __init__(self) -> None:
        self.calls = 0
        self.closes = 0

    def poll(self):
        self.calls += 1
        if self.calls == 1:
            raise OSError("device unplugged")
        return mock_snapshot(self.calls)

    def close(self) -> None:
        self.closes += 1


class PollingTests(unittest.TestCase):
    def test_failure_closes_then_next_cycle_reconnects(self) -> None:
        client = FlakyClient()
        snapshots = []
        errors = []
        waits = []

        def waiter(seconds: float) -> bool:
            waits.append(seconds)
            return False

        loop = PollingLoop(
            client,
            poll_interval_ms=500,
            reconnect_interval_ms=1200,
            on_snapshot=snapshots.append,
            on_error=errors.append,
            waiter=waiter,
        )
        loop.run(max_cycles=2)
        self.assertEqual(client.calls, 2)
        self.assertFalse(snapshots[0].connected)
        self.assertTrue(snapshots[1].connected)
        self.assertIn("device unplugged", errors[0])
        self.assertEqual(waits, [1.2, 0.5])
        self.assertGreaterEqual(client.closes, 2)


if __name__ == "__main__":
    unittest.main()

