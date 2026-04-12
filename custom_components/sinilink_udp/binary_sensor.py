"""Binary sensor entities for Sinilink XY-WFTX."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import SinilinkCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SinilinkCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            SinilinkEStopSensor(coordinator),
            SinilinkLedSensor(coordinator),
            SinilinkTempAlarmSensor(coordinator),
        ]
    )


class SinilinkEStopSensor(CoordinatorEntity[SinilinkCoordinator], BinarySensorEntity):
    """E-stop state from the device (param[18])."""

    _attr_has_entity_name = True
    _attr_name = "E-stop"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: SinilinkCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac}_estop"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.mac)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=f"Sinilink {coordinator.mac}",
        )

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        return data.estop if data else None


class SinilinkLedSensor(CoordinatorEntity[SinilinkCoordinator], BinarySensorEntity):
    """LED state from the device. Firmware inverted: param[21]=0 means on."""

    _attr_has_entity_name = True
    _attr_name = "LED"

    def __init__(self, coordinator: SinilinkCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac}_led"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.mac)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=f"Sinilink {coordinator.mac}",
        )

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if data is None:
            return None
        return not data.led  # inverted: param 0 = on, 1 = off


class SinilinkTempAlarmSensor(CoordinatorEntity[SinilinkCoordinator], BinarySensorEntity):
    """Derived: temperature outside the device's buzzer alarm band.

    The UDP status payload exposes the alarm *thresholds* (param[11] high,
    param[13] low) but not the buzzer's current state. This sensor
    computes it from ``current_temp`` vs the thresholds, matching when the
    device's physical buzzer is sounding.
    """

    _attr_has_entity_name = True
    _attr_name = "Temperature alarm"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: SinilinkCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac}_temp_alarm"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.mac)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=f"Sinilink {coordinator.mac}",
        )

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data
        if not data or data.current_temp is None:
            return None
        if (
            data.alarm_low_enabled
            and data.alarm_low is not None
            and data.current_temp < data.alarm_low
        ):
            return True
        if (
            data.alarm_high_enabled
            and data.alarm_high is not None
            and data.current_temp > data.alarm_high
        ):
            return True
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        if not data:
            return {}
        return {
            "current_temp": data.current_temp,
            "alarm_low": data.alarm_low,
            "alarm_low_enabled": data.alarm_low_enabled,
            "alarm_high": data.alarm_high,
            "alarm_high_enabled": data.alarm_high_enabled,
        }
