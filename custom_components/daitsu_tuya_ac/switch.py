"""Switch platform for Daitsu / TCL AC feature toggles (Display, Beep, Eco, etc.)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, FEATURE_SWITCHES
from .coordinator import DaitsuTuyaCoordinator
from .entity import DaitsuTuyaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Daitsu feature switches."""
    coordinator: DaitsuTuyaCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = []
    for dev_id, dev in (coordinator.data or {}).items():
        status = dev.get("status", {})
        for code, name, icon in FEATURE_SWITCHES:
            if code in status and isinstance(status[code], bool):
                entities.append(
                    DaitsuFeatureSwitch(coordinator, dev_id, code, name, icon)
                )
    async_add_entities(entities)


class DaitsuFeatureSwitch(DaitsuTuyaEntity, SwitchEntity):
    """Represents a boolean option toggle on the Daitsu AC."""

    def __init__(
        self,
        coordinator: DaitsuTuyaCoordinator,
        device_id: str,
        dp_code: str,
        name: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator, device_id)
        self._dp_code = dp_code
        self._attr_unique_id = f"{device_id}_{dp_code}"
        self._attr_name = name
        self._attr_icon = icon

    @property
    def is_on(self) -> bool:
        return bool(self._status.get(self._dp_code, False))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_send_command(self._device_id, self._dp_code, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_send_command(self._device_id, self._dp_code, False)
