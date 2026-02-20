from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.text import TextEntity, TextEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import DotDataCoordinator


@dataclass(frozen=True, kw_only=True)
class DotTextEntityDescription(TextEntityDescription):
    max_length: int = 255


TEXT_DESCRIPTIONS: tuple[DotTextEntityDescription, ...] = (
    DotTextEntityDescription(
        key="text_title",
        name="Text Title",
        icon="mdi:format-title",
        max_length=100,
    ),
    DotTextEntityDescription(
        key="text_message",
        name="Text Message",
        icon="mdi:message-text-outline",
        max_length=500,
    ),
    DotTextEntityDescription(
        key="text_signature",
        name="Text Signature",
        icon="mdi:signature",
        max_length=100,
    ),
    DotTextEntityDescription(
        key="image_data",
        name="Image Data",
        icon="mdi:image-outline",
        max_length=100000,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DotDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[DotTextEntity] = []

    for device_id in coordinator.data:
        for description in TEXT_DESCRIPTIONS:
            entities.append(
                DotTextEntity(coordinator, device_id, description)
            )

    async_add_entities(entities)


class DotTextEntity(CoordinatorEntity[DotDataCoordinator], TextEntity):
    """Text input entity for Dot. Quote/0 device controls."""

    entity_description: DotTextEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DotDataCoordinator,
        device_id: str,
        description: DotTextEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_{description.key}"
        self._attr_native_max = description.max_length
        self._current_value: str = ""

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
    def native_value(self) -> str:
        return self._current_value

    async def async_set_value(self, value: str) -> None:
        self._current_value = value
        self.async_write_ha_state()
