"""
Traffic logger.

Subscribes to the bus and writes every transmitted frame to a CSV log:
timestamp,arbitration_id,extended,dlc,data_hex,source_ecu
"""

import csv
from pathlib import Path

from ..bus.frame import CANFrame

FIELDNAMES = ["timestamp", "arbitration_id", "extended", "dlc", "data_hex", "source_ecu"]


class CANLogger:
    def __init__(self, log_path: str | Path):
        self.log_path = Path(log_path)
        self._file = open(self.log_path, "w", newline="")
        self._writer = csv.DictWriter(self._file, fieldnames=FIELDNAMES)
        self._writer.writeheader()
        self.frames_logged = 0

    def log_frame(self, frame: CANFrame) -> None:
        """Callback suitable for bus.subscribe(). Writes one row per frame."""
        self._writer.writerow({
            "timestamp": frame.timestamp,
            "arbitration_id": hex(frame.arbitration_id),
            "extended": int(frame.extended),
            "dlc": frame.dlc,
            "data_hex": frame.data.hex(),
            "source_ecu": frame.source_ecu,
        })
        self.frames_logged += 1

    def flush(self) -> None:
        self._file.flush()

    def close(self) -> None:
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
