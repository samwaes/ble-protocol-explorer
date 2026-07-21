"""Sensor platform for Medisana BS430."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfMass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BUILD_COMMIT, INTEGRATION_VERSION, MANUFACTURER, MAX_PROFILE_ID, MODEL, PRIMARY_PROFILE_ID, PROFILE_NAME_KEY_PREFIX
from .coordinator import MedisanaBS430Coordinator


@dataclass(frozen=True, kw_only=True)
class BS430SensorDescription(SensorEntityDescription):
    data_key: str


SENSORS = (
    BS430SensorDescription(key="weight", name="Weight", data_key="weight_kg", native_unit_of_measurement=UnitOfMass.KILOGRAMS, device_class=SensorDeviceClass.WEIGHT, state_class=SensorStateClass.MEASUREMENT),
    BS430SensorDescription(key="body_fat", name="Body fat", data_key="body_fat_percent", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT),
    BS430SensorDescription(key="body_water", name="Body water", data_key="body_water_percent", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT),
    BS430SensorDescription(key="muscle", name="Muscle", data_key="muscle_percent", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT),
    BS430SensorDescription(key="bone_mass", name="Bone mass", data_key="bone_mass_kg", native_unit_of_measurement=UnitOfMass.KILOGRAMS, device_class=SensorDeviceClass.WEIGHT, state_class=SensorStateClass.MEASUREMENT),
    BS430SensorDescription(key="impedance", name="Impedance", data_key="impedance_ohm", native_unit_of_measurement="Ω", state_class=SensorStateClass.MEASUREMENT, entity_registry_enabled_default=False),
    BS430SensorDescription(key="profile", name="Profile", data_key="profile_id_candidate", entity_registry_enabled_default=False),
)


def _configured_profiles(entry: ConfigEntry) -> list[int]:
    profiles = [PRIMARY_PROFILE_ID]
    for profile_id in range(2, MAX_PROFILE_ID + 1):
        if str(entry.options.get(f"{PROFILE_NAME_KEY_PREFIX}{profile_id}", "")).strip():
            profiles.append(profile_id)
    return profiles


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coordinator: MedisanaBS430Coordinator = entry.runtime_data
    async_add_entities(
        BS430Sensor(coordinator, entry, description, profile_id)
        for profile_id in _configured_profiles(entry)
        for description in SENSORS
    )


class BS430Sensor(CoordinatorEntity[MedisanaBS430Coordinator], SensorEntity):
    entity_description: BS430SensorDescription
    _attr_has_entity_name = True

    def __init__(self, coordinator: MedisanaBS430Coordinator, entry: ConfigEntry, description: BS430SensorDescription, profile_id: int) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self.profile_id = profile_id
        self.profile_name = str(entry.options.get(f"{PROFILE_NAME_KEY_PREFIX}{profile_id}", "")).strip()
        if profile_id == PRIMARY_PROFILE_ID:
            self._attr_unique_id = f"{entry.unique_id}_{description.key}"
        else:
            self._attr_unique_id = f"{entry.unique_id}_profile_{profile_id}_{description.key}"
        label = self.profile_name or f"Profile {profile_id}"
        self._attr_name = description.name if profile_id == PRIMARY_PROFILE_ID and not self.profile_name else f"{label} {description.name}"
        self._attr_device_info = {
            "identifiers": {("medisana_bs430", entry.unique_id)},
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "name": entry.title,
            "sw_version": f"{INTEGRATION_VERSION} ({BUILD_COMMIT[:7]})",
        }

    def _latest(self) -> dict[str, Any] | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("latest_by_profile", {}).get(self.profile_id)

    @property
    def available(self) -> bool:
        latest = self._latest()
        if latest and self.entity_description.data_key in latest:
            return latest.get(self.entity_description.data_key) is not None
        return super().available

    @property
    def native_value(self) -> Any:
        latest = self._latest()
        return latest.get(self.entity_description.data_key) if latest else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        latest = self._latest()
        base = {
            "profile_id": self.profile_id,
            "profile_name": self.profile_name or None,
            "integration_version": INTEGRATION_VERSION,
            "build_commit": BUILD_COMMIT,
        }
        if not latest:
            return base
        return {
            **base,
            "measurement_time": latest.get("timestamp_local"),
            "profile_status": latest.get("profile_status"),
            "sync_record_count": self.coordinator.data.get("record_count"),
        }
