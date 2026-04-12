"""Climate (thermostat) entity for Sinilink XY-WFTX.

The XY-WFTX in Auto mode is a hysteresis thermostat: the relay turns ON
when ``current_temp`` falls below the **start temp** (param[6]) and OFF
when it rises above the **stop temp** (param[7]). HA models this with
``TARGET_TEMPERATURE_RANGE`` (target_temperature_low / _high).

Write support requires an MQTT broker configured in the integration.
Without MQTT, the entity is read-only.
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL, MQTT_CMD_MODE, MQTT_CMD_RELAY, MQTT_CMD_START_TEMP, MQTT_CMD_STOP_TEMP
from .coordinator import SinilinkCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SinilinkCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SinilinkThermostat(coordinator)])


class SinilinkThermostat(CoordinatorEntity[SinilinkCoordinator], ClimateEntity):
    """Hysteresis thermostat backed by a Sinilink XY-WFTX."""

    _attr_has_entity_name = True
    _attr_name = "Thermostat"
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_min_temp = -40
    _attr_max_temp = 110
    _attr_target_temperature_step = 0.1

    def __init__(self, coordinator: SinilinkCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac}_climate"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.mac)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=f"Sinilink {coordinator.mac}",
        )

    @property
    def supported_features(self) -> ClimateEntityFeature:
        if self.coordinator.mqtt_available:
            return (
                ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
                | ClimateEntityFeature.TURN_ON
                | ClimateEntityFeature.TURN_OFF
            )
        return ClimateEntityFeature(0)

    @property
    def temperature_unit(self) -> str:
        data = self.coordinator.data
        if data and data.unit.upper() == "F":
            return UnitOfTemperature.FAHRENHEIT
        return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self) -> float | None:
        data = self.coordinator.data
        return data.current_temp if data else None

    @property
    def target_temperature_low(self) -> float | None:
        data = self.coordinator.data
        return data.start_temp if data else None

    @property
    def target_temperature_high(self) -> float | None:
        data = self.coordinator.data
        return data.stop_temp if data else None

    @property
    def hvac_mode(self) -> HVACMode:
        data = self.coordinator.data
        if data and data.relay:
            return HVACMode.HEAT
        return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction:
        data = self.coordinator.data
        if not data:
            return HVACAction.OFF
        if data.estop:
            return HVACAction.IDLE
        if data.relay:
            return HVACAction.HEATING
        return HVACAction.IDLE

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        if not data:
            return {}
        return {
            "mode": data.mode,
            "heat_cool": data.heat_cool,
            "alarm_high": data.alarm_high,
            "alarm_high_enabled": data.alarm_high_enabled,
            "alarm_low": data.alarm_low,
            "alarm_low_enabled": data.alarm_low_enabled,
            "estop": data.estop,
            "notifications": data.notifications,
            "mqtt_available": self.coordinator.mqtt_available,
            "raw_param": data.param,
        }

    async def async_set_temperature(self, **kwargs: Any) -> None:
        low = kwargs.get(ATTR_TARGET_TEMP_LOW)
        high = kwargs.get(ATTR_TARGET_TEMP_HIGH)
        if low is not None:
            await self.coordinator.async_mqtt_command(MQTT_CMD_START_TEMP, float(low))
        if high is not None:
            await self.coordinator.async_mqtt_command(MQTT_CMD_STOP_TEMP, float(high))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.HEAT:
            await self.coordinator.async_mqtt_command(MQTT_CMD_MODE, "A")
            await self.coordinator.async_mqtt_command(MQTT_CMD_RELAY, "open")
        elif hvac_mode == HVACMode.OFF:
            await self.coordinator.async_mqtt_command(MQTT_CMD_RELAY, "close")
