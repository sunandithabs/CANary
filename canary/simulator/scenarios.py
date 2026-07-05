"""
Attack scenarios.

Each function injects one attack pattern into a running Simulator.
Used to validate detection rules and to generate sample datasets.
"""

from ..bus.frame import CANFrame
from .simulator import Simulator


def inject_spoofing(sim: Simulator) -> None:
    """A frame using engine_ecu's ID (0x0C0) but from a fake source."""
    sim.inject(CANFrame(
        arbitration_id=0x0C0, data=bytes(8), timestamp=sim.time, source_ecu="attacker_ecu",
    ))


def inject_malformed_frame(sim: Simulator) -> None:
    """engine_ecu's ID with the wrong payload size."""
    sim.inject(CANFrame(
        arbitration_id=0x0C0, data=b"\x01\x02", timestamp=sim.time, source_ecu="engine_ecu",
    ))


def inject_replay_attack(sim: Simulator, captured_payload: bytes) -> None:
    """Resends a previously captured payload out of its normal rhythm."""
    sim.inject(CANFrame(
        arbitration_id=0x0C0, data=captured_payload, timestamp=sim.time, source_ecu="engine_ecu",
    ))


def inject_flooding(sim: Simulator, frame_count: int = 100) -> None:
    """Bursts frames on engine_ecu's ID far faster than its baseline
    period allows."""
    for i in range(frame_count):
        sim.inject(CANFrame(
            arbitration_id=0x0C0, data=bytes([i % 256] + [0] * 7),
            timestamp=sim.time, source_ecu="engine_ecu",
        ))
        sim.time += 0.0001  # far below the 10ms baseline period
