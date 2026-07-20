"""Config flow for Medisana BS430."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME

from .const import CONF_ADDRESS, DOMAIN, MODEL


class MedisanaBS430ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle configuration of a Medisana BS430."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery_info: BluetoothServiceInfoBleak | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle Bluetooth discovery."""
        self._discovery_info = discovery_info
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self.context["title_placeholders"] = {"name": discovery_info.name or MODEL}
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a discovered scale."""
        if self._discovery_info is None:
            return self.async_abort(reason="no_discovery_info")
        if user_input is not None:
            return self.async_create_entry(
                title=user_input.get(CONF_NAME, MODEL),
                data={CONF_ADDRESS: self._discovery_info.address},
            )
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({vol.Optional(CONF_NAME, default=MODEL): str}),
            description_placeholders={
                "address": self._discovery_info.address,
                "name": self._discovery_info.name or MODEL,
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Direct users to Bluetooth discovery."""
        return self.async_abort(reason="bluetooth_discovery_required")
