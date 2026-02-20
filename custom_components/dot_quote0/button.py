from __future__ import annotations

import base64
import logging
from pathlib import Path

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import DotDataCoordinator

_LOGGER = logging.getLogger(__name__)


def _get_entity_state(hass: HomeAssistant, entity_id: str) -> str | None:
    """Get the current state value of an entity."""
    state = hass.states.get(entity_id)
    if state is None or state.state in ("unknown", "unavailable", ""):
        return None
    return state.state


def _resolve_image(image_value: str) -> str:
    """Return base64 image data. If value looks like a file path, read and encode it."""
    if image_value.startswith("/") or image_value.startswith("./"):
        path = Path(image_value)
        if path.is_file():
            return base64.b64encode(path.read_bytes()).decode("utf-8")
        raise ValueError(f"Image file not found: {image_value}")
    return image_value


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DotDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ButtonEntity] = []

    for device_id in coordinator.data:
        entities.append(DotNextContentButton(coordinator, device_id))
        entities.append(DotSendTextButton(coordinator, device_id))
        entities.append(DotSendImageButton(coordinator, device_id))

    async_add_entities(entities)


def _device_info(coordinator: DotDataCoordinator, device_id: str) -> DeviceInfo:
    data = coordinator.data.get(device_id)
    model_name = "Quote/0"
    if data:
        model_name = f"Quote/0 (Edition {data.edition})"
    return DeviceInfo(
        identifiers={(DOMAIN, device_id)},
        name=data.display_name if data else f"Quote/0 {device_id[-4:]}",
        manufacturer=MANUFACTURER,
        model=model_name,
        sw_version=data.firmware_version if data else None,
    )


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
        return _device_info(self.coordinator, self._device_id)

    @property
    def available(self) -> bool:
        data = self.coordinator.data.get(self._device_id)
        return data is not None and data.online

    async def async_press(self) -> None:
        await self.coordinator.api.switch_next_content(self._device_id)
        await self.coordinator.async_request_refresh()


class DotSendTextButton(CoordinatorEntity[DotDataCoordinator], ButtonEntity):
    """Button that sends text content from the text input entities to the device."""

    _attr_has_entity_name = True
    _attr_name = "Send Text"
    _attr_icon = "mdi:send"

    def __init__(
        self, coordinator: DotDataCoordinator, device_id: str
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_send_text"

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self.coordinator, self._device_id)

    @property
    def available(self) -> bool:
        data = self.coordinator.data.get(self._device_id)
        return data is not None and data.online

    async def async_press(self) -> None:
        did = self._device_id
        title = _get_entity_state(self.hass, f"text.{DOMAIN}_{did}_text_title")
        message = _get_entity_state(self.hass, f"text.{DOMAIN}_{did}_text_message")
        signature = _get_entity_state(
            self.hass, f"text.{DOMAIN}_{did}_text_signature"
        )

        if not title and not message:
            _LOGGER.warning("Send Text: both title and message are empty, skipping")
            return

        await self.coordinator.api.send_text(
            did,
            refreshNow=True,
            title=title,
            message=message,
            signature=signature,
        )
        await self.coordinator.async_request_refresh()


class DotSendImageButton(CoordinatorEntity[DotDataCoordinator], ButtonEntity):
    """Button that sends image content from the image data entity to the device."""

    _attr_has_entity_name = True
    _attr_name = "Send Image"
    _attr_icon = "mdi:image-move"

    def __init__(
        self, coordinator: DotDataCoordinator, device_id: str
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_send_image"

    @property
    def device_info(self) -> DeviceInfo:
        return _device_info(self.coordinator, self._device_id)

    @property
    def available(self) -> bool:
        data = self.coordinator.data.get(self._device_id)
        return data is not None and data.online

    async def async_press(self) -> None:
        did = self._device_id
        image_raw = _get_entity_state(self.hass, f"text.{DOMAIN}_{did}_image_data")

        if not image_raw:
            _LOGGER.warning("Send Image: image data is empty, skipping")
            return

        image_data = await self.hass.async_add_executor_job(
            _resolve_image, image_raw
        )

        dither_type = _get_entity_state(
            self.hass, f"select.{DOMAIN}_{did}_dither_type"
        )

        await self.coordinator.api.send_image(
            did,
            refreshNow=True,
            image=image_data,
            ditherType=dither_type,
        )
        await self.coordinator.async_request_refresh()
