"""Pure helpers for rebuilding hourly statistics from stored BS430 records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import fmean
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
    """Reconstruct hourly measurement statistics with carry-forward semantics.

    Home Assistant measurement sensors keep their last state until the next
    reading. For missing Bluetooth periods, the scale gives us discrete stored
    readings. Rebuilding every hour between the first and last recovered reading
    avoids leaving the stale pre-outage value in Home Assistant long-term stats.
    Hours with multiple weigh-ins keep their observed min/max and arithmetic mean.
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
        observations = observations_by_hour.get(current_hour, [])
        if observations:
            observations.sort(key=lambda item: item[0])
            values = [value for _timestamp, value in observations]
            carry_value = values[-1]
            result.append(
                HourlyMeasurementStatistic(
                    start=current_hour,
                    mean=fmean(values),
                    minimum=min(values),
                    maximum=max(values),
                )
            )
        elif carry_value is not None:
            result.append(
                HourlyMeasurementStatistic(
                    start=current_hour,
                    mean=carry_value,
                    minimum=carry_value,
                    maximum=carry_value,
                )
            )
        current_hour += timedelta(hours=1)

    return result
