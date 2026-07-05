"""
ECU node simulation.

Each ECU sends a CAN frame on a schedule with its own arbitration ID
and payload behavior, plus timing jitter for realism.
"""

import random
import time
from dataclasses import dataclass
from typing import Callable

from ..bus.bus import BusInterface
from ..bus.frame import CANFrame


@dataclass
class ECUProfile:
    """Describes how one ECU behaves: which ID it owns, how often it
    talks, and how it builds its payload each time."""
    name: str
    arbitration_id: int
    period_seconds: float
    jitter_seconds: float
    payload_fn: Callable[[], bytes]
    extended: bool = False


class ECU:
    def __init__(self, profile: ECUProfile, bus: BusInterface):
        self.profile = profile
        self.bus = bus
        self._next_send_time = 0.0
        self.frames_sent = 0

    def maybe_send(self, now: float) -> None:
        """Called every simulation step. Sends a frame only if this
        ECU's schedule says it's time, then reschedules itself."""
        if now < self._next_send_time:
            return

        frame = CANFrame(
            arbitration_id=self.profile.arbitration_id,
            data=self.profile.payload_fn(),
            extended=self.profile.extended,
            timestamp=now,
            source_ecu=self.profile.name,
        )
        self.bus.offer(frame)
        self.frames_sent += 1

        jitter = random.uniform(-self.profile.jitter_seconds, self.profile.jitter_seconds)
        self._next_send_time = now + self.profile.period_seconds + jitter


# ---- Example payload generators for realistic sample ECUs ----

def engine_rpm_payload_fn():
    """Simulates RPM wobbling between 800 (idle) and 3000, encoded as
    a 16-bit big-endian value in the first two bytes."""
    state = {"rpm": 800}

    def _generate() -> bytes:
        state["rpm"] += random.randint(-50, 80)
        state["rpm"] = max(800, min(3000, state["rpm"]))
        rpm = state["rpm"]
        return bytes([(rpm >> 8) & 0xFF, rpm & 0xFF, 0, 0, 0, 0, 0, 0])

    return _generate


def door_sensor_payload_fn():
    """Simulates a door open/closed flag, mostly closed, rarely opens."""
    def _generate() -> bytes:
        is_open = 1 if random.random() < 0.02 else 0
        return bytes([is_open, 0, 0, 0, 0, 0, 0, 0])
    return _generate


def build_sample_ecus(bus: BusInterface) -> list[ECU]:
    """Convenience factory: a small realistic fleet of ECUs for demos
    and tests."""
    return [
        ECU(ECUProfile(
            name="engine_ecu", arbitration_id=0x0C0,
            period_seconds=0.01, jitter_seconds=0.001,
            payload_fn=engine_rpm_payload_fn(),
        ), bus),
        ECU(ECUProfile(
            name="brake_ecu", arbitration_id=0x1A0,
            period_seconds=0.02, jitter_seconds=0.002,
            payload_fn=lambda: bytes([0, 0, 0, 0, 0, 0, 0, 0]),
        ), bus),
        ECU(ECUProfile(
            name="door_ecu", arbitration_id=0x3F0,
            period_seconds=0.5, jitter_seconds=0.05,
            payload_fn=door_sensor_payload_fn(),
        ), bus),
    ]
