"""DataUpdateCoordinator for the Sinilink XY-WFTX integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_POLL_INTERVAL, DISCOVERY_PAYLOAD, DOMAIN
from .protocol import (
    SinilinkProtocolError,
    SinilinkStatus,
    async_query,
    build_command,
    parse_status,
)

_LOGGER = logging.getLogger(__name__)


class SinilinkCoordinator(DataUpdateCoordinator[SinilinkStatus]):
    """Polls a single Sinilink device and pushes commands to it."""

    def __init__(self, hass: HomeAssistant, host: str, mac: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}:{mac}",
            update_interval=timedelta(seconds=DEFAULT_POLL_INTERVAL),
        )
        self.host = host
        self.mac = mac.upper()

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

    async def async_send_param(self, param: list[Any]) -> None:
        """Send a new param array to the device, then refresh."""
        payload = build_command(self.mac, param)
        try:
            await async_query(self.host, payload, expect_reply=False)
        except OSError as err:
            raise UpdateFailed(f"UDP send to {self.host} failed: {err}") from err
        await self.async_request_refresh()
