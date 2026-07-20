"""Interactive Medisana BS430 BLE protocol explorer for Windows.

The tool captures BS430 traffic safely. It never writes proprietary commands
automatically. Data is written to 0x8A81 only after `send <hex bytes>` and an
explicit YES confirmation.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
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


@dataclass
class Packet:
    timestamp_utc: str
    direction: str
    characteristic: str
    payload_hex: str
    length: int
    note: str = ""


class SessionRecorder:
    def __init__(self, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.csv_path = output_dir / f"bs430-session-{stamp}.csv"
        self.log_path = output_dir / f"bs430-session-{stamp}.log"
        self.packets: list[Packet] = []

    def record(self, direction: str, characteristic: str, payload: bytes, note: str = "") -> Packet:
        packet = Packet(datetime.now(timezone.utc).isoformat(timespec="milliseconds"), direction, characteristic, payload.hex(" ").upper(), len(payload), note)
        self.packets.append(packet)
        with self.csv_path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            if handle.tell() == 0:
                writer.writerow(Packet.__annotations__.keys())
            writer.writerow([packet.timestamp_utc, packet.direction, packet.characteristic, packet.payload_hex, packet.length, packet.note])
        return packet


def configure_logging(path: Path) -> logging.Logger:
    logger = logging.getLogger("bs430-explorer")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S")
    for handler in (logging.StreamHandler(sys.stdout), logging.FileHandler(path, encoding="utf-8")):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def matches(device: BLEDevice, advertisement: AdvertisementData, address: str) -> bool:
    name = (advertisement.local_name or device.name or "").upper()
    services = {value.lower() for value in advertisement.service_uuids or []}
    return device.address.upper() == address.upper() or TARGET_NAME_FRAGMENT in name or SERVICE_UUID in services


async def wait_for_scale(address: str, logger: logging.Logger) -> BLEDevice:
    found: asyncio.Future[BLEDevice] = asyncio.get_running_loop().create_future()

    def callback(device: BLEDevice, advertisement: AdvertisementData) -> None:
        if not found.done() and matches(device, advertisement, address):
            logger.info("Found scale: name=%r address=%s RSSI=%s", advertisement.local_name or device.name, device.address, advertisement.rssi)
            found.set_result(device)

    scanner = BleakScanner(detection_callback=callback)
    await scanner.start()
    try:
        logger.info("Scanning. Complete a normal weighing now.")
        return await found
    finally:
        await scanner.stop()


def parse_hex(value: str) -> bytes:
    cleaned = value.replace("0x", "").replace(",", " ").replace(":", " ")
    parts = [part for part in cleaned.split() if part]
    if not parts:
        raise ValueError("No hexadecimal bytes supplied")
    if any(len(part) > 2 for part in parts):
        raise ValueError("Enter separate bytes, for example: send 01 02 FF")
    return bytes(int(part, 16) for part in parts)


async def console(client: BleakClient, recorder: SessionRecorder, logger: logging.Logger, disconnected: asyncio.Event) -> None:
    help_text = "Commands: help | read | send <hex bytes> | packets | note <text> | quit\nNo command is written unless you explicitly use send."
    logger.info(help_text)
    last_note = ""
    while client.is_connected and not disconnected.is_set():
        try:
            raw = await asyncio.to_thread(input, "bs430> ")
        except EOFError:
            return
        command = raw.strip()
        if not command:
            continue
        verb, _, argument = command.partition(" ")
        verb = verb.lower()
        try:
            if verb == "help":
                print(help_text)
            elif verb == "read":
                payload = bytes(await client.read_gatt_char(CHAR_READ))
                recorder.record("READ", CHAR_READ, payload, last_note)
                logger.info("READ 8A20 (%d): %s", len(payload), payload.hex(" ").upper())
            elif verb == "send":
                payload = parse_hex(argument)
                confirmation = await asyncio.to_thread(input, f"Write {payload.hex(' ').upper()} to 8A81? Type YES: ")
                if confirmation != "YES":
                    logger.info("Write cancelled.")
                    continue
                recorder.record("TX", CHAR_WRITE, payload, last_note)
                logger.info("TX 8A81 (%d): %s", len(payload), payload.hex(" ").upper())
                await client.write_gatt_char(CHAR_WRITE, payload, response=True)
            elif verb == "packets":
                for index, packet in enumerate(recorder.packets, start=1):
                    print(f"{index:03d} {packet.timestamp_utc} {packet.direction:4} {packet.characteristic[-12:-8]} {packet.payload_hex} {packet.note}")
            elif verb == "note":
                last_note = argument.strip()
                logger.info("Capture note set to: %s", last_note or "(empty)")
            elif verb in {"quit", "exit"}:
                return
            else:
                logger.warning("Unknown command. Type help.")
        except Exception as exc:
            logger.error("Command failed: %s", exc)


async def capture(device: BLEDevice, recorder: SessionRecorder, logger: logging.Logger) -> None:
    disconnected = asyncio.Event()

    def on_disconnect(_: BleakClient) -> None:
        logger.info("Scale disconnected.")
        disconnected.set()

    async with BleakClient(device, disconnected_callback=on_disconnect, timeout=12.0) as client:
        logger.info("Connected: %s", client.is_connected)

        def notification(sender, data: bytearray) -> None:
            uuid = getattr(sender, "uuid", str(sender))
            payload = bytes(data)
            recorder.record("RX", uuid, payload)
            logger.info("RX %s (%d): %s", uuid[-12:-8], len(payload), payload.hex(" ").upper())

        for uuid in INDICATION_UUIDS:
            await client.start_notify(uuid, notification)
            logger.info("Indications enabled: %s", uuid[-12:-8])

        payload = bytes(await client.read_gatt_char(CHAR_READ))
        recorder.record("READ", CHAR_READ, payload, "automatic initial read")
        logger.info("READ 8A20 (%d): %s", len(payload), payload.hex(" ").upper())
        await console(client, recorder, logger, disconnected)


async def run(args: argparse.Namespace) -> None:
    recorder = SessionRecorder(Path(args.output))
    logger = configure_logging(recorder.log_path)
    logger.info("CSV: %s", recorder.csv_path)
    logger.info("LOG: %s", recorder.log_path)
    logger.info("Home Assistant is not accessed or modified.")
    device = await wait_for_scale(args.address, logger)
    await capture(device, recorder, logger)


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive Medisana BS430 protocol explorer")
    parser.add_argument("--address", default=TARGET_ADDRESS)
    parser.add_argument("--output", default="captures/private")
    args = parser.parse_args()
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
