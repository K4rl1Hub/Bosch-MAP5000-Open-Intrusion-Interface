
from homeassistant.components.alarm_control_panel import AlarmControlPanelEntity
from homeassistant.components.alarm_control_panel.const import AlarmControlPanelEntityFeature
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from .const import (DOMAIN, CONF_ARM_DELAY, CONF_BYPASS_OFF_NORMAL_DEVICES, DEFAULT_BYPASS_OFF_NORMAL_DEVICES)

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coord = data["coordinator"]
    client = data["client"]
    reg = data["registry"]

    area_siid = entry.data.get("area_siid") or await client.first_area_siid()
    if not area_siid:
        area_siid = await client.first_area_siid()
    panel = MapAlarmPanel(coord, entry, client, area_siid)
    async_add_entities([panel])


    #last_area = reg.get_last_resource(area_siid)
    #if last_area is not None:
    resource = await client.load_panel_config(area_siid)
    if resource is None:
        resource = {"resource": area_siid}
    panel._on_update(area_siid, resource)

class MapAlarmPanel(AlarmControlPanelEntity):
    _attr_code_arm_required=False
    _attr_code_format=None
    _attr_supported_features = ( AlarmControlPanelEntityFeature.ARM_AWAY )

    def __init__(self, coord, entry, client, area_siid: str):
        self._coord=coord; self._client=client; self._siid=area_siid
        self._state="disarmed"
        self._entry=entry
        self._device_info = DeviceInfo(identifiers={(DOMAIN, "map5000")}, manufacturer="Bosch", model="MAP5000", name="MAP5000")
        coord.reg.async_add_listener(self._on_update)

    @property
    def device_info(self): return self._device_info
    @property
    def state(self): return self._state
    @property
    def name(self):  return "MAP5000 Alarm Panel"
    @property
    def unique_id(self): return f"{DOMAIN}_alarm_{self._siid}"
    @property
    def extra_state_attributes(self): return getattr(self, "_attrs", {})


    @callback
    def _on_update(self, siid, payload):
        res = payload or {}
        if "resource" in payload:
            res = payload.get("resource")
            
        self_link = res.get("@self", "")

        self._attrs = getattr(self, "_attrs", {})
        self._attrs["siid"] = self._siid
        self_link = res.get("@self")
        if isinstance(self_link, str):
            self._attrs["sid"] = self_link.split("/")[-1]
        else:
            self._attrs["sid"] = self._siid

        if "oiiArmable" in res:
            self._attrs["oiiArmable"] = res.get("oiiArmable")
        if "readyToArm" in res:
            self._attrs["readyToArm"] = res.get("readyToArm")
        if "readyToDisarm" in res:
            self._attrs["readyToDisarm"] = res.get("readyToDisarm")
        if "numberOfBypassedDevices" in res:
            self._attrs["numberOfBypassedDevices"] = res.get("numberOfBypassedDevices")

        self_link=res.get("@self","")
        # incidents: /inc/<AreaSIID>/<id>
        if isinstance(self_link,str) and self_link.startswith("/inc/"):
            parts=self_link.split("/")
            if len(parts)>=3 and parts[2]==self._siid:
                if payload.get("etype")=="CREATED":
                    self._state="triggered"
                elif payload.get("etype")=="DELETED":
                    pass
                self.async_write_ha_state()
                return
        # area state
        if siid==self._siid or (isinstance(self_link,str) and self_link.endswith(self._siid)):
            armed = res.get("armed")
            if armed is True: 
                self._state="armed_away"
            elif armed is False: 
                self._state="disarmed"
            self.async_write_ha_state()

    async def async_alarm_disarm(self, code=None):
        payload = {"@cmd": "DISARM"}
        await self._client.post(f"/{self._siid}", payload)

    async def async_alarm_arm_away(self, code=None):
        self._state="arming"
        self.async_write_ha_state()

        try:
            bypassOffNormalDevices = self._entry.options.get(
                                        CONF_BYPASS_OFF_NORMAL_DEVICES,
                                        DEFAULT_BYPASS_OFF_NORMAL_DEVICES,
                                    )
            arm_delay = self._entry.options.get(CONF_ARM_DELAY, "ZERO")

            payload = {
                "@cmd":"ARM", 
                "bypassOffNormalDevices": bypassOffNormalDevices, 
                "exitDelay": arm_delay
            }
            await self._client.post(f"/{self._siid}", payload)
        except Exception as e:
            self._state="disarmed"
            self.async_write_ha_state()
            raise e
