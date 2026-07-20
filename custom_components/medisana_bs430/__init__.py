"""Home Assistant integration for the Medisana BS430."""

from __future__ import annotations

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import CONF_ADDRESS, PLATFORMS
from .coordinator import MedisanaBS430Coordinator


type MedisanaBS430ConfigEntry = ConfigEntry[MedisanaBS430Coordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: MedisanaBS430ConfigEntry
) -> bool:
    """Set up Medisana BS430 from a config entry."""
    coordinator = MedisanaBS430Coordinator(hass, entry)
    entry.runtime_data = coordinator

    @callback
    def _async_discovered_scale(
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        """React immediately when the short BS430 sync window opens."""
        coordinator.async_handle_bluetooth_discovery(service_info)

    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            _async_discovered_scale,
            {"address": entry.data[CONF_ADDRESS], "connectable": True},
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
    )

    # The scale is normally asleep during Home Assistant startup. Do not fail
    # setup merely because it is unavailable; the callback above synchronizes
    # as soon as a validated weighing wakes it.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: MedisanaBS430ConfigEntry
) -> bool:
    """Unload a Medisana BS430 config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
