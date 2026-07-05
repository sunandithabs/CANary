"""
CAN frame data model.

Represents a single CAN 2.0 frame as it would appear on the bus.
Extended (29-bit) IDs are supported via `extended=True`; standard
frames use 11-bit IDs.
"""

from dataclasses import dataclass, field
import time

STANDARD_ID_MAX = 0x7FF        # 11-bit
EXTENDED_ID_MAX = 0x1FFFFFFF   # 29-bit
MAX_DLC = 8


@dataclass(frozen=True)
class CANFrame:
    arbitration_id: int
    data: bytes
    extended: bool = False
    timestamp: float = field(default_factory=time.monotonic)
    source_ecu: str = "unknown"

    def __post_init__(self):
        max_id = EXTENDED_ID_MAX if self.extended else STANDARD_ID_MAX
        if not (0 <= self.arbitration_id <= max_id):
            raise ValueError(
                f"arbitration_id {self.arbitration_id:#x} out of range "
                f"for {'extended' if self.extended else 'standard'} frame"
            )
        if len(self.data) > MAX_DLC:
            raise ValueError(f"payload length {len(self.data)} exceeds max DLC of {MAX_DLC}")

    @property
    def dlc(self) -> int:
        return len(self.data)

    def __repr__(self) -> str:
        hex_data = self.data.hex(" ")
        id_fmt = f"{self.arbitration_id:08X}" if self.extended else f"{self.arbitration_id:03X}"
        return f"<CANFrame id=0x{id_fmt} dlc={self.dlc} data=[{hex_data}] src={self.source_ecu}>"
