"""
Detection rules.

Each rule inspects one frame against its baseline and history, and
returns an Alert or None. Rules are independent; the Detector runs
them all in sequence per frame.
"""

from typing import Optional

from ..bus.frame import CANFrame
from .alert import Alert, Severity
from .baseline import IDBaseline, IDState


class UnknownIDRule:
    """A frame using an arbitration ID with no known baseline."""

    name = "unknown_id"

    def check(self, frame: CANFrame, baseline: Optional[IDBaseline], state: IDState) -> Optional[Alert]:
        if baseline is None:
            return Alert(
                timestamp=frame.timestamp, severity=Severity.HIGH, rule_name=self.name,
                arbitration_id=frame.arbitration_id, source_ecu=frame.source_ecu,
                message="frame from an arbitration ID with no known baseline",
            )
        return None


class SourceMismatchRule:
    """A known ID sent by a different source than the one that owns it."""

    name = "source_mismatch"

    def check(self, frame: CANFrame, baseline: Optional[IDBaseline], state: IDState) -> Optional[Alert]:
        if baseline and frame.source_ecu != baseline.expected_source:
            return Alert(
                timestamp=frame.timestamp, severity=Severity.CRITICAL, rule_name=self.name,
                arbitration_id=frame.arbitration_id, source_ecu=frame.source_ecu,
                message=f"expected source '{baseline.expected_source}', got '{frame.source_ecu}'",
            )
        return None


class MalformedFrameRule:
    """A known ID's payload size (DLC) doesn't match its baseline."""

    name = "malformed_frame"

    def check(self, frame: CANFrame, baseline: Optional[IDBaseline], state: IDState) -> Optional[Alert]:
        if baseline and frame.dlc != baseline.expected_dlc:
            return Alert(
                timestamp=frame.timestamp, severity=Severity.MEDIUM, rule_name=self.name,
                arbitration_id=frame.arbitration_id, source_ecu=frame.source_ecu,
                message=f"expected DLC {baseline.expected_dlc}, got {frame.dlc}",
            )
        return None


class ImpossibleFrequencyRule:
    """A known ID repeats faster than its baseline period allows."""

    name = "impossible_frequency"
    MIN_INTERVAL_FRACTION = 0.3  # below 30% of expected period is implausible

    def check(self, frame: CANFrame, baseline: Optional[IDBaseline], state: IDState) -> Optional[Alert]:
        if baseline is None or state.last_timestamp is None:
            return None
        interval = frame.timestamp - state.last_timestamp
        min_plausible = baseline.expected_period_seconds * self.MIN_INTERVAL_FRACTION
        if interval < min_plausible:
            return Alert(
                timestamp=frame.timestamp, severity=Severity.HIGH, rule_name=self.name,
                arbitration_id=frame.arbitration_id, source_ecu=frame.source_ecu,
                message=f"interval {interval*1000:.2f}ms is below plausible minimum "
                        f"{min_plausible*1000:.2f}ms for this ID",
            )
        return None


class FloodingRule:
    """An ID's recent send rate far exceeds its baseline rate."""

    name = "flooding"
    RATE_MULTIPLIER_THRESHOLD = 5.0

    def check(self, frame: CANFrame, baseline: Optional[IDBaseline], state: IDState) -> Optional[Alert]:
        if baseline is None or len(state.recent_timestamps) < state.recent_timestamps.maxlen:
            return None
        window_span = state.recent_timestamps[-1] - state.recent_timestamps[0]
        if window_span <= 0:
            return None
        observed_rate = len(state.recent_timestamps) / window_span
        expected_rate = 1.0 / baseline.expected_period_seconds
        if observed_rate > expected_rate * self.RATE_MULTIPLIER_THRESHOLD:
            return Alert(
                timestamp=frame.timestamp, severity=Severity.CRITICAL, rule_name=self.name,
                arbitration_id=frame.arbitration_id, source_ecu=frame.source_ecu,
                message=f"observed rate {observed_rate:.1f} Hz exceeds "
                        f"{self.RATE_MULTIPLIER_THRESHOLD}x baseline ({expected_rate:.1f} Hz)",
            )
        return None


class ReplayAttackRule:
    """An identical payload for the same ID repeats sooner than normal
    drift would allow."""

    name = "replay_attack"

    def check(self, frame: CANFrame, baseline: Optional[IDBaseline], state: IDState) -> Optional[Alert]:
        if baseline is None or state.last_payload is None or state.last_timestamp is None:
            return None
        interval = frame.timestamp - state.last_timestamp
        if frame.data == state.last_payload and interval < baseline.expected_period_seconds * 0.5:
            return Alert(
                timestamp=frame.timestamp, severity=Severity.HIGH, rule_name=self.name,
                arbitration_id=frame.arbitration_id, source_ecu=frame.source_ecu,
                message="identical payload repeated earlier than normal drift would allow",
            )
        return None


DEFAULT_RULES = [
    UnknownIDRule(),
    SourceMismatchRule(),
    MalformedFrameRule(),
    ImpossibleFrequencyRule(),
    FloodingRule(),
    ReplayAttackRule(),
]
