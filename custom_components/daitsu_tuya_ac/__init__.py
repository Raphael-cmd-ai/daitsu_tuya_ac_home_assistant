"""The Daitsu / TCL Tuya AC integration (Local v3.5 & Cloud)."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_CONNECTION_MODE,
    CONF_DEVICE_ID,
    CONF_DEVICE_NAME,
    CONF_HOST,
    CONF_LOCAL_KEY,
    CONF_POLL_INTERVAL,
    CONF_PROTOCOL_VERSION,
    CONF_REGION,
    CONF_USER_ID,
    DEFAULT_LOCAL_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    MODE_CLOUD,
    MODE_LOCAL,
)
from .coordinator import DaitsuTuyaCoordinator
from .tuya_api import TuyaCloudApi
from .tuya_local_api import TuyaLocalApi

PLATFORMS: list[Platform] = [
    Platform.CLIMATE,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Daitsu / TCL Tuya AC from a config entry."""
    mode = entry.data.get(CONF_CONNECTION_MODE, MODE_CLOUD)

    if mode == MODE_LOCAL:
        api = TuyaLocalApi(
            hass=hass,
            device_name=entry.data.get(CONF_DEVICE_NAME, "Daitsu Artic Plus"),
            host=entry.data[CONF_HOST],
            device_id=entry.data[CONF_DEVICE_ID],
            local_key=entry.data[CONF_LOCAL_KEY],
            protocol_version=entry.data.get(CONF_PROTOCOL_VERSION, "auto"),
        )
        poll_interval = int(
            entry.data.get(CONF_POLL_INTERVAL, DEFAULT_LOCAL_POLL_INTERVAL)
        )
    else:
        session = async_get_clientsession(hass)
        api = TuyaCloudApi(
            session=session,
            access_id=entry.data[CONF_ACCESS_ID],
            access_secret=entry.data[CONF_ACCESS_SECRET],
            region=entry.data.get(CONF_REGION, "EU"),
            user_id=entry.data.get(CONF_USER_ID, ""),
        )
        poll_interval = int(entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL))

    coordinator = DaitsuTuyaCoordinator(hass, api, poll_interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
