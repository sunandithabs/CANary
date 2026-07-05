/*
 * CAN CRC-15 checksum.
 *
 * Polynomial CAN 2.0 controllers use to detect corrupted frames:
 * x^15 + x^14 + x^10 + x^8 + x^7 + x^4 + x^3 + 1 (0x4599).
 *
 * Processes the frame one bit at a time, matching how CAN
 * transceivers compute it in hardware.
 */

#include <stdint.h>
#include <stddef.h>

#define CAN_CRC_POLY 0x4599
#define CAN_CRC_WIDTH 15

/*
 * Computes the CAN CRC-15 over `data`, `length` bytes.
 * Exposed with a C linkage name so ctypes can find it unmangled.
 */
uint16_t can_crc15(const uint8_t *data, size_t length) {
    uint16_t crc = 0;

    for (size_t byte_idx = 0; byte_idx < length; byte_idx++) {
        uint8_t byte = data[byte_idx];

        for (int bit_idx = 7; bit_idx >= 0; bit_idx--) {
            uint8_t bit = (byte >> bit_idx) & 0x01;
            uint8_t crc_msb = (crc >> (CAN_CRC_WIDTH - 1)) & 0x01;

            crc <<= 1;
            if (crc_msb ^ bit) {
                crc ^= CAN_CRC_POLY;
            }
        }
    }

    /* Keep to 15 bits */
    return crc & 0x7FFF;
}
