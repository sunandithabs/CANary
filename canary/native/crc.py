"""
Python bridge to the native CRC-15 implementation.

Loads the compiled shared library (libcrc15.so) and exposes a plain
Python function, `crc15(data: bytes) -> int`, so the rest of the
codebase never has to think about ctypes directly.

If the .so hasn't been built yet, raises a clear error pointing at
`native/build.sh` rather than a cryptic OSError.
"""

import ctypes
from pathlib import Path

_NATIVE_DIR = Path(__file__).parent
_LIB_PATH = _NATIVE_DIR / "libcrc15.so"

if not _LIB_PATH.exists():
    raise FileNotFoundError(
        f"{_LIB_PATH} not found. Build it first with:\n"
        f"    bash {_NATIVE_DIR / 'build.sh'}"
    )

_lib = ctypes.CDLL(str(_LIB_PATH))
_lib.can_crc15.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
_lib.can_crc15.restype = ctypes.c_uint16


def crc15(data: bytes) -> int:
    """Computes the CAN CRC-15 checksum over `data` using the native
    C implementation."""
    buffer = (ctypes.c_uint8 * len(data))(*data)
    return _lib.can_crc15(buffer, len(data))
