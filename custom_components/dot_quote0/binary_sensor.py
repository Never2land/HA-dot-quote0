from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import DotDataCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DotDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = []
    for device_id in coordinator.data:
        entities.append(DotOnlineBinarySensor(coordinator, device_id))
        entities.append(DotExternalPowerBinarySensor(coordinator, device_id))
    async_add_entities(entities)


class DotOnlineBinarySensor(CoordinatorEntity[DotDataCoordinator], BinarySensorEntity):
    """Binary sensor indicating whether a Dot. device is online."""

    _attr_has_entity_name = True
    _attr_name = "Online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self, coordinator: DotDataCoordinator, device_id: str
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_online"

    @property
    def device_info(self) -> DeviceInfo:
        data = self.coordinator.data.get(self._device_id)
        model_name = "Quote/0"
        if data:
            model_name = f"Quote/0 (Edition {data.edition})"
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=data.display_name if data else f"Quote/0 {self._device_id[-4:]}",
            manufacturer=MANUFACTURER,
            model=model_name,
            sw_version=data.firmware_version if data else None,
        )

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data.get(self._device_id)
        if data is None:
            return None
        return data.online


class DotExternalPowerBinarySensor(DotOnlineBinarySensor):
    """Binary sensor indicating whether a Dot. device is on USB power."""

    _attr_name = "External Power"
    _attr_device_class = BinarySensorDeviceClass.PLUG

    def __init__(
        self, coordinator: DotDataCoordinator, device_id: str
    ) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_external_power"

    @property
    def available(self) -> bool:
        data = self.coordinator.data.get(self._device_id)
        return data is not None and data.online

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data.get(self._device_id)
        if data is None:
            return None
        return data.external_power
