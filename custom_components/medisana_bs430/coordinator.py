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
        self._automatic_task: asyncio.Task | None = None
        self.last_error: str | None = None
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
        """Synchronize using a fresh Bluetooth advertisement device."""
        async with self._sync_lock:
            try:
                result = await synchronize(ble_device)
            except Exception as err:
                self.last_error = str(err)
                raise UpdateFailed(f"BS430 synchronization failed: {err}") from err

            self.last_error = None
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
        if self._automatic_task and not self._automatic_task.done():
            return
        _LOGGER.info(
            "BS430 wake advertisement received from %s via %s",
            service_info.address,
            service_info.source,
        )
        self._automatic_task = self.hass.async_create_task(
            self._async_sync_from_discovery(service_info),
            "Medisana BS430 automatic synchronization",
        )

    async def _async_sync_from_discovery(
        self, service_info: bluetooth.BluetoothServiceInfoBleak
    ) -> None:
        """Retry briefly while the scale's Bluetooth wake window is open."""
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                await self._async_synchronize_device(service_info.device)
                _LOGGER.info("Automatic BS430 synchronization succeeded")
                return
            except UpdateFailed as err:
                last_error = err
                _LOGGER.warning(
                    "Automatic BS430 synchronization attempt %d failed: %s",
                    attempt,
                    err,
                )
                if attempt < 3:
                    await asyncio.sleep(0.8)
        if last_error:
            _LOGGER.error("Automatic BS430 synchronization failed: %s", last_error)

    async def async_sync_now(self) -> None:
        """Run a user-requested synchronization."""
        await self.async_request_refresh()
