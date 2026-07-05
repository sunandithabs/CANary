import tempfile
from pathlib import Path

from canary.bus import CANBus, CANFrame
from canary.logger import CANLogger, read_log, replay_log


def test_logger_writes_expected_rows():
    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "test.csv"
        bus = CANBus()

        with CANLogger(log_path) as logger:
            bus.subscribe(logger.log_frame)
            bus.offer(CANFrame(arbitration_id=0x123, data=b"\x01\x02", source_ecu="engine_ecu"))
            bus.tick()
            logger.flush()

            assert logger.frames_logged == 1

        content = log_path.read_text()
        assert "0x123" in content
        assert "engine_ecu" in content
        assert "0102" in content


def test_read_log_roundtrips_frame_data():
    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "test.csv"
        bus = CANBus()
        original = CANFrame(arbitration_id=0x1A0, data=b"\xde\xad\xbe\xef", source_ecu="brake_ecu")

        with CANLogger(log_path) as logger:
            bus.subscribe(logger.log_frame)
            bus.offer(original)
            bus.tick()
            logger.flush()

        replayed = list(read_log(log_path))
        assert len(replayed) == 1
        assert replayed[0].arbitration_id == original.arbitration_id
        assert replayed[0].data == original.data
        assert replayed[0].source_ecu == original.source_ecu


def test_replay_log_pushes_frames_onto_new_bus():
    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "test.csv"
        record_bus = CANBus()

        with CANLogger(log_path) as logger:
            record_bus.subscribe(logger.log_frame)
            record_bus.offer(CANFrame(arbitration_id=0x200, data=b"\x01", source_ecu="door_ecu"))
            record_bus.offer(CANFrame(arbitration_id=0x100, data=b"\x02", source_ecu="engine_ecu"))
            record_bus.tick()
            record_bus.tick()
            logger.flush()

        replay_bus = CANBus()
        received = []
        replay_bus.subscribe(lambda f: received.append(f.arbitration_id))

        count = replay_log(log_path, replay_bus, speed=0)  # speed=0 skips sleeping for fast tests

        assert count == 2
        assert received == [0x100, 0x200]  # replay preserves the order frames actually won arbitration in
