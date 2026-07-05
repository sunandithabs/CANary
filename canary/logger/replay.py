"""
Replay engine.

Reads a CSV log and pushes frames back onto a bus, preserving the
original timing gaps (scaled by a speed multiplier).
"""

import csv
import time
from pathlib import Path
from typing import Iterator

from ..bus.bus import BusInterface
from ..bus.frame import CANFrame


def read_log(log_path: str | Path) -> Iterator[CANFrame]:
    """Parses a CSV log file back into CANFrame objects, in file order."""
    with open(log_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield CANFrame(
                arbitration_id=int(row["arbitration_id"], 16),
                data=bytes.fromhex(row["data_hex"]),
                extended=bool(int(row["extended"])),
                timestamp=float(row["timestamp"]),
                source_ecu=row["source_ecu"],
            )


def replay_log(log_path: str | Path, bus: BusInterface, speed: float = 1.0) -> int:
    """Replays a log file onto the bus, sleeping between frames to
    reproduce the original timing (scaled by `speed`; speed=2.0 plays
    twice as fast, speed=0 disables sleeping entirely for fast tests).

    Returns the number of frames replayed.
    """
    frames = list(read_log(log_path))
    count = 0
    prev_timestamp = None

    for frame in frames:
        if speed > 0 and prev_timestamp is not None:
            gap = (frame.timestamp - prev_timestamp) / speed
            if gap > 0:
                time.sleep(gap)
        bus.offer(frame)
        bus.tick()
        count += 1
        prev_timestamp = frame.timestamp

    return count
