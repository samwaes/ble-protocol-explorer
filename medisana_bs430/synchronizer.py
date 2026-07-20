"""Packet assembly and duplicate-safe synchronization state."""

from __future__ import annotations

from .decoder import decode_feature_frame, decode_weight_frame, timestamp_key
from .models import Measurement, SyncResult
from .protocol import CHAR_FEATURE, CHAR_STATUS, CHAR_WEIGHT


class MeasurementAssembler:
    def __init__(self) -> None:
        self._pending: dict[int, Measurement] = {}
        self._complete: dict[str, Measurement] = {}
        self.status_frames: list[str] = []

    def feed(self, characteristic: str, payload: bytes) -> Measurement | None:
        uuid = characteristic.lower()
        if uuid == CHAR_STATUS:
            self.status_frames.append(payload.hex(" ").upper())
            return None
        if uuid == CHAR_WEIGHT:
            measurement = decode_weight_frame(payload)
            self._pending[measurement.timestamp_raw] = measurement
            return None
        if uuid == CHAR_FEATURE:
            key = timestamp_key(payload)
            measurement = decode_feature_frame(payload, self._pending.get(key))
            self._pending.pop(key, None)
            self._complete[measurement.fingerprint] = measurement
            return measurement
        return None

    def result(self, completion_reason: str) -> SyncResult:
        measurements = sorted(
            self._complete.values(), key=lambda item: item.timestamp_raw, reverse=True
        )
        return SyncResult(
            measurements=measurements,
            status_frames=list(self.status_frames),
            completion_reason=completion_reason,
        )
