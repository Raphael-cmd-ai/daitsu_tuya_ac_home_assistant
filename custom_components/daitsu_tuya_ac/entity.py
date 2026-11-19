"""Base entity for Daitsu / TCL Tuya AC devices."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DaitsuTuyaCoordinator


class DaitsuTuyaEntity(CoordinatorEntity[DaitsuTuyaCoordinator]):
    """Shared base class grouping all entities under one HA device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DaitsuTuyaCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id

    @property
    def _device(self) -> dict[str, Any]:
        return (self.coordinator.data or {}).get(self._device_id, {})

    @property
    def _status(self) -> dict[str, Any]:
        return self._device.get("status", {})

    @property
    def available(self) -> bool:
        return bool(self.coordinator.last_update_success and self._device.get("online", True))

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device.get("name", "Daitsu Klimaanlage"),
            manufacturer="Daitsu / TCL (Tuya)",
            model=self._device.get("product_name", "Artic Plus"),
        )


def normalize_temp(raw: Any) -> float | None:
    """Normalize Daitsu/TCL temperature values (scale 2 / 1 / 0)."""
    if raw is None or isinstance(raw, bool):
        return None
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return None
    if abs(val) >= 1000.0:
        return round(val / 100.0, 1)
    if val > 60.0 or val < -40.0:
        return round(val / 10.0, 1)
    return round(val, 1)


def detect_temp_scale(raw: Any) -> float:
    """Detect the integer scaling multiplier for temp_set."""
    if raw is None or isinstance(raw, bool):
        return 100.0
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return 100.0
    if abs(val) >= 1000.0:
        return 100.0
    if val > 60.0 or val < -40.0:
        return 10.0
    return 1.0
