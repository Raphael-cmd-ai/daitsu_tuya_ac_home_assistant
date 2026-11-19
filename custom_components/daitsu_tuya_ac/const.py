"""Constants and Daitsu/TCL Tuya mappings for the Daitsu Tuya AC integration."""

from __future__ import annotations

from homeassistant.components.climate import HVACMode

DOMAIN = "daitsu_tuya_ac"

CONF_ACCESS_ID = "access_id"
CONF_ACCESS_SECRET = "access_secret"
CONF_REGION = "region"
CONF_USER_ID = "user_id"
CONF_POLL_INTERVAL = "poll_interval"

DEFAULT_POLL_INTERVAL = 15

TUYA_REGIONS: dict[str, tuple[str, str]] = {
    "EU": ("Central Europe (EU)", "https://openapi.tuyaeu.com"),
    "WE": ("Western Europe (WE)", "https://openapi-weaz.tuyaeu.com"),
    "US": ("Western America (US)", "https://openapi.tuyaus.com"),
    "UE": ("Eastern America (UE)", "https://openapi-ueaz.tuyaus.com"),
    "CN": ("China (CN)", "https://openapi.tuyacn.com"),
    "IN": ("India (IN)", "https://openapi.tuyain.com"),
}

# Exact Daitsu Artic Plus / TCL Tuya mode enum mapping (0..4)
MODE_CODE_TO_HVAC: dict[str, HVACMode] = {
    "0": HVACMode.AUTO,
    "1": HVACMode.COOL,
    "2": HVACMode.DRY,
    "3": HVACMode.FAN_ONLY,
    "4": HVACMode.HEAT,
    "auto": HVACMode.AUTO,
    "cold": HVACMode.COOL,
    "cool": HVACMode.COOL,
    "wet": HVACMode.DRY,
    "dry": HVACMode.DRY,
    "wind": HVACMode.FAN_ONLY,
    "fan": HVACMode.FAN_ONLY,
    "heat": HVACMode.HEAT,
}

HVAC_TO_MODE_CODE: dict[HVACMode, str] = {
    HVACMode.AUTO: "0",
    HVACMode.COOL: "1",
    HVACMode.DRY: "2",
    HVACMode.FAN_ONLY: "3",
    HVACMode.HEAT: "4",
}

# Exact Daitsu Artic Plus / TCL fan_speed_enum mapping (0..7)
FAN_CODE_TO_NAME: dict[str, str] = {
    "0": "Auto",
    "1": "Leise",
    "2": "Sanft",
    "3": "Niedrig",
    "4": "Mittel",
    "5": "Stark",
    "6": "Hoch",
    "7": "Turbo",
}
FAN_NAME_TO_CODE: dict[str, str] = {v: k for k, v in FAN_CODE_TO_NAME.items()}

# Exact Daitsu Artic Plus / TCL louver positions (9..13 fixed, 1..4 swing)
VERTICAL_LOUVER_CODE_TO_NAME: dict[str, str] = {
    "0": "Aus",
    "1": "Schwenken (Auf/Ab)",
    "2": "Schwenken (Oben)",
    "3": "Schwenken (Unten)",
    "9": "Ganz oben",
    "10": "Oben",
    "11": "Mitte",
    "12": "Unten",
    "13": "Ganz unten",
}
VERTICAL_LOUVER_NAME_TO_CODE: dict[str, str] = {
    v: k for k, v in VERTICAL_LOUVER_CODE_TO_NAME.items()
}

HORIZONTAL_LOUVER_CODE_TO_NAME: dict[str, str] = {
    "0": "Aus",
    "1": "Schwenken (Links/Rechts)",
    "2": "Schwenken (Links)",
    "3": "Schwenken (Mitte)",
    "4": "Schwenken (Rechts)",
    "9": "Ganz links",
    "10": "Leicht links",
    "11": "Mitte",
    "12": "Leicht rechts",
    "13": "Ganz rechts",
}
HORIZONTAL_LOUVER_NAME_TO_CODE: dict[str, str] = {
    v: k for k, v in HORIZONTAL_LOUVER_CODE_TO_NAME.items()
}

# Feature switches supported by Daitsu Artic Plus (code, German name, MDI icon)
FEATURE_SWITCHES: list[tuple[str, str, str]] = [
    ("light", "Display-Licht", "mdi:led-on"),
    ("beep", "Piepton", "mdi:volume-high"),
    ("eco", "Eco-Modus", "mdi:leaf"),
    ("ai_eco_switch", "AI-Eco", "mdi:auto-fix"),
    ("drying", "Anti-Schimmel Trocknen", "mdi:water-off"),
    ("cleaning", "Selbstreinigung", "mdi:sparkles"),
    ("eight_add_hot", "8 °C Frostschutz", "mdi:snowflake-thermometer"),
]
