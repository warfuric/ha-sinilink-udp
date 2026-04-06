"""Sensor entities for Sinilink XY-WFTX."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
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
    async_add_entities([SinilinkTemperatureSensor(coordinator)])


class SinilinkTemperatureSensor(CoordinatorEntity[SinilinkCoordinator], SensorEntity):
    """Current measured temperature from the device."""

    _attr_has_entity_name = True
    _attr_name = "Temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: SinilinkCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.mac}_temperature"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.mac)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name=f"Sinilink {coordinator.mac}",
        )

    @property
    def native_unit_of_measurement(self) -> str:
        data = self.coordinator.data
        if data and data.unit.upper() == "F":
            return UnitOfTemperature.FAHRENHEIT
        return UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        return data.current_temp if data else None
