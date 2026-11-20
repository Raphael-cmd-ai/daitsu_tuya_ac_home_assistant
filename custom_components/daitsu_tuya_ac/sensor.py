"""Sensor platform for Daitsu / TCL live temperature, power, and diagnostic telemetry."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import DaitsuTuyaCoordinator
from .entity import DaitsuTuyaEntity, normalize_temp


@dataclass(frozen=True)
class DaitsuSensorSpec:
    key: str
    dp_code: str
    name: str
    icon: str
    unit: str | None
    device_class: SensorDeviceClass | None
    state_class: SensorStateClass | None
    value_fn: Callable[[dict[str, Any]], Any]


def _format_error_code(status: dict[str, Any]) -> str:
    text = str(status.get("error_code") or "")
    if text in ("", "0", "AA=="):
        return "Kein Fehler"
    return text


def _normalize_room_temp(status: dict[str, Any]) -> float | None:
    return normalize_temp(status.get("temp_current"))


def _normalize_outdoor_temp(status: dict[str, Any]) -> float | None:
    """Daitsu/TCL 'ure' outdoor temperature always uses scale 2 (hundredths of °C)."""
    raw = status.get("ure")
    if raw is None or isinstance(raw, bool):
        return None
    try:
        return round(float(raw) / 100.0, 1)
    except (TypeError, ValueError):
        return None


def _format_electricity_kwh(status: dict[str, Any]) -> float | None:
    if not status.get("switch", False):
        return 0.0
    raw = status.get("electricity")
    if raw is None or isinstance(raw, bool):
        return None
    try:
        return round(float(raw) / 1000.0, 3)
    except (TypeError, ValueError):
        return None


def _estimate_power_watts(status: dict[str, Any]) -> int | None:
    """Calculate live average power (W) from electricity (Wh) over virtual_period (s)."""
    if not status.get("switch", False):
        return 0
    raw_wh = status.get("electricity")
    if raw_wh is None or isinstance(raw_wh, bool):
        return None
    try:
        wh = float(raw_wh)
        period_s = float(status.get("virtual_period") or 120.0)
        if period_s <= 0:
            period_s = 120.0
        return int(round((wh * 3600.0) / period_s))
    except (TypeError, ValueError):
        return None


SENSOR_SPECS: list[DaitsuSensorSpec] = [
    DaitsuSensorSpec(
        key="temp_current",
        dp_code="temp_current",
        name="Raumtemperatur",
        icon="mdi:home-thermometer",
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_normalize_room_temp,
    ),
    DaitsuSensorSpec(
        key="ure",
        dp_code="ure",
        name="Außentemperatur",
        icon="mdi:thermometer",
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_normalize_outdoor_temp,
    ),
    DaitsuSensorSpec(
        key="power_watts",
        dp_code="electricity",
        name="Aktuelle Leistung",
        icon="mdi:lightning-bolt",
        unit=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_estimate_power_watts,
    ),
    DaitsuSensorSpec(
        key="electricity",
        dp_code="electricity",
        name="Stromverbrauch (Intervall)",
        icon="mdi:flash",
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_format_electricity_kwh,
    ),
    DaitsuSensorSpec(
        key="error_code",
        dp_code="error_code",
        name="Fehlerdiagnose",
        icon="mdi:alert-circle-check-outline",
        unit=None,
        device_class=None,
        state_class=None,
        value_fn=_format_error_code,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Daitsu live telemetry sensors."""
    coordinator: DaitsuTuyaCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []
    for dev_id, dev in (coordinator.data or {}).items():
        status = dev.get("status", {})
        for spec in SENSOR_SPECS:
            if spec.dp_code in status:
                entities.append(DaitsuTelemetrySensor(coordinator, dev_id, spec))
    async_add_entities(entities)


class DaitsuTelemetrySensor(DaitsuTuyaEntity, SensorEntity):
    """Live telemetry sensor for Daitsu / TCL AC."""

    def __init__(
        self,
        coordinator: DaitsuTuyaCoordinator,
        device_id: str,
        spec: DaitsuSensorSpec,
    ) -> None:
        super().__init__(coordinator, device_id)
        self._spec = spec
        self._attr_unique_id = f"{device_id}_{spec.key}_sensor"
        self._attr_name = spec.name
        self._attr_icon = spec.icon
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_device_class = spec.device_class
        self._attr_state_class = spec.state_class

    @property
    def native_value(self) -> Any:
        return self._spec.value_fn(self._status)
