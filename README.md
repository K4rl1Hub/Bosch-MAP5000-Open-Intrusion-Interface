
# Home Assistant — Bosch MAP500 Integration

A comprehensive guide to install, configure, and operate the **Bosch MAP500** integration in Home Assistant. This README covers prerequisites, installation methods (HACS and manual), configuration options, entity model, automations, troubleshooting, and contribution guidelines.

> ⚠️ **Note**: The MAP500 ecosystem can vary by region and firmware. This integration targets the Bosch **MAP500 gateway** used to expose devices (e.g., HVAC/boiler/thermostat sensors/actuators) to Home Assistant. Adapt entity names and endpoints to your deployment.

---

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Option A: HACS](#option-a-hacs)
  - [Option B: Manual](#option-b-manual)
- [Configuration](#configuration)
  - [Basic Setup](#basic-setup)
  - [Advanced Options](#advanced-options)
- [Entity Model](#entity-model)
- [Usage Examples](#usage-examples)
  - [Dashboards](#dashboards)
  - [Automations](#automations)
- [Troubleshooting](#troubleshooting)
- [Known Limitations](#known-limitations)
- [Security Considerations](#security-considerations)
- [Development](#development)
- [Contributing](#contributing)
- [Versioning & Changelog](#versioning--changelog)
- [License](#license)

---

## Overview

**Bosch MAP500 Integration** bridges your Bosch **MAP500 gateway** into Home Assistant (HA), exposing sensors, binary sensors, and controls for compatible devices (e.g., boilers/HVAC zones, temperature setpoints, operating modes, fault codes).

**Goals:**
- Reliable local polling/subscribe to MAP500 endpoints
- Clean entity model aligned with Home Assistant best practices
- Minimal configuration with sensible defaults

## Features
- ✅ Auto-discovery of devices attached to the MAP500 gateway
- ✅ Sensor entities (e.g., temperatures, pressures, energy, states)
- ✅ Binary sensors (e.g., faults, connectivity, burner state)
- ✅ Controls (e.g., set heating mode, setpoint)
- ✅ Device Info, unique IDs, area assignment
- ✅ Configurable polling interval & timeout
- ✅ Optional debug logging

> Add/remove bullets to reflect actual capabilities in your build.

## Prerequisites
- **Home Assistant** 2023.12+ (recommended)
- **Bosch MAP500 Gateway** on the same network
- Network access from HA to MAP500 (TCP/HTTP/HTTPS depending on your implementation)
- Credentials or token if MAP500 requires authentication
- Python 3.11+ inside HA environment (for custom integrations)

## Installation

### Option A: HACS
1. Open **HACS** → **Integrations** → **⋮** → **Custom repositories**
2. Add your repository URL: `https://github.com/<your-org>/<your-repo>` with category **Integration**
3. Search for **Bosch MAP500** in HACS and **Install**
4. **Restart** Home Assistant

### Option B: Manual
1. Copy the `custom_components/bosch_map500/` folder into your HA config directory
   - Path: `<config>/custom_components/bosch_map500/`
2. Ensure `manifest.json`, `__init__.py`, `config_flow.py` (if using UI), and platform files `sensor.py`, `binary_sensor.py`, `climate.py` (as applicable) are present
3. **Restart** Home Assistant

## Configuration

### Basic Setup
There are two recommended configuration flows.

#### UI (Config Flow)
- Go to **Settings → Devices & Services → Add Integration**
- Search for **Bosch MAP500**
- Enter **Host**, **Port**, and **Credentials/Token**
- Optional: **Poll interval**, **Timeout**, **SSL verify**

#### YAML (if you prefer static config)
Add to `configuration.yaml`:

```yaml
bosch_map500:
  host: 192.168.1.50
  port: 443
  ssl: true
  verify_ssl: true
  username: !secret bosch_map500_user
  password: !secret bosch_map500_pass
  poll_interval: 30  # seconds
  request_timeout: 10 # seconds
  device_whitelist:
    - zone_living
    - zone_bedroom
  entity_prefix: "MAP500"
  enable_fault_entities: true
  debug: false
```

> Remove or rename keys to match your integration implementation.

### Advanced Options
- **Device Filtering**: `device_whitelist` or `device_blacklist`
- **Entity Naming**: `entity_prefix` for consistent naming
- **SSL**: toggle `ssl`/`verify_ssl` for self-signed certs
- **Logging**: set `debug: true`, then check `home-assistant.log`

## Entity Model

> Adjust to reflect your code. This section helps users understand the mapping.

### Sensors
- `sensor.map500_outdoor_temperature`
- `sensor.map500_supply_temperature`
- `sensor.map500_return_temperature`
- `sensor.map500_pressure`
- `sensor.map500_energy_consumption_daily`

### Binary Sensors
- `binary_sensor.map500_burner_active`
- `binary_sensor.map500_fault`
- `binary_sensor.map500_gateway_online`

### Climate (if supported)
- `climate.map500_zone_<name>` — supports `hvac_modes: [heat, auto, off]` and `target_temperature`

### Diagnostics
- `sensor.map500_firmware_version`
- `sensor.map500_last_update`

## Usage Examples

### Dashboards
Add a `thermostat` card for a climate entity:

```yaml
type: thermostat
entity: climate.map500_zone_living
name: Living Room
```

Display multiple sensors in an entities card:

```yaml
type: entities
title: MAP500 Overview
entities:
  - sensor.map500_outdoor_temperature
  - sensor.map500_supply_temperature
  - sensor.map500_return_temperature
  - sensor.map500_pressure
  - binary_sensor.map500_fault
```

### Automations
Turn off heating when a window is open:

```yaml
alias: MAP500 — Pause heating when window open
trigger:
  - platform: state
    entity_id: binary_sensor.living_window
    to: 'on'
condition: []
action:
  - service: climate.set_hvac_mode
    target:
      entity_id: climate.map500_zone_living
    data:
      hvac_mode: 'off'
mode: single
```

Raise an alert on faults:

```yaml
alias: MAP500 — Fault alert
trigger:
  - platform: state
    entity_id: binary_sensor.map500_fault
    to: 'on'
action:
  - service: notify.mobile_app_michael_phone
    data:
      title: "Bosch MAP500 Fault"
      message: "A fault has been reported by the gateway. Check diagnostics."
mode: single
```

## Troubleshooting
- **Integration not discovered**: Verify files are under `custom_components/bosch_map500/` and restart HA.
- **Cannot connect**: Check network reachability (`ping`), correct `host`/`port`, and whether MAP500 requires HTTPS.
- **Auth errors**: Confirm credentials or token; try `verify_ssl: false` temporarily if using self-signed.
- **Missing entities**: Enable debug, check logs, and review device whitelist/blacklist.
- **Slow updates**: Increase `poll_interval`; ensure gateway isn’t rate-limiting.
- **Fault entity always on**: Inspect raw API payloads; map to proper state logic.

Enable debug logging:

```yaml
logger:
  default: warning
  logs:
    custom_components.bosch_map500: debug
```

## Known Limitations
- MAP500 API/version differences across regions/firmware
- Limited write operations depending on device capabilities
- No cloud control; local network only (unless you implement cloud fallback)

## Security Considerations
- Prefer local-only access; avoid exposing MAP500 to WAN
- Use strong credentials; rotate tokens
- If enabling remote access, require TLS and proper certificates

## Development

### Project Structure (example)
```
custom_components/bosch_map500/
├── __init__.py
├── manifest.json
├── config_flow.py
├── api.py
├── sensor.py
├── binary_sensor.py
├── climate.py
├── diagnostics.py
└── translations/
```

### Local Dev
- Use **Developer Tools → Reload** for quick iteration
- Run HA in a dev container; mount `custom_components`
- Write unit tests for entity state mapping and error handling

### Coding Guidelines
- Follow HA platform/entity conventions
- Use `DataUpdateCoordinator` for polling
- Provide `device_info` and stable `unique_id`

## Contributing
Pull requests are welcome! Please:
- Open an issue describing the change/bug
- Include test coverage where feasible
- Keep docs and examples updated

## Versioning & Changelog
This project uses **Semantic Versioning**. Track changes in `CHANGELOG.md`.

## License
MIT (or your preferred license). Include `LICENSE` in the repo.

---

### Support
- Create an issue on GitHub: `https://github.com/<your-org>/<your-repo>/issues`
- Share logs and configuration (redact secrets)

