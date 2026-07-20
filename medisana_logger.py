"""Medisana BS430 BLE diagnostic logger for Windows.

This tool does not modify Home Assistant. It uses the Windows Bluetooth adapter,
waits for the scale to wake up, connects, enables indications, reads known
characteristics, and records all received packets.

Stop with Ctrl+C.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

TARGET_ADDRESS = "DB:BC:F9:44:FC:17"
TARGET_NAME_FRAGMENT = "17FC44F9BCDB"
SERVICE_UUID = "000078b2-0000-1000-8000-00805f9b34fb"
CHAR_READ = "00008a20-0000-1000-8000-00805f9b34fb"
CHAR_INDICATE_1 = "00008a21-0000-1000-8000-00805f9b34fb"
CHAR_INDICATE_2 = "00008a22-0000-1000-8000-00805f9b34fb"
CHAR_WRITE = "00008a81-0000-1000-8000-00805f9b34fb"
CHAR_INDICATE_3 = "00008a82-0000-1000-8000-00805f9b34fb"
INDICATION_UUIDS = [CHAR_INDICATE_1, CHAR_INDICATE_2, CHAR_INDICATE_3]


def configure_logging(log_path: Path) -> logging.Logger:
    logger = logging.getLogger("medisana")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def hex_bytes(data: bytes | bytearray) -> str:
    return " ".join(f"{byte:02X}" for byte in data)


def device_matches(device: BLEDevice, advertisement: AdvertisementData, address: str) -> bool:
    advertised_name = advertisement.local_name or device.name or ""
    service_uuids = {uuid.lower() for uuid in advertisement.service_uuids or []}
    return (
        device.address.upper() == address.upper()
        or TARGET_NAME_FRAGMENT in advertised_name.upper()
        or SERVICE_UUID in service_uuids
    )


async def wait_for_scale(address: str, logger: logging.Logger) -> BLEDevice:
    found: asyncio.Future[BLEDevice] = asyncio.get_running_loop().create_future()

    def detection_callback(device: BLEDevice, advertisement: AdvertisementData) -> None:
        if not found.done() and device_matches(device, advertisement, address):
            logger.info(
                "Scale advertisement found: name=%r address=%s RSSI=%s services=%s",
                advertisement.local_name or device.name,
                device.address,
                advertisement.rssi,
                advertisement.service_uuids,
            )
            found.set_result(device)

    scanner = BleakScanner(detection_callback=detection_callback)
    await scanner.start()
    try:
        logger.info("Scanning. Complete a weighing now and wait for the scale to wake.")
        return await found
    finally:
        await scanner.stop()


async def capture_session(device: BLEDevice, logger: logging.Logger, listen_seconds: int) -> None:
    disconnected = asyncio.Event()

    def on_disconnect(_: BleakClient) -> None:
        logger.info("Scale disconnected.")
        disconnected.set()

    logger.info("Connecting to %s...", device.address)
    async with BleakClient(device, disconnected_callback=on_disconnect, timeout=12.0) as client:
        logger.info("Connected: %s", client.is_connected)
        logger.info("Discovered GATT services:")
        for service in client.services:
            logger.info("  SERVICE %s", service.uuid)
            for characteristic in service.characteristics:
                logger.info("    CHAR %s properties=%s", characteristic.uuid, ",".join(characteristic.properties))

        def notification_handler(sender, data: bytearray) -> None:
            uuid = getattr(sender, "uuid", str(sender))
            logger.info("RX uuid=%s len=%d hex=%s", uuid, len(data), hex_bytes(data))

        active_notifications: list[str] = []
        for uuid in INDICATION_UUIDS:
            try:
                await client.start_notify(uuid, notification_handler)
                active_notifications.append(uuid)
                logger.info("Indications enabled on %s", uuid)
            except Exception as exc:
                logger.warning("Could not enable %s: %s", uuid, exc)

        try:
            value = await client.read_gatt_char(CHAR_READ)
            logger.info("READ uuid=%s len=%d hex=%s", CHAR_READ, len(value), hex_bytes(value))
        except Exception as exc:
            logger.warning("Could not read %s: %s", CHAR_READ, exc)

        logger.info("Listening for up to %d seconds. Leave the scale awake if possible.", listen_seconds)
        try:
            await asyncio.wait_for(disconnected.wait(), timeout=listen_seconds)
        except asyncio.TimeoutError:
            logger.info("Listening period completed.")

        for uuid in active_notifications:
            if client.is_connected:
                try:
                    await client.stop_notify(uuid)
                except Exception:
                    pass


async def run(args: argparse.Namespace, logger: logging.Logger) -> None:
    session_number = 0
    while True:
        session_number += 1
        logger.info("=" * 72)
        logger.info("Waiting for measurement session %d", session_number)
        try:
            device = await wait_for_scale(args.address, logger)
            await capture_session(device, logger, args.listen)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Session failed: %s", exc)
        if args.once:
            return
        logger.info("Returning to scan mode in 3 seconds.")
        await asyncio.sleep(3)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture BLE traffic from a Medisana BS430.")
    parser.add_argument("--address", default=TARGET_ADDRESS)
    parser.add_argument("--listen", type=int, default=90)
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = Path(__file__).resolve().parent / f"medisana-{timestamp}.log"
    logger = configure_logging(log_path)
    logger.info("Log file: %s", log_path)
    logger.info("This test does not communicate with Home Assistant.")
    try:
        asyncio.run(run(args, logger))
    except KeyboardInterrupt:
        logger.info("Stopped by user.")


if __name__ == "__main__":
    main()
