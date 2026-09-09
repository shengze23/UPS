from __future__ import annotations

import csv
from pathlib import Path
import tempfile
import unittest

from openups.logging_service import CSV_COLUMNS, CsvTelemetryLogger
from openups.models import mock_snapshot


class CsvLoggingTests(unittest.TestCase):
    def test_header_is_written_once_and_rows_include_six_cells(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "upslog.csv"
            logger = CsvTelemetryLogger(path)
            logger.append(mock_snapshot(0))
            logger.append(mock_snapshot(1))
            with path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.reader(stream))
            self.assertEqual(tuple(rows[0]), CSV_COLUMNS)
            self.assertEqual(len(rows), 3)
            self.assertEqual(len(rows[1]), len(CSV_COLUMNS))


if __name__ == "__main__":
    unittest.main()

