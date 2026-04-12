"""Config flow for the Sinilink XY-WFTX integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_MAC
from homeassistant.data_entry_flow import FlowResult

from .const import (
    BROADCAST_ADDR,
    CONF_MQTT_HOST,
    CONF_MQTT_PORT,
    DEFAULT_MQTT_PORT,
    DISCOVERY_PAYLOAD,
    DOMAIN,
)
from .protocol import (
    SinilinkProtocolError,
    async_discover,
    async_query,
    parse_status,
)

_LOGGER = logging.getLogger(__name__)


class SinilinkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sinilink XY-WFTX (Local UDP)."""

    VERSION = 2

    def __init__(self) -> None:
        self._discovered: dict[str, dict[str, str]] = {}
        self._device_host: str = ""
        self._device_mac: str = ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        return self.async_show_menu(
            step_id="user",
            menu_options=["scan", "manual"],
        )

    async def async_step_scan(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
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
        self._device_host = info["ip"]
        self._device_mac = mac
        return await self.async_step_mqtt()

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
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
                    self._device_host = host
                    self._device_mac = status.mac
                    return await self.async_step_mqtt()

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

    async def async_step_mqtt(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """MQTT broker configuration (optional — skip for read-only mode)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            mqtt_host = user_input.get(CONF_MQTT_HOST, "").strip()
            mqtt_port = user_input.get(CONF_MQTT_PORT, DEFAULT_MQTT_PORT)

            if mqtt_host:
                # Validate connectivity
                try:
                    import aiomqtt
                    async with aiomqtt.Client(mqtt_host, port=mqtt_port) as _:
                        pass
                except Exception:
                    errors["base"] = "mqtt_cannot_connect"

                if not errors:
                    return await self._create_entry(
                        self._device_host,
                        self._device_mac,
                        mqtt_host=mqtt_host,
                        mqtt_port=mqtt_port,
                    )
            else:
                # Skip MQTT — read-only mode
                return await self._create_entry(
                    self._device_host, self._device_mac
                )

        return self.async_show_form(
            step_id="mqtt",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_MQTT_HOST, default=""): str,
                    vol.Optional(CONF_MQTT_PORT, default=DEFAULT_MQTT_PORT): int,
                }
            ),
            errors=errors,
        )

    async def _create_entry(
        self,
        host: str,
        mac: str,
        mqtt_host: str | None = None,
        mqtt_port: int | None = None,
    ) -> FlowResult:
        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        return self.async_create_entry(
            title=f"Sinilink {mac}",
            data={
                CONF_HOST: host,
                CONF_MAC: mac,
                CONF_MQTT_HOST: mqtt_host,
                CONF_MQTT_PORT: mqtt_port,
            },
        )
