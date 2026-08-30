"""Pure packet decoding for the Medisana BS430."""

from __future__ import annotations

from datetime import datetime, timezone

from .models import Measurement
from .protocol import MEDISANA_EPOCH_OFFSET

_TIMESTAMP_PLAUSIBILITY_SECONDS = int(5 * 365.25 * 24 * 60 * 60)


def timestamp_key(payload: bytes) -> int:
    if len(payload) < 5:
        raise ValueError("Frame is too short to contain a timestamp")
    offset = 5 if payload[0] == 0x1D else 1
    if len(payload) < offset + 4:
        raise ValueError("Frame is too short to contain a timestamp")
    return int.from_bytes(payload[offset : offset + 4], "little")


def decode_timestamp(
    raw: int, *, reference: datetime | None = None
) -> tuple[datetime, str]:
    """Decode a BS430 timestamp that may use Unix or the legacy 2010 epoch.

    Captures from the same physical BS430 have contained both encodings. The
    scale only keeps a small recent history, so the candidate closest to the
    current/reference time is the safest deterministic choice. A five-year
    plausibility window is used first, then proximity is used as a fallback so
    diagnostics still expose clock-corrupted records rather than crashing.
    """
    if raw < 0:
        raise ValueError("Timestamp cannot be negative")

    reference = reference or datetime.now(timezone.utc)
    if reference.tzinfo is None or reference.utcoffset() is None:
        raise ValueError("Reference timestamp must be timezone-aware")
    reference = reference.astimezone(timezone.utc)

    candidates = (
        (datetime.fromtimestamp(raw, timezone.utc), "unix"),
        (
            datetime.fromtimestamp(raw + MEDISANA_EPOCH_OFFSET, timezone.utc),
            "medisana_2010",
        ),
    )
    plausible = [
        candidate
        for candidate in candidates
        if abs((candidate[0] - reference).total_seconds())
        <= _TIMESTAMP_PLAUSIBILITY_SECONDS
    ]
    pool = plausible or list(candidates)
    return min(pool, key=lambda candidate: abs((candidate[0] - reference).total_seconds()))


def timestamp_to_utc(raw: int, *, reference: datetime | None = None) -> str:
    """Return the corrected UTC timestamp as an ISO-8601 string."""
    decoded, _epoch = decode_timestamp(raw, reference=reference)
    return decoded.isoformat(timespec="seconds")


def decode_weight_frame(payload: bytes) -> Measurement:
    if len(payload) < 19:
        raise ValueError(f"Weight frame is too short: {len(payload)} bytes")
    raw_timestamp = int.from_bytes(payload[5:9], "little")
    timestamp, epoch = decode_timestamp(raw_timestamp)
    raw_impedance = int.from_bytes(payload[9:11], "little")
    return Measurement(
        timestamp_raw=raw_timestamp,
        scale_timestamp_utc=timestamp.isoformat(timespec="seconds"),
        timestamp_epoch=epoch,
        weight_kg=int.from_bytes(payload[1:3], "little") / 100.0,
        impedance_ohm=raw_impedance / 10.0,
        profile_id_candidate=payload[13],
        profile_confidence="probable" if payload[13] else "unconfirmed",
        weight_frame_hex=payload.hex(" ").upper(),
        unknown_weight_bytes_hex=" ".join(
            f"{value:02X}"
            for index, value in enumerate(payload)
            if index not in {1, 2, 5, 6, 7, 8, 9, 10, 13}
        ),
    )


def _feature_value(payload: bytes, offset: int) -> float:
    return (int.from_bytes(payload[offset : offset + 2], "little") & 0x0FFF) / 10.0


def decode_feature_frame(
    payload: bytes, measurement: Measurement | None = None
) -> Measurement:
    if len(payload) < 19:
        raise ValueError(f"Feature frame is too short: {len(payload)} bytes")
    raw_timestamp = int.from_bytes(payload[1:5], "little")
    if measurement is None:
        timestamp, epoch = decode_timestamp(raw_timestamp)
        result = Measurement(
            raw_timestamp,
            timestamp.isoformat(timespec="seconds"),
            timestamp_epoch=epoch,
        )
    else:
        result = measurement
    if result.timestamp_raw != raw_timestamp:
        raise ValueError("Feature frame timestamp does not match weight frame")
    result.body_fat_percent = _feature_value(payload, 8)
    result.body_water_percent = _feature_value(payload, 10)
    result.muscle_percent = _feature_value(payload, 12)
    result.bone_mass_kg = _feature_value(payload, 14)
    result.feature_frame_hex = payload.hex(" ").upper()
    known = set(range(1, 5)) | set(range(8, 16))
    result.unknown_feature_bytes_hex = " ".join(
        f"{value:02X}" for index, value in enumerate(payload) if index not in known
    )
    return result
