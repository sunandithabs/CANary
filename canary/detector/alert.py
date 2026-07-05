"""
Alert model.

A uniform, plain structure every detection rule produces. The
dashboard (or any future export) reads these without knowing which
rule generated them.
"""

from dataclasses import dataclass
from enum import IntEnum


class Severity(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class Alert:
    timestamp: float
    severity: Severity
    rule_name: str
    arbitration_id: int
    message: str
    source_ecu: str = "unknown"

    def __repr__(self) -> str:
        return (
            f"[{self.severity}] {self.rule_name} "
            f"id=0x{self.arbitration_id:03X} src={self.source_ecu} :: {self.message}"
        )
