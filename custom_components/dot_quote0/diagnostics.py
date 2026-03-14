from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import DotDataCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    coordinator: DotDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    devices_diag: dict[str, Any] = {}

    for device_id, device_data in coordinator.data.items():
        devices_diag[device_id] = {
            "alias": device_data.alias,
            "location": device_data.location,
            "series": device_data.series,
            "model": device_data.model,
            "edition": device_data.edition,
            "firmware_version": device_data.firmware_version,
            "power_state": device_data.power_state,
            "power_description": device_data.power_description,
            "battery_status": device_data.battery_status,
            "wifi_signal": device_data.wifi_signal,
            "online": device_data.online,
            "last_render": device_data.last_render,
            "next_render_battery": device_data.next_render_battery,
            "next_render_power": device_data.next_render_power,
            "screen_rotated": device_data.screen_rotated,
            "screen_border": device_data.screen_border,
            "tasks": device_data.tasks,
        }

    return {
        "entry_data": {"api_key": "**REDACTED**"},
        "devices": devices_diag,
    }
