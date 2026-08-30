"""Pure helpers for rebuilding hourly statistics from stored BS430 records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from .models import Measurement


@dataclass(frozen=True, slots=True)
class HourlyMeasurementStatistic:
    """One reconstructed Home Assistant long-term statistics hour."""

    start: datetime
    mean: float
    minimum: float
    maximum: float


def _measurement_time(measurement: Measurement) -> datetime:
    value = datetime.fromisoformat(measurement.scale_timestamp_utc)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Measurement timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


def build_hourly_measurement_statistics(
    measurements: Iterable[Measurement], value_attribute: str
) -> list[HourlyMeasurementStatistic]:
    """Reconstruct hourly statistics with Home Assistant state semantics.

    Recovered measurements are treated as state changes. The value remains
    active until the next weighing, so each hourly mean is time-weighted and
    min/max include every value active in that hour. For the portion of the first
    hour before the first recovered point, the first recovered value is used.
    """
    points: list[tuple[datetime, float]] = []
    for measurement in measurements:
        value = getattr(measurement, value_attribute, None)
        if value is None:
            continue
        points.append((_measurement_time(measurement), float(value)))

    if not points:
        return []

    points.sort(key=lambda item: item[0])
    observations_by_hour: dict[datetime, list[tuple[datetime, float]]] = {}
    for timestamp, value in points:
        hour = timestamp.replace(minute=0, second=0, microsecond=0)
        observations_by_hour.setdefault(hour, []).append((timestamp, value))

    first_hour = points[0][0].replace(minute=0, second=0, microsecond=0)
    last_hour = points[-1][0].replace(minute=0, second=0, microsecond=0)
    current_hour = first_hour
    carry_value: float | None = None
    result: list[HourlyMeasurementStatistic] = []

    while current_hour <= last_hour:
        hour_end = current_hour + timedelta(hours=1)
        observations = sorted(observations_by_hour.get(current_hour, []))
        if carry_value is None:
            if not observations:
                current_hour = hour_end
                continue
            carry_value = observations[0][1]

        current_value = carry_value
        current_time = current_hour
        values_in_hour = [current_value]
        weighted_sum = 0.0

        for timestamp, value in observations:
            weighted_sum += current_value * (timestamp - current_time).total_seconds()
            current_value = value
            current_time = timestamp
            values_in_hour.append(value)

        weighted_sum += current_value * (hour_end - current_time).total_seconds()
        carry_value = current_value
        result.append(
            HourlyMeasurementStatistic(
                start=current_hour,
                mean=weighted_sum / 3600.0,
                minimum=min(values_in_hour),
                maximum=max(values_in_hour),
            )
        )
        current_hour = hour_end

    return result
