import tempfile
from pathlib import Path

from canary.simulator import (
    Simulator, inject_spoofing, inject_malformed_frame,
    inject_replay_attack, inject_flooding,
)


def test_normal_traffic_produces_zero_alerts():
    with tempfile.TemporaryDirectory() as tmp:
        sim = Simulator(str(Path(tmp) / "log.csv"))
        sim.run(2000)
        sim.close()
        assert sim.detector.alerts == []
        assert sim.stats.total_frames > 0


def test_spoofing_scenario_is_detected():
    with tempfile.TemporaryDirectory() as tmp:
        sim = Simulator(str(Path(tmp) / "log.csv"))
        sim.run(500)
        inject_spoofing(sim)
        sim.close()
        assert any(a.rule_name == "source_mismatch" for a in sim.detector.alerts)


def test_malformed_frame_scenario_is_detected():
    with tempfile.TemporaryDirectory() as tmp:
        sim = Simulator(str(Path(tmp) / "log.csv"))
        sim.run(500)
        inject_malformed_frame(sim)
        sim.close()
        assert any(a.rule_name == "malformed_frame" for a in sim.detector.alerts)


def test_flooding_scenario_is_detected():
    with tempfile.TemporaryDirectory() as tmp:
        sim = Simulator(str(Path(tmp) / "log.csv"))
        sim.run(500)
        inject_flooding(sim, frame_count=100)
        sim.close()
        assert any(a.rule_name == "flooding" for a in sim.detector.alerts)
        assert any(a.rule_name == "impossible_frequency" for a in sim.detector.alerts)


def test_replay_scenario_is_detected():
    with tempfile.TemporaryDirectory() as tmp:
        sim = Simulator(str(Path(tmp) / "log.csv"))
        sim.run(500)
        # Capture the real last payload; a hardcoded guess wouldn't
        # match since engine_ecu's RPM payload drifts every frame.
        captured = sim.detector.last_payload_for(0x0C0)
        # Inject shortly after the real transmission so the gap is
        # small enough to look like a replay regardless of ECU phase.
        sim.time = sim.detector.last_seen_for(0x0C0) + 0.0005
        inject_replay_attack(sim, captured)
        sim.close()
        assert any(a.rule_name == "replay_attack" for a in sim.detector.alerts)


def test_log_file_is_written_and_nonempty():
    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "log.csv"
        sim = Simulator(str(log_path))
        sim.run(100)
        sim.close()
        content = log_path.read_text()
        assert "engine_ecu" in content
        assert sim.logger.frames_logged > 0
