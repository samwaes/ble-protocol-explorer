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
from homeassistant.util import dt as dt_util

from .bs430.bluetooth import synchronize
from .const import CONF_ADDRESS, DOMAIN, MAX_PROFILE_ID, MIN_PROFILE_ID, PRIMARY_PROFILE_ID

_LOGGER = logging.getLogger(__name__)


class MedisanaBS430Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate synchronization sessions with the scale."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, _LOGGER, name=DOMAIN, config_entry=entry, update_interval=None)
        self.address = entry.data[CONF_ADDRESS]
        self.last_measurements: list[dict[str, Any]] = []
        self.last_quarantined_measurements: list[dict[str, Any]] = []
        self.profile_observations: list[dict[str, Any]] = []
        self.latest_by_profile: dict[int, dict[str, Any]] = {}
        self._sync_lock = asyncio.Lock()
        self._automatic_task: asyncio.Task | None = None
        self.last_error: str | None = None
        self.last_advertisement: str | None = None
        self.last_attempt: str | None = None
        self.last_successful_sync: str | None = None
        self.last_trigger: str | None = None
        self.advertisement_count = 0
        self.automatic_trigger_count = 0
        self.manual_trigger_count = 0
        self.successful_sync_count = 0
        self.failed_sync_count = 0
        self.accepted_record_count = 0
        self.quarantined_record_count = 0
        self.sync_state = "waiting_for_scale"
        self.data = {
            "latest": None,
            "latest_by_profile": {},
            "measurements": [],
            "quarantined_measurements": [],
            "record_count": 0,
            "accepted_record_count": 0,
            "quarantined_record_count": 0,
            "completion_reason": "waiting_for_scale",
        }

    def _clear_advertisement_history(self) -> None:
        """Allow the next identical wake advertisement to trigger a callback."""
        bluetooth.async_clear_advertisement_history(self.hass, self.address)
        _LOGGER.debug("Cleared BS430 advertisement history for the next wake cycle")

    @staticmethod
    def _profile_observation(measurement: dict[str, Any], status: str) -> dict[str, Any]:
        """Create a privacy-conscious observation for profile validation."""
        return {
            "scale_timestamp_utc": measurement.get("scale_timestamp_utc"),
            "timestamp_raw": measurement.get("timestamp_raw"),
            "profile_id_candidate": measurement.get("profile_id_candidate"),
            "profile_confidence": measurement.get("profile_confidence"),
            "status": status,
            "has_weight_frame": measurement.get("weight_frame_hex") is not None,
            "has_feature_frame": measurement.get("feature_frame_hex") is not None,
        }

    async def _async_update_data(self) -> dict[str, Any]:
        """Synchronize all currently stored records from the scale."""
        self.manual_trigger_count += 1
        self.last_trigger = "manual"
        self.sync_state = "locating_scale"
        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if ble_device is None:
            self.sync_state = "waiting_for_scale"
            raise UpdateFailed("Scale is not currently available; complete a validated weighing")
        return await self._async_synchronize_device(ble_device, trigger="manual")

    async def _async_synchronize_device(self, ble_device: Any, *, trigger: str) -> dict[str, Any]:
        """Synchronize using a fresh Bluetooth advertisement device."""
        async with self._sync_lock:
            self.last_attempt = dt_util.utcnow().isoformat()
            self.last_trigger = trigger
            self.sync_state = "connecting"
            try:
                result = await synchronize(ble_device)
            except Exception as err:
                self.last_error = str(err)
                self.failed_sync_count += 1
                self.sync_state = "waiting_for_scale"
                raise UpdateFailed(f"BS430 synchronization failed: {err}") from err

            self.last_error = None
            self.successful_sync_count += 1
            self.last_successful_sync = dt_util.utcnow().isoformat()
            self.sync_state = "complete"

            received_measurements = [asdict(item) for item in result.measurements]
            accepted: list[dict[str, Any]] = []
            quarantined: list[dict[str, Any]] = []
            observations: list[dict[str, Any]] = []

            for measurement in received_measurements:
                profile_id = measurement.get("profile_id_candidate")
                if isinstance(profile_id, int) and MIN_PROFILE_ID <= profile_id <= MAX_PROFILE_ID:
                    accepted.append(measurement)
                    observations.append(self._profile_observation(measurement, "accepted"))
                    if profile_id not in self.latest_by_profile:
                        self.latest_by_profile[profile_id] = measurement
                else:
                    quarantined.append(measurement)
                    observations.append(self._profile_observation(measurement, "quarantined_invalid_profile"))

            self.last_measurements = accepted
            self.last_quarantined_measurements = quarantined
            self.profile_observations = (observations + self.profile_observations)[:40]
            self.accepted_record_count += len(accepted)
            self.quarantined_record_count += len(quarantined)

            if quarantined:
                _LOGGER.warning("Quarantined %d BS430 record(s) with an invalid profile", len(quarantined))

            data = {
                "latest": self.latest_by_profile.get(PRIMARY_PROFILE_ID),
                "latest_by_profile": dict(self.latest_by_profile),
                "measurements": accepted,
                "quarantined_measurements": quarantined,
                "record_count": len(received_measurements),
                "accepted_record_count": len(accepted),
                "quarantined_record_count": len(quarantined),
                "completion_reason": result.completion_reason,
            }
            self.async_set_updated_data(data)
            self.sync_state = "waiting_for_scale"
            return data

    def async_handle_bluetooth_discovery(self, service_info: bluetooth.BluetoothServiceInfoBleak) -> None:
        """Start synchronization immediately when the configured scale wakes."""
        self.advertisement_count += 1
        self.last_advertisement = dt_util.utcnow().isoformat()
        if self._automatic_task and not self._automatic_task.done():
            _LOGGER.debug("BS430 advertisement received while synchronization is already active")
            return
        self.automatic_trigger_count += 1
        self.last_trigger = "automatic"
        self.sync_state = "advertisement_seen"
        _LOGGER.info("BS430 wake advertisement received from %s via %s", service_info.address, service_info.source)
        self._automatic_task = self.hass.async_create_task(
            self._async_sync_from_discovery(service_info),
            "Medisana BS430 automatic synchronization",
        )

    async def _async_sync_from_discovery(self, service_info: bluetooth.BluetoothServiceInfoBleak) -> None:
        """Retry while the scale's approximately 30-second wake window is open."""
        last_error: Exception | None = None
        try:
            for attempt in range(1, 9):
                try:
                    self.sync_state = "connecting"
                    ble_device = bluetooth.async_ble_device_from_address(
                        self.hass, service_info.address, connectable=True
                    ) or service_info.device
                    await self._async_synchronize_device(ble_device, trigger="automatic")
                    _LOGGER.info("Automatic BS430 synchronization succeeded on attempt %d", attempt)
                    return
                except UpdateFailed as err:
                    last_error = err
                    _LOGGER.warning("Automatic BS430 synchronization attempt %d failed: %s", attempt, err)
                    if attempt < 8:
                        await asyncio.sleep(2.5)
            self.sync_state = "waiting_for_scale"
            if last_error:
                _LOGGER.error("Automatic BS430 synchronization failed: %s", last_error)
        finally:
            self._clear_advertisement_history()

    async def async_sync_now(self) -> None:
        """Run a user-requested synchronization."""
        try:
            await self.async_request_refresh()
        finally:
            self._clear_advertisement_history()
