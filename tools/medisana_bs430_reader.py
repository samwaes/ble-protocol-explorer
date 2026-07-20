"""Read Medisana BS430 measurements over Bluetooth Low Energy.

The protocol facts implemented here were independently reimplemented from the
openScale Medisana BS44x/BS430 driver. No openScale source code is copied.

The BS430 uses service 0x78B2. After enabling indications on 0x8A22, 0x8A21,
and 0x8A82, the client writes 0x02 followed by the current Unix timestamp as a
32-bit little-endian value to 0x8A81. Measurements then arrive on 0x8A21 and
0x8A22.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

TARGET_ADDRESS = "DB:BC:F9:44:FC:17"
TARGET_NAME_PREFIX = "0203B"
SERVICE_UUID = "000078b2-0000-1000-8000-00805f9b34fb"
CHAR_WEIGHT = "00008a21-0000-1000-8000-00805f9b34fb"
CHAR_FEATURE = "00008a22-0000-1000-8000-00805f9b34fb"
CHAR_COMMAND = "00008a81-0000-1000-8000-00805f9b34fb"
CHAR_STATUS = "00008a82-0000-1000-8000-00805f9b34fb"
INDICATION_UUIDS = [CHAR_FEATURE, CHAR_WEIGHT, CHAR_STATUS]


@dataclass
class RawPacket:
    timestamp_utc: str
    characteristic: str
    payload_hex: str
    length: int


@dataclass
class Measurement:
    received_at_utc: str | None = None
    scale_timestamp_utc: str | None = None
    weight_kg: float | None = None
    body_fat_percent: float | None = None
    body_water_percent: float | None = None
    muscle_percent: float | None = None
    bone_mass_kg: float | None = None
    weight_frame_hex: str | None = None
    feature_frame_hex: str | None = None

    @property
    def complete(self) -> bool:
        return self.weight_kg is not None and self.feature_frame_hex is not None


class SessionRecorder:
    def __init__(self, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.csv_path = output_dir / f"bs430-session-{stamp}.csv"
        self.log_path = output_dir / f"bs430-session-{stamp}.log"
        self.json_path = output_dir / f"bs430-measurement-{stamp}.json"
        self.measurement = Measurement()

    def record_packet(self, characteristic: str, payload: bytes) -> None:
        packet = RawPacket(
            timestamp_utc=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            characteristic=short_uuid(characteristic),
            payload_hex=payload.hex(" ").upper(),
            length=len(payload),
        )
        with self.csv_path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=RawPacket.__annotations__.keys())
            if handle.tell() == 0:
                writer.writeheader()
            writer.writerow(asdict(packet))

    def save_measurement(self) -> None:
        self.json_path.write_text(
            json.dumps(asdict(self.measurement), indent=2, sort_keys=True),
            encoding="utf-8",
        )


def configure_logging(path: Path) -> logging.Logger:
    logger = logging.getLogger("bs430-reader")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )
    for handler in (
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(path, encoding="utf-8"),
    ):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def short_uuid(value: str) -> str:
    value = value.lower()
    if value.startswith("0000") and value.endswith("-0000-1000-8000-00805f9b34fb"):
        return value[4:8].upper()
    return value


def matches(device: BLEDevice, advertisement: AdvertisementData, address: str) -> bool:
    name = (advertisement.local_name or device.name or "").upper()
    services = {value.lower() for value in advertisement.service_uuids or []}
    return (
        device.address.upper() == address.upper()
        or name.startswith(TARGET_NAME_PREFIX)
        or SERVICE_UUID in services
    )


async def wait_for_scale(address: str, logger: logging.Logger) -> BLEDevice:
    found: asyncio.Future[BLEDevice] = asyncio.get_running_loop().create_future()

    def callback(device: BLEDevice, advertisement: AdvertisementData) -> None:
        if not found.done() and matches(device, advertisement, address):
            logger.info(
                "Found scale: name=%r address=%s RSSI=%s",
                advertisement.local_name or device.name,
                device.address,
                advertisement.rssi,
            )
            found.set_result(device)

    scanner = BleakScanner(detection_callback=callback)
    await scanner.start()
    try:
        logger.info("Scanning. Complete a normal body-analysis weighing now.")
        return await found
    finally:
        await scanner.stop()


def decode_weight(payload: bytes, measurement: Measurement) -> None:
    if len(payload) < 9:
        raise ValueError(f"Weight frame is too short: {len(payload)} bytes")

    raw_weight = int.from_bytes(payload[1:3], byteorder="little", signed=False)
    timestamp = int.from_bytes(payload[5:9], byteorder="little", signed=False)

    measurement.weight_kg = raw_weight / 100.0
    measurement.weight_frame_hex = payload.hex(" ").upper()
    measurement.received_at_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        measurement.scale_timestamp_utc = datetime.fromtimestamp(
            timestamp, tz=timezone.utc
        ).isoformat(timespec="seconds")
    except (OverflowError, OSError, ValueError):
        measurement.scale_timestamp_utc = f"invalid:{timestamp}"


def decode_feature_value(payload: bytes, offset: int) -> float:
    raw = int.from_bytes(payload[offset : offset + 2], byteorder="little", signed=False)
    return (raw & 0x0FFF) / 10.0


def decode_features(payload: bytes, measurement: Measurement) -> None:
    if len(payload) < 16:
        raise ValueError(f"Feature frame is too short: {len(payload)} bytes")

    measurement.body_fat_percent = decode_feature_value(payload, 8)
    measurement.body_water_percent = decode_feature_value(payload, 10)
    measurement.muscle_percent = decode_feature_value(payload, 12)
    measurement.bone_mass_kg = decode_feature_value(payload, 14)
    measurement.feature_frame_hex = payload.hex(" ").upper()
    measurement.received_at_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")


def time_command() -> bytes:
    unix_seconds = int(time.time())
    return bytes([0x02]) + unix_seconds.to_bytes(4, byteorder="little", signed=False)


def log_measurement(logger: logging.Logger, measurement: Measurement) -> None:
    logger.info(
        "DECODED weight=%s kg fat=%s%% water=%s%% muscle=%s%% bone=%s kg scale_time=%s",
        measurement.weight_kg,
        measurement.body_fat_percent,
        measurement.body_water_percent,
        measurement.muscle_percent,
        measurement.bone_mass_kg,
        measurement.scale_timestamp_utc,
    )


async def capture(
    device: BLEDevice,
    recorder: SessionRecorder,
    logger: logging.Logger,
    timeout_seconds: float,
) -> None:
    disconnected = asyncio.Event()
    measurement_ready = asyncio.Event()

    def on_disconnect(_: BleakClient) -> None:
        logger.info("Scale disconnected.")
        disconnected.set()

    async with BleakClient(
        device,
        disconnected_callback=on_disconnect,
        timeout=12.0,
    ) as client:
        logger.info("Connected: %s", client.is_connected)

        def notification(sender: Any, data: bytearray) -> None:
            uuid = str(getattr(sender, "uuid", sender)).lower()
            payload = bytes(data)
            recorder.record_packet(uuid, payload)
            logger.info(
                "RX %s (%d): %s",
                short_uuid(uuid),
                len(payload),
                payload.hex(" ").upper(),
            )

            try:
                if uuid == CHAR_WEIGHT:
                    decode_weight(payload, recorder.measurement)
                elif uuid == CHAR_FEATURE:
                    decode_features(payload, recorder.measurement)
                elif uuid == CHAR_STATUS:
                    logger.info("Status/session frame received on 8A82.")

                if recorder.measurement.complete:
                    recorder.save_measurement()
                    log_measurement(logger, recorder.measurement)
                    measurement_ready.set()
            except ValueError as exc:
                logger.warning("Could not decode %s: %s", short_uuid(uuid), exc)

        # Follow the ordering used by the established openScale driver.
        for uuid in INDICATION_UUIDS:
            await client.start_notify(uuid, notification)
            logger.info("Indications enabled: %s", short_uuid(uuid))

        command = time_command()
        logger.info("TX 8A81 (%d): %s", len(command), command.hex(" ").upper())
        await client.write_gatt_char(CHAR_COMMAND, command, response=True)
        logger.info("Time/request command accepted. Waiting for measurement frames.")

        measurement_task = asyncio.create_task(measurement_ready.wait())
        disconnect_task = asyncio.create_task(disconnected.wait())
        done, pending = await asyncio.wait(
            {measurement_task, disconnect_task},
            timeout=timeout_seconds,
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()

        if measurement_task in done and measurement_ready.is_set():
            logger.info("Measurement captured successfully: %s", recorder.json_path)
            await asyncio.sleep(1.0)
        elif disconnected.is_set():
            logger.warning("Scale disconnected before a complete measurement was decoded.")
        else:
            logger.warning("Timed out after %.1f seconds without a complete measurement.", timeout_seconds)

        if recorder.measurement.weight_kg is not None:
            recorder.save_measurement()


async def run(args: argparse.Namespace) -> None:
    recorder = SessionRecorder(Path(args.output))
    logger = configure_logging(recorder.log_path)
    logger.info("CSV packets: %s", recorder.csv_path)
    logger.info("Decoded JSON: %s", recorder.json_path)
    logger.info("Home Assistant is not accessed or modified.")
    device = await wait_for_scale(args.address, logger)
    await capture(device, recorder, logger, args.timeout)


def main() -> None:
    parser = argparse.ArgumentParser(description="Read Medisana BS430 measurements")
    parser.add_argument("--address", default=TARGET_ADDRESS)
    parser.add_argument("--output", default="captures/private")
    parser.add_argument("--timeout", type=float, default=35.0)
    args = parser.parse_args()

    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\nStopped.")
    except Exception as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
