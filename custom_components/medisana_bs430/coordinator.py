"""Data coordinator for the Medisana BS430 integration."""

from __future__ import annotations

from dataclasses import asdict
import logging
from typing import Any

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from medisana_bs430.bluetooth import synchronize

from .const import CONF_ADDRESS, DOMAIN

_LOGGER = logging.getLogger(__name__)


class MedisanaBS430Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate explicit synchronization sessions with the scale."""

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

    async def _async_update_data(self) -> dict[str, Any]:
        """Synchronize all currently stored records from the scale."""
        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if ble_device is None:
            raise UpdateFailed(
                "Scale is not currently available; wake it by completing a weighing"
            )

        try:
            result = await synchronize(ble_device)
        except Exception as err:
            raise UpdateFailed(f"BS430 synchronization failed: {err}") from err

        self.last_measurements = [asdict(item) for item in result.measurements]
        latest = self.last_measurements[0] if self.last_measurements else None
        return {
            "latest": latest,
            "measurements": self.last_measurements,
            "record_count": len(self.last_measurements),
            "completion_reason": result.completion_reason,
        }

    async def async_sync_now(self) -> None:
        """Run a user-requested synchronization."""
        await self.async_request_refresh()
