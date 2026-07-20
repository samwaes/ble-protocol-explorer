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

from .const import MANUFACTURER, MODEL
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
    BS430SensorDescription(key="profile", name="Profile", data_key="profile_candidate", entity_registry_enabled_default=False),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coordinator: MedisanaBS430Coordinator = entry.runtime_data
    async_add_entities(BS430Sensor(coordinator, entry, description) for description in SENSORS)


class BS430Sensor(CoordinatorEntity[MedisanaBS430Coordinator], SensorEntity):
    entity_description: BS430SensorDescription
    _attr_has_entity_name = True

    def __init__(self, coordinator: MedisanaBS430Coordinator, entry: ConfigEntry, description: BS430SensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.unique_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {("medisana_bs430", entry.unique_id)},
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "name": entry.title,
        }

    @property
    def native_value(self) -> Any:
        latest = self.coordinator.data.get("latest") if self.coordinator.data else None
        return latest.get(self.entity_description.data_key) if latest else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        latest = self.coordinator.data.get("latest") if self.coordinator.data else None
        if not latest:
            return {}
        return {
            "measurement_time": latest.get("timestamp_local"),
            "profile_status": latest.get("profile_status"),
            "sync_record_count": self.coordinator.data.get("record_count"),
        }
