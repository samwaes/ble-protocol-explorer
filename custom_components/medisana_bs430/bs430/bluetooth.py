"""BLE transport for the BS430 inside Home Assistant."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from bleak import BleakClient
from bleak.backends.device import BLEDevice

from .models import SyncResult
from .protocol import CHAR_COMMAND, INDICATION_UUIDS, build_sync_command
from .synchronizer import MeasurementAssembler


async def synchronize(
    device: BLEDevice,
    *,
    timeout_seconds: float = 45.0,
    quiet_seconds: float = 8.0,
    packet_callback: Callable[[str, bytes], None] | None = None,
) -> SyncResult:
    """Synchronize every stored record currently offered by the scale."""
    assembler = MeasurementAssembler()
    disconnected = asyncio.Event()
    loop = asyncio.get_running_loop()
    last_packet = loop.time()

    def on_disconnect(_: BleakClient) -> None:
        disconnected.set()

    async with BleakClient(
        device, disconnected_callback=on_disconnect, timeout=12.0
    ) as client:
        def notification(sender, data: bytearray) -> None:
            nonlocal last_packet
            uuid = str(getattr(sender, "uuid", sender)).lower()
            payload = bytes(data)
            last_packet = loop.time()
            assembler.feed(uuid, payload)
            if packet_callback is not None:
                packet_callback(uuid, payload)

        for uuid in INDICATION_UUIDS:
            await client.start_notify(uuid, notification)
        await client.write_gatt_char(
            CHAR_COMMAND, build_sync_command(), response=True
        )

        started = loop.time()
        reason = "timeout"
        while True:
            now = loop.time()
            if disconnected.is_set():
                reason = "scale_disconnected"
                break
            if now - started >= timeout_seconds:
                break
            if assembler.result("pending").measurements and now - last_packet >= quiet_seconds:
                reason = "quiet_period"
                break
            await asyncio.sleep(0.25)

    return assembler.result(reason)
