"""Dedicated MQTT client for Sinilink XY-WFTX devices.

Connects to the standalone Mosquitto broker that the device uses (not
HA's built-in MQTT integration). Provides command publishing and
optional status subscription.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Callable
from typing import Any

import aiomqtt

from .const import MQTT_TOPIC_COMMAND, MQTT_TOPIC_ONLINE, MQTT_TOPIC_STATUS
from .protocol import SinilinkProtocolError, SinilinkStatus, parse_status

_LOGGER = logging.getLogger(__name__)


class SinilinkMqttClient:
    """Async MQTT client for a single Sinilink device."""

    def __init__(
        self,
        host: str,
        port: int,
        mac: str,
        on_status: Callable[[SinilinkStatus], None] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.mac = mac.upper()
        self._on_status = on_status
        self._client: aiomqtt.Client | None = None
        self._listener_task: asyncio.Task[None] | None = None
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def status_topic(self) -> str:
        return f"{MQTT_TOPIC_STATUS}{self.mac}"

    @property
    def command_topic(self) -> str:
        return f"{MQTT_TOPIC_COMMAND}{self.mac}"

    @property
    def online_topic(self) -> str:
        return f"{MQTT_TOPIC_ONLINE}{self.mac}"

    async def async_connect(self) -> None:
        """Connect to the broker and start the listener."""
        self._listener_task = asyncio.create_task(self._listen_loop())

    async def async_disconnect(self) -> None:
        """Stop the listener and disconnect."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None
        self._connected = False

    async def async_send_command(
        self, method: str, param: str | int | float
    ) -> None:
        """Publish a command to ``APPWT{MAC}``."""
        if not self._client or not self._connected:
            raise ConnectionError("MQTT client is not connected")
        payload = json.dumps(
            {"method": method, "param": param, "time": int(time.time())},
            separators=(",", ":"),
        )
        await self._client.publish(self.command_topic, payload)
        _LOGGER.debug("MQTT command sent: %s → %s", self.command_topic, payload)

    async def _listen_loop(self) -> None:
        """Reconnecting listener loop."""
        backoff = 1
        while True:
            try:
                async with aiomqtt.Client(
                    self.host,
                    port=self.port,
                    identifier=f"ha-sinilink-{self.mac}",
                ) as client:
                    self._client = client
                    self._connected = True
                    backoff = 1
                    _LOGGER.info(
                        "MQTT connected to %s:%s for %s",
                        self.host, self.port, self.mac,
                    )
                    await client.subscribe(self.status_topic)
                    await client.subscribe(self.online_topic)
                    async for message in client.messages:
                        self._handle_message(message)
            except aiomqtt.MqttError as err:
                self._connected = False
                self._client = None
                _LOGGER.warning(
                    "MQTT connection lost (%s), reconnecting in %ss",
                    err, backoff,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)
            except asyncio.CancelledError:
                self._connected = False
                self._client = None
                return

    def _handle_message(self, message: aiomqtt.Message) -> None:
        topic = str(message.topic)
        payload = message.payload
        if isinstance(payload, (bytes, bytearray)):
            payload = payload.decode("utf-8", errors="replace")

        if topic == self.status_topic and self._on_status:
            try:
                status = parse_status(payload.encode("utf-8"))
                self._on_status(status)
            except SinilinkProtocolError as err:
                _LOGGER.debug("MQTT status parse error: %s", err)
