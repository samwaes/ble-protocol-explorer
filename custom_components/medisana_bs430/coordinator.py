"""Data coordinator for the Medisana BS430 integration."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
import logging
from typing import Any

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .bs430.bluetooth import synchronize
from .const import CONF_ADDRESS, DOMAIN

_LOGGER = logging.getLogger(__name__)


class MedisanaBS430Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate synchronization sessions with the scale."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=None,
        )
        self.address = entry.data[CONF_ADDRESS]
        self.last_measurements: list[dict[str, Any]] = []
        self._sync_lock = asyncio.Lock()
        self._last_trigger_monotonic = 0.0
        self.data = {
            "latest": None,
            "measurements": [],
            "record_count": 0,
            "completion_reason": "waiting_for_scale",
        }

    async def _async_update_data(self) -> dict[str, Any]:
        """Synchronize all currently stored records from the scale."""
        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if ble_device is None:
            raise UpdateFailed(
                "Scale is not currently available; complete a validated weighing"
            )
        return await self._async_synchronize_device(ble_device)

    async def _async_synchronize_device(self, ble_device) -> dict[str, Any]:
        """Synchronize using the device from a fresh Bluetooth advertisement."""
        async with self._sync_lock:
            try:
                result = await synchronize(ble_device)
            except Exception as err:
                raise UpdateFailed(f"BS430 synchronization failed: {err}") from err

            self.last_measurements = [asdict(item) for item in result.measurements]
            latest = self.last_measurements[0] if self.last_measurements else None
            data = {
                "latest": latest,
                "measurements": self.last_measurements,
                "record_count": len(self.last_measurements),
                "completion_reason": result.completion_reason,
            }
            self.async_set_updated_data(data)
            return data

    def async_handle_bluetooth_discovery(
        self, service_info: bluetooth.BluetoothServiceInfoBleak
    ) -> None:
        """Start synchronization immediately when the configured scale wakes."""
        now = self.hass.loop.time()
        if self._sync_lock.locked() or now - self._last_trigger_monotonic < 5:
            return
        self._last_trigger_monotonic = now
        self.hass.async_create_task(
            self._async_sync_from_discovery(service_info),
            "Medisana BS430 automatic synchronization",
        )

    async def _async_sync_from_discovery(
        self, service_info: bluetooth.BluetoothServiceInfoBleak
    ) -> None:
        """Run an automatic synchronization from a discovery callback."""
        try:
            await self._async_synchronize_device(service_info.device)
        except UpdateFailed as err:
            _LOGGER.debug("Automatic BS430 synchronization did not complete: %s", err)

    async def async_sync_now(self) -> None:
        """Run a user-requested synchronization."""
        await self.async_request_refresh()
