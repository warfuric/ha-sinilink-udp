"""Pure UDP protocol for Sinilink XY-WFTX devices.

No Home Assistant imports — this module is unit-testable in isolation.

Protocol summary (see reverse-engineering guide §2):
  * Device listens on UDP/1024.
  * Discovery: send the ASCII bytes ``SINILINK521`` to the device IP.
  * Reply format: ``MAC,{"MAC":"...","time":EPOCH,"param":[...]}``
  * Control: send ``MAC{"MAC":"...","time":EPOCH,"param":[...]}`` (no comma).
"""
from __future__ import annotations

import asyncio
import json
import logging
import socket
import time
from dataclasses import dataclass
from typing import Any

from .const import (
    DISCOVERY_DURATION,
    DISCOVERY_PAYLOAD,
    PARAM_ALARM_HIGH,
    PARAM_ALARM_HIGH_ENABLE,
    PARAM_ALARM_LOW,
    PARAM_ALARM_LOW_ENABLE,
    PARAM_CURRENT_TEMP,
    PARAM_ESTOP,
    PARAM_LED,
    PARAM_NOTIFICATIONS,
    PARAM_HEAT_COOL,
    PARAM_MODE,
    PARAM_RELAY,
    PARAM_START_TEMP,
    PARAM_STOP_TEMP,
    PARAM_UNIT,
    UDP_PORT,
    UDP_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class SinilinkProtocolError(Exception):
    """Raised when a Sinilink response cannot be parsed."""


@dataclass
class SinilinkStatus:
    """Decoded status from a Sinilink device."""

    mac: str
    epoch: int
    param: list[Any]
    relay: bool
    mode: str
    current_temp: float | None
    unit: str
    heat_cool: str
    start_temp: float | None
    stop_temp: float | None
    alarm_high: float | None
    alarm_high_enabled: bool
    alarm_low: float | None
    alarm_low_enabled: bool
    estop: bool
    led: bool
    notifications: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "mac": self.mac,
            "epoch": self.epoch,
            "param": self.param,
            "relay": self.relay,
            "mode": self.mode,
            "current_temp": self.current_temp,
            "unit": self.unit,
            "heat_cool": self.heat_cool,
            "start_temp": self.start_temp,
            "stop_temp": self.stop_temp,
            "alarm_high": self.alarm_high,
            "alarm_high_enabled": self.alarm_high_enabled,
            "alarm_low": self.alarm_low,
            "alarm_low_enabled": self.alarm_low_enabled,
            "estop": self.estop,
            "led": self.led,
            "notifications": self.notifications,
        }


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_status(raw: bytes) -> SinilinkStatus:
    """Parse a status reply from the device.

    Reply shape::

        MAC,{"MAC":"...","time":EPOCH,"param":[...]}
    """
    try:
        text = raw.decode("utf-8", errors="replace").strip()
    except Exception as err:  # pragma: no cover - decode is permissive
        raise SinilinkProtocolError(f"undecodable reply: {err!r}") from err

    brace = text.find("{")
    if brace < 0:
        raise SinilinkProtocolError(f"no JSON in reply: {text!r}")

    json_part = text[brace:]
    try:
        payload = json.loads(json_part)
    except json.JSONDecodeError as err:
        raise SinilinkProtocolError(f"invalid JSON: {err}; raw={text!r}") from err

    mac = str(payload.get("MAC", "")).upper()
    if not mac:
        raise SinilinkProtocolError(f"missing MAC field: {payload!r}")

    param = payload.get("param") or []
    if not isinstance(param, list):
        raise SinilinkProtocolError(f"param is not a list: {param!r}")

    def _get(idx: int, default: Any = None) -> Any:
        return param[idx] if idx < len(param) else default

    return SinilinkStatus(
        mac=mac,
        epoch=int(payload.get("time", payload.get("tim", 0)) or 0),
        param=list(param),
        relay=bool(_get(PARAM_RELAY, 0)),
        mode=str(_get(PARAM_MODE, "A")),
        current_temp=_safe_float(_get(PARAM_CURRENT_TEMP)),
        unit=str(_get(PARAM_UNIT, "C")),
        heat_cool=str(_get(PARAM_HEAT_COOL, "H")),
        start_temp=_safe_float(_get(PARAM_START_TEMP)),
        stop_temp=_safe_float(_get(PARAM_STOP_TEMP)),
        alarm_high=_safe_float(_get(PARAM_ALARM_HIGH)),
        alarm_high_enabled=bool(_get(PARAM_ALARM_HIGH_ENABLE, 0)),
        alarm_low=_safe_float(_get(PARAM_ALARM_LOW)),
        alarm_low_enabled=bool(_get(PARAM_ALARM_LOW_ENABLE, 0)),
        estop=bool(_get(PARAM_ESTOP, 0)),
        led=bool(_get(PARAM_LED, 0)),
        notifications=bool(_get(PARAM_NOTIFICATIONS, 0)),
    )


def build_command(mac: str, param: list[Any], epoch: int | None = None) -> bytes:
    """Build a control payload for the device.

    Format::

        MAC{"MAC":"MAC","time":EPOCH,"param":[...]}
    """
    if epoch is None:
        epoch = int(time.time())
    body = json.dumps(
        {"MAC": mac, "time": epoch, "param": param},
        separators=(",", ":"),
    )
    return f"{mac}{body}".encode("utf-8")


class _UDPClientProtocol(asyncio.DatagramProtocol):
    def __init__(self, future: asyncio.Future[bytes]) -> None:
        self._future = future

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        if not self._future.done():
            self._future.set_result(data)

    def error_received(self, exc: Exception) -> None:  # pragma: no cover
        if not self._future.done():
            self._future.set_exception(exc)

    def connection_lost(self, exc: Exception | None) -> None:
        if exc and not self._future.done():
            self._future.set_exception(exc)


async def async_query(
    host: str,
    payload: bytes,
    *,
    expect_reply: bool = True,
    timeout: float = UDP_TIMEOUT,
) -> bytes | None:
    """Send a UDP packet to ``host`` and optionally wait for a reply."""
    loop = asyncio.get_running_loop()
    future: asyncio.Future[bytes] = loop.create_future()

    transport, _ = await loop.create_datagram_endpoint(
        lambda: _UDPClientProtocol(future),
        remote_addr=(host, UDP_PORT),
    )
    try:
        transport.sendto(payload)
        if not expect_reply:
            return None
        return await asyncio.wait_for(future, timeout=timeout)
    finally:
        transport.close()


class _BroadcastCollector(asyncio.DatagramProtocol):
    def __init__(self) -> None:
        self.replies: list[tuple[bytes, tuple[str, int]]] = []

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        self.replies.append((data, addr))


async def async_discover(
    broadcast: str,
    *,
    duration: float = DISCOVERY_DURATION,
) -> list[SinilinkStatus]:
    """Broadcast SINILINK521 and collect any replies for ``duration`` seconds.

    Returns a deduplicated list (by MAC) of parsed statuses, with each
    status's ``param`` list left intact and ``mac`` carrying the source IP
    in the unused ``epoch`` slot's caller — actually we attach IP via a
    side-channel: returned statuses include an ``ip`` attribute injected
    onto their ``__dict__``.
    """
    loop = asyncio.get_running_loop()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", 0))
    sock.setblocking(False)

    collector = _BroadcastCollector()
    transport, _ = await loop.create_datagram_endpoint(lambda: collector, sock=sock)
    try:
        transport.sendto(DISCOVERY_PAYLOAD, (broadcast, UDP_PORT))
        await asyncio.sleep(duration)
    finally:
        transport.close()

    seen: dict[str, SinilinkStatus] = {}
    for data, addr in collector.replies:
        try:
            status = parse_status(data)
        except SinilinkProtocolError as err:
            _LOGGER.debug("discovery: ignored reply from %s: %s", addr, err)
            continue
        # Attach source IP for the config flow's UI listing.
        status.__dict__["ip"] = addr[0]
        seen.setdefault(status.mac, status)

    return list(seen.values())


# Re-export DISCOVERY_PAYLOAD for callers that import only from this module.
__all__ = [
    "DISCOVERY_PAYLOAD",
    "SinilinkProtocolError",
    "SinilinkStatus",
    "async_discover",
    "async_query",
    "build_command",
    "parse_status",
]
