from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import DotDataCoordinator

DITHER_OPTIONS = ["DIFFUSION", "ORDERED", "NONE"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DotDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        DotDitherTypeSelect(coordinator, device_id)
        for device_id in coordinator.data
    ]
    async_add_entities(entities)


class DotDitherTypeSelect(CoordinatorEntity[DotDataCoordinator], SelectEntity):
    """Select entity for image dither type."""

    _attr_has_entity_name = True
    _attr_name = "Dither Type"
    _attr_icon = "mdi:blur"
    _attr_options = DITHER_OPTIONS
    _attr_current_option = "DIFFUSION"

    def __init__(
        self, coordinator: DotDataCoordinator, device_id: str
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_dither_type"

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

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self.async_write_ha_state()
