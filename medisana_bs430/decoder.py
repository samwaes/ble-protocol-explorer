"""Pure packet decoding for the Medisana BS430."""

from __future__ import annotations

from datetime import datetime, timezone

from .models import Measurement
from .protocol import MEDISANA_EPOCH_OFFSET


def timestamp_key(payload: bytes) -> int:
    if len(payload) < 5:
        raise ValueError("Frame is too short to contain a timestamp")
    offset = 5 if payload[0] == 0x1D else 1
    if len(payload) < offset + 4:
        raise ValueError("Frame is too short to contain a timestamp")
    return int.from_bytes(payload[offset:offset + 4], "little")


def timestamp_to_utc(raw: int) -> str:
    unix_seconds = raw + MEDISANA_EPOCH_OFFSET
    return datetime.fromtimestamp(unix_seconds, timezone.utc).isoformat(timespec="seconds")


def decode_weight_frame(payload: bytes) -> Measurement:
    if len(payload) < 19:
        raise ValueError(f"Weight frame is too short: {len(payload)} bytes")
    raw_timestamp = int.from_bytes(payload[5:9], "little")
    raw_impedance = int.from_bytes(payload[9:11], "little")
    return Measurement(
        timestamp_raw=raw_timestamp,
        scale_timestamp_utc=timestamp_to_utc(raw_timestamp),
        weight_kg=int.from_bytes(payload[1:3], "little") / 100.0,
        impedance_ohm=raw_impedance / 10.0,
        profile_id_candidate=payload[13],
        profile_confidence="probable" if payload[13] else "unconfirmed",
        weight_frame_hex=payload.hex(" ").upper(),
        unknown_weight_bytes_hex=" ".join(f"{b:02X}" for i, b in enumerate(payload) if i not in {1,2,5,6,7,8,9,10,13}),
    )


def _feature_value(payload: bytes, offset: int) -> float:
    return (int.from_bytes(payload[offset:offset + 2], "little") & 0x0FFF) / 10.0


def decode_feature_frame(payload: bytes, measurement: Measurement | None = None) -> Measurement:
    if len(payload) < 19:
        raise ValueError(f"Feature frame is too short: {len(payload)} bytes")
    raw_timestamp = int.from_bytes(payload[1:5], "little")
    result = measurement or Measurement(raw_timestamp, timestamp_to_utc(raw_timestamp))
    if result.timestamp_raw != raw_timestamp:
        raise ValueError("Feature frame timestamp does not match weight frame")
    result.body_fat_percent = _feature_value(payload, 8)
    result.body_water_percent = _feature_value(payload, 10)
    result.muscle_percent = _feature_value(payload, 12)
    result.bone_mass_kg = _feature_value(payload, 14)
    result.feature_frame_hex = payload.hex(" ").upper()
    result.unknown_feature_bytes_hex = " ".join(f"{b:02X}" for i, b in enumerate(payload) if i not in set(range(1,5)) | set(range(8,16)))
    return result
