"""100% Local Wi-Fi Tuya Protocol v3.5 / v3.4 / v3.3 client using tinytuya (0 Cloud calls)."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .const import CODE_TO_LOCAL_DP_ID, LOCAL_DP_ID_TO_CODE
from .tuya_api import TuyaApiError

_LOGGER = logging.getLogger(__name__)


class TuyaLocalApi:
    """Direct local LAN client (TCP 6668) compatible with TuyaCloudApi interface."""

    def __init__(
        self,
        hass: HomeAssistant,
        device_name: str,
        host: str,
        device_id: str,
        local_key: str,
        protocol_version: str = "auto",
    ) -> None:
        self._hass = hass
        self._device_name = device_name.strip() or "Daitsu Artic Plus"
        self._host = host.strip()
        self._device_id = device_id.strip()
        self._local_key = local_key.strip()
        self._requested_version = protocol_version
        self._resolved_version: float | None = (
            None if protocol_version == "auto" else float(protocol_version)
        )
        self._logged_initial_dps = False

    def _create_device(self, version: float) -> Any:
        import tinytuya  # pylint: disable=import-outside-toplevel

        dev = tinytuya.Device(
            dev_id=self._device_id,
            address=self._host,
            local_key=self._local_key,
            version=version,
        )
        dev.set_socketTimeout(5)
        dev.set_socketRetryLimit(2)
        return dev

    def _poll_sync(self) -> dict[str, Any]:
        versions_to_try = (
            [self._resolved_version]
            if self._resolved_version is not None
            else [3.5, 3.4, 3.3]
        )

        last_err: str = "Keine Antwort vom Gerät."
        for ver in versions_to_try:
            try:
                dev = self._create_device(ver)
                data = dev.status()
                if isinstance(data, dict) and "dps" in data and isinstance(data["dps"], dict):
                    self._resolved_version = ver
                    dps: dict[str, Any] = data["dps"]
                    if not self._logged_initial_dps:
                        self._logged_initial_dps = True
                        _LOGGER.info(
                            "Local Daitsu (%s, v%s) connected! Raw DPS: %s",
                            self._host,
                            ver,
                            dps,
                        )
                    return dps
                if isinstance(data, dict) and "Error" in data:
                    last_err = f"v{ver}: {data.get('Error')} ({data.get('Err', '')})"
                else:
                    last_err = f"v{ver}: Unerwartete Antwort {data}"
            except Exception as err:  # pylint: disable=broad-except
                last_err = f"v{ver}: {err}"

        raise TuyaApiError(None, f"Lokale Verbindung fehlgeschlagen ({self._host}): {last_err}")

    def _send_sync(self, dp_id: str, value: Any) -> None:
        ver = self._resolved_version or 3.5
        dev = self._create_device(ver)
        resp = dev.set_value(dp_id, value, nowait=False)
        if isinstance(resp, dict) and "Error" in resp:
            raise TuyaApiError(
                None,
                f"Lokaler Befehl DP {dp_id}={value} fehlgeschlagen: {resp.get('Error')}",
            )

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Poll the local Daitsu AC and map numeric DPS to canonical DP codes."""
        raw_dps = await self._hass.async_add_executor_job(self._poll_sync)

        status_map: dict[str, Any] = {}
        for dp_id, val in raw_dps.items():
            dp_key = str(dp_id)
            code = LOCAL_DP_ID_TO_CODE.get(dp_key)
            if code:
                status_map[code] = val
            else:
                status_map[f"dp_{dp_key}"] = val

        return [
            {
                "id": self._device_id,
                "name": self._device_name,
                "category": "kt",
                "online": True,
                "product_name": f"Daitsu / TCL Local (v{self._resolved_version or 3.5})",
                "status": status_map,
            }
        ]

    async def async_send_command(
        self, device_id: str, code: str, value: Any
    ) -> None:
        """Translate canonical DP code to numeric DP ID and send directly over LAN."""
        dp_id = CODE_TO_LOCAL_DP_ID.get(code)
        if dp_id is None:
            if code.startswith("dp_"):
                dp_id = code.removeprefix("dp_")
            else:
                raise TuyaApiError(None, f"Unbekannter lokaler DP-Code: {code}")

        await self._hass.async_add_executor_job(self._send_sync, dp_id, value)
