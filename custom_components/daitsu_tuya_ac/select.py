"""Select platform for Daitsu / TCL vertical and horizontal louvers."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    HORIZONTAL_LOUVER_CODE_TO_NAME,
    HORIZONTAL_LOUVER_NAME_TO_CODE,
    VERTICAL_LOUVER_CODE_TO_NAME,
    VERTICAL_LOUVER_NAME_TO_CODE,
)
from .coordinator import DaitsuTuyaCoordinator
from .entity import DaitsuTuyaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up louver select entities."""
    coordinator: DaitsuTuyaCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SelectEntity] = []
    for dev_id, dev in (coordinator.data or {}).items():
        status = dev.get("status", {})
        if "gear_vertical" in status:
            entities.append(
                DaitsuLouverSelect(
                    coordinator=coordinator,
                    device_id=dev_id,
                    dp_code="gear_vertical",
                    name="Lamelle Vertikal",
                    icon="mdi:arrow-up-down",
                    code_to_name=VERTICAL_LOUVER_CODE_TO_NAME,
                    name_to_code=VERTICAL_LOUVER_NAME_TO_CODE,
                )
            )
        if "gear_horizontal" in status:
            entities.append(
                DaitsuLouverSelect(
                    coordinator=coordinator,
                    device_id=dev_id,
                    dp_code="gear_horizontal",
                    name="Lamelle Horizontal",
                    icon="mdi:arrow-left-right",
                    code_to_name=HORIZONTAL_LOUVER_CODE_TO_NAME,
                    name_to_code=HORIZONTAL_LOUVER_NAME_TO_CODE,
                )
            )
    async_add_entities(entities)


class DaitsuLouverSelect(DaitsuTuyaEntity, SelectEntity):
    """Controls vertical or horizontal louvers with exact 9..13 Daitsu positions."""

    def __init__(
        self,
        coordinator: DaitsuTuyaCoordinator,
        device_id: str,
        dp_code: str,
        name: str,
        icon: str,
        code_to_name: dict[str, str],
        name_to_code: dict[str, str],
    ) -> None:
        super().__init__(coordinator, device_id)
        self._dp_code = dp_code
        self._code_to_name = code_to_name
        self._name_to_code = name_to_code
        self._attr_unique_id = f"{device_id}_{dp_code}"
        self._attr_name = name
        self._attr_icon = icon
        self._attr_options = list(code_to_name.values())

    @property
    def current_option(self) -> str | None:
        raw = str(self._status.get(self._dp_code, "0"))
        return self._code_to_name.get(raw, "Aus")

    async def async_select_option(self, option: str) -> None:
        code = self._name_to_code.get(option, "0")
        await self.coordinator.async_send_command(self._device_id, self._dp_code, code)
