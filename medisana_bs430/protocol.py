"""BS430 GATT constants and command encoding."""

from __future__ import annotations

import time

SERVICE_UUID = "000078b2-0000-1000-8000-00805f9b34fb"
CHAR_WEIGHT = "00008a21-0000-1000-8000-00805f9b34fb"
CHAR_FEATURE = "00008a22-0000-1000-8000-00805f9b34fb"
CHAR_COMMAND = "00008a81-0000-1000-8000-00805f9b34fb"
CHAR_STATUS = "00008a82-0000-1000-8000-00805f9b34fb"
INDICATION_UUIDS = (CHAR_FEATURE, CHAR_WEIGHT, CHAR_STATUS)
NAME_PREFIX = "0203B"
MEDISANA_EPOCH_OFFSET = 1_262_304_000


def build_sync_command(unix_seconds: int | None = None) -> bytes:
    """Build the established BS430 synchronization request."""
    value = int(time.time()) if unix_seconds is None else unix_seconds
    return bytes([0x02]) + value.to_bytes(4, "little", signed=False)
