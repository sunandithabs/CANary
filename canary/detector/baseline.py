"""
Baseline and per-ID state tracking.

IDBaseline describes normal behavior for one arbitration ID: who
sends it, how often, how big. IDState tracks rolling per-ID history
used for timing and repetition checks.
"""

from collections import deque
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class IDBaseline:
    expected_source: str
    expected_dlc: int
    expected_period_seconds: float


@dataclass
class IDState:
    last_timestamp: Optional[float] = None
    last_payload: Optional[bytes] = None
    recent_timestamps: deque = field(default_factory=lambda: deque(maxlen=50))


def build_baseline_from_ecus(ecus) -> dict[int, IDBaseline]:
    """Convenience: derive a baseline dict straight from a list of ECU
    objects (Module 2), so tests and demos don't have to hand-write one."""
    baseline = {}
    for ecu in ecus:
        profile = ecu.profile
        baseline[profile.arbitration_id] = IDBaseline(
            expected_source=profile.name,
            expected_dlc=len(profile.payload_fn()),
            expected_period_seconds=profile.period_seconds,
        )
    return baseline
