"""Button platform for Medisana BS430."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import MedisanaBS430Coordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coordinator: MedisanaBS430Coordinator = entry.runtime_data
    async_add_entities([MedisanaBS430SyncButton(coordinator, entry)])


class MedisanaBS430SyncButton(CoordinatorEntity[MedisanaBS430Coordinator], ButtonEntity):
    """Trigger a synchronization session."""

    _attr_has_entity_name = True
    _attr_name = "Synchronize now"
    _attr_icon = "mdi:sync"

    def __init__(self, coordinator: MedisanaBS430Coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_synchronize"
        self._attr_device_info = {
            "identifiers": {("medisana_bs430", entry.unique_id)},
            "manufacturer": "Medisana",
            "model": "BS430",
            "name": entry.title,
        }

    async def async_press(self) -> None:
        await self.coordinator.async_sync_now()
