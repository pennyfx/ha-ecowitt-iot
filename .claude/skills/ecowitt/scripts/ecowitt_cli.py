#!/usr/bin/env python3
"""CLI tool to interact with Ecowitt weather station gateways (GW3000, GW2000, etc.) via local HTTP API."""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

CONFIG_PATH = Path(__file__).parent / ".ecowitt_host"
TIMEOUT = 10


def get_host():
    """Resolve device IP from env var, config file, or CLI flag."""
    host = os.environ.get("ECOWITT_HOST")
    if host:
        return host
    if CONFIG_PATH.exists():
        return CONFIG_PATH.read_text().strip()
    return None


def save_host(host):
    CONFIG_PATH.write_text(host + "\n")


def api_get(host, endpoint):
    """GET request to the device's local API, returns parsed JSON."""
    url = f"http://{host}/{endpoint}"
    try:
        with urlopen(url, timeout=TIMEOUT) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        print(f"HTTP error {e.code} from {url}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Connection failed to {host}: {e.reason}", file=sys.stderr)
        sys.exit(1)


def api_post(host, endpoint, payload):
    """POST JSON to the device's local API, returns parsed JSON."""
    url = f"http://{host}/{endpoint}"
    data = json.dumps(payload).encode()
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        print(f"HTTP error {e.code} from {url}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Connection failed to {host}: {e.reason}", file=sys.stderr)
        sys.exit(1)


def cmd_info(host, _args):
    """Show device information."""
    ver = api_get(host, "get_version")
    sys_info = api_get(host, "get_device_info")
    net = api_get(host, "get_network_info")
    units = api_get(host, "get_units_info")

    print(f"Device Name : {sys_info.get('apName', 'N/A')}")
    print(f"Firmware    : {ver.get('version', 'N/A')}")
    print(f"MAC Address : {net.get('mac', 'N/A')}")
    print(f"IP Address  : {host}")

    unit_map_temp = {"0": "Celsius", "1": "Fahrenheit"}
    unit_map_press = {"0": "inHg", "1": "hPa", "2": "mmHg"}
    unit_map_wind = {"0": "m/s", "1": "km/h", "2": "mph", "3": "knots", "4": "ft/s", "5": "BFT"}
    unit_map_rain = {"0": "mm", "1": "in"}
    unit_map_light = {"0": "W/m²", "1": "Klux", "2": "Kfc"}

    print(f"\nUnit Settings:")
    print(f"  Temperature : {unit_map_temp.get(str(units.get('temperature', '')), units.get('temperature', 'N/A'))}")
    print(f"  Pressure    : {unit_map_press.get(str(units.get('pressure', '')), units.get('pressure', 'N/A'))}")
    print(f"  Wind        : {unit_map_wind.get(str(units.get('wind', '')), units.get('wind', 'N/A'))}")
    print(f"  Rain        : {unit_map_rain.get(str(units.get('rain', '')), units.get('rain', 'N/A'))}")
    print(f"  Light       : {unit_map_light.get(str(units.get('light', '')), units.get('light', 'N/A'))}")


def cmd_weather(host, _args):
    """Show current weather readings from live data."""
    data = api_get(host, "get_livedata_info")
    units = api_get(host, "get_units_info")

    # Determine display units
    temp_unit = "°F" if str(units.get("temperature", "")) == "1" else "°C"
    wind_units = {
        "0": "m/s", "1": "km/h", "2": "mph", "3": "knots", "4": "ft/s", "5": "BFT"
    }
    wind_unit = wind_units.get(str(units.get("wind", "")), "")
    rain_unit = "in" if str(units.get("rain", "")) == "1" else "mm"

    # Indoor data from wh25
    if "wh25" in data and data["wh25"]:
        wh = data["wh25"][0]
        print("=== Indoor ===")
        print(f"  Temperature : {wh.get('intemp', 'N/A')} {temp_unit}")
        print(f"  Humidity    : {wh.get('inhumi', 'N/A')}")
        print(f"  Abs Pressure: {wh.get('abs', 'N/A')}")
        print(f"  Rel Pressure: {wh.get('rel', 'N/A')}")

    # Outdoor common data
    if "common_list" in data:
        fields = {}
        for item in data["common_list"]:
            fields[item["id"]] = item.get("val", "N/A")

        print("\n=== Outdoor ===")
        if "0x02" in fields:
            print(f"  Temperature  : {fields['0x02']} {temp_unit}")
        if "0x07" in fields:
            print(f"  Humidity     : {fields['0x07']}")
        if "0x03" in fields:
            print(f"  Dew Point    : {fields['0x03']} {temp_unit}")
        if "3" in fields:
            print(f"  Feels Like   : {fields['3']} {temp_unit}")

        has_wind = any(k in fields for k in ("0x0A", "0x0B", "0x0C", "0x19"))
        if has_wind:
            print("\n=== Wind ===")
            if "0x0A" in fields:
                print(f"  Direction    : {fields['0x0A']}°")
            if "0x0B" in fields:
                print(f"  Speed        : {fields['0x0B']}")
            if "0x0C" in fields:
                print(f"  Gust         : {fields['0x0C']}")
            if "0x19" in fields:
                print(f"  Day Max      : {fields['0x19']}")

        has_solar = any(k in fields for k in ("0x15", "0x17"))
        if has_solar:
            print("\n=== Solar / UV ===")
            if "0x15" in fields:
                print(f"  Solar Radiation: {fields['0x15']}")
            if "0x17" in fields:
                print(f"  UV Index       : {fields['0x17']}")

    # Rainfall
    if "rain" in data and data["rain"]:
        print("\n=== Rainfall ===")
        rain_ids = {
            "0x0E": "Rate", "0x0D": "Event", "0x10": "Daily",
            "0x11": "Weekly", "0x12": "Monthly", "0x13": "Yearly",
            "0x14": "Total", "0x7C": "24 Hour"
        }
        for item in data["rain"]:
            label = rain_ids.get(item["id"], item["id"])
            print(f"  {label:12s}: {item.get('val', 'N/A')}")

    if "piezoRain" in data and data["piezoRain"]:
        print("\n=== Piezo Rainfall ===")
        for item in data["piezoRain"]:
            rain_ids = {
                "0x0E": "Rate", "0x0D": "Event", "0x10": "Daily",
                "0x11": "Weekly", "0x12": "Monthly", "0x13": "Yearly",
                "0x14": "Total", "0x7C": "24 Hour", "srain_piezo": "State"
            }
            label = rain_ids.get(item["id"], item["id"])
            print(f"  {label:12s}: {item.get('val', 'N/A')}")

    # Lightning
    if "lightning" in data and data["lightning"]:
        lt = data["lightning"][0]
        print("\n=== Lightning ===")
        print(f"  Distance    : {lt.get('distance', 'N/A')}")
        print(f"  Last Strike : {lt.get('timestamp', 'N/A')}")
        print(f"  Daily Count : {lt.get('count', 'N/A')}")

    # CO2 / AQI
    if "co2" in data and data["co2"]:
        co = data["co2"][0]
        print("\n=== Air Quality (CO2 Sensor) ===")
        print(f"  CO2          : {co.get('CO2', 'N/A')} ppm")
        print(f"  CO2 24H Avg  : {co.get('CO2_24H', 'N/A')} ppm")
        print(f"  PM2.5        : {co.get('PM25', 'N/A')} ug/m3")
        print(f"  PM10         : {co.get('PM10', 'N/A')} ug/m3")
        print(f"  Temperature  : {co.get('temp', 'N/A')} {temp_unit}")
        print(f"  Humidity     : {co.get('humidity', 'N/A')}")

    # Multi-channel sensors
    for section, label in [
        ("ch_aisle", "Temperature & Humidity Channels"),
        ("ch_soil", "Soil Moisture Channels"),
        ("ch_temp", "Temperature-Only Channels"),
        ("ch_leaf", "Leaf Wetness Channels"),
        ("ch_pm25", "PM2.5 Channels"),
        ("ch_leak", "Leak Detection Channels"),
        ("ch_lds", "Laser Distance Channels"),
        ("ch_ec", "Soil EC Channels"),
    ]:
        if section in data and data[section]:
            print(f"\n=== {label} ===")
            for item in data[section]:
                ch = item.get("channel", "?")
                name = item.get("name", "")
                prefix = f"  CH{ch}" + (f" ({name})" if name else "")
                parts = []
                for k, v in item.items():
                    if k not in ("channel", "name"):
                        parts.append(f"{k}={v}")
                print(f"{prefix}: {', '.join(parts)}")


SENSOR_TYPE_NAMES = {
    0: "WH69 Sensor Array",
    1: "WH68 Wind Sensor",
    2: "WH80 Sonic Array",
    3: "WH40 Rainfall Sensor",
    4: "WH25 Indoor T&RH&P",
    5: "WH26 Outdoor T&RH",
    6: "T&H CH1", 7: "T&H CH2", 8: "T&H CH3", 9: "T&H CH4",
    10: "T&H CH5", 11: "T&H CH6", 12: "T&H CH7", 13: "T&H CH8",
    14: "Soil CH1", 15: "Soil CH2", 16: "Soil CH3", 17: "Soil CH4",
    18: "Soil CH5", 19: "Soil CH6", 20: "Soil CH7", 21: "Soil CH8",
    22: "PM2.5 CH1", 23: "PM2.5 CH2", 24: "PM2.5 CH3", 25: "PM2.5 CH4",
    26: "WH57 Lightning Sensor",
    27: "Leak CH1", 28: "Leak CH2", 29: "Leak CH3", 30: "Leak CH4",
    31: "Temp CH1", 32: "Temp CH2", 33: "Temp CH3", 34: "Temp CH4",
    35: "Temp CH5", 36: "Temp CH6", 37: "Temp CH7", 38: "Temp CH8",
    39: "WH45 AQI Combo Sensor",
    40: "Leaf CH1", 41: "Leaf CH2", 42: "Leaf CH3", 43: "Leaf CH4",
    44: "Leaf CH5", 45: "Leaf CH6", 46: "Leaf CH7", 47: "Leaf CH8",
    48: "WH90 Haptic Array (7-in-1)",
    49: "WH85 Haptic 3-in-1",
    58: "Soil CH9", 59: "Soil CH10", 60: "Soil CH11", 61: "Soil CH12",
    62: "Soil CH13", 63: "Soil CH14", 64: "Soil CH15", 65: "Soil CH16",
    66: "LDS CH1", 67: "LDS CH2", 68: "LDS CH3", 69: "LDS CH4",
    70: "WN20 Rain Gauge Mini",
}


def format_battery(batt_val):
    """Convert battery level to a readable string."""
    try:
        level = int(batt_val)
        if 1 <= level <= 5:
            return f"{level}/5 ({level * 20}%)"
        elif level == 6:
            return "DC powered"
        return str(batt_val)
    except (ValueError, TypeError):
        return str(batt_val)


COMMON_LIST_IDS = {
    "0x02": "Temperature",
    "0x07": "Humidity",
    "0x03": "Dew Point",
    "0x0A": "Wind Direction",
    "0x0B": "Wind Speed",
    "0x0C": "Wind Gust",
    "0x15": "Solar Radiation",
    "0x17": "UV Index",
    "0x19": "Day Wind Max",
    "3": "Feels Like",
    "0x6D": "Wind Dir 10min Avg",
    "4": "Apparent Temp",
    "5": "VPD",
    "0xA1": "BGT",
    "0xA2": "WBGT",
}

RAIN_IDS = {
    "0x0D": "Event", "0x0E": "Rate", "0x10": "Daily",
    "0x11": "Weekly", "0x12": "Monthly", "0x13": "Yearly",
    "0x14": "Total", "0x7C": "24 Hour", "srain_piezo": "State",
}

# Map sensor types to the live data sections they provide
SENSOR_DATA_SECTIONS = {
    0: ["common_list:outdoor", "rain"],          # WH69 Sensor Array
    1: ["common_list:wind"],                      # WH68 Wind Sensor
    2: ["common_list:outdoor", "common_list:wind"],  # WH80 Sonic Array
    3: ["rain"],                                  # WH40 Rainfall Sensor
    4: ["wh25"],                                  # WH25 Indoor
    5: ["common_list:outdoor"],                   # WH26 Outdoor T&RH
    26: ["lightning"],                            # WH57 Lightning
    39: ["co2"],                                  # WH45 AQI Combo
    48: ["common_list:outdoor", "common_list:wind", "common_list:solar", "piezoRain"],  # WH90
    49: ["common_list:outdoor", "common_list:wind", "common_list:solar", "piezoRain"],  # WH85
    70: ["rain"],                                 # WN20 Rain Gauge Mini
}
# Channel sensors: type 6-13 → ch_aisle, 14-21 → ch_soil, 22-25 → ch_pm25,
# 27-30 → ch_leak, 31-38 → ch_temp, 40-47 → ch_leaf, 58-65 → ch_soil, 66-69 → ch_lds
for i in range(8):
    SENSOR_DATA_SECTIONS[6 + i] = [f"ch_aisle:CH{i+1}"]
    SENSOR_DATA_SECTIONS[40 + i] = [f"ch_leaf:CH{i+1}"]
    SENSOR_DATA_SECTIONS[31 + i] = [f"ch_temp:CH{i+1}"]
for i in range(8):
    SENSOR_DATA_SECTIONS[14 + i] = [f"ch_soil:CH{i+1}"]
for i in range(8):
    SENSOR_DATA_SECTIONS[58 + i] = [f"ch_soil:CH{i+9}"]
for i in range(4):
    SENSOR_DATA_SECTIONS[22 + i] = [f"ch_pm25:CH{i+1}"]
    SENSOR_DATA_SECTIONS[27 + i] = [f"ch_leak:CH{i+1}"]
    SENSOR_DATA_SECTIONS[66 + i] = [f"ch_lds:CH{i+1}"]


def get_live_readings(live_data, sensor_type):
    """Extract current readings relevant to a sensor type from live data."""
    readings = []
    sections = SENSOR_DATA_SECTIONS.get(sensor_type, [])

    for section in sections:
        if section == "wh25" and "wh25" in live_data and live_data["wh25"]:
            wh = live_data["wh25"][0]
            for key, label in [("intemp", "Indoor Temp"), ("inhumi", "Indoor Humidity"),
                               ("abs", "Abs Pressure"), ("rel", "Rel Pressure")]:
                if key in wh and wh[key] not in ("--", "", None):
                    readings.append(f"{label}: {wh[key]}")

        elif section.startswith("common_list") and "common_list" in live_data:
            subset = section.split(":")[1] if ":" in section else "all"
            outdoor_ids = {"0x02", "0x07", "0x03", "3", "4", "5", "0xA1", "0xA2"}
            wind_ids = {"0x0A", "0x0B", "0x0C", "0x19", "0x6D"}
            solar_ids = {"0x15", "0x17"}
            for item in live_data["common_list"]:
                item_id = item.get("id", "")
                val = item.get("val", "")
                if val in ("--", "", None):
                    continue
                if subset == "outdoor" and item_id not in outdoor_ids:
                    continue
                if subset == "wind" and item_id not in wind_ids:
                    continue
                if subset == "solar" and item_id not in solar_ids:
                    continue
                label = COMMON_LIST_IDS.get(item_id, item_id)
                readings.append(f"{label}: {val}")

        elif section in ("rain", "piezoRain") and section in live_data:
            for item in live_data[section]:
                val = item.get("val", "")
                if val in ("--", "", None):
                    continue
                label = RAIN_IDS.get(item.get("id", ""), item.get("id", ""))
                readings.append(f"Rain {label}: {val}")

        elif section == "lightning" and "lightning" in live_data and live_data["lightning"]:
            lt = live_data["lightning"][0]
            for key, label in [("distance", "Distance"), ("timestamp", "Last Strike"),
                               ("count", "Daily Count")]:
                if key in lt and lt[key] not in ("--", "", None):
                    readings.append(f"Lightning {label}: {lt[key]}")

        elif section == "co2" and "co2" in live_data and live_data["co2"]:
            co = live_data["co2"][0]
            for key, label in [("CO2", "CO2"), ("CO2_24H", "CO2 24H"), ("PM25", "PM2.5"),
                               ("PM10", "PM10"), ("temp", "Temp"), ("humidity", "Humidity")]:
                if key in co and co[key] not in ("--", "", None):
                    readings.append(f"{label}: {co[key]}")

        elif ":" in section:
            sec_name, ch_label = section.split(":", 1)
            if sec_name in live_data:
                ch_num = ch_label.replace("CH", "")
                for item in live_data[sec_name]:
                    if item.get("channel") == ch_num:
                        name = item.get("name", "")
                        for key, val in item.items():
                            if key not in ("channel", "name") and val not in ("--", "", None):
                                label = name if name else ch_label
                                readings.append(f"{label} {key}: {val}")

    return readings


def cmd_sensors(host, _args):
    """Show sensor battery/signal status and current readings."""
    live_data = api_get(host, "get_livedata_info")
    found = False
    for page in (1, 2):
        data = api_get(host, f"get_sensors_info?page={page}")
        if not data:
            continue
        for sensor in data:
            sid = sensor.get("id", "N/A")
            if sid in ("FFFFFFFF", "FFFFFFFE"):
                continue
            if not found:
                print("=== Connected Sensors ===\n")
                found = True
            stype_raw = sensor.get("type", "?")
            try:
                stype_int = int(stype_raw)
            except (ValueError, TypeError):
                stype_int = -1
            name = SENSOR_TYPE_NAMES.get(stype_int, f"Unknown (type {stype_raw})")
            batt = format_battery(sensor.get("batt", "N/A"))
            signal = sensor.get("signal", "N/A")
            rssi = sensor.get("rssi", "N/A")
            print(f"  {name}")
            print(f"    ID: {sid} | Battery: {batt} | Signal: {signal}/4 | RSSI: {rssi} dBm")
            readings = get_live_readings(live_data, stype_int)
            if readings:
                print(f"    Current readings:")
                for r in readings:
                    print(f"      {r}")
            print()
    if not found:
        print("No external sensors registered.")


def cmd_iot_list(host, _args):
    """List IoT devices."""
    data = api_get(host, "get_iot_device_list")
    if not data or "command" not in data:
        print("No IoT devices found.")
        return

    model_names = {1: "WFC01 (Water Timer)", 2: "AC1100 (Smart Plug)", 3: "WFC02 (Water Timer v2)"}
    devices = data["command"]
    if not devices:
        print("No IoT devices found.")
        return

    print(f"{'ID':>6s}  {'Model':>6s}  {'Type':<24s}  {'Name':<20s}  {'Online':<8s}  {'Running':<8s}")
    print("-" * 100)
    for dev in devices:
        dev_id = dev.get("id", "?")
        model = dev.get("model", "?")
        model_name = model_names.get(model, f"Unknown ({model})")
        nickname = dev.get("nickname", "N/A")
        rfnet = "Yes" if dev.get("rfnet_state") == 1 else "No"
        running_key = {1: "water_running", 2: "ac_running", 3: "water_running"}.get(model, "")
        running = "Yes" if dev.get(running_key) == 1 else "No"
        print(f"{dev_id:>6}  {model:>6}  {model_name:<24s}  {nickname:<20s}  {rfnet:<8s}  {running:<8s}")


def cmd_iot_switch(host, args):
    """Switch an IoT device on or off."""
    iot_id = int(args.id)
    iot_model = int(args.model)
    state = 1 if args.state.lower() == "on" else 0

    if state == 0:
        cmd = {"cmd": "quick_stop", "id": iot_id, "model": iot_model}
    else:
        if iot_model == 3:
            cmd = {
                "position": 100, "always_on": 1, "val_type": 1,
                "val": 0, "cmd": "quick_run", "id": iot_id, "model": iot_model
            }
        else:
            cmd = {
                "on_type": 0, "off_type": 0, "always_on": 1,
                "on_time": 0, "off_time": 0, "val_type": 1,
                "val": 0, "cmd": "quick_run", "id": iot_id, "model": iot_model
            }

    payload = {"command": [cmd]}
    result = api_post(host, "parse_quick_cmd_iot", payload)
    action = "ON" if state else "OFF"
    print(f"Sent {action} command to device {iot_id} (model {iot_model})")
    if result:
        print(f"Response: {json.dumps(result, indent=2)}")


def cmd_iot_read(host, args):
    """Read current status of a specific IoT device."""
    iot_id = int(args.id)
    iot_model = int(args.model)

    payload = {"command": [{"cmd": "read_device", "id": iot_id, "model": iot_model}]}
    result = api_post(host, "parse_quick_cmd_iot", payload)
    print(json.dumps(result, indent=2))


SD_DATA_PORT = 81


def cmd_history(host, args):
    """Show SD card info and optionally download historical data."""
    data = api_get(host, "get_sdmmc_info")
    if not data or "info" not in data:
        print("No SD card detected.")
        return

    info = data["info"]
    files = data.get("file_list", [])

    print(f"=== SD Card ===")
    print(f"  Name     : {info.get('Name', 'N/A')}")
    print(f"  Type     : {info.get('Type', 'N/A')}")
    print(f"  Size     : {info.get('Size', 'N/A')}")
    print(f"  Speed    : {info.get('Speed', 'N/A')}")
    print(f"  Interval : {info.get('Interval', 'N/A')} minutes")
    print(f"\n=== CSV Files ({len(files)}) ===")
    print(f"  {'File Name':<35s}  {'Size':>8s}")
    print(f"  {'-'*35}  {'-'*8}")
    for f in files:
        print(f"  {f['name']:<35s}  {f['size']:>8s}")

    print(f"\n  Download URL: http://{host}:{SD_DATA_PORT}/<filename>")


def cmd_history_download(host, args):
    """Download a CSV file from the SD card."""
    filename = args.filename

    # If 'all', download everything
    if filename == "all":
        data = api_get(host, "get_sdmmc_info")
        files = [f["name"] for f in data.get("file_list", [])]
    else:
        files = [filename]

    outdir = Path(args.output) if args.output else Path(".")
    outdir.mkdir(parents=True, exist_ok=True)

    for fname in files:
        url = f"http://{host}:{SD_DATA_PORT}/{fname}"
        print(f"  Downloading {fname}...", end=" ", flush=True)
        try:
            with urlopen(url, timeout=60) as resp:
                content = resp.read()
            outpath = outdir / fname
            outpath.write_bytes(content)
            print(f"OK ({len(content)} bytes -> {outpath})")
        except (HTTPError, URLError) as e:
            print(f"FAILED: {e}")


def cmd_raw(host, args):
    """Make a raw GET request to any endpoint."""
    data = api_get(host, args.endpoint)
    print(json.dumps(data, indent=2))


def cmd_configure(host, args):
    """Save the device IP address."""
    save_host(args.ip)
    print(f"Saved device IP: {args.ip}")
    # Verify connectivity
    try:
        ver = api_get(args.ip, "get_version")
        print(f"Connected successfully. Firmware: {ver.get('version', 'N/A')}")
    except SystemExit:
        print("Warning: Could not connect to device. IP saved anyway.", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Control Ecowitt weather station gateways via local HTTP API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s configure 192.168.1.100       Set device IP
  %(prog)s info                          Show device information
  %(prog)s weather                       Show current weather
  %(prog)s sensors                       Show sensor battery/signal status
  %(prog)s history list                  Show SD card files
  %(prog)s history download 202601A.csv  Download a CSV file
  %(prog)s history download all -o data  Download all files to data/
  %(prog)s iot list                      List IoT devices
  %(prog)s iot switch 1753 1 on          Turn on IoT device
  %(prog)s raw get_livedata_info         Raw API call

Environment:
  ECOWITT_HOST    Device IP address (overrides saved config)
"""
    )
    parser.add_argument("--host", help="Device IP (overrides env/config)")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("info", help="Show device information")
    sub.add_parser("weather", help="Show current weather readings")
    sub.add_parser("sensors", help="Show sensor battery/signal status")

    # History / SD card subcommands
    hist_parser = sub.add_parser("history", help="SD card historical data")
    hist_sub = hist_parser.add_subparsers(dest="hist_command")

    hist_sub.add_parser("list", help="List SD card info and CSV files")

    dl_p = hist_sub.add_parser("download", help="Download CSV file(s) from SD card")
    dl_p.add_argument("filename", help="CSV filename to download, or 'all' for everything")
    dl_p.add_argument("-o", "--output", help="Output directory (default: current dir)")

    # IoT subcommands
    iot_parser = sub.add_parser("iot", help="IoT device management")
    iot_sub = iot_parser.add_subparsers(dest="iot_command")

    iot_sub.add_parser("list", help="List IoT devices")

    switch_p = iot_sub.add_parser("switch", help="Turn IoT device on/off")
    switch_p.add_argument("id", help="Device ID")
    switch_p.add_argument("model", help="Device model number (1=WFC01, 2=AC1100, 3=WFC02)")
    switch_p.add_argument("state", choices=["on", "off"], help="Desired state")

    read_p = iot_sub.add_parser("read", help="Read IoT device status")
    read_p.add_argument("id", help="Device ID")
    read_p.add_argument("model", help="Device model number")

    # Raw endpoint access
    raw_p = sub.add_parser("raw", help="Raw GET request to device endpoint")
    raw_p.add_argument("endpoint", help="API endpoint (e.g. get_livedata_info)")

    # Configure
    conf_p = sub.add_parser("configure", help="Save device IP address")
    conf_p.add_argument("ip", help="Device IP address")

    args = parser.parse_args()

    if args.command == "configure":
        cmd_configure(None, args)
        return

    host = args.host or get_host()
    if not host:
        print("No device IP configured. Use one of:", file=sys.stderr)
        print("  ecowitt_cli.py configure <IP>", file=sys.stderr)
        print("  ecowitt_cli.py --host <IP> <command>", file=sys.stderr)
        print("  export ECOWITT_HOST=<IP>", file=sys.stderr)
        sys.exit(1)

    commands = {
        "info": cmd_info,
        "weather": cmd_weather,
        "sensors": cmd_sensors,
        "raw": cmd_raw,
    }

    if args.command == "iot":
        if args.iot_command == "list":
            cmd_iot_list(host, args)
        elif args.iot_command == "switch":
            cmd_iot_switch(host, args)
        elif args.iot_command == "read":
            cmd_iot_read(host, args)
        else:
            iot_parser.print_help()
    elif args.command == "history":
        if args.hist_command == "download":
            cmd_history_download(host, args)
        else:
            cmd_history(host, args)
    elif args.command in commands:
        commands[args.command](host, args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
