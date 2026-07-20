"""Data models for Medisana BS430 synchronization."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class RawPacket:
    received_at_utc: str
    characteristic: str
    payload_hex: str
    length: int


@dataclass(slots=True)
class Measurement:
    timestamp_raw: int
    scale_timestamp_utc: str
    weight_kg: float | None = None
    body_fat_percent: float | None = None
    body_water_percent: float | None = None
    muscle_percent: float | None = None
    bone_mass_kg: float | None = None
    impedance_ohm: float | None = None
    profile_id_candidate: int | None = None
    profile_confidence: str = "unconfirmed"
    weight_frame_hex: str | None = None
    feature_frame_hex: str | None = None
    unknown_weight_bytes_hex: str | None = None
    unknown_feature_bytes_hex: str | None = None

    @property
    def complete(self) -> bool:
        return self.weight_frame_hex is not None and self.feature_frame_hex is not None

    @property
    def fingerprint(self) -> str:
        return f"{self.timestamp_raw}:{self.weight_frame_hex}:{self.feature_frame_hex}"


@dataclass(slots=True)
class SyncResult:
    measurements: list[Measurement] = field(default_factory=list)
    packets: list[RawPacket] = field(default_factory=list)
    status_frames: list[str] = field(default_factory=list)
    completion_reason: str = "unknown"
