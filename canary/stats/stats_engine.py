"""
Stats engine.

Subscribes to the bus and maintains running aggregates for the
dashboard: per-ID rates, top talkers, arbitration latency, and bus
utilization. Pure consumer, no bus-internal access.
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

from ..bus.bus import BusInterface
from ..bus.frame import CANFrame

LATENCY_WINDOW = 100
RATE_WINDOW_SECONDS = 1.0


@dataclass
class IDStats:
    frame_count: int = 0
    byte_count: int = 0
    recent_timestamps: deque = field(default_factory=lambda: deque(maxlen=200))


class StatsEngine:
    def __init__(self, bus: BusInterface):
        self.bus = bus
        self._by_id: dict[int, IDStats] = defaultdict(IDStats)
        self._by_source: dict[str, int] = defaultdict(int)
        self._latencies: deque = deque(maxlen=LATENCY_WINDOW)
        self._first_observed_time: float = None
        self._last_observed_time: float = None
        self.total_frames = 0

    def observe(self, frame: CANFrame, now: float = None) -> None:
        """Callback for bus.subscribe(). `now` lets a caller supply a
        clock (e.g. simulated time) instead of wall time."""
        if now is None:
            now = time.monotonic()

        if self._first_observed_time is None:
            self._first_observed_time = now
        self._last_observed_time = now

        stats = self._by_id[frame.arbitration_id]
        stats.frame_count += 1
        stats.byte_count += frame.dlc
        stats.recent_timestamps.append(now)

        self._by_source[frame.source_ecu] += 1
        self._latencies.append(max(0.0, now - frame.timestamp))
        self.total_frames += 1

    def message_rate(self, arbitration_id: int) -> float:
        """Frames/sec for one ID, based on its recent timestamp window."""
        stats = self._by_id.get(arbitration_id)
        if not stats or len(stats.recent_timestamps) < 2:
            return 0.0
        span = stats.recent_timestamps[-1] - stats.recent_timestamps[0]
        if span <= 0:
            return 0.0
        return (len(stats.recent_timestamps) - 1) / span

    def top_talkers(self, n: int = 5) -> list[tuple[str, int]]:
        return sorted(self._by_source.items(), key=lambda kv: kv[1], reverse=True)[:n]

    def average_latency_ms(self) -> float:
        if not self._latencies:
            return 0.0
        return (sum(self._latencies) / len(self._latencies)) * 1000

    def bus_utilization(self) -> float:
        if self._first_observed_time is None or self._last_observed_time is None:
            return 0.0
        elapsed = self._last_observed_time - self._first_observed_time
        return self.bus.utilization(elapsed) if hasattr(self.bus, "utilization") else 0.0

    def snapshot(self) -> dict:
        """Structured dict for the dashboard to render."""
        return {
            "total_frames": self.total_frames,
            "bus_utilization_pct": round(self.bus_utilization() * 100, 2),
            "average_latency_ms": round(self.average_latency_ms(), 3),
            "top_talkers": self.top_talkers(),
            "dropped_frames": getattr(self.bus, "frames_dropped", 0),
            "per_id_rates": {
                arb_id: round(self.message_rate(arb_id), 2) for arb_id in self._by_id
            },
        }
