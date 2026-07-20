"""Diagnostics support for Medisana BS430."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import BUILD_COMMIT, INTEGRATION_VERSION


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return privacy-conscious diagnostics for a config entry."""
    coordinator = entry.runtime_data
    latest = None
    if coordinator.data:
        latest = coordinator.data.get("latest")
    return {
        "release": {
            "integration_version": INTEGRATION_VERSION,
            "build_commit": BUILD_COMMIT,
        },
        "entry": {
            "title": entry.title,
            "unique_id": entry.unique_id,
        },
        "runtime": {
            "sync_state": coordinator.sync_state,
            "last_trigger": coordinator.last_trigger,
            "last_advertisement": coordinator.last_advertisement,
            "last_attempt": coordinator.last_attempt,
            "last_successful_sync": coordinator.last_successful_sync,
            "last_error": coordinator.last_error,
            "advertisement_count": coordinator.advertisement_count,
            "automatic_trigger_count": coordinator.automatic_trigger_count,
            "manual_trigger_count": coordinator.manual_trigger_count,
            "successful_sync_count": coordinator.successful_sync_count,
            "failed_sync_count": coordinator.failed_sync_count,
            "record_count": coordinator.data.get("record_count", 0)
            if coordinator.data
            else 0,
            "completion_reason": coordinator.data.get("completion_reason")
            if coordinator.data
            else None,
            "latest_measurement_available": latest is not None,
        },
        "protocol": {
            "profile_decoding": "probable-not-confirmed",
            "scale_writes_enabled": False,
        },
    }
