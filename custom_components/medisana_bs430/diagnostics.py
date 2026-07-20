"""Diagnostics support for Medisana BS430."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return privacy-conscious diagnostics for a config entry."""
    coordinator = entry.runtime_data
    latest = None
    if coordinator.data:
        latest = coordinator.data.get("latest")
    return {
        "entry": {
            "title": entry.title,
            "unique_id": entry.unique_id,
        },
        "runtime": {
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
