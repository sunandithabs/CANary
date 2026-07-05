import time
from canary.bus import SimulatedBus, CANFrame
from canary.stats import StatsEngine


def test_top_talkers_ranks_by_frame_count():
    bus = SimulatedBus()
    stats = StatsEngine(bus)
    bus.subscribe(stats.observe)

    for _ in range(5):
        bus.offer(CANFrame(arbitration_id=0x100, data=b"\x01", source_ecu="engine_ecu"))
        bus.tick()
    for _ in range(2):
        bus.offer(CANFrame(arbitration_id=0x200, data=b"\x01", source_ecu="door_ecu"))
        bus.tick()

    talkers = stats.top_talkers()
    assert talkers[0] == ("engine_ecu", 5)
    assert talkers[1] == ("door_ecu", 2)


def test_message_rate_is_zero_with_insufficient_data():
    bus = SimulatedBus()
    stats = StatsEngine(bus)
    bus.subscribe(stats.observe)
    bus.offer(CANFrame(arbitration_id=0x100, data=b"\x01", source_ecu="engine_ecu"))
    bus.tick()
    assert stats.message_rate(0x100) == 0.0  # only one sample, no interval yet


def test_message_rate_reflects_actual_frequency():
    bus = SimulatedBus()
    stats = StatsEngine(bus)
    bus.subscribe(stats.observe)

    for _ in range(10):
        bus.offer(CANFrame(arbitration_id=0x100, data=b"\x01", source_ecu="engine_ecu"))
        bus.tick()
        time.sleep(0.005)

    rate = stats.message_rate(0x100)
    assert rate > 0


def test_snapshot_contains_expected_keys():
    bus = SimulatedBus()
    stats = StatsEngine(bus)
    bus.subscribe(stats.observe)
    bus.offer(CANFrame(arbitration_id=0x100, data=b"\x01\x02", source_ecu="engine_ecu"))
    bus.tick()

    snap = stats.snapshot()
    for key in ["total_frames", "bus_utilization_pct", "average_latency_ms",
                "top_talkers", "dropped_frames", "per_id_rates"]:
        assert key in snap
    assert snap["total_frames"] == 1
    assert snap["dropped_frames"] == 0  # documented: drop simulation intentionally omitted


def test_average_latency_is_nonnegative():
    bus = SimulatedBus()
    stats = StatsEngine(bus)
    bus.subscribe(stats.observe)
    bus.offer(CANFrame(arbitration_id=0x100, data=b"\x01", source_ecu="engine_ecu"))
    bus.tick()
    assert stats.average_latency_ms() >= 0.0
