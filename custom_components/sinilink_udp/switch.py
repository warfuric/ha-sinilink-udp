"""Switch entities for Sinilink XY-WFTX (writable via MQTT)."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MANUFACTURER,
    MODEL,
    MQTT_CMD_ESTOP,
    MQTT_CMD_LED,
    MQTT_CMD_NOTIFICATIONS,
    MQTT_CMD_RELAY,
)
from .coordinator import SinilinkCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SinilinkCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            SinilinkRelaySwitch(coordinator),
            SinilinkLedSwitch(coordinator),
            SinilinkEStopSwitch(coordinator),
            SinilinkNotificationsSwitch(coordinator),
        ]
    )


class _SinilinkSwitch(CoordinatorEntity[SinilinkCoordinator], SwitchEntity):
    """Base class for MQTT-writable Sinilink switches."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SinilinkCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.mac)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=f"Sinilink {coordinator.mac}",
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.mqtt_available


class SinilinkRelaySwitch(_SinilinkSwitch):
    """Direct relay on/off switch."""

    _attr_name = "Relay"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: SinilinkCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac}_relay_switch"

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        return data.relay if data else None

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_mqtt_command(MQTT_CMD_RELAY, "open")

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_mqtt_command(MQTT_CMD_RELAY, "close")


class SinilinkLedSwitch(_SinilinkSwitch):
    """LED on/off switch. Firmware uses inverted logic: param[21]=0 means on."""

    _attr_name = "LED"

    def __init__(self, coordinator: SinilinkCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac}_led_switch"

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if data is None:
            return None
        return not data.led  # inverted: param 0 = on, 1 = off

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_mqtt_command(MQTT_CMD_LED, "0")

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_mqtt_command(MQTT_CMD_LED, "1")


class SinilinkEStopSwitch(_SinilinkSwitch):
    """E-stop arm/disarm switch."""

    _attr_name = "E-stop"

    def __init__(self, coordinator: SinilinkCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac}_estop_switch"

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        return data.estop if data else None

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_mqtt_command(MQTT_CMD_ESTOP, 1)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_mqtt_command(MQTT_CMD_ESTOP, 0)


class SinilinkNotificationsSwitch(_SinilinkSwitch):
    """Cloud push notifications on/off."""

    _attr_name = "Notifications"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: SinilinkCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac}_notifications_switch"

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        return data.notifications if data else None

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_mqtt_command(MQTT_CMD_NOTIFICATIONS, "1")

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_mqtt_command(MQTT_CMD_NOTIFICATIONS, "0")
