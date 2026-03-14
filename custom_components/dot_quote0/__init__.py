from __future__ import annotations

import base64
import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

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
SERVICE_SEND_SYSTEM_STATUS = "send_system_status"
SERVICE_SEND_CALENDAR = "send_calendar"
SERVICE_SEND_WEATHER = "send_weather"

SEND_TEXT_SCHEMA = vol.Schema(
    {
        vol.Required("serial"): cv.string,
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
        vol.Required("serial"): cv.string,
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

SEND_SYSTEM_STATUS_SCHEMA = vol.Schema(
    {
        vol.Required("serial"): cv.string,
        vol.Optional("refresh_now", default=True): cv.boolean,
        vol.Optional("task_key"): cv.string,
    }
)

SEND_CALENDAR_SCHEMA = vol.Schema(
    {
        vol.Required("serial"): cv.string,
        vol.Required("calendar_entity"): cv.entity_id,
        vol.Optional("hours_ahead", default=24): cv.positive_int,
        vol.Optional("max_events", default=5): cv.positive_int,
        vol.Optional("refresh_now", default=True): cv.boolean,
        vol.Optional("task_key"): cv.string,
    }
)

SEND_WEATHER_SCHEMA = vol.Schema(
    {
        vol.Required("serial"): cv.string,
        vol.Required("weather_entity"): cv.entity_id,
        vol.Optional("include_forecast", default=True): cv.boolean,
        vol.Optional("forecast_days", default=3): cv.positive_int,
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
            for service_name in (
                SERVICE_SEND_TEXT, SERVICE_SEND_IMAGE,
                SERVICE_SEND_SYSTEM_STATUS, SERVICE_SEND_CALENDAR,
                SERVICE_SEND_WEATHER,
            ):
                hass.services.async_remove(DOMAIN, service_name)
    return unload_ok


async def _async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_SEND_TEXT):
        return

    async def handle_send_text(call: ServiceCall) -> None:
        device_id = call.data["serial"]
        api = _find_api_for_device(hass, device_id)
        if api is None:
            raise DotApiError(f"Device '{device_id}' not found. Check the serial number.")
        try:
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
        except DotApiError as err:
            if "not found" in str(err).lower():
                raise DotApiError(
                    f"Device '{device_id}' has no Text API content program configured. "
                    "Add one in the Dot. app first."
                ) from err
            raise

    async def handle_send_image(call: ServiceCall) -> None:
        device_id = call.data["serial"]
        api = _find_api_for_device(hass, device_id)
        if api is None:
            raise DotApiError(f"Device '{device_id}' not found. Check the serial number.")
        image_data = await hass.async_add_executor_job(
            _resolve_image, call.data["image"]
        )
        try:
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
        except DotApiError as err:
            if "not found" in str(err).lower():
                raise DotApiError(
                    f"Device '{device_id}' has no Image API content program configured. "
                    "Add one in the Dot. app first."
                ) from err
            raise

    async def handle_send_system_status(call: ServiceCall) -> None:
        device_id = call.data["serial"]
        api = _find_api_for_device(hass, device_id)
        if api is None:
            raise DotApiError(f"Device '{device_id}' not found. Check the serial number.")

        lines: list[str] = []

        # HA version
        lines.append(f"HA: {hass.config.version}")

        # Uptime
        for entity_id in ("sensor.uptime", "sensor.home_assistant_uptime"):
            state = hass.states.get(entity_id)
            if state and state.state not in ("unknown", "unavailable"):
                lines.append(f"Uptime: {state.state}")
                break

        # CPU usage
        for entity_id in ("sensor.processor_use", "sensor.processor_use_percent"):
            state = hass.states.get(entity_id)
            if state and state.state not in ("unknown", "unavailable"):
                lines.append(f"CPU: {state.state}%")
                break

        # Memory usage
        for entity_id in ("sensor.memory_use_percent",):
            state = hass.states.get(entity_id)
            if state and state.state not in ("unknown", "unavailable"):
                lines.append(f"Memory: {state.state}%")
                break

        # Disk usage
        for entity_id in ("sensor.disk_use_percent", "sensor.disk_use_percent_home"):
            state = hass.states.get(entity_id)
            if state and state.state not in ("unknown", "unavailable"):
                lines.append(f"Disk: {state.state}%")
                break

        # Entity/automation counts
        entity_count = len(hass.states.async_all())
        lines.append(f"Entities: {entity_count}")

        message = "\n".join(lines) if lines else "No system data available"
        now = dt_util.now().strftime("%Y-%m-%d %H:%M")

        await api.send_text(
            device_id,
            refreshNow=call.data.get("refresh_now", True),
            title="System Status",
            message=message,
            signature=now,
            taskKey=call.data.get("task_key"),
        )

    async def handle_send_calendar(call: ServiceCall) -> None:
        device_id = call.data["serial"]
        api = _find_api_for_device(hass, device_id)
        if api is None:
            raise DotApiError(f"Device '{device_id}' not found. Check the serial number.")

        calendar_entity = call.data["calendar_entity"]
        hours_ahead = call.data.get("hours_ahead", 24)
        max_events = call.data.get("max_events", 5)

        start = dt_util.now()
        end = start + timedelta(hours=hours_ahead)

        result = await hass.services.async_call(
            "calendar",
            "get_events",
            {
                "entity_id": calendar_entity,
                "start_date_time": start.isoformat(),
                "end_date_time": end.isoformat(),
            },
            blocking=True,
            return_response=True,
        )

        events = []
        if result and calendar_entity in result:
            events = result[calendar_entity].get("events", [])

        if not events:
            message = "No upcoming events"
        else:
            lines = []
            for event in events[:max_events]:
                summary = event.get("summary", "Untitled")
                event_start = event.get("start", "")
                if "T" in str(event_start):
                    # datetime event - show time
                    try:
                        dt = dt_util.parse_datetime(event_start)
                        time_str = dt.strftime("%H:%M") if dt else event_start
                    except (ValueError, AttributeError):
                        time_str = event_start
                else:
                    time_str = "All day"
                lines.append(f"{time_str} {summary}")
            message = "\n".join(lines)

        cal_state = hass.states.get(calendar_entity)
        cal_name = cal_state.attributes.get("friendly_name", "Calendar") if cal_state else "Calendar"
        signature = f"Next {hours_ahead}h"

        await api.send_text(
            device_id,
            refreshNow=call.data.get("refresh_now", True),
            title=cal_name,
            message=message,
            signature=signature,
            taskKey=call.data.get("task_key"),
        )

    async def handle_send_weather(call: ServiceCall) -> None:
        device_id = call.data["serial"]
        api = _find_api_for_device(hass, device_id)
        if api is None:
            raise DotApiError(f"Device '{device_id}' not found. Check the serial number.")

        weather_entity = call.data["weather_entity"]
        include_forecast = call.data.get("include_forecast", True)
        forecast_days = call.data.get("forecast_days", 3)

        state = hass.states.get(weather_entity)
        if state is None or state.state in ("unknown", "unavailable"):
            raise DotApiError(f"Weather entity '{weather_entity}' is not available.")

        attrs = state.attributes
        condition = state.state.replace("_", " ").title()
        temp = attrs.get("temperature")
        temp_unit = attrs.get("temperature_unit", "")
        humidity = attrs.get("humidity")
        wind_speed = attrs.get("wind_speed")
        wind_unit = attrs.get("wind_speed_unit", "")

        lines = [condition]
        if temp is not None:
            lines.append(f"Temp: {temp}{temp_unit}")
        if humidity is not None:
            lines.append(f"Humidity: {humidity}%")
        if wind_speed is not None:
            lines.append(f"Wind: {wind_speed} {wind_unit}")

        if include_forecast and forecast_days > 0:
            try:
                forecast_result = await hass.services.async_call(
                    "weather",
                    "get_forecasts",
                    {"entity_id": weather_entity, "type": "daily"},
                    blocking=True,
                    return_response=True,
                )
                forecasts = []
                if forecast_result and weather_entity in forecast_result:
                    forecasts = forecast_result[weather_entity].get("forecast", [])
                if forecasts:
                    lines.append("---")
                    for fc in forecasts[:forecast_days]:
                        fc_date = fc.get("datetime", "")
                        try:
                            dt = dt_util.parse_datetime(fc_date)
                            date_str = dt.strftime("%a") if dt else fc_date[:10]
                        except (ValueError, AttributeError):
                            date_str = fc_date[:10]
                        fc_cond = fc.get("condition", "").replace("_", " ").title()
                        fc_high = fc.get("temperature")
                        fc_low = fc.get("templow")
                        if fc_high is not None and fc_low is not None:
                            lines.append(f"{date_str}: {fc_cond} {fc_low}-{fc_high}{temp_unit}")
                        elif fc_high is not None:
                            lines.append(f"{date_str}: {fc_cond} {fc_high}{temp_unit}")
                        else:
                            lines.append(f"{date_str}: {fc_cond}")
            except Exception:
                _LOGGER.debug("Could not fetch forecast for %s", weather_entity)

        friendly_name = attrs.get("friendly_name", "Weather")
        now = dt_util.now().strftime("%Y-%m-%d %H:%M")

        await api.send_text(
            device_id,
            refreshNow=call.data.get("refresh_now", True),
            title=friendly_name,
            message="\n".join(lines),
            signature=now,
            taskKey=call.data.get("task_key"),
        )

    hass.services.async_register(
        DOMAIN, SERVICE_SEND_TEXT, handle_send_text, schema=SEND_TEXT_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SEND_IMAGE, handle_send_image, schema=SEND_IMAGE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SEND_SYSTEM_STATUS, handle_send_system_status,
        schema=SEND_SYSTEM_STATUS_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SEND_CALENDAR, handle_send_calendar,
        schema=SEND_CALENDAR_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SEND_WEATHER, handle_send_weather,
        schema=SEND_WEATHER_SCHEMA,
    )
