from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DotApi, DotApiError
from .const import CONF_API_KEY, DOMAIN
from .coordinator import DotDataCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.TEXT,
    Platform.SELECT,
]

SERVICE_SEND_TEXT = "send_text"
SERVICE_SEND_IMAGE = "send_image"

SEND_TEXT_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Optional("title"): cv.string,
        vol.Optional("message"): cv.string,
        vol.Optional("signature"): cv.string,
        vol.Optional("icon"): cv.string,
        vol.Optional("link"): cv.string,
        vol.Optional("refresh_now", default=True): cv.boolean,
        vol.Optional("task_key"): cv.string,
    }
)

SEND_IMAGE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
        vol.Required("image"): cv.string,
        vol.Optional("link"): cv.string,
        vol.Optional("border", default=0): vol.In([0, 1]),
        vol.Optional("dither_type"): vol.In(["DIFFUSION", "ORDERED", "NONE"]),
        vol.Optional("dither_kernel"): vol.In([
            "FLOYD_STEINBERG", "ATKINSON", "BURKES", "SIERRA2", "STUCKI",
            "JARVIS_JUDICE_NINKE", "DIFFUSION_ROW", "DIFFUSION_COLUMN",
            "DIFFUSION_2D", "THRESHOLD",
        ]),
        vol.Optional("refresh_now", default=True): cv.boolean,
        vol.Optional("task_key"): cv.string,
    }
)


def _resolve_image(image_value: str) -> str:
    """Return base64 image data. If value looks like a file path, read and encode it."""
    if image_value.startswith("/") or image_value.startswith("./"):
        path = Path(image_value)
        if path.is_file():
            return base64.b64encode(path.read_bytes()).decode("utf-8")
        raise DotApiError(f"Image file not found: {image_value}")
    return image_value


def _find_api_for_device(
    hass: HomeAssistant, device_id: str
) -> DotApi | None:
    """Find the API client that owns the given device_id."""
    for entry_id, coordinator in hass.data.get(DOMAIN, {}).items():
        if isinstance(coordinator, DotDataCoordinator):
            if device_id in (coordinator.data or {}):
                return coordinator.api
    return None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    api = DotApi(session, entry.data[CONF_API_KEY])

    devices = await api.get_devices()
    coordinator = DotDataCoordinator(hass, api, devices)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    await _async_register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
            for service_name in (SERVICE_SEND_TEXT, SERVICE_SEND_IMAGE):
                hass.services.async_remove(DOMAIN, service_name)
    return unload_ok


async def _async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_SEND_TEXT):
        return

    async def handle_send_text(call: ServiceCall) -> None:
        device_id = call.data["device_id"]
        api = _find_api_for_device(hass, device_id)
        if api is None:
            raise DotApiError(f"No configured integration owns device {device_id}")
        await api.send_text(
            device_id,
            refreshNow=call.data.get("refresh_now", True),
            title=call.data.get("title"),
            message=call.data.get("message"),
            signature=call.data.get("signature"),
            icon=call.data.get("icon"),
            link=call.data.get("link"),
            taskKey=call.data.get("task_key"),
        )

    async def handle_send_image(call: ServiceCall) -> None:
        device_id = call.data["device_id"]
        api = _find_api_for_device(hass, device_id)
        if api is None:
            raise DotApiError(f"No configured integration owns device {device_id}")
        image_data = await hass.async_add_executor_job(
            _resolve_image, call.data["image"]
        )
        await api.send_image(
            device_id,
            refreshNow=call.data.get("refresh_now", True),
            image=image_data,
            link=call.data.get("link"),
            border=call.data.get("border", 0),
            ditherType=call.data.get("dither_type"),
            ditherKernel=call.data.get("dither_kernel"),
            taskKey=call.data.get("task_key"),
        )

    hass.services.async_register(
        DOMAIN, SERVICE_SEND_TEXT, handle_send_text, schema=SEND_TEXT_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SEND_IMAGE, handle_send_image, schema=SEND_IMAGE_SCHEMA
    )
