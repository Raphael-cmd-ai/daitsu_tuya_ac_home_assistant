"""Config flow for Daitsu / TCL Tuya AC."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_POLL_INTERVAL,
    CONF_REGION,
    CONF_USER_ID,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    TUYA_REGIONS,
)
from .tuya_api import TuyaApiError, TuyaCloudApi


class DaitsuTuyaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Daitsu / TCL Tuya AC."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
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
                    return self.async_create_entry(
                        title=f"Daitsu Tuya ({user_input[CONF_REGION]})",
                        data=user_input,
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
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
