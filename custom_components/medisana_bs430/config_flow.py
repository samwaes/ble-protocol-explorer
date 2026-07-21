"""Config flow for Medisana BS430."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME

from .const import CONF_ADDRESS, DOMAIN, MAX_PROFILE_ID, MODEL, PROFILE_NAME_KEY_PREFIX
from .bs430.protocol import NAME_PREFIX, SERVICE_UUID


class MedisanaBS430ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle configuration of a Medisana BS430."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery_info: BluetoothServiceInfoBleak | None = None

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the profile naming options flow."""
        return MedisanaBS430OptionsFlow()

    @staticmethod
    def _is_bs430(service_info: BluetoothServiceInfoBleak) -> bool:
        name = (service_info.name or "").upper()
        service_uuids = {uuid.lower() for uuid in service_info.service_uuids}
        return name.startswith(NAME_PREFIX) or SERVICE_UUID in service_uuids

    async def async_step_bluetooth(self, discovery_info: BluetoothServiceInfoBleak) -> ConfigFlowResult:
        self._discovery_info = discovery_info
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self.context["title_placeholders"] = {"name": discovery_info.name or MODEL}
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
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

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        discoveries = [
            info
            for info in bluetooth.async_discovered_service_info(self.hass, connectable=True)
            if self._is_bs430(info)
        ]
        if len(discoveries) == 1:
            return await self.async_step_bluetooth(discoveries[0])
        if len(discoveries) > 1:
            return await self.async_step_bluetooth(max(discoveries, key=lambda info: info.rssi))
        errors = {"base": "device_not_found"} if user_input is not None else {}
        return self.async_show_form(step_id="user", data_schema=vol.Schema({}), errors=errors)


class MedisanaBS430OptionsFlow(OptionsFlow):
    """Configure the person name linked to each scale profile."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            cleaned = {key: str(value).strip() for key, value in user_input.items()}
            return self.async_create_entry(title="", data=cleaned)

        schema: dict[Any, Any] = {}
        for profile_id in range(1, MAX_PROFILE_ID + 1):
            key = f"{PROFILE_NAME_KEY_PREFIX}{profile_id}"
            schema[vol.Optional(key, default=self.config_entry.options.get(key, ""))] = str
        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema))
