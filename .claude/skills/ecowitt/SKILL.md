---
name: ecowitt
description: Control and query Ecowitt weather station devices on the local network. Use when the user asks about weather data, sensor readings, IoT device control, or anything related to their Ecowitt GW3000 gateway.
argument-hint: "[command] e.g. weather, info, iot list, iot switch, history"
---

# Ecowitt Device Control

You have access to a CLI tool at `tools/ecowitt_cli.py` that communicates with Ecowitt weather station gateways via their local HTTP API. No external dependencies are needed (stdlib only).

## Device Details

- **Device**: GW3000B-WIFIE3EB
- **Firmware**: GW3000B_V1.1.4
- **IP**: 192.168.68.77 (already configured in `tools/.ecowitt_host`)
- **MAC**: 5C:01:3B:38:E3:EB
- **Units**: Temperature: °F, Pressure: inHg, Wind: mph, Rain: in, Light: Klux

## Connected Sensors

| Sensor | Model | ID | Provides |
|--------|-------|----|----------|
| WH90 Haptic Array (7-in-1) | Type 48 | B483 | Outdoor temp/humidity, wind speed/direction/gust, solar radiation, UV index, piezo rain |
| WH25 (built-in) | Type 4 | internal | Indoor temp/humidity, absolute/relative pressure |

The WH90 is an all-in-one ultrasonic outdoor weather station. No traditional rain gauge or separate wind sensor - the WH90 handles all outdoor measurements.

## SD Card / Historical Data

A 256GB micro SD card (SN256, SDHC/SDXC) is installed and actively logging every **5 minutes**.

- **Data port**: Files are served on **port 81** (`http://192.168.68.77:81/<filename>`)
- **File listing**: `get_sdmmc_info` endpoint on port 80
- **Web UI**: `http://192.168.68.77/cardInfo.html` (login: admin, leave password blank)

### CSV File Naming

- `YYYYMM{A|B}.csv` - main weather data
- `YYYYMMAllsensors_{A|B}.csv` - expanded version with all sensor channels
- A/B suffix: file splits when a file gets large within a month

### CSV Columns (main files)

Time, Timestamp, Indoor Temperature(°F), Indoor Humidity(%), Outdoor Temperature(°F), Outdoor Humidity(%), Dew Point(°F), Feels Like(°F), BGT(°F), WBGT(°F), VPD(kPa), Wind(mph), Gust(mph), windDir_10min_avg(deg), Wind Direction(deg), ABS Pressure(inHg), REL Pressure(inHg), Solar Rad(W/m2), UV-Index, Rain Rate(in/Hr), 24h Rain(in), Hourly Rain(in), Event Rain(in), Daily Rain(in), Weekly Rain(in), Monthly Rain(in), Yearly Rain(in), Piezo Rate(in/Hr), Piezo 24h Rain(in), Piezo Hourly Rain(in), Piezo Event Rain(in), Piezo Daily Rain(in), Piezo Weekly Rain(in), Piezo Monthly Rain(in), Piezo Yearly Rain(in)

## Available Commands

Run commands using: `python3 tools/ecowitt_cli.py <command>`

| Command | Description |
|---------|-------------|
| `configure <IP>` | Save device IP address and verify connectivity |
| `info` | Show device name, firmware version, MAC, unit settings |
| `weather` | Show current weather (temp, humidity, wind, rain, UV, etc.) |
| `sensors` | Show connected sensors, battery/signal, and current readings |
| `history list` | Show SD card info and CSV file listing |
| `history download <file>` | Download a CSV file from SD card |
| `history download all -o <dir>` | Download all CSV files to a directory |
| `iot list` | List all connected IoT devices (WFC01, AC1100, WFC02) |
| `iot switch <id> <model> on\|off` | Turn an IoT device on or off |
| `iot read <id> <model>` | Read detailed status of a specific IoT device |
| `raw <endpoint>` | Raw GET request to any device endpoint |

## Raw API Endpoints

For advanced queries, use `raw` with these endpoints:

| Endpoint | Port | Data |
|----------|------|------|
| `get_livedata_info` | 80 | All live weather sensor data (JSON with common_list, rain, wh25, etc.) |
| `get_version` | 80 | Firmware version |
| `get_device_info` | 80 | Device name (apName) |
| `get_network_info` | 80 | MAC address |
| `get_units_info` | 80 | Unit settings (temperature, pressure, wind, rain, light) |
| `get_sensors_info?page=1` | 80 | Sensor info page 1 (battery, signal, RSSI) |
| `get_sensors_info?page=2` | 80 | Sensor info page 2 |
| `get_iot_device_list` | 80 | IoT device inventory |
| `get_sdmmc_info` | 80 | SD card info and file list |
| `get_calibration_data` | 80 | Sensor calibration offsets and gains |
| `get_rain_totals` | 80 | Rain gauge config and totals |
| `get_piezo_rain` | 80 | Piezo rain calibration gains |
| `<filename>.csv` | **81** | Download CSV file from SD card |

## Sensor Type Reference

| Type ID | Sensor | Data Provided |
|---------|--------|---------------|
| 0 | WH69 Sensor Array | Outdoor temp/humidity, wind, rain |
| 1 | WH68 Wind Sensor | Wind speed/direction |
| 2 | WH80 Sonic Array | Outdoor temp/humidity, wind |
| 3 | WH40 Rainfall Sensor | Rain gauge |
| 4 | WH25 Indoor T&RH&P | Indoor temp, humidity, pressure (built-in) |
| 5 | WH26 Outdoor T&RH | Outdoor temp, humidity |
| 6-13 | T&H CH1-CH8 | Multi-channel temp & humidity |
| 14-21 | Soil CH1-CH8 | Soil moisture |
| 22-25 | PM2.5 CH1-CH4 | Particulate matter |
| 26 | WH57 Lightning | Lightning distance, count |
| 27-30 | Leak CH1-CH4 | Water leak detection |
| 31-38 | Temp CH1-CH8 | Temperature only |
| 39 | WH45 AQI Combo | CO2, PM1/2.5/4/10, temp, humidity |
| 40-47 | Leaf CH1-CH8 | Leaf wetness |
| 48 | WH90 Haptic Array (7-in-1) | Outdoor temp/humidity, ultrasonic wind, piezo rain, solar, UV |
| 49 | WH85 Haptic 3-in-1 | Outdoor temp/humidity, wind, rain, solar, UV |
| 58-65 | Soil CH9-CH16 | Soil moisture (extended) |
| 66-69 | LDS CH1-CH4 | Laser distance |
| 70 | WN20 Rain Gauge Mini | Rain |

## IoT Device Models

| Model ID | Name | Type |
|----------|------|------|
| 1 | WFC01 | Water Timer |
| 2 | AC1100 | Smart Plug |
| 3 | WFC02 | Water Timer v2 |

## Interpreting Weather Data

When presenting weather data to the user:
- Format temperatures with appropriate units (device is configured for °F)
- Round values sensibly (1 decimal for temp, 0-2 for rain)
- Summarize conditions naturally ("It's 72°F and partly cloudy with light winds from the SW")
- Skip empty/unavailable readings (values like "--" or empty strings)
- If the user asks a natural question like "what's the weather?", use the `weather` command and present it conversationally

## Controlling IoT Devices

When the user wants to control a device:
1. First run `iot list` to see available devices and their IDs/models
2. Confirm the action with the user before switching (e.g., "Turn on Water Timer 'Garden' (ID 1753)?")
3. Use `iot switch <id> <model> on|off` to execute
4. Optionally verify with `iot read <id> <model>` afterward

## Handling Arguments

If `$ARGUMENTS` contains a recognized command (weather, info, sensors, iot list, etc.), execute it directly. Otherwise, interpret the user's intent and pick the right command.

Examples:
- `/ecowitt` or `/ecowitt weather` → run weather command
- `/ecowitt turn on the garden timer` → list IoT devices, find matching one, confirm, switch on
- `/ecowitt is my sensor battery low?` → run sensors command, report status
- `/ecowitt raw get_livedata_info` → raw API call
- `/ecowitt history` → list SD card files and data range
- `/ecowitt download all the history` → download all CSV files
- `/ecowitt what was the temperature last week?` → download recent CSV, analyze data
