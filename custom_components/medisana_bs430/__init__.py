"""Home Assistant integration for the Medisana BS430."""

from __future__ import annotations

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .bs430.protocol import NAME_PREFIX, SERVICE_UUID
from .const import PLATFORMS
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
        """React immediately when a validated weighing wakes the scale."""
        coordinator.async_handle_bluetooth_discovery(service_info)

    # Match the stable BS430 advertisement rather than only the stored address.
    # This avoids missing the very short wake window when the Bluetooth backend
    # reports the device through a refreshed or proxy-specific address object.
    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            _async_discovered_scale,
            {
                "local_name": f"{NAME_PREFIX}*",
                "service_uuid": SERVICE_UUID,
                "connectable": True,
            },
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
    )

    # The scale is normally asleep during startup. Entities are loaded without
    # forcing a connection; the callback synchronizes during the next validated
    # weighing when the Bluetooth symbol appears.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: MedisanaBS430ConfigEntry
) -> bool:
    """Unload a Medisana BS430 config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
