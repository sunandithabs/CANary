import pytest
from canary.bus import CANFrame, CANBus


def test_frame_valid_standard():
    f = CANFrame(arbitration_id=0x100, data=b"\x01\x02\x03")
    assert f.dlc == 3
    assert f.arbitration_id == 0x100
    assert not f.extended


def test_frame_rejects_id_out_of_range():
    with pytest.raises(ValueError):
        CANFrame(arbitration_id=0x800, data=b"\x00")  # exceeds 11-bit standard max


def test_frame_rejects_oversized_payload():
    with pytest.raises(ValueError):
        CANFrame(arbitration_id=0x100, data=b"\x00" * 9)


def test_extended_frame_allows_large_id():
    f = CANFrame(arbitration_id=0x1FFFFFFF, data=b"\xff", extended=True)
    assert f.arbitration_id == 0x1FFFFFFF


def test_bus_arbitration_priority_order():
    bus = CANBus()
    received = []
    bus.subscribe(lambda f: received.append(f.arbitration_id))

    # Offer low-priority (higher ID) frame first, then higher-priority (lower ID)
    bus.offer(CANFrame(arbitration_id=0x300, data=b"\x01"))
    bus.offer(CANFrame(arbitration_id=0x100, data=b"\x02"))
    bus.offer(CANFrame(arbitration_id=0x200, data=b"\x03"))

    bus.tick()
    bus.tick()
    bus.tick()

    # Despite offer order, lowest arbitration ID should win each round
    assert received == [0x100, 0x200, 0x300]


def test_bus_utilization_tracks_transmitted_bits():
    bus = CANBus(bitrate_bps=500_000)
    bus.offer(CANFrame(arbitration_id=0x100, data=b"\x00" * 8))
    bus.tick()
    util = bus.utilization(elapsed_seconds=0.001)
    assert 0 < util <= 1.0


def test_bus_pending_count_decreases_after_tick():
    bus = CANBus()
    bus.offer(CANFrame(arbitration_id=0x100, data=b"\x01"))
    assert bus.pending_count == 1
    bus.tick()
    assert bus.pending_count == 0
