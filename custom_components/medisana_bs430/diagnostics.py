"""Diagnostics support for Medisana BS430."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import BUILD_COMMIT, INTEGRATION_VERSION, MAX_PROFILE_ID, PROFILE_NAME_KEY_PREFIX


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return privacy-conscious diagnostics for a config entry."""
    coordinator = entry.runtime_data
    latest_by_profile = coordinator.data.get("latest_by_profile", {}) if coordinator.data else {}
    profile_names = {
        profile_id: entry.options.get(f"{PROFILE_NAME_KEY_PREFIX}{profile_id}", "")
        for profile_id in range(1, MAX_PROFILE_ID + 1)
        if entry.options.get(f"{PROFILE_NAME_KEY_PREFIX}{profile_id}", "")
    }
    return {
        "release": {
            "integration_version": INTEGRATION_VERSION,
            "build_commit": BUILD_COMMIT,
        },
        "entry": {"title": entry.title, "unique_id": entry.unique_id},
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
            "record_count": coordinator.data.get("record_count", 0) if coordinator.data else 0,
            "accepted_record_count_last_sync": coordinator.data.get("accepted_record_count", 0) if coordinator.data else 0,
            "quarantined_record_count_last_sync": coordinator.data.get("quarantined_record_count", 0) if coordinator.data else 0,
            "accepted_record_count_session": coordinator.accepted_record_count,
            "quarantined_record_count_session": coordinator.quarantined_record_count,
            "completion_reason": coordinator.data.get("completion_reason") if coordinator.data else None,
            "profiles_with_current_data": sorted(latest_by_profile),
        },
        "profiles": {
            "mode": "profiles-1-to-8",
            "supported_profile_ids": list(range(1, MAX_PROFILE_ID + 1)),
            "configured_profile_names": profile_names,
            "observations": coordinator.profile_observations,
            "invalid_records_retained_in_memory": len(coordinator.last_quarantined_measurements),
        },
        "protocol": {"scale_writes_enabled": False},
    }
