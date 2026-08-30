from datetime import datetime, timezone

import pytest

from medisana_bs430.history import build_hourly_measurement_statistics
from medisana_bs430.models import Measurement


def _measurement(timestamp: str, weight: float) -> Measurement:
    return Measurement(
        timestamp_raw=0,
        scale_timestamp_utc=timestamp,
        timestamp_epoch="unix",
        weight_kg=weight,
    )


def test_history_rebuilds_missing_hours_with_last_known_value() -> None:
    measurements = [
        _measurement("2026-08-05T10:15:00+00:00", 80.0),
        _measurement("2026-08-05T12:30:00+00:00", 79.5),
    ]

    result = build_hourly_measurement_statistics(measurements, "weight_kg")

    assert [item.start for item in result] == [
        datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc),
        datetime(2026, 8, 5, 11, 0, tzinfo=timezone.utc),
        datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc),
    ]
    assert [item.mean for item in result] == [80.0, 80.0, 79.75]


def test_history_time_weights_multiple_measurements_in_one_hour() -> None:
    measurements = [
        _measurement("2026-08-05T10:05:00+00:00", 80.0),
        _measurement("2026-08-05T10:45:00+00:00", 79.6),
    ]

    result = build_hourly_measurement_statistics(measurements, "weight_kg")

    assert len(result) == 1
    assert result[0].start == datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc)
    assert result[0].mean == pytest.approx(79.9)
    assert result[0].minimum == 79.6
    assert result[0].maximum == 80.0


def test_history_skips_measurements_without_requested_value() -> None:
    measurement = Measurement(
        timestamp_raw=0,
        scale_timestamp_utc="2026-08-05T10:15:00+00:00",
        timestamp_epoch="unix",
        weight_kg=80.0,
    )

    assert build_hourly_measurement_statistics([measurement], "body_fat_percent") == []
