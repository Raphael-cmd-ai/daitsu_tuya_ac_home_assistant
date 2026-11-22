"""Config flow for Daitsu / TCL Tuya AC (SmartLife QR-Push, Local v3.5, or Cloud)."""

from __future__ import annotations

import base64
import io
from typing import Any

import segno
from tuya_sharing import LoginControl
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_CONNECTION_MODE,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_ENDPOINT,
    CONF_HOST,
    CONF_LOCAL_KEY,
    CONF_POLL_INTERVAL,
    CONF_PROTOCOL_VERSION,
    CONF_REGION,
    CONF_TERMINAL_ID,
    CONF_TOKEN_INFO,
    CONF_USER_CODE,
    CONF_USER_ID,
    DEFAULT_LOCAL_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    LOCAL_PROTOCOL_VERSIONS,
    MODE_CLOUD,
    MODE_LOCAL,
    MODE_SMARTLIFE,
    TUYA_REGIONS,
    TUYA_SHARING_CLIENT_ID,
    TUYA_SHARING_SCHEMA,
)
from .tuya_api import TuyaApiError, TuyaCloudApi
from .tuya_local_api import TuyaLocalApi


def _make_qr_svg_data_uri(content: str) -> str:
    """Render QR code as inline SVG data URI for Home Assistant UI."""
    buf = io.BytesIO()
    segno.make(content).save(buf, kind="svg", scale=5, border=2)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


class DaitsuTuyaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Daitsu / TCL Tuya AC."""

    VERSION = 1

    def __init__(self) -> None:
        self._login_control = LoginControl()
        self._user_code: str = ""
        self._qr_code: str = ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let the user choose connection mode."""
        return self.async_show_menu(
            step_id="user",
            menu_options=[MODE_SMARTLIFE, MODE_LOCAL, MODE_CLOUD],
        )

    # ------------------------------------------------------------------
    # 1. SmartLife QR-Code Login (0 Developer Quota, Real-Time MQTT Push)
    # ------------------------------------------------------------------
    async def async_step_smartlife(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Ask for SmartLife User Code and request QR code."""
        errors: dict[str, str] = {}

        if user_input is not None:
            user_code = user_input[CONF_USER_CODE].strip()
            response = await self.hass.async_add_executor_job(
                self._login_control.qr_code,
                TUYA_SHARING_CLIENT_ID,
                TUYA_SHARING_SCHEMA,
                user_code,
            )
            if response.get("success") and response.get("result", {}).get("qrcode"):
                self._user_code = user_code
                self._qr_code = response["result"]["qrcode"]
                return await self.async_step_smartlife_scan()
            errors["base"] = "invalid_user_code"

        return self.async_show_form(
            step_id="smartlife",
            data_schema=vol.Schema({vol.Required(CONF_USER_CODE): str}),
            errors=errors,
        )

    async def async_step_smartlife_scan(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Display QR code and verify login once scanned in SmartLife."""
        errors: dict[str, str] = {}

        if user_input is not None:
            ret, info = await self.hass.async_add_executor_job(
                self._login_control.login_result,
                self._qr_code,
                TUYA_SHARING_CLIENT_ID,
                self._user_code,
            )
            if ret and isinstance(info, dict):
                token_info = {
                    "t": info.get("t"),
                    "uid": info.get("uid"),
                    "expire_time": info.get("expire_time"),
                    "access_token": info.get("access_token"),
                    "refresh_token": info.get("refresh_token"),
                }
                await self.async_set_unique_id(f"smartlife_{self._user_code}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Daitsu SmartLife ({info.get('username') or self._user_code})",
                    data={
                        CONF_CONNECTION_MODE: MODE_SMARTLIFE,
                        CONF_USER_CODE: self._user_code,
                        CONF_TERMINAL_ID: info.get("terminal_id", ""),
                        CONF_ENDPOINT: info.get("endpoint", ""),
                        CONF_TOKEN_INFO: token_info,
                    },
                )
            errors["base"] = "qr_not_scanned"

        qr_uri = _make_qr_svg_data_uri(f"tuyaSmart--qrLogin?token={self._qr_code}")
        return self.async_show_form(
            step_id="smartlife_scan",
            data_schema=vol.Schema({}),
            description_placeholders={"qr_code": qr_uri},
            errors=errors,
        )

    # ------------------------------------------------------------------
    # 2. Local LAN Mode (v3.5 / v3.4 / v3.3)
    # ------------------------------------------------------------------
    async def async_step_local(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure 100% local LAN connection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api = TuyaLocalApi(
                hass=self.hass,
                device_name=user_input[CONF_DEVICE_NAME],
                host=user_input[CONF_HOST],
                device_id=user_input[CONF_DEVICE_ID],
                local_key=user_input[CONF_LOCAL_KEY],
                protocol_version=user_input[CONF_PROTOCOL_VERSION],
            )
            try:
                devices = await api.async_get_devices()
                if not devices:
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(
                        f"local_{user_input[CONF_DEVICE_ID].strip()}"
                    )
                    self._abort_if_unique_id_configured()
                    data = {
                        CONF_CONNECTION_MODE: MODE_LOCAL,
                        **user_input,
                    }
                    return self.async_create_entry(
                        title=f"{user_input[CONF_DEVICE_NAME].strip()} (Lokal)",
                        data=data,
                    )
            except TuyaApiError:
                errors["base"] = "local_connect_failed"
            except Exception:
                errors["base"] = "local_connect_failed"

        schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE_NAME, default="Daitsu Artic Plus"): str,
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_DEVICE_ID): str,
                vol.Required(CONF_LOCAL_KEY): str,
                vol.Required(CONF_PROTOCOL_VERSION, default="auto"): vol.In(
                    LOCAL_PROTOCOL_VERSIONS
                ),
                vol.Optional(
                    CONF_POLL_INTERVAL, default=DEFAULT_LOCAL_POLL_INTERVAL
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
            }
        )

        return self.async_show_form(
            step_id="local",
            data_schema=schema,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # 3. Tuya Open Cloud Developer API (90s polling)
    # ------------------------------------------------------------------
    async def async_step_cloud(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure Tuya Open Cloud API connection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            api = TuyaCloudApi(
                session=session,
                access_id=user_input[CONF_ACCESS_ID],
                access_secret=user_input[CONF_ACCESS_SECRET],
                region=user_input[CONF_REGION],
                user_id=user_input.get(CONF_USER_ID, ""),
            )
            try:
                devices = await api.async_get_devices()
                if not devices:
                    errors["base"] = "no_devices"
                else:
                    await self.async_set_unique_id(
                        f"{user_input[CONF_REGION]}_{user_input[CONF_ACCESS_ID].strip()}"
                    )
                    self._abort_if_unique_id_configured()
                    data = {
                        CONF_CONNECTION_MODE: MODE_CLOUD,
                        **user_input,
                    }
                    return self.async_create_entry(
                        title=f"Daitsu Tuya ({user_input[CONF_REGION]})",
                        data=data,
                    )
            except TuyaApiError as err:
                if err.code in (1004, 1106, 28841105):
                    errors["base"] = "invalid_auth"
                else:
                    errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "cannot_connect"

        region_choices = {code: label for code, (label, _) in TUYA_REGIONS.items()}
        schema = vol.Schema(
            {
                vol.Required(CONF_ACCESS_ID): str,
                vol.Required(CONF_ACCESS_SECRET): str,
                vol.Required(CONF_REGION, default="EU"): vol.In(region_choices),
                vol.Optional(CONF_USER_ID, default=""): str,
                vol.Optional(
                    CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL
                ): vol.All(vol.Coerce(int), vol.Range(min=30, max=600)),
            }
        )

        return self.async_show_form(
            step_id="cloud",
            data_schema=schema,
            errors=errors,
        )
