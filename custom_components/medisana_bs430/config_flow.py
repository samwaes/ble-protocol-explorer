"""Config flow for Medisana BS430."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME

from .const import CONF_ADDRESS, DOMAIN, MODEL
from .bs430.protocol import NAME_PREFIX, SERVICE_UUID


class MedisanaBS430ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle configuration of a Medisana BS430."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery_info: BluetoothServiceInfoBleak | None = None

    @staticmethod
    def _is_bs430(service_info: BluetoothServiceInfoBleak) -> bool:
        """Return whether a discovery belongs to a BS430."""
        name = (service_info.name or "").upper()
        service_uuids = {uuid.lower() for uuid in service_info.service_uuids}
        return name.startswith(NAME_PREFIX) or SERVICE_UUID in service_uuids

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
        """Find a recently discovered scale during manual setup."""
        discoveries = [
            info
            for info in bluetooth.async_discovered_service_info(
                self.hass, connectable=True
            )
            if self._is_bs430(info)
        ]

        if len(discoveries) == 1:
            return await self.async_step_bluetooth(discoveries[0])

        if len(discoveries) > 1:
            # BS430 installations normally contain one scale. Prefer the
            # strongest currently cached advertisement and still confirm it.
            selected = max(discoveries, key=lambda info: info.rssi)
            return await self.async_step_bluetooth(selected)

        errors = {"base": "device_not_found"} if user_input is not None else {}
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            errors=errors,
        )
