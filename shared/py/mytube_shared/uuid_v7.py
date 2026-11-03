"""RFC 9562 UUIDv7 generator."""

import os
import time
import uuid


def uuid7() -> uuid.UUID:
    """Generate a UUIDv7 (time-ordered, millisecond precision, random trailing)."""
    # 48-bit timestamp in milliseconds
    ms = int(time.time() * 1000)
    rand_bytes = os.urandom(10)

    # Construct the 16 bytes:
    # 6 bytes (48 bits): ms timestamp
    # 2 bytes: 4-bit version (0b0111 = 7) + 12-bit random
    # 2 bytes: 2-bit variant (0b10) + 14-bit random
    # 6 bytes: 48-bit random
    b = bytearray(16)
    b[0] = (ms >> 40) & 0xFF
    b[1] = (ms >> 32) & 0xFF
    b[2] = (ms >> 24) & 0xFF
    b[3] = (ms >> 16) & 0xFF
    b[4] = (ms >> 8) & 0xFF
    b[5] = ms & 0xFF

    # Version 7 in high nibble of byte 6
    b[6] = 0x70 | (rand_bytes[0] & 0x0F)
    b[7] = rand_bytes[1]

    # Variant (10xx) in high two bits of byte 8
    b[8] = 0x80 | (rand_bytes[2] & 0x3F)
    b[9] = rand_bytes[3]
    b[10:16] = rand_bytes[4:10]

    return uuid.UUID(bytes=bytes(b))


def uuid7_str() -> str:
    """Return UUIDv7 as a standard string."""
    return str(uuid7())
