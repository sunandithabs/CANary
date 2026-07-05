"""
Simulator.

Owns sequencing: advances simulated time, lets ECUs decide when to
send, ticks the bus, and lets logger/detector/stats consume via their
subscribe() callbacks. No detection or telemetry logic of its own.
"""

from ..bus.bus import SimulatedBus
from ..bus.frame import CANFrame
from ..ecu.ecu import ECU, build_sample_ecus
from ..detector.detector import Detector
from ..detector.baseline import build_baseline_from_ecus
from ..logger.logger import CANLogger
from ..stats.stats_engine import StatsEngine


class Simulator:
    def __init__(self, log_path: str, tick_seconds: float = 0.001):
        self.bus = SimulatedBus()
        self.tick_seconds = tick_seconds
        self.time = 0.0

        self.ecus: list[ECU] = build_sample_ecus(self.bus)
        baseline = build_baseline_from_ecus(self.ecus)

        self.logger = CANLogger(log_path)
        self.detector = Detector(baseline)
        self.stats = StatsEngine(self.bus)

        self.bus.subscribe(self.logger.log_frame)
        self.bus.subscribe(self.detector.inspect)
        self.bus.subscribe(lambda frame: self.stats.observe(frame, now=self.time))

    def step(self) -> None:
        """Advances one tick: ECUs check their schedule, bus resolves
        arbitration for anything offered this tick."""
        for ecu in self.ecus:
            ecu.maybe_send(self.time)
        self.bus.tick()
        self.time += self.tick_seconds

    def run(self, ticks: int) -> None:
        for _ in range(ticks):
            self.step()

    def inject(self, frame: CANFrame) -> None:
        """Injects a frame directly onto the bus, bypassing ECU
        scheduling. Used for attack scenarios."""
        self.bus.offer(frame)
        self.bus.tick()

    def close(self) -> None:
        self.logger.flush()
        self.logger.close()
