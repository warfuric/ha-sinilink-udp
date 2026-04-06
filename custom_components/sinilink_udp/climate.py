"""Climate (thermostat) entity for Sinilink XY-WFTX.

The XY-WFTX in Auto mode is a hysteresis thermostat: the relay turns ON
when ``current_temp`` falls below the **start temp** (param[6]) and OFF
when it rises above the **stop temp** (param[7]). HA models this with
``TARGET_TEMPERATURE_RANGE`` (target_temperature_low / _high) — the low
slider is the device's start temp, the high slider is the stop temp.

WRITES ARE DISABLED. The first write attempt (toggling HVAC mode to heat)
crashed the device's WiFi stack and required a power cycle. The write
protocol used by this firmware is not yet known — the read protocol is
solid, but the app uses a different command shape than the CVE-2022-43704
PoC suggests. Until we capture the real app→device packets and match
them, ``async_set_temperature`` and ``async_set_hvac_mode`` are no-ops
that raise ``HomeAssistantError`` so HA shows a clear failure rather than
silently bricking the device again.

Manual mode and the device's timer/cycle features are out of scope.
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
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
    async_add_entities([SinilinkThermostat(coordinator)])


class SinilinkThermostat(CoordinatorEntity[SinilinkCoordinator], ClimateEntity):
    """Hysteresis thermostat backed by a Sinilink XY-WFTX."""

    _attr_has_entity_name = True
    _attr_name = "Thermostat"
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    # Writes are disabled — no supported_features bits set, so HA renders
    # the entity as read-only (no sliders, no mode dropdown).
    _attr_supported_features = ClimateEntityFeature(0)
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
        # "Start temp" — heater turns ON below this value.
        data = self.coordinator.data
        return data.start_temp if data else None

    @property
    def target_temperature_high(self) -> float | None:
        # "Stop temp" — heater turns OFF above this value.
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
            # Device is locked out by its own e-stop; report idle so the UI
            # makes it visually obvious heat isn't flowing even if mode=heat.
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
            "raw_param": data.param,
        }

    async def async_set_temperature(self, **kwargs: Any) -> None:
        raise HomeAssistantError(
            "Sinilink writes are disabled in v0.1 — the device firmware "
            "crashed the only time we tried. Re-enable in code once the "
            "real write protocol has been captured from the official app."
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        raise HomeAssistantError(
            "Sinilink writes are disabled in v0.1 — see climate.py for "
            "context."
        )
