# Bosch MAP5000 – Home Assistant Integration

## Native Open Intrusion Interface (OII) Integration – No MQTT Required

This Home Assistant integration connects the **Bosch MAP5000** intrusion detection system natively via the **Open Intrusion Interface (OII)**. No MQTT bridge, no external proxy services, and no additional middleware are required.

The integration provides real-time synchronization of sensors, outputs, keypads, and alarm status — including detailed **user login/logout/arming/disarming events** from MAP5000 keypads.

---

# 🚀 Features

## ✔ Native OII Communication
The integration uses only official MAP5000 OII endpoints:
- `/config`
- `/devices`
- `/points`
- `/areas`
- `/inc/*`
- `/sub` (Subscriptions)
- `FETCHEVENTS`
- OII Commands: `ARM`, `DISARM`, `ON`, `OFF`

Advantages:
- No MQTT or third-party services
- Secure HTTP Digest authentication
- Real-time updates
- Full transparency and reliability

---

# 📡 Entities Provided

## 🔵 Binary Sensors
The integration automatically detects the following MAP5000 device types:

| MAP5000 Type | HA Device Class | Description |
|--------------|------------------|-------------|
| `POINT.LSNEXPANDER` | door / window / opening | Contacts (doors, windows, magnetic switches) |
| `POINT.PIR` | motion | Motion detectors |
| `POINT.TAMPER` | tamper | Tamper switches |
| `POWERSUPPLY` | power | Power supply state |
| `BATTERY` | battery | Battery condition |
| `BATTERYCHARGER` | battery_charging | Charger state |

### Dynamic Door/Window Classification
For `POINT.LSNEXPANDER`, the entity name is analyzed:
- contains **"Tür"** → `door`
- contains **"Fenster"** → `window`
- otherwise → `opening`

### Extended Attributes
Binary sensors expose additional MAP5000-specific fields:
- `bypassable` *(from /config)*
- `partOfWalktest` *(from /config)*
- `bypassed` *(from /devices)*
- `siid`
- `sid`

---

## 🟢 Switches (Outputs)
All `OUTPUT.*` devices are mapped to switch entities:

- State from `on: true|false`
- Availability from `opState` + `enabled`
- Switching via:
  ```json
  {"@cmd": "ON"}
  ```
  and
  ```json
  {"@cmd": "OFF"}
  ```

Examples:
- Siren
- Strobe light
- LEDs
- Relay outputs
- Keypad internal beeper

---

## 🟣 Keypads as ENUM Sensors
Every MAP5000 keypad appears as a **sensor with well-defined ENUM states**.

### Supported States
```
idle
login
logout
arm
disarm
keypress
other
```

### Attributes
Keypad sensors expose:
- `userId`
- `userName`
- `function` (raw OII field)
- `result`
- `time`
- `siid`
- `sid`

### Logbook Integration
Each keypad event generates a Home Assistant logbook entry:
```
Max Mustermann → login (SUCCESS) at 2025-01-12T21:35:31
```
This enables:
- Tracking user actions
- Detecting who armed/disarmed the alarm
- Logging keypad access events

---

## 🔴 Alarm Control Panel
The integration exposes the MAP5000 area as a native `alarm_control_panel`.

### Supported Actions
- `arm_home`
- `arm_away` (maps to OII ARM)
- `disarm`

### States
- `armed_home`
- `armed_away`
- `disarmed`
- `triggered`

Alarm triggers are reported via `/inc/*` events.

---

# ⚙ Installation

1. Copy the directory:
   ```
   custom_components/map5000/
   ```
   into your Home Assistant configuration folder:
   ```
   /config/custom_components/map5000/
   ```

2. Restart Home Assistant.

3. Add the integration via:
   **Settings → Devices & Services → Add Integration → “Bosch MAP5000”**

---

# 🔧 Configuration
All configuration is performed in the Home Assistant UI.

## `include_types`
Comma-separated list, e.g.:
```
POINT.LSNEXPANDER,POINT.PIR,POINT.TAMPER,OUTPUT.,KEYPAD
```

## `exclude_types`
Comma-separated list:
```
SYSTEM.,SUPERV.
```

## `type_mapping`
JSON object allowing overrides for device_class and state logic.

## `output_mapping`
JSON object for customizing OII output commands, e.g.:
```json
{
  "OUTPUT.SIREN": {
    "state_property": "on",
    "turn_on": {"@cmd": "ON"},
    "turn_off": {"@cmd": "OFF"}
  }
}
```

---

# 🧪 Example Automations

### Notify on Keypad Login
```yaml
trigger:
  - platform: state
    entity_id: sensor.keypad_eg
    to: "login"
action:
  - service: notify.mobile_app
    data:
      message: "{{ state_attr('sensor.keypad_eg','userName') }} logged in at the keypad."
```

### Log Arming Event
```yaml
trigger:
  - platform: state
    entity_id: sensor.keypad_eg
    to: "arm"
action:
  - service: logbook.log
    data:
      name: "MAP5000"
      message: "System armed by {{ state_attr('sensor.keypad_eg','userName') }}."
```

---

# 🔍 Architecture & Internals
- Fully async (httpx)
- Digest authentication
- Subscription loop separate from setup (no HA bootstrap blocking)
- Initial state snapshot using coordinator cache
- Platforms:
  - `binary_sensor`
  - `switch`
  - `sensor`
  - `alarm_control_panel`

---

# ❤️ Support & Contributions
Issues and Pull Requests are welcome.
This project evolves with community feedback.
