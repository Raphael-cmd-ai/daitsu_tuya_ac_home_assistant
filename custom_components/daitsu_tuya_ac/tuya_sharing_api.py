"""SmartLife QR-Code (tuya-device-sharing-sdk) backend with real-time MQTT push & zero developer quota."""

from __future__ import annotations

from collections.abc import Callable
import json
import logging
from typing import Any

from tuya_sharing import CustomerDevice, Manager, SharingDeviceListener, SharingTokenListener

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ENDPOINT,
    CONF_TERMINAL_ID,
    CONF_TOKEN_INFO,
    CONF_USER_CODE,
    TUYA_SHARING_CLIENT_ID,
)
from .tuya_api import TuyaApiError

_LOGGER = logging.getLogger(__name__)


class _HATokenListener(SharingTokenListener):
    """Persists refreshed SmartLife tokens back into the HA ConfigEntry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry = entry

    def update_token(self, token_info: dict[str, Any]) -> None:
        new_data = {**self._entry.data, CONF_TOKEN_INFO: token_info}
        self._hass.add_job(
            self._hass.config_entries.async_update_entry,
            self._entry,
            data=new_data,
        )


class _HADeviceListener(SharingDeviceListener):
    """Forwards real-time Tuya MQTT push updates directly to the coordinator."""

    def __init__(self, on_push: Callable[[], None]) -> None:
        self._on_push = on_push

    def update_device(self, device: CustomerDevice) -> None:
        self._on_push()

    def add_device(self, device: CustomerDevice) -> None:
        self._on_push()

    def remove_device(self, device_id: str) -> None:
        self._on_push()


class TuyaSharingApi:
    """SmartLife App QR-Code backend: zero developer quota + instant MQTT push."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        on_push_update: Callable[[dict[str, dict[str, Any]]], None] | None = None,
    ) -> None:
        self._hass = hass
        self._entry = entry
        self._on_push_update = on_push_update
        self._manager: Manager | None = None

    def set_push_callback(
        self, callback: Callable[[dict[str, dict[str, Any]]], None]
    ) -> None:
        self._on_push_update = callback

    def _ensure_manager_sync(self) -> Manager:
        if self._manager is not None:
            return self._manager

        token_listener = _HATokenListener(self._hass, self._entry)
        manager = Manager(
            TUYA_SHARING_CLIENT_ID,
            self._entry.data[CONF_USER_CODE],
            self._entry.data[CONF_TERMINAL_ID],
            self._entry.data[CONF_ENDPOINT],
            dict(self._entry.data[CONF_TOKEN_INFO]),
            token_listener,
        )
        manager.update_device_cache()
        for dev_id, dev in (manager.device_map or {}).items():
            fn_map = {
                k: getattr(v, "values", "")
                for k, v in (getattr(dev, "function", None) or {}).items()
            }
            _LOGGER.warning(
                "SmartLife device %s (%s) | functions=%s | status=%s",
                getattr(dev, "name", dev_id),
                dev_id,
                fn_map,
                getattr(dev, "status", {}),
            )
        manager.add_device_listener(_HADeviceListener(self._handle_mqtt_push))
        try:
            manager.refresh_mq()
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning("SmartLife MQTT Push konnte nicht gestartet werden: %s", err)

        self._manager = manager
        return manager

    def _handle_mqtt_push(self) -> None:
        if self._on_push_update is None or self._manager is None:
            return
        devices = self._serialize_device_map(self._manager)
        data = {dev["id"]: dev for dev in devices}
        self._hass.loop.call_soon_threadsafe(self._on_push_update, data)

    @staticmethod
    def _serialize_device_map(manager: Manager) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for dev_id, dev in (manager.device_map or {}).items():
            status = dict(getattr(dev, "status", None) or {})
            result.append(
                {
                    "id": dev_id,
                    "name": getattr(dev, "name", None) or "Daitsu Artic Plus",
                    "category": getattr(dev, "category", ""),
                    "online": bool(getattr(dev, "online", True)),
                    "product_name": getattr(dev, "product_name", "Daitsu / TCL AC"),
                    "status": status,
                }
            )
        return result

    def _fetch_sync(self) -> list[dict[str, Any]]:
        first_init = self._manager is None
        manager = self._ensure_manager_sync()
        if not first_init:
            manager.update_device_cache()
        return self._serialize_device_map(manager)

    def _adapt_value_to_function_spec(
        self, manager: Manager, device_id: str, code: str, value: Any
    ) -> Any:
        """Auto-adapt enum values if SmartLife exposes text enums instead of 0..7 / 0..4."""
        dev = (manager.device_map or {}).get(device_id)
        if dev is None:
            return value
        fn = (getattr(dev, "function", None) or {}).get(code)
        if fn is None:
            return value
        try:
            spec = json.loads(getattr(fn, "values", "{}") or "{}")
        except (TypeError, ValueError):
            return value
        allowed = spec.get("range")
        if not isinstance(allowed, list) or not allowed:
            return value
        val_str = str(value)
        if val_str in allowed:
            return val_str

        # Map numeric Daitsu mode codes -> SmartLife text enum if required
        if code == "mode":
            candidates = {
                "0": ["auto"],
                "1": ["cold", "cool"],
                "2": ["wet", "dry"],
                "3": ["wind", "fan"],
                "4": ["heat", "hot"],
            }.get(val_str, [])
            for c in candidates:
                if c in allowed:
                    return c

        # Map numeric Daitsu fan codes -> SmartLife text enum if required
        if code == "fan_speed_enum":
            candidates = {
                "0": ["auto"],
                "1": ["mute", "quiet", "low"],
                "2": ["low"],
                "3": ["low", "mid_low", "mid"],
                "4": ["mid", "middle", "medium"],
                "5": ["mid_high", "mid", "high"],
                "6": ["high"],
                "7": ["strong", "turbo", "high"],
            }.get(val_str, [])
            for c in candidates:
                if c in allowed:
                    return c

        return value

    def _send_sync(self, device_id: str, code: str, value: Any) -> None:
        manager = self._ensure_manager_sync()
        adapted_value = self._adapt_value_to_function_spec(
            manager, device_id, code, value
        )
        _LOGGER.warning(
            "SmartLife send_commands %s: %s=%r (adapted=%r)",
            device_id,
            code,
            value,
            adapted_value,
        )
        resp = manager.send_commands(device_id, [{"code": code, "value": adapted_value}])
        if isinstance(resp, dict) and resp.get("success") is False:
            raise TuyaApiError(
                resp.get("code"),
                resp.get("msg", f"Befehl {code}={adapted_value} fehlgeschlagen."),
            )

    async def async_get_devices(self) -> list[dict[str, Any]]:
        try:
            return await self._hass.async_add_executor_job(self._fetch_sync)
        except Exception as err:  # pylint: disable=broad-except
            raise TuyaApiError(None, f"SmartLife-Verbindungsfehler: {err}") from err

    async def async_send_command(
        self, device_id: str, code: str, value: Any
    ) -> None:
        try:
            await self._hass.async_add_executor_job(
                self._send_sync, device_id, code, value
            )
        except TuyaApiError:
            raise
        except Exception as err:  # pylint: disable=broad-except
            raise TuyaApiError(None, f"SmartLife-Befehl fehlgeschlagen: {err}") from err

    async def async_stop(self) -> None:
        """Stop background MQTT thread cleanly on unload."""
        manager = self._manager
        self._manager = None
        if manager is not None and getattr(manager, "mq", None) is not None:
            await self._hass.async_add_executor_job(manager.mq.stop)
