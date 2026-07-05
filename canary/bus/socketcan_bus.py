"""
SocketCAN bus.

Talks to a real Linux CAN interface (e.g. vcan0, or a physical CAN
adapter like can0) using the kernel's native SocketCAN API: a raw
AF_CAN socket, no external library required.

Frame format on the wire is the kernel's `struct can_frame`:
    canid_t can_id;   // 32-bit ID, with EFF/RTR/ERR flag bits set
    __u8    can_dlc;  // payload length, 0-8
    __u8    __pad, __res0, __res1;
    __u8    data[8];
That's 16 bytes total: "=IB3x8s" in struct.pack terms.

Requires Linux with CAN support and CAP_NET_RAW (or root) to bind an
interface. Setup for a virtual interface (no hardware needed):
    sudo modprobe vcan
    sudo ip link add dev vcan0 type vcan
    sudo ip link set up vcan0
"""

import socket
import struct
import threading
from typing import Callable, List

from .bus import BusInterface
from .frame import CANFrame

CAN_EFF_FLAG = 0x80000000
CAN_EFF_MASK = 0x1FFFFFFF
CAN_SFF_MASK = 0x000007FF
FRAME_FORMAT = "=IB3x8s"
FRAME_SIZE = struct.calcsize(FRAME_FORMAT)


def _encode(frame: CANFrame) -> bytes:
    can_id = frame.arbitration_id
    if frame.extended:
        can_id |= CAN_EFF_FLAG
    data = frame.data.ljust(8, b"\x00")
    return struct.pack(FRAME_FORMAT, can_id, frame.dlc, data)


def _decode(raw: bytes, source_ecu: str = "vcan0") -> CANFrame:
    can_id, dlc, data = struct.unpack(FRAME_FORMAT, raw)
    extended = bool(can_id & CAN_EFF_FLAG)
    arb_id = can_id & (CAN_EFF_MASK if extended else CAN_SFF_MASK)
    return CANFrame(
        arbitration_id=arb_id, data=data[:dlc], extended=extended,
        source_ecu=source_ecu,
    )


class SocketCANBus(BusInterface):
    def __init__(self, interface: str = "vcan0"):
        self.interface = interface
        self._sock = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
        # By default SocketCAN doesn't loop a sent frame back to the
        # socket that sent it, only to other sockets on the interface.
        # We use one socket for both offer() and receiving, so we need
        # our own frames looped back too.
        self._sock.setsockopt(socket.SOL_CAN_RAW, socket.CAN_RAW_RECV_OWN_MSGS, 1)
        self._sock.bind((interface,))
        self._subscribers: List[Callable[[CANFrame], None]] = []
        self._running = False
        self._recv_thread = None

    def subscribe(self, callback: Callable[[CANFrame], None]) -> None:
        self._subscribers.append(callback)

    def offer(self, frame: CANFrame) -> None:
        """Sends immediately. Real hardware/kernel handles arbitration;
        there's no software queue to manage here."""
        self._sock.send(_encode(frame))

    def start_listening(self) -> None:
        """Spawns a background thread reading frames off the interface
        and dispatching them to subscribers. Call once; stop_listening()
        to tear down."""
        if self._running:
            return
        self._running = True
        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._recv_thread.start()

    def stop_listening(self) -> None:
        self._running = False
        if self._recv_thread:
            self._recv_thread.join(timeout=1.0)

    def _recv_loop(self) -> None:
        self._sock.settimeout(0.5)
        while self._running:
            try:
                raw, _ = self._sock.recvfrom(FRAME_SIZE)
            except socket.timeout:
                continue
            frame = _decode(raw, source_ecu=self.interface)
            for callback in self._subscribers:
                callback(frame)

    def close(self) -> None:
        self.stop_listening()
        self._sock.close()
