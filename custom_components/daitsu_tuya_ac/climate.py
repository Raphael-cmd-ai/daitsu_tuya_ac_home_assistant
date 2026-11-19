"""Climate platform for Daitsu / TCL Tuya AC."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    FAN_CODE_TO_NAME,
    FAN_NAME_TO_CODE,
    HVAC_TO_MODE_CODE,
    MODE_CODE_TO_HVAC,
    VERTICAL_LOUVER_CODE_TO_NAME,
    VERTICAL_LOUVER_NAME_TO_CODE,
)
from .coordinator import DaitsuTuyaCoordinator
from .entity import DaitsuTuyaEntity, detect_temp_scale, normalize_temp


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Daitsu Tuya climate entities."""
    coordinator: DaitsuTuyaCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        DaitsuTuyaClimate(coordinator, dev_id)
        for dev_id, dev in (coordinator.data or {}).items()
        if "temp_set" in dev.get("status", {}) or "mode" in dev.get("status", {})
    ]
    async_add_entities(entities)


class DaitsuTuyaClimate(DaitsuTuyaEntity, ClimateEntity):
    """Representation of a Daitsu / TCL Tuya Air Conditioner."""

    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.5
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.AUTO,
        HVACMode.COOL,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
        HVACMode.HEAT,
    ]
    _attr_fan_modes = list(FAN_CODE_TO_NAME.values())
    _attr_swing_modes = list(VERTICAL_LOUVER_CODE_TO_NAME.values())
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: DaitsuTuyaCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_climate"

    @property
    def min_temp(self) -> float:
        return normalize_temp(self._status.get("lower_tem_limit")) or 16.0

    @property
    def max_temp(self) -> float:
        return normalize_temp(self._status.get("upper_tem_limit")) or 31.0

    @property
    def current_temperature(self) -> float | None:
        return normalize_temp(self._status.get("temp_current"))

    @property
    def target_temperature(self) -> float | None:
        return normalize_temp(self._status.get("temp_set"))

    @property
    def hvac_mode(self) -> HVACMode:
        if not self._status.get("switch", False):
            return HVACMode.OFF
        raw_mode = str(self._status.get("mode", "0")).lower()
        return MODE_CODE_TO_HVAC.get(raw_mode, HVACMode.AUTO)

    @property
    def fan_mode(self) -> str | None:
        raw_fan = str(self._status.get("fan_speed_enum", "0"))
        return FAN_CODE_TO_NAME.get(raw_fan, "Auto")

    @property
    def swing_mode(self) -> str | None:
        raw_v = str(self._status.get("gear_vertical", "0"))
        return VERTICAL_LOUVER_CODE_TO_NAME.get(raw_v, "Aus")

    async def async_turn_on(self) -> None:
        await self.coordinator.async_send_command(self._device_id, "switch", True)

    async def async_turn_off(self) -> None:
        await self.coordinator.async_send_command(self._device_id, "switch", False)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.async_send_command(self._device_id, "switch", False)
            return
        if not self._status.get("switch", False):
            await self.coordinator.async_send_command(self._device_id, "switch", True)
        mode_code = HVAC_TO_MODE_CODE.get(hvac_mode, "0")
        await self.coordinator.async_send_command(self._device_id, "mode", mode_code)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        scale = detect_temp_scale(self._status.get("temp_set"))
        raw_value = int(round(float(temp) * scale))
        await self.coordinator.async_send_command(self._device_id, "temp_set", raw_value)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        code = FAN_NAME_TO_CODE.get(fan_mode, "0")
        await self.coordinator.async_send_command(
            self._device_id, "fan_speed_enum", code
        )

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        code = VERTICAL_LOUVER_NAME_TO_CODE.get(swing_mode, "0")
        await self.coordinator.async_send_command(
            self._device_id, "gear_vertical", code
        )
