from .frame import CANFrame
from .bus import BusInterface, SimulatedBus
from .socketcan_bus import SocketCANBus

# Backward-compat alias: existing tests/modules reference CANBus directly.
# New code should prefer SimulatedBus / BusInterface.
CANBus = SimulatedBus

__all__ = ["CANFrame", "BusInterface", "SimulatedBus", "SocketCANBus", "CANBus"]
