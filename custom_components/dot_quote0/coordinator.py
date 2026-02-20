from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DotApi, DotApiError, DotConnectionError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class DotDeviceData:
    """Parsed device status data."""

    def __init__(self, device_info: dict[str, Any], status: dict[str, Any]) -> None:
        self.device_id: str = device_info["id"]
        self.series: str = device_info.get("series", "quote")
        self.model: str = device_info.get("model", "quote_0")
        self.edition: int = device_info.get("edition", 1)

        self.alias: str | None = status.get("alias")
        self.location: str | None = status.get("location")

        st = status.get("status", {})
        self.firmware_version: str = st.get("version", "unknown")
        self.power_state: str = st.get("current", "unknown")
        self.power_description: str = st.get("description", "")
        self.battery_status: str = st.get("battery", "unknown")
        self.wifi_signal: str = st.get("wifi", "unknown")

        ri = status.get("renderInfo", {})
        self.last_render: str | None = ri.get("last")

        current = ri.get("current", {})
        self.screen_rotated: bool = current.get("rotated", False)
        self.screen_border: int = current.get("border", 0)
        self.current_images: list[str] = current.get("image") or []

        nxt = ri.get("next", {})
        self.next_render_battery: str | None = nxt.get("battery")
        self.next_render_power: str | None = nxt.get("power")

        self.online: bool = True

    @property
    def display_name(self) -> str:
        if self.alias:
            return self.alias
        return f"Quote/0 {self.device_id[-4:]}"

    @property
    def wifi_rssi(self) -> int | None:
        """Parse Wi-Fi signal string like '-62 dBm' to int."""
        try:
            return int(self.wifi_signal.replace(" dBm", "").strip())
        except (ValueError, AttributeError):
            return None


class DotDataCoordinator(DataUpdateCoordinator[dict[str, DotDeviceData]]):
    """Coordinator that polls status for all Dot. devices."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        api: DotApi,
        devices: list[dict[str, Any]],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api
        self._devices = devices

    async def _async_update_data(self) -> dict[str, DotDeviceData]:
        data: dict[str, DotDeviceData] = {}
        for dev in self._devices:
            device_id = dev["id"]
            try:
                status = await self.api.get_device_status(device_id)
                data[device_id] = DotDeviceData(dev, status)
            except DotConnectionError as err:
                raise UpdateFailed(f"Connection error for {device_id}: {err}") from err
            except DotApiError as err:
                _LOGGER.warning("Failed to get status for %s: %s", device_id, err)
                dd = DotDeviceData(dev, {})
                dd.online = False
                data[device_id] = dd
        return data
