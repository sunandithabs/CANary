from canary.bus import CANBus
from canary.ecu import ECU, ECUProfile, build_sample_ecus


def test_ecu_sends_only_when_due():
    bus = CANBus()
    sent_ids = []
    bus.subscribe(lambda f: sent_ids.append(f.arbitration_id))

    profile = ECUProfile(
        name="test_ecu", arbitration_id=0x123,
        period_seconds=1.0, jitter_seconds=0.0,
        payload_fn=lambda: b"\x01",
    )
    ecu = ECU(profile, bus)

    ecu.maybe_send(now=0.0)
    bus.tick()
    assert sent_ids == [0x123]
    assert ecu.frames_sent == 1

    # Not due yet (period is 1.0s)
    ecu.maybe_send(now=0.5)
    assert bus.pending_count == 0
    assert ecu.frames_sent == 1

    # Due now
    ecu.maybe_send(now=1.0)
    assert bus.pending_count == 1
    assert ecu.frames_sent == 2


def test_ecu_jitter_stays_within_bounds():
    bus = CANBus()
    profile = ECUProfile(
        name="jitter_ecu", arbitration_id=0x200,
        period_seconds=1.0, jitter_seconds=0.1,
        payload_fn=lambda: b"\x00",
    )
    ecu = ECU(profile, bus)
    ecu.maybe_send(now=0.0)
    # next_send_time should be within [1.0 - 0.1, 1.0 + 0.1]
    assert 0.9 <= ecu._next_send_time <= 1.1


def test_build_sample_ecus_returns_distinct_ids():
    bus = CANBus()
    ecus = build_sample_ecus(bus)
    ids = {e.profile.arbitration_id for e in ecus}
    assert len(ids) == len(ecus)  # no duplicate IDs


def test_engine_ecu_payload_within_realistic_rpm_range():
    bus = CANBus()
    ecus = build_sample_ecus(bus)
    engine = next(e for e in ecus if e.profile.name == "engine_ecu")

    received = []
    bus.subscribe(lambda f: received.append(f))

    t = 0.0
    for _ in range(50):
        engine.maybe_send(now=t)
        bus.tick()
        t += 0.01

    assert len(received) > 0
    for frame in received:
        rpm = (frame.data[0] << 8) | frame.data[1]
        assert 800 <= rpm <= 3000
