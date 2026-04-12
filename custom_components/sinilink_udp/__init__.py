"""Sinilink XY-WFTX integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MAC, Platform
from homeassistant.core import HomeAssistant

from .const import CONF_MQTT_HOST, CONF_MQTT_PORT, DOMAIN
from .coordinator import SinilinkCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sinilink XY-WFTX from a config entry."""
    coordinator = SinilinkCoordinator(
        hass,
        host=entry.data[CONF_HOST],
        mac=entry.data[CONF_MAC],
        mqtt_host=entry.data.get(CONF_MQTT_HOST),
        mqtt_port=entry.data.get(CONF_MQTT_PORT),
    )
    await coordinator.async_config_entry_first_refresh()
    await coordinator.async_start_mqtt()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Sinilink config entry."""
    coordinator: SinilinkCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_stop_mqtt()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entry from v1 (no MQTT) to v2."""
    if entry.version < 2:
        _LOGGER.info("Migrating config entry %s from v%s to v2", entry.entry_id, entry.version)
        new_data = {**entry.data}
        new_data.setdefault(CONF_MQTT_HOST, None)
        new_data.setdefault(CONF_MQTT_PORT, None)
        hass.config_entries.async_update_entry(entry, data=new_data, version=2)
    return True
