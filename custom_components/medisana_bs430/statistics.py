"""Historical statistics backfill for Medisana BS430."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.components.recorder import DOMAIN as RECORDER_DOMAIN
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import async_import_statistics
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfMass
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util.unit_conversion import MassConverter, UnitlessRatioConverter

from .bs430.history import build_hourly_measurement_statistics
from .bs430.models import Measurement
from .const import (
    CONF_IMPORT_HISTORY,
    DEFAULT_IMPORT_HISTORY,
    DOMAIN,
    MAX_PROFILE_ID,
    MIN_PROFILE_ID,
    PRIMARY_PROFILE_ID,
)


@dataclass(frozen=True, slots=True)
class _StatisticSensorSpec:
    key: str
    value_attribute: str
    unit: str | None
    unit_class: str | None


_STATISTIC_SENSOR_SPECS = (
    _StatisticSensorSpec("weight", "weight_kg", UnitOfMass.KILOGRAMS, MassConverter.UNIT_CLASS),
    _StatisticSensorSpec(
        "body_fat",
        "body_fat_percent",
        PERCENTAGE,
        UnitlessRatioConverter.UNIT_CLASS,
    ),
    _StatisticSensorSpec(
        "body_water",
        "body_water_percent",
        PERCENTAGE,
        UnitlessRatioConverter.UNIT_CLASS,
    ),
    _StatisticSensorSpec(
        "muscle", "muscle_percent", PERCENTAGE, UnitlessRatioConverter.UNIT_CLASS
    ),
    _StatisticSensorSpec("bone_mass", "bone_mass_kg", UnitOfMass.KILOGRAMS, MassConverter.UNIT_CLASS),
    _StatisticSensorSpec("impedance", "impedance_ohm", "Ω", None),
)

_MAX_HISTORY_AGE = timedelta(days=5 * 366)
_MAX_FUTURE_SKEW = timedelta(days=1)


def _sensor_unique_id(entry: ConfigEntry, profile_id: int, sensor_key: str) -> str | None:
    """Return the unique ID used by sensor.py for a profile sensor."""
    if entry.unique_id is None:
        return None
    if profile_id == PRIMARY_PROFILE_ID:
        return f"{entry.unique_id}_{sensor_key}"
    return f"{entry.unique_id}_profile_{profile_id}_{sensor_key}"


def _measurement_datetime(measurement: Measurement) -> datetime | None:
    """Return a safe UTC measurement timestamp for historical import."""
    try:
        timestamp = datetime.fromisoformat(measurement.scale_timestamp_utc)
    except (TypeError, ValueError):
        return None
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        return None
    return timestamp.astimezone(timezone.utc)


def _plausible_measurements(measurements: list[Measurement]) -> list[Measurement]:
    """Reject clock-corrupted records before they can reach recorder statistics."""
    now = datetime.now(timezone.utc)
    earliest = now - _MAX_HISTORY_AGE
    latest = now + _MAX_FUTURE_SKEW
    result: list[Measurement] = []
    for measurement in measurements:
        timestamp = _measurement_datetime(measurement)
        if timestamp is None or timestamp < earliest or timestamp > latest:
            continue
        result.append(measurement)
    return result


def import_recovered_history(
    hass: HomeAssistant,
    entry: ConfigEntry,
    measurements: list[Measurement],
) -> dict[str, Any]:
    """Backfill Home Assistant long-term statistics from scale memory.

    Home Assistant's supported import API works at hourly resolution. Existing
    rows for the same entity/hour are updated, making repeated scale syncs
    idempotent. We reconstruct carry-forward hours between weigh-ins so a stale
    pre-outage value does not remain across the Bluetooth gap.
    """
    if not entry.options.get(CONF_IMPORT_HISTORY, DEFAULT_IMPORT_HISTORY):
        return {
            "enabled": False,
            "records_considered": 0,
            "statistics_imported": 0,
            "entities_imported": 0,
        }

    valid = _plausible_measurements(measurements)
    registry = er.async_get(hass)
    imported_statistics = 0
    imported_entities = 0

    for profile_id in range(MIN_PROFILE_ID, MAX_PROFILE_ID + 1):
        profile_measurements = [
            measurement
            for measurement in valid
            if measurement.profile_id_candidate == profile_id
        ]
        if not profile_measurements:
            continue

        for spec in _STATISTIC_SENSOR_SPECS:
            unique_id = _sensor_unique_id(entry, profile_id, spec.key)
            if unique_id is None:
                continue
            entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
            if entity_id is None:
                continue

            hourly = build_hourly_measurement_statistics(
                profile_measurements, spec.value_attribute
            )
            if not hourly:
                continue

            metadata: StatisticMetaData = {
                "mean_type": StatisticMeanType.ARITHMETIC,
                "has_sum": False,
                "name": None,
                "source": RECORDER_DOMAIN,
                "statistic_id": entity_id,
                "unit_class": spec.unit_class,
                "unit_of_measurement": spec.unit,
            }
            statistics: list[StatisticData] = [
                {
                    "start": item.start,
                    "mean": item.mean,
                    "min": item.minimum,
                    "max": item.maximum,
                }
                for item in hourly
            ]
            async_import_statistics(hass, metadata, statistics)
            imported_statistics += len(statistics)
            imported_entities += 1

    return {
        "enabled": True,
        "records_considered": len(valid),
        "statistics_imported": imported_statistics,
        "entities_imported": imported_entities,
    }
