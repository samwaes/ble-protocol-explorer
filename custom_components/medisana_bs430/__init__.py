"""Home Assistant integration for the Medisana BS430."""

from __future__ import annotations

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .bs430.protocol import NAME_PREFIX
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
        """React immediately when a validated weighing wakes the scale."""
        coordinator.async_handle_bluetooth_discovery(service_info)

    # Do not require the proprietary service UUID in every advertisement.
    # The BS430 does not consistently include it throughout the short wake
    # window, while its local-name prefix remains stable.
    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            _async_discovered_scale,
            {
                "local_name": f"{NAME_PREFIX}*",
                "connectable": True,
            },
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
    )

    # Also register the configured address as a fallback. Duplicate callbacks
    # are harmless because the coordinator allows only one active sync task.
    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            _async_discovered_scale,
            {
                "address": entry.data[CONF_ADDRESS],
                "connectable": True,
            },
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
    )

    # The scale is normally asleep during startup. Entities are loaded without
    # forcing a connection; the callbacks synchronize during the next validated
    # weighing when the Bluetooth symbol appears.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: MedisanaBS430ConfigEntry
) -> bool:
    """Unload a Medisana BS430 config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
