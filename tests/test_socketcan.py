import socket
import pytest

from canary.bus import CANFrame
from canary.bus.socketcan_bus import SocketCANBus, _encode, _decode

VCAN_INTERFACE = "vcan0"


def _vcan_available() -> bool:
    try:
        s = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
        s.bind((VCAN_INTERFACE,))
        s.close()
        return True
    except OSError:
        return False


requires_vcan = pytest.mark.skipif(
    not _vcan_available(),
    reason=f"SocketCAN or '{VCAN_INTERFACE}' not available in this environment",
)


# ---- Encode/decode round-trip tests: no kernel CAN support needed ----

def test_encode_decode_roundtrip_standard_frame():
    original = CANFrame(arbitration_id=0x123, data=b"\x01\x02\x03", source_ecu="test")
    raw = _encode(original)
    decoded = _decode(raw)
    assert decoded.arbitration_id == original.arbitration_id
    assert decoded.data == original.data
    assert not decoded.extended


def test_encode_decode_roundtrip_extended_frame():
    original = CANFrame(arbitration_id=0x1FFFFFFF, data=b"\xff", extended=True, source_ecu="test")
    raw = _encode(original)
    decoded = _decode(raw)
    assert decoded.arbitration_id == original.arbitration_id
    assert decoded.extended


def test_encode_produces_16_byte_frame():
    frame = CANFrame(arbitration_id=0x100, data=b"\x01\x02\x03\x04")
    raw = _encode(frame)
    assert len(raw) == 16


def test_decode_truncates_data_to_dlc():
    frame = CANFrame(arbitration_id=0x100, data=b"\x01\x02")
    raw = _encode(frame)
    decoded = _decode(raw)
    assert decoded.data == b"\x01\x02"  # not padded to 8 bytes


# ---- Live tests against a real vcan0 interface. Skipped automatically
# if the kernel has no CAN support or vcan0 doesn't exist. To run these:
#   sudo modprobe vcan
#   sudo ip link add dev vcan0 type vcan
#   sudo ip link set up vcan0

@requires_vcan
def test_socketcan_send_and_receive_roundtrip():
    bus = SocketCANBus(VCAN_INTERFACE)
    received = []
    bus.subscribe(lambda f: received.append(f))
    bus.start_listening()

    bus.offer(CANFrame(arbitration_id=0x123, data=b"\xde\xad\xbe\xef"))

    import time
    time.sleep(0.2)
    bus.close()

    assert len(received) == 1
    assert received[0].arbitration_id == 0x123
    assert received[0].data == b"\xde\xad\xbe\xef"


@requires_vcan
def test_socketcan_conforms_to_bus_interface():
    from canary.bus import BusInterface
    bus = SocketCANBus(VCAN_INTERFACE)
    assert isinstance(bus, BusInterface)
    bus.close()
