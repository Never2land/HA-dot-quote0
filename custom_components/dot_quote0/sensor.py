from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import DotDataCoordinator, DotDeviceData


@dataclass(frozen=True, kw_only=True)
class DotSensorEntityDescription(SensorEntityDescription):
    value_fn: Callable[[DotDeviceData], Any]


SENSOR_DESCRIPTIONS: tuple[DotSensorEntityDescription, ...] = (
    DotSensorEntityDescription(
        key="power_state",
        translation_key="power_state",
        name="Power State",
        icon="mdi:power",
        value_fn=lambda d: d.power_state,
    ),
    DotSensorEntityDescription(
        key="battery_status",
        translation_key="battery_status",
        name="Battery Status",
        icon="mdi:battery",
        value_fn=lambda d: d.battery_status,
    ),
    DotSensorEntityDescription(
        key="wifi_signal",
        translation_key="wifi_signal",
        name="Wi-Fi Signal",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        icon="mdi:wifi",
        value_fn=lambda d: d.wifi_rssi,
    ),
    DotSensorEntityDescription(
        key="firmware_version",
        translation_key="firmware_version",
        name="Firmware Version",
        icon="mdi:chip",
        value_fn=lambda d: d.firmware_version,
    ),
    DotSensorEntityDescription(
        key="last_render",
        translation_key="last_render",
        name="Last Render",
        icon="mdi:clock-outline",
        value_fn=lambda d: d.last_render,
    ),
    DotSensorEntityDescription(
        key="next_render_battery",
        translation_key="next_render_battery",
        name="Next Render (Battery)",
        icon="mdi:clock-fast",
        value_fn=lambda d: d.next_render_battery,
    ),
    DotSensorEntityDescription(
        key="next_render_power",
        translation_key="next_render_power",
        name="Next Render (Power)",
        icon="mdi:clock-fast",
        value_fn=lambda d: d.next_render_power,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DotDataCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[DotSensorEntity] = []

    for device_id in coordinator.data:
        for description in SENSOR_DESCRIPTIONS:
            entities.append(
                DotSensorEntity(coordinator, device_id, description)
            )

    async_add_entities(entities)


class DotSensorEntity(CoordinatorEntity[DotDataCoordinator], SensorEntity):
    """Sensor entity for a Dot. Quote/0 device."""

    entity_description: DotSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DotDataCoordinator,
        device_id: str,
        description: DotSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_{description.key}"

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

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data.get(self._device_id)
        if data is None:
            return None
        return self.entity_description.value_fn(data)
