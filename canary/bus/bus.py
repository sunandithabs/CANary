"""
CAN bus core.

Arbitration is modeled as strict priority ordering (lower ID wins).
Tracks bus utilization against a configured bit rate.
"""

import heapq
import itertools
from typing import Callable, List

from .frame import CANFrame

# Rough overhead per classic CAN frame in bits (SOF + arbitration + control +
# CRC + ACK + EOF + stuffing headroom), used for utilization estimates.
FRAME_OVERHEAD_BITS = 47


class BusInterface:
    """Contract every bus implementation must satisfy. Callers should
    depend on this, not on SimulatedBus directly."""

    def subscribe(self, callback) -> None:
        raise NotImplementedError

    def offer(self, frame) -> None:
        raise NotImplementedError


class SimulatedBus(BusInterface):
    def __init__(self, bitrate_bps: int = 500_000):
        self.bitrate_bps = bitrate_bps
        self._pending: List[tuple] = []   # heap of (arbitration_id, seq, frame)
        self._seq_counter = itertools.count()
        self._subscribers: List[Callable[[CANFrame], None]] = []
        self._bits_transmitted = 0
        self._window_start = None
        self.frames_transmitted = 0
        self.frames_dropped = 0

    def subscribe(self, callback: Callable[[CANFrame], None]) -> None:
        """Register a listener (logger, detector, dashboard) for every
        frame that wins arbitration and is transmitted."""
        self._subscribers.append(callback)

    def offer(self, frame: CANFrame) -> None:
        """An ECU offers a frame to the bus. It queues for arbitration
        rather than transmitting immediately, so simultaneous offers
        resolve by priority (lowest arbitration_id first)."""
        heapq.heappush(self._pending, (frame.arbitration_id, next(self._seq_counter), frame))

    def tick(self) -> None:
        """Resolve one round of arbitration: the highest-priority pending
        frame transmits, all others remain queued for the next tick."""
        if not self._pending:
            return
        _, _, frame = heapq.heappop(self._pending)
        self._transmit(frame)

    def _transmit(self, frame: CANFrame) -> None:
        frame_bits = FRAME_OVERHEAD_BITS + frame.dlc * 8
        self._bits_transmitted += frame_bits
        self.frames_transmitted += 1
        for callback in self._subscribers:
            callback(frame)

    def utilization(self, elapsed_seconds: float) -> float:
        """Bus utilization as a fraction of capacity over the elapsed window.
        Caller tracks elapsed_seconds; the bus only tracks bits transmitted."""
        if elapsed_seconds <= 0:
            return 0.0
        capacity_bits = self.bitrate_bps * elapsed_seconds
        return min(self._bits_transmitted / capacity_bits, 1.0)

    def reset_utilization_counter(self) -> None:
        self._bits_transmitted = 0

    @property
    def pending_count(self) -> int:
        return len(self._pending)
