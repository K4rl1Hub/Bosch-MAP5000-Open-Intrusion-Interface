
from __future__ import annotations

from typing import Optional, Tuple

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.components.logbook.const import EVENT_LOGBOOK_ENTRY

from .const import DOMAIN
from .coordinator import OIICoordinator, MapRegistry, DeviceEntry

# Kanonische Zustände (enum)
_STATE_OPTIONS = ["idle", "login", "logout", "arm", "disarm", "keypress", "other"]

def _normalize_function(func: Optional[str]) -> str:
    """Mappe OII 'function' (LOGIN/LOGOUT/ARM/DISARM/KEYPRESS/...) auf kanonische, kleingeschriebene Enum-Zustände."""
    if not func or not isinstance(func, str):
        return "idle"
    f = func.strip().lower()
    if f == "login":
        return "login"
    if f == "logout":
        return "logout"
    if f == "arm":
        return "arm"
    if f == "disarm":
        return "disarm"
    if f == "keypress":
        return "keypress"
    # Unbekannt → "other"
    return "other"

def _get(res: dict, *keys):
    for k in keys:
        if k in res:
            return res[k]
    return None


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coord: OIICoordinator = data["coordinator"]
    reg: MapRegistry = data["registry"]

    entities = []
    for siid, dev in reg.devices.items():
        # Keypads als Sensor anlegen (deviceConfiguration.type == "KEYPAD")
        if isinstance(dev.type, str) and dev.type.upper().startswith("KEYPAD"):
            entities.append(MapKeypadSensor(coord, reg, dev))

    async_add_entities(entities)


class MapKeypadSensor(SensorEntity):
    """Sensor für Keypad-Events (UserId, Login/Logout/Arm/Disarm/Keypress etc.)."""

    # ENUM-Sensor (HA ≥ 2023.8)
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = _STATE_OPTIONS

    def __init__(self, coord: OIICoordinator, reg: MapRegistry, dev: DeviceEntry):
        self._coord = coord
        self._reg = reg
        self._dev = dev

        self._state: str = "idle"
        self._attrs: dict = {}
        self._last_logged_signature: Optional[Tuple[str, Optional[int], Optional[str], Optional[str]]] = None
        # (function_norm, userId, result, time) → Duplikatvermeidung im Logbuch

        self._attr_unique_id = f"{DOMAIN}_keypad_{dev.siid}"
        self._attr_name = dev.name or dev.siid
        self._device_info = DeviceInfo(
            identifiers={(DOMAIN, "map5000")},
            manufacturer="Bosch",
            model="MAP5000",
            name="MAP5000",
        )

        reg.async_add_listener(self._on_update)

    # ---- HA basics ----
    @property
    def device_info(self) -> DeviceInfo:
        return self._device_info

    @property
    def native_value(self) -> str:
        return self._state

    @property
    def extra_state_attributes(self) -> dict:
        return self._attrs

    @property
    def icon(self) -> str:
        # Etwas UI-Feedback: je nach Zustand anderes Icon
        match self._state:
            case "login":
                return "mdi:account-key"
            case "logout":
                return "mdi:account-off"
            case "arm":
                return "mdi:shield-check"
            case "disarm":
                return "mdi:shield-off"
            case "keypress":
                return "mdi:dialpad"
            case "other":
                return "mdi:information-outline"
            case _:
                return "mdi:security"

    # ---- Event Callback from Coordinator ----
    @callback
    def _on_update(self, siid: str, payload: dict):
        if siid != self._dev.siid:
            return

        res = payload.get("resource") or {}
        # etype might be useful ("CREATED"/"CHANGED"/"DELETED")
        etype = payload.get("etype")

        # base ids
        self._attrs["siid"] = self._dev.siid
        self_link = res.get("@self", "")
        self._attrs["sid"] = self_link.split("/")[-1] if isinstance(self_link, str) and self_link.startswith("/") else self._dev.siid

        # Keypad event data
        user_id   = _get(res, "userID", "userId", "UserID", "UserId")
        activated = _get(res, "activated", "Activated")     # true or false
        #user_name = res.get("userName")    # not provided by OII API; derive from userId if needed
        #result    = res.get("result")      # not provided by OII API
        #timeval   = res.get("time")        # not provided by OII API

        # Attribute setzen (nur wenn vorhanden)
        if user_id   is not None: self._attrs["userId"]   = str(user_id)
        if activated is not None: self._attrs["activated"] = bool(activated)
        #if user_name is not None: self._attrs["userName"] = user_name
        #if function  is not None: self._attrs["function"] = function
        #if result    is not None: self._attrs["result"]   = result
        #if timeval   is not None: self._attrs["time"]     = timeval

        # determine new state from activated / user_id data
        if activated is True and user_id not in (None, "", "0"):
            new_state = "login"
        elif activated is False and self._state == "login" and self._prev_uid not in (None, "", "0"):
            new_state = "logout"
        else:
            new_state = "idle"

        self._state = new_state
        if user_id is not None:
            self._prev_uid = str(user_id)


        self.async_write_ha_state()

        # Logbuch-Eintrag (Duplikate vermeiden)
        #sig = (self._state, user_id, result, timeval)
        #if self._state != "idle" and sig != self._last_logged_signature:
        #    self._last_logged_signature = sig
        #    self._log_to_logbook(self._state, user_id, user_name, result, timeval)

        # Fire HA Event (disabled for now; not yet needed)
        # self.hass.bus.fire(
        #     "map5000_keypad_event",
        #     {"entity_id": self.entity_id, "siid": self._dev.siid, "state": self._state,
        #     "userId": user_id, "userName": user_name, "result": result, "time": timeval}
        # )


    # ---- Logbuch ----
    def _log_to_logbook(
        self,
        state: str,
        user_id: Optional[int],
        user_name: Optional[str],
        result: Optional[str],
        timeval: Optional[str],
    ) -> None:
        """Schreibt einen Logbuch-Eintrag für das Keypad-Event."""
        who = (str(user_name).strip() if user_name else f"UserId {user_id}" if user_id is not None else "Unbekannter Benutzer")
        res_txt = f" ({result})" if result else ""
        when_txt = f" um {timeval}" if timeval else ""

        # Schöne, übersichtliche Nachricht
        # Beispiel: "Max Mustermann → login (SUCCESS) um 2025-01-12T21:35:31"
        message = f"{who} → {state}{res_txt}{when_txt}"

        self.hass.bus.fire(
            EVENT_LOGBOOK_ENTRY,
            {
                "name": f"Keypad {self.name}",
                "message": message,
                "domain": DOMAIN,
                "entity_id": self.entity_id,
            },
        )
