"""Home Assistant integration for the Medisana BS430."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import PLATFORMS
from .coordinator import MedisanaBS430Coordinator


type MedisanaBS430ConfigEntry = ConfigEntry[MedisanaBS430Coordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: MedisanaBS430ConfigEntry
) -> bool:
    """Set up Medisana BS430 from a config entry."""
    coordinator = MedisanaBS430Coordinator(hass, entry)
    entry.runtime_data = coordinator
    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: MedisanaBS430ConfigEntry
) -> bool:
    """Unload a Medisana BS430 config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
