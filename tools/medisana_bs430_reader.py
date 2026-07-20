"""Synchronize stored Medisana BS430 measurements over Bluetooth LE.

The scale can return several historical measurements in one session. Weight and
feature frames are paired by their shared four-byte measurement timestamp rather
than by arrival order. Captures from the tested BS430 show measurement timestamps
as seconds since 2010-01-01, while the synchronization request still uses the
current Unix timestamp.
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
from datetime import datetime, timedelta, timezone
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
MEDISANA_EPOCH = datetime(2010, 1, 1, tzinfo=timezone.utc)


@dataclass
class RawPacket:
    received_at_utc: str
    characteristic: str
    payload_hex: str
    length: int


@dataclass
class Measurement:
    sequence: int
    timestamp_key_hex: str
    scale_timestamp_utc: str | None = None
    received_at_utc: str | None = None
    weight_kg: float | None = None
    body_fat_percent: float | None = None
    body_water_percent: float | None = None
    muscle_percent: float | None = None
    bone_mass_kg: float | None = None
    impedance_ohm: float | None = None
    profile_id_candidate: int | None = None
    profile_id_status: str = "unconfirmed"
    weight_frame_hex: str | None = None
    feature_frame_hex: str | None = None
    weight_unknown_bytes_hex: str | None = None
    feature_unknown_bytes_hex: str | None = None

    @property
    def complete(self) -> bool:
        return self.weight_frame_hex is not None and self.feature_frame_hex is not None


class SessionRecorder:
    def __init__(self, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.csv_path = output_dir / f"bs430-sync-{stamp}.csv"
        self.log_path = output_dir / f"bs430-sync-{stamp}.log"
        self.json_path = output_dir / f"bs430-sync-{stamp}.json"
        self.pending: dict[str, Measurement] = {}
        self.measurements: list[Measurement] = []
        self.status_frames: list[str] = []
        self.last_packet_monotonic = time.monotonic()
        self.request_hex: str | None = None

    def record_packet(self, characteristic: str, payload: bytes) -> None:
        self.last_packet_monotonic = time.monotonic()
        packet = RawPacket(
            received_at_utc=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            characteristic=short_uuid(characteristic),
            payload_hex=payload.hex(" ").upper(),
            length=len(payload),
        )
        with self.csv_path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=RawPacket.__annotations__.keys())
            if handle.tell() == 0:
                writer.writeheader()
            writer.writerow(asdict(packet))

    def measurement_for(self, key: str) -> Measurement:
        measurement = self.pending.get(key)
        if measurement is None:
            measurement = Measurement(
                sequence=len(self.measurements) + len(self.pending) + 1,
                timestamp_key_hex=key,
            )
            self.pending[key] = measurement
        return measurement

    def complete_if_ready(self, key: str) -> Measurement | None:
        measurement = self.pending.get(key)
        if measurement is None or not measurement.complete:
            return None
        self.pending.pop(key)
        measurement.sequence = len(self.measurements) + 1
        self.measurements.append(measurement)
        return measurement

    def save(self, completion_reason: str) -> None:
        all_records = self.measurements + list(self.pending.values())
        all_records.sort(key=lambda item: item.scale_timestamp_utc or "", reverse=True)
        for index, measurement in enumerate(all_records, start=1):
            measurement.sequence = index

        payload = {
            "session": {
                "completed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "completion_reason": completion_reason,
                "request_hex": self.request_hex,
                "record_count": len(all_records),
                "complete_record_count": sum(item.complete for item in all_records),
                "status_frame_count": len(self.status_frames),
                "measurement_epoch": "2010-01-01T00:00:00+00:00",
                "profile_note": (
                    "Byte 13 is exposed as a candidate profile number. The tested user "
                    "is configured as profile 1, but the field is not yet independently confirmed."
                ),
            },
            "measurements": [asdict(item) | {"complete": item.complete} for item in all_records],
            "status_frames": self.status_frames,
        }
        self.json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def configure_logging(path: Path) -> logging.Logger:
    logger = logging.getLogger("bs430-reader")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )
    for handler in (logging.StreamHandler(sys.stdout), logging.FileHandler(path, encoding="utf-8")):
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
        logger.info("Scanning. Complete a normal body-analysis weighing or wake the scale.")
        return await found
    finally:
        await scanner.stop()


def timestamp_key(payload: bytes, characteristic: str) -> str:
    if characteristic == CHAR_WEIGHT:
        if len(payload) < 9:
            raise ValueError(f"Weight frame is too short: {len(payload)} bytes")
        raw = payload[5:9]
    elif characteristic == CHAR_FEATURE:
        if len(payload) < 5:
            raise ValueError(f"Feature frame is too short: {len(payload)} bytes")
        raw = payload[1:5]
    else:
        raise ValueError(f"No timestamp layout defined for {short_uuid(characteristic)}")
    return raw.hex().upper()


def decode_scale_time(raw: bytes) -> str:
    seconds = int.from_bytes(raw, byteorder="little", signed=False)
    return (MEDISANA_EPOCH + timedelta(seconds=seconds)).isoformat(timespec="seconds")


def decode_weight(payload: bytes, measurement: Measurement) -> None:
    raw_weight = int.from_bytes(payload[1:3], byteorder="little", signed=False)
    measurement.weight_kg = raw_weight / 100.0
    measurement.scale_timestamp_utc = decode_scale_time(payload[5:9])
    measurement.received_at_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
    measurement.weight_frame_hex = payload.hex(" ").upper()

    if len(payload) >= 11:
        measurement.impedance_ohm = int.from_bytes(payload[9:11], "little") / 10.0
    if len(payload) >= 14:
        measurement.profile_id_candidate = payload[13]

    known = {1, 2, 5, 6, 7, 8, 9, 10, 13}
    measurement.weight_unknown_bytes_hex = " ".join(
        f"{value:02X}" for index, value in enumerate(payload) if index not in known
    )


def decode_feature_value(payload: bytes, offset: int) -> float:
    raw = int.from_bytes(payload[offset : offset + 2], byteorder="little", signed=False)
    return (raw & 0x0FFF) / 10.0


def decode_features(payload: bytes, measurement: Measurement) -> None:
    if len(payload) < 16:
        raise ValueError(f"Feature frame is too short: {len(payload)} bytes")
    measurement.scale_timestamp_utc = decode_scale_time(payload[1:5])
    measurement.body_fat_percent = decode_feature_value(payload, 8)
    measurement.body_water_percent = decode_feature_value(payload, 10)
    measurement.muscle_percent = decode_feature_value(payload, 12)
    measurement.bone_mass_kg = decode_feature_value(payload, 14)
    measurement.feature_frame_hex = payload.hex(" ").upper()
    measurement.received_at_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
    known = set(range(1, 5)) | set(range(8, 16))
    measurement.feature_unknown_bytes_hex = " ".join(
        f"{value:02X}" for index, value in enumerate(payload) if index not in known
    )


def time_command() -> bytes:
    return bytes([0x02]) + int(time.time()).to_bytes(4, byteorder="little", signed=False)


def log_measurement(logger: logging.Logger, measurement: Measurement) -> None:
    logger.info(
        "RECORD %d time=%s weight=%s kg fat=%s%% water=%s%% muscle=%s%% "
        "bone=%s kg impedance=%s ohm profile_candidate=%s",
        measurement.sequence,
        measurement.scale_timestamp_utc,
        measurement.weight_kg,
        measurement.body_fat_percent,
        measurement.body_water_percent,
        measurement.muscle_percent,
        measurement.bone_mass_kg,
        measurement.impedance_ohm,
        measurement.profile_id_candidate,
    )


async def capture(
    device: BLEDevice,
    recorder: SessionRecorder,
    logger: logging.Logger,
    timeout_seconds: float,
    quiet_seconds: float,
) -> str:
    disconnected = asyncio.Event()

    def on_disconnect(_: BleakClient) -> None:
        logger.info("Scale disconnected.")
        disconnected.set()

    async with BleakClient(device, disconnected_callback=on_disconnect, timeout=12.0) as client:
        logger.info("Connected: %s", client.is_connected)

        def notification(sender: Any, data: bytearray) -> None:
            uuid = str(getattr(sender, "uuid", sender)).lower()
            payload = bytes(data)
            recorder.record_packet(uuid, payload)
            logger.info("RX %s (%d): %s", short_uuid(uuid), len(payload), payload.hex(" ").upper())

            try:
                if uuid in (CHAR_WEIGHT, CHAR_FEATURE):
                    key = timestamp_key(payload, uuid)
                    measurement = recorder.measurement_for(key)
                    if uuid == CHAR_WEIGHT:
                        decode_weight(payload, measurement)
                    else:
                        decode_features(payload, measurement)
                    completed = recorder.complete_if_ready(key)
                    if completed is not None:
                        log_measurement(logger, completed)
                elif uuid == CHAR_STATUS:
                    recorder.status_frames.append(payload.hex(" ").upper())
                    logger.info("Status/session frame preserved.")
            except ValueError as exc:
                logger.warning("Could not decode %s: %s", short_uuid(uuid), exc)

        for uuid in INDICATION_UUIDS:
            await client.start_notify(uuid, notification)
            logger.info("Indications enabled: %s", short_uuid(uuid))

        command = time_command()
        recorder.request_hex = command.hex(" ").upper()
        logger.info("TX 8A81 (%d): %s", len(command), recorder.request_hex)
        await client.write_gatt_char(CHAR_COMMAND, command, response=True)
        logger.info("Synchronization request accepted. Waiting for stored records.")

        started = time.monotonic()
        while True:
            if disconnected.is_set():
                return "scale_disconnected"
            if time.monotonic() - started >= timeout_seconds:
                return "sync_timeout"
            if recorder.measurements and time.monotonic() - recorder.last_packet_monotonic >= quiet_seconds:
                return "quiet_period"
            await asyncio.sleep(0.25)


async def run(args: argparse.Namespace) -> None:
    recorder = SessionRecorder(Path(args.output))
    logger = configure_logging(recorder.log_path)
    logger.info("CSV packets: %s", recorder.csv_path)
    logger.info("Decoded JSON: %s", recorder.json_path)
    logger.info("Home Assistant is not accessed or modified.")
    device = await wait_for_scale(args.address, logger)
    reason = await capture(device, recorder, logger, args.timeout, args.quiet)
    recorder.save(reason)
    logger.info(
        "Sync completed: reason=%s complete=%d pending=%d JSON=%s",
        reason,
        len(recorder.measurements),
        len(recorder.pending),
        recorder.json_path,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Synchronize Medisana BS430 measurements")
    parser.add_argument("--address", default=TARGET_ADDRESS)
    parser.add_argument("--output", default="captures/private")
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--quiet", type=float, default=8.0)
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
