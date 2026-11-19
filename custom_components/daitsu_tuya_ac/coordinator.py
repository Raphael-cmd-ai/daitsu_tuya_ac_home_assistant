"""DataUpdateCoordinator for Daitsu / TCL Tuya AC."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .tuya_api import TuyaApiError, TuyaCloudApi

_LOGGER = logging.getLogger(__name__)


class DaitsuTuyaCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Manages polling of Daitsu/TCL devices from Tuya Cloud."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: TuyaCloudApi,
        poll_interval_seconds: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=poll_interval_seconds),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            devices = await self.api.async_get_devices()
        except TuyaApiError as err:
            raise UpdateFailed(f"Tuya Cloud Fehler ({err.code}): {err}") from err
        return {dev["id"]: dev for dev in devices}

    async def async_send_command(
        self, device_id: str, code: str, value: Any
    ) -> None:
        """Send command with optimistic local state update."""
        await self.api.async_send_command(device_id, code, value)
        if self.data and device_id in self.data:
            updated = dict(self.data)
            dev = dict(updated[device_id])
            status = dict(dev.get("status", {}))
            status[code] = value
            dev["status"] = status
            updated[device_id] = dev
            self.async_set_updated_data(updated)
        await self.async_request_refresh()
