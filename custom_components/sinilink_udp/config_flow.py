"""Config flow for the Sinilink XY-WFTX integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_MAC
from homeassistant.data_entry_flow import FlowResult

from .const import BROADCAST_ADDR, DISCOVERY_PAYLOAD, DOMAIN
from .protocol import (
    SinilinkProtocolError,
    async_discover,
    async_query,
    parse_status,
)

_LOGGER = logging.getLogger(__name__)


class SinilinkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sinilink XY-WFTX (Local UDP)."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered: dict[str, dict[str, str]] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Initial menu: scan or manual."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["scan", "manual"],
        )

    async def async_step_scan(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Broadcast SINILINK521 and present discovered devices."""
        if user_input is None:
            try:
                results = await async_discover(BROADCAST_ADDR)
            except OSError as err:
                _LOGGER.warning("broadcast discovery failed: %s", err)
                return self.async_show_form(
                    step_id="scan",
                    errors={"base": "discovery_failed"},
                    data_schema=vol.Schema({}),
                )

            self._discovered = {
                status.mac: {"ip": status.__dict__.get("ip", ""), "mac": status.mac}
                for status in results
            }

            if not self._discovered:
                return self.async_show_form(
                    step_id="scan",
                    errors={"base": "no_devices_found"},
                    description_placeholders={"hint": "try manual entry"},
                    data_schema=vol.Schema({}),
                )

            choices = {
                mac: f"{info['mac']} @ {info['ip']}"
                for mac, info in self._discovered.items()
            }
            return self.async_show_form(
                step_id="scan",
                data_schema=vol.Schema({vol.Required("device"): vol.In(choices)}),
            )

        mac = user_input["device"]
        info = self._discovered[mac]
        return await self._create_entry(info["ip"], mac)

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manual host/MAC entry with validation."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            mac_input = user_input[CONF_MAC].upper()
            try:
                raw = await async_query(host, DISCOVERY_PAYLOAD)
                if raw is None:
                    raise SinilinkProtocolError("no reply")
                status = parse_status(raw)
            except (OSError, TimeoutError):
                errors["base"] = "cannot_connect"
            except SinilinkProtocolError:
                errors["base"] = "invalid_response"
            else:
                if status.mac != mac_input:
                    errors[CONF_MAC] = "mac_mismatch"
                else:
                    return await self._create_entry(host, status.mac)

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_MAC): str,
                }
            ),
            errors=errors,
        )

    async def _create_entry(self, host: str, mac: str) -> FlowResult:
        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        return self.async_create_entry(
            title=f"Sinilink {mac}",
            data={CONF_HOST: host, CONF_MAC: mac},
        )
