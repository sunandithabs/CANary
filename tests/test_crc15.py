from canary.native import crc15

CAN_CRC_POLY = 0x4599
CRC_WIDTH = 15


def python_reference_crc15(data: bytes) -> int:
    """Pure-Python reference implementation, used to validate the C
    implementation against known-correct output."""
    crc = 0
    for byte in data:
        for bit_idx in range(7, -1, -1):
            bit = (byte >> bit_idx) & 0x01
            crc_msb = (crc >> (CRC_WIDTH - 1)) & 0x01
            crc = (crc << 1) & 0x7FFF
            if crc_msb ^ bit:
                crc ^= CAN_CRC_POLY
    return crc & 0x7FFF


def test_crc15_matches_python_reference_for_various_payloads():
    test_payloads = [
        b"",
        b"\x00",
        b"\xff",
        b"\x01\x02\x03\x04\x05\x06\x07\x08",
        b"\xde\xad\xbe\xef",
        bytes(range(8)),
    ]
    for payload in test_payloads:
        assert crc15(payload) == python_reference_crc15(payload), (
            f"mismatch for payload {payload.hex()}"
        )


def test_crc15_is_deterministic():
    payload = b"\x12\x34\x56\x78"
    assert crc15(payload) == crc15(payload)


def test_crc15_detects_single_bit_corruption():
    original = b"\x01\x02\x03\x04"
    corrupted = b"\x01\x02\x03\x05"  # one bit flipped in the last byte
    assert crc15(original) != crc15(corrupted)


def test_crc15_fits_in_15_bits():
    payload = bytes(range(8)) * 4
    result = crc15(payload)
    assert 0 <= result <= 0x7FFF
