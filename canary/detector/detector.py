"""
Detector engine.

Subscribes to the bus, runs every rule against each frame, and
collects Alerts. State updates after rules run, so each rule sees
history up to but not including the current frame.
"""

from typing import Optional

from ..bus.frame import CANFrame
from .alert import Alert
from .baseline import IDBaseline, IDState
from .rules import DEFAULT_RULES


class Detector:
    def __init__(self, baseline: dict[int, IDBaseline], rules=None):
        self.baseline = baseline
        self.rules = rules if rules is not None else DEFAULT_RULES
        self._state: dict[int, IDState] = {}
        self.alerts: list[Alert] = []

    def _state_for(self, arbitration_id: int) -> IDState:
        if arbitration_id not in self._state:
            self._state[arbitration_id] = IDState()
        return self._state[arbitration_id]

    def inspect(self, frame: CANFrame) -> None:
        """Callback for bus.subscribe(). Runs all rules against this
        frame, then updates tracked state."""
        id_baseline: Optional[IDBaseline] = self.baseline.get(frame.arbitration_id)
        state = self._state_for(frame.arbitration_id)

        for rule in self.rules:
            alert = rule.check(frame, id_baseline, state)
            if alert is not None:
                self.alerts.append(alert)

        state.last_timestamp = frame.timestamp
        state.last_payload = frame.data
        state.recent_timestamps.append(frame.timestamp)

    def last_payload_for(self, arbitration_id: int) -> Optional[bytes]:
        """Most recently observed payload for an ID, if any."""
        state = self._state.get(arbitration_id)
        return state.last_payload if state else None

    def last_seen_for(self, arbitration_id: int) -> Optional[float]:
        """Timestamp this ID was last observed at, if any."""
        state = self._state.get(arbitration_id)
        return state.last_timestamp if state else None

    def alerts_by_severity(self, severity) -> list[Alert]:
        return [a for a in self.alerts if a.severity == severity]

    def clear_alerts(self) -> None:
        self.alerts.clear()
