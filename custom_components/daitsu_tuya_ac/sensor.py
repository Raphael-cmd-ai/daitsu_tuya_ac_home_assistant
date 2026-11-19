"""Sensor platform for Daitsu / TCL live inverter and temperature telemetry."""

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
    UnitOfFrequency,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import DaitsuTuyaCoordinator
from .entity import DaitsuTuyaEntity, normalize_temp


@dataclass(frozen=True)
class DaitsuSensorSpec:
    dp_code: str
    name: str
    icon: str
    unit: str | None
    device_class: SensorDeviceClass | None
    state_class: SensorStateClass | None
    value_fn: Callable[[Any], Any]


def _format_error_code(raw: Any) -> str:
    text = str(raw or "")
    if text in ("", "0", "AA=="):
        return "Kein Fehler"
    return text


def _format_electricity_kwh(raw: Any) -> float | None:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        return round(float(raw) / 1000.0, 3)
    except (TypeError, ValueError):
        return None


def _to_int(raw: Any) -> int | None:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        return int(round(float(raw)))
    except (TypeError, ValueError):
        return None


SENSOR_SPECS: list[DaitsuSensorSpec] = [
    DaitsuSensorSpec(
        dp_code="temp_current",
        name="Raumtemperatur",
        icon="mdi:home-thermometer",
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=normalize_temp,
    ),
    DaitsuSensorSpec(
        dp_code="ure",
        name="Außentemperatur",
        icon="mdi:thermometer",
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=normalize_temp,
    ),
    DaitsuSensorSpec(
        dp_code="compressor_frequency",
        name="Kompressor-Frequenz (Ist)",
        icon="mdi:sine-wave",
        unit=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_to_int,
    ),
    DaitsuSensorSpec(
        dp_code="outdoor_comptar_freqrun",
        name="Kompressor-Frequenz (Soll)",
        icon="mdi:target",
        unit=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_to_int,
    ),
    DaitsuSensorSpec(
        dp_code="external_unit_fanspeed",
        name="Außenlüfter Drehzahl",
        icon="mdi:fan",
        unit="rpm",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_to_int,
    ),
    DaitsuSensorSpec(
        dp_code="electricity",
        name="Stromverbrauch (Intervall)",
        icon="mdi:flash",
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_format_electricity_kwh,
    ),
    DaitsuSensorSpec(
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
    """Set up Daitsu telemetry sensors."""
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
        self._attr_unique_id = f"{device_id}_{spec.dp_code}_sensor"
        self._attr_name = spec.name
        self._attr_icon = spec.icon
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_device_class = spec.device_class
        self._attr_state_class = spec.state_class

    @property
    def native_value(self) -> Any:
        return self._spec.value_fn(self._status.get(self._spec.dp_code))
