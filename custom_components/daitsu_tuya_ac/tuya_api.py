"""Async Tuya Open Cloud API (Sign 2.0 / HMAC-SHA256) client for Home Assistant."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from typing import Any

import aiohttp

from .const import TUYA_REGIONS

EMPTY_BODY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


class TuyaApiError(Exception):
    """Raised when Tuya Cloud API returns an error."""

    def __init__(self, code: int | None, message: str) -> None:
        super().__init__(message)
        self.code = code


class TuyaCloudApi:
    """Minimal async Tuya Open Cloud API v1/v2 client."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        access_id: str,
        access_secret: str,
        region: str,
        user_id: str = "",
    ) -> None:
        self._session = session
        self._access_id = access_id.strip()
        self._access_secret = access_secret.strip()
        self._user_id = user_id.strip()
        _, self._base_url = TUYA_REGIONS.get(region, TUYA_REGIONS["EU"])

        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self._token_lock = asyncio.Lock()
        self._working_devices_endpoint: str | None = None
        self._working_command_prefix: str | None = None

    @staticmethod
    def _canonicalize_url(path_with_query: str) -> str:
        if "?" not in path_with_query:
            return path_with_query
        path, raw_query = path_with_query.split("?", 1)
        if not raw_query:
            return path
        params = sorted(
            (p for p in raw_query.split("&") if p),
            key=lambda p: p.split("=", 1)[0],
        )
        return f"{path}?{'&'.join(params)}"

    def _build_sign(
        self,
        method: str,
        path_with_query: str,
        body: str,
        timestamp: str,
        access_token: str | None = None,
    ) -> str:
        content_sha256 = (
            EMPTY_BODY_SHA256
            if not body
            else hashlib.sha256(body.encode("utf-8")).hexdigest()
        )
        canonical_url = self._canonicalize_url(path_with_query)
        string_to_sign = f"{method.upper()}\n{content_sha256}\n\n{canonical_url}"
        payload = (
            f"{self._access_id}{access_token or ''}{timestamp}{string_to_sign}"
        )
        return (
            hmac.new(
                self._access_secret.encode("utf-8"),
                payload.encode("utf-8"),
                hashlib.sha256,
            )
            .hexdigest()
            .upper()
        )

    async def _get_token(self, force_refresh: bool = False) -> str:
        async with self._token_lock:
            now = time.time()
            if (
                not force_refresh
                and self._token
                and now < self._token_expires_at - 60
            ):
                return self._token

            path = "/v1.0/token?grant_type=1"
            ts = str(int(time.time() * 1000))
            sign = self._build_sign("GET", path, "", ts, access_token=None)
            headers = {
                "client_id": self._access_id,
                "sign": sign,
                "t": ts,
                "sign_method": "HMAC-SHA256",
            }
            data = await self._http_request("GET", path, headers)
            result = data.get("result") or {}
            token = result.get("access_token")
            expire_time = int(result.get("expire_time", 7200))
            if not token:
                raise TuyaApiError(None, "Kein Access-Token von Tuya erhalten.")

            self._token = token
            self._token_expires_at = time.time() + expire_time
            return token

    async def _signed_request(
        self,
        method: str,
        path_with_query: str,
        body_dict: dict[str, Any] | None = None,
        retry_on_expired: bool = True,
    ) -> dict[str, Any]:
        token = await self._get_token(force_refresh=False)
        body_str = (
            json.dumps(body_dict, separators=(",", ":")) if body_dict is not None else ""
        )
        ts = str(int(time.time() * 1000))
        sign = self._build_sign(method, path_with_query, body_str, ts, access_token=token)
        headers = {
            "client_id": self._access_id,
            "access_token": token,
            "sign": sign,
            "t": ts,
            "sign_method": "HMAC-SHA256",
        }
        if body_dict is not None:
            headers["Content-Type"] = "application/json"

        try:
            return await self._http_request(method, path_with_query, headers, body_str)
        except TuyaApiError as err:
            if err.code == 1010 and retry_on_expired:
                await self._get_token(force_refresh=True)
                return await self._signed_request(
                    method, path_with_query, body_dict, retry_on_expired=False
                )
            raise

    async def _http_request(
        self,
        method: str,
        path_with_query: str,
        headers: dict[str, str],
        body: str = "",
    ) -> dict[str, Any]:
        url = f"{self._base_url}{path_with_query}"
        try:
            async with self._session.request(
                method,
                url,
                headers=headers,
                data=body.encode("utf-8") if body else None,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                raw = await resp.text()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise TuyaApiError(None, f"Netzwerkfehler zur Tuya Cloud: {err}") from err

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as err:
            raise TuyaApiError(None, "Ungültige JSON-Antwort von Tuya.") from err

        if not payload.get("success", False):
            raise TuyaApiError(
                payload.get("code"),
                payload.get("msg", "Unbekannter Tuya-Fehler"),
            )
        return payload

    async def async_get_devices(self) -> list[dict[str, Any]]:
        """Fetch devices using cached working endpoint to minimize Tuya API quota usage."""
        last_err: TuyaApiError | None = None
        raw_devices: list[dict[str, Any]] | None = None

        endpoints: list[tuple[str, str]] = []
        if self._working_devices_endpoint == "user" and self._user_id:
            endpoints = [("user", f"/v1.0/users/{self._user_id}/devices")]
        elif self._working_devices_endpoint == "associated":
            endpoints = [("associated", "/v1.0/iot-01/associated-users/devices?size=50")]
        elif self._working_devices_endpoint == "v2":
            endpoints = [("v2", "/v2.0/cloud/thing/device?page_size=20")]
        else:
            if self._user_id:
                endpoints.append(("user", f"/v1.0/users/{self._user_id}/devices"))
            endpoints.append(("associated", "/v1.0/iot-01/associated-users/devices?size=50"))
            endpoints.append(("v2", "/v2.0/cloud/thing/device?page_size=20"))

        for key, path in endpoints:
            try:
                resp = await self._signed_request("GET", path)
                res = resp.get("result")
                if isinstance(res, dict):
                    raw_devices = res.get("devices") or []
                elif isinstance(res, list):
                    raw_devices = res
                else:
                    raw_devices = []
                self._working_devices_endpoint = key
                break
            except TuyaApiError as err:
                last_err = err
                if err.code not in (1106, 1109, 2406, 28841105):
                    raise

        if raw_devices is None:
            raise last_err or TuyaApiError(None, "Geräte konnten nicht geladen werden.")

        # Ensure every device has a live status dict
        devices: list[dict[str, Any]] = []
        for dev in raw_devices:
            dev_id = dev.get("id")
            if not dev_id:
                continue
            status_list = dev.get("status")
            if status_list is None:
                status_list = await self._async_get_status_best_effort(dev_id)
            status_map = {
                item["code"]: item.get("value")
                for item in (status_list or [])
                if isinstance(item, dict) and "code" in item
            }
            devices.append(
                {
                    "id": dev_id,
                    "name": dev.get("custom_name") or dev.get("name") or "Daitsu Klima",
                    "category": dev.get("category", ""),
                    "online": bool(dev.get("online", dev.get("is_online", True))),
                    "product_name": dev.get("product_name", "Daitsu / TCL AC"),
                    "status": status_map,
                }
            )
        return devices

    async def _async_get_status_best_effort(self, device_id: str) -> list[dict[str, Any]]:
        try:
            resp = await self._signed_request(
                "GET", f"/v1.0/iot-03/devices/{device_id}/status"
            )
            return resp.get("result") or []
        except TuyaApiError:
            return []

    async def async_send_command(
        self, device_id: str, code: str, value: Any
    ) -> None:
        """Send a single DP command to a device using cached working prefix."""
        body = {"commands": [{"code": code, "value": value}]}
        if self._working_command_prefix == "iot03":
            await self._signed_request(
                "POST", f"/v1.0/iot-03/devices/{device_id}/commands", body
            )
            return

        try:
            await self._signed_request("POST", f"/v1.0/devices/{device_id}/commands", body)
            self._working_command_prefix = "v1"
        except TuyaApiError as err:
            if err.code in (1106, 28841105):
                await self._signed_request(
                    "POST", f"/v1.0/iot-03/devices/{device_id}/commands", body
                )
                self._working_command_prefix = "iot03"
            else:
                raise
