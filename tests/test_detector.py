from canary.bus import CANFrame
from canary.detector import Detector, IDBaseline, Severity


def make_detector():
    baseline = {
        0x100: IDBaseline(expected_source="engine_ecu", expected_dlc=8, expected_period_seconds=0.01),
    }
    return Detector(baseline)


def test_normal_traffic_produces_no_alerts():
    detector = make_detector()
    t = 0.0
    for i in range(20):
        frame = CANFrame(
            arbitration_id=0x100, data=bytes([i % 256] + [0] * 7),
            timestamp=t, source_ecu="engine_ecu",
        )
        detector.inspect(frame)
        t += 0.01
    assert detector.alerts == []


def test_unknown_id_rule_fires_for_unbaselined_id():
    detector = make_detector()
    frame = CANFrame(arbitration_id=0x555, data=b"\x01", timestamp=0.0, source_ecu="mystery_ecu")
    detector.inspect(frame)
    assert len(detector.alerts) == 1
    assert detector.alerts[0].rule_name == "unknown_id"


def test_source_mismatch_rule_fires_for_spoofed_source():
    detector = make_detector()
    frame = CANFrame(
        arbitration_id=0x100, data=bytes(8), timestamp=0.0, source_ecu="attacker_ecu",
    )
    detector.inspect(frame)
    assert any(a.rule_name == "source_mismatch" for a in detector.alerts)
    mismatch = next(a for a in detector.alerts if a.rule_name == "source_mismatch")
    assert mismatch.severity == Severity.CRITICAL


def test_malformed_frame_rule_fires_for_wrong_dlc():
    detector = make_detector()
    frame = CANFrame(arbitration_id=0x100, data=b"\x01\x02", timestamp=0.0, source_ecu="engine_ecu")
    detector.inspect(frame)
    assert any(a.rule_name == "malformed_frame" for a in detector.alerts)


def test_impossible_frequency_rule_fires_on_too_fast_repeat():
    detector = make_detector()
    first = CANFrame(arbitration_id=0x100, data=bytes(8), timestamp=0.0, source_ecu="engine_ecu")
    detector.inspect(first)
    # baseline period is 0.01s; sending again after 0.001s is far too fast
    second = CANFrame(arbitration_id=0x100, data=bytes(8), timestamp=0.001, source_ecu="engine_ecu")
    detector.inspect(second)
    assert any(a.rule_name == "impossible_frequency" for a in detector.alerts)


def test_flooding_rule_fires_on_sustained_high_rate():
    detector = make_detector()
    t = 0.0
    # baseline period 0.01s -> expected rate 100Hz; flood at ~1000Hz
    for i in range(60):
        frame = CANFrame(arbitration_id=0x100, data=bytes([i % 256] + [0] * 7), timestamp=t, source_ecu="engine_ecu")
        detector.inspect(frame)
        t += 0.001
    assert any(a.rule_name == "flooding" for a in detector.alerts)


def test_replay_attack_rule_fires_on_identical_early_repeat():
    detector = make_detector()
    payload = bytes([1, 2, 3, 4, 5, 6, 7, 8])
    first = CANFrame(arbitration_id=0x100, data=payload, timestamp=0.0, source_ecu="engine_ecu")
    detector.inspect(first)
    # identical payload again well before a full period would normally elapse
    second = CANFrame(arbitration_id=0x100, data=payload, timestamp=0.002, source_ecu="engine_ecu")
    detector.inspect(second)
    assert any(a.rule_name == "replay_attack" for a in detector.alerts)


def test_clear_alerts_empties_the_list():
    detector = make_detector()
    detector.inspect(CANFrame(arbitration_id=0x555, data=b"\x01", timestamp=0.0, source_ecu="x"))
    assert len(detector.alerts) == 1
    detector.clear_alerts()
    assert detector.alerts == []
