from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import DotDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DotDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        DotNextContentButton(coordinator, device_id)
        for device_id in coordinator.data
    ]
    async_add_entities(entities)


class DotNextContentButton(CoordinatorEntity[DotDataCoordinator], ButtonEntity):
    """Button to switch a Dot. device to the next content."""

    _attr_has_entity_name = True
    _attr_name = "Next Content"
    _attr_icon = "mdi:skip-next"

    def __init__(
        self, coordinator: DotDataCoordinator, device_id: str
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_next_content"

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
    def available(self) -> bool:
        data = self.coordinator.data.get(self._device_id)
        return data is not None and data.online

    async def async_press(self) -> None:
        await self.coordinator.api.switch_next_content(self._device_id)
        await self.coordinator.async_request_refresh()
