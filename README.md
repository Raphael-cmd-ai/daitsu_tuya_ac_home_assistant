# Daitsu / TCL Tuya AC (`TCWBRCU1`) – Home Assistant Custom Integration

A custom Home Assistant integration built specifically for **Daitsu Artic Plus** and compatible **TCL split air conditioners** equipped with the newer Tuya **`TCWBRCU1`** Wi-Fi & Bluetooth module (`FCC ID: 2ANDL-TCWBRCU1`, RTL8720CF).

Unlike generic LocalTuya or standard Tuya integrations—which often misread temperature scaling (`scale: 2`), miss louver positions (`9–13`), or expose broken switches—this integration maps every real hardware data point accurately via the official Tuya Open Cloud API (Sign 2.0).

---

## Features

- **Climate (`climate`)**:
  - Power On/Off, live room temperature, and target temperature in **`0.5 °C` steps** (`16.0–31.0 °C`, proper `scale: 2` handling).
  - All 5 HVAC modes (`0–4`): *Auto, Cool, Dry, Fan Only, Heat*.
  - All 8 fan speeds (`0–7`): *Auto, Quiet, Gentle, Low, Medium, Strong, High, Turbo*.
- **2D Louver Control (`select`)**:
  - **Vertical Louver (`gear_vertical`)** & **Horizontal Louver (`gear_horizontal`)** with the exact Daitsu/TCL fixed positions (`9–13`) and swing modes (`1–4`).
- **Hardware Switches (`switch`)**:
  - Display Light (`light`), Beep (`beep`), Eco Mode (`eco`), AI-Eco (`ai_eco_switch`), Anti-Mold Drying (`drying`), Self-Cleaning (`cleaning`), and 8 °C Freeze Protection (`eight_add_hot`).
- **Live Telemetry Sensors (`sensor`)**:
  - **Room Temperature** (`temp_current`, °C)
  - **Outdoor Temperature** (`ure`, °C – proper `scale: 2` handling even below 10 °C / sub-zero)
  - **Current Power** (calculated live in `W` from 2-minute interval energy, drops to `0 W` when off)
  - **Interval Energy** (`electricity`, kWh)
  - **Error Diagnostics** (`error_code`)
- **Bonus – Tesla-Style 2D Airflow Custom Card (`www/daitsu-airflow-card.js`)**:
  - Included interactive touch/mouse 2D airflow touchpad with live mode-colored airflow curves, 4-way D-pad arrows, and quick swing toggles.

---

## Installation

### Option 1: HACS (Recommended)
1. Open **HACS** in Home Assistant → click the **3 dots** (top right) → **Custom repositories**.
2. Add `https://github.com/Raphael-cmd-ai/daitsu_tuya_ac_home_assistant` with category **Integration**.
3. Search for **Daitsu / TCL Tuya Klimaanlage** in HACS and click **Download**.
4. **Restart Home Assistant**.

### Option 2: Manual Installation
1. Copy the folder `custom_components/daitsu_tuya_ac` into your Home Assistant config directory at `/config/custom_components/daitsu_tuya_ac`.
2. **Restart Home Assistant**.

### Configuration
1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Daitsu / TCL Tuya Klimaanlage**.
3. Enter your **Tuya IoT Cloud** credentials (**Access ID**, **Access Secret**, **Region**, and optionally **User ID / UID**). Make sure **IoT Core** is authorized in your Tuya Cloud project.

---

## Optional: Tesla-Style 2D Airflow Card & Pro Dashboard
1. Copy `www/daitsu-airflow-card.js` to `/config/www/daitsu-airflow-card.js`.
2. In Home Assistant go to **Settings → Dashboards → (3 dots) → Resources → Add Resource**:
   - **URL:** `/local/daitsu-airflow-card.js`
   - **Type:** `JavaScript Module`
3. Check `dashboard_daitsu_pro.yaml` or `dashboard_example.yaml` for ready-to-use Lovelace dashboard layouts.
