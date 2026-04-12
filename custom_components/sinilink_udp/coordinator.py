"""DataUpdateCoordinator for the Sinilink XY-WFTX integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_POLL_INTERVAL, DISCOVERY_PAYLOAD, DOMAIN
from .mqtt import SinilinkMqttClient
from .protocol import (
    SinilinkProtocolError,
    SinilinkStatus,
    async_query,
    parse_status,
)

_LOGGER = logging.getLogger(__name__)


class SinilinkCoordinator(DataUpdateCoordinator[SinilinkStatus]):
    """Polls a single Sinilink device via UDP and sends commands via MQTT."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        mac: str,
        mqtt_host: str | None = None,
        mqtt_port: int | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}:{mac}",
            update_interval=timedelta(seconds=DEFAULT_POLL_INTERVAL),
        )
        self.host = host
        self.mac = mac.upper()
        self._mqtt_client: SinilinkMqttClient | None = None
        if mqtt_host and mqtt_port:
            self._mqtt_client = SinilinkMqttClient(
                host=mqtt_host,
                port=mqtt_port,
                mac=self.mac,
                on_status=self._on_mqtt_status,
            )

    @property
    def mqtt_available(self) -> bool:
        return self._mqtt_client is not None and self._mqtt_client.connected

    async def async_start_mqtt(self) -> None:
        if self._mqtt_client:
            await self._mqtt_client.async_connect()

    async def async_stop_mqtt(self) -> None:
        if self._mqtt_client:
            await self._mqtt_client.async_disconnect()

    async def _async_update_data(self) -> SinilinkStatus:
        try:
            raw = await async_query(self.host, DISCOVERY_PAYLOAD)
        except (OSError, TimeoutError) as err:
            raise UpdateFailed(f"UDP query to {self.host} failed: {err}") from err
        if raw is None:
            raise UpdateFailed("no reply from device")
        try:
            return parse_status(raw)
        except SinilinkProtocolError as err:
            raise UpdateFailed(f"could not parse reply: {err}") from err

    async def async_mqtt_command(
        self, method: str, param: str | int | float
    ) -> None:
        """Send an MQTT command and refresh status."""
        if not self._mqtt_client:
            raise HomeAssistantError(
                "MQTT is not configured. Add the MQTT broker in the "
                "integration options to enable write control."
            )
        if not self._mqtt_client.connected:
            raise HomeAssistantError(
                "MQTT broker is not connected. Check the broker at "
                f"{self._mqtt_client.host}:{self._mqtt_client.port}."
            )
        try:
            await self._mqtt_client.async_send_command(method, param)
        except (ConnectionError, OSError) as err:
            raise HomeAssistantError(f"MQTT command failed: {err}") from err
        await self.async_request_refresh()

    def _on_mqtt_status(self, status: SinilinkStatus) -> None:
        """Called by the MQTT client when a PROWT message arrives."""
        self.async_set_updated_data(status)
