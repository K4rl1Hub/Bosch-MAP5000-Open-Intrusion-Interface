
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from .const import (
    DOMAIN,
    CONF_BYPASS_OFF_NORMAL_DEVICES,
    DEFAULT_BYPASS_OFF_NORMAL_DEVICES,
)

from .coordinator import OIICoordinator, MapRegistry, DeviceEntry

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coord: OIICoordinator = data["coordinator"]
    reg: MapRegistry = data["registry"]
    client = data["client"]

    ents=[]
    for siid, dev in reg.devices.items():
        if dev.type.startswith("OUTPUT."):
            ents.append(MapOutputSwitch(coord, reg, client, dev))
        if dev.type.startswith("POINT."):
            if dev.bypassable is not None and dev.bypassable:
                ents.append(MapSensorBypassSwitch(coord, reg, client, dev))
    async_add_entities(ents)

    for ent in ents:
        last = reg.get_last_resource(ent._dev.siid)
        if last is not None:
            ent._on_update(ent._dev.siid, {"resource": last})

    panel = runtime.panel 
    async_add_entities([
        MapBypassOffNormalDevicesSwitch(hass, entry, panel)
    ])


class MapOutputSwitch(SwitchEntity):
    
    def __init__(self, coord: OIICoordinator, reg: MapRegistry, client, dev: DeviceEntry):
        self._coord=coord 
        self._reg=reg 
        self._client=client 
        self._dev=dev
        self._is_on=None
        self._attrs={}
        self._mapping = reg.map_output(dev.type)
        self._attr_unique_id=f"{DOMAIN}_out_{dev.siid}"
        self._attr_name=dev.name or dev.siid
        self._attr_available=True
        self._device_info = DeviceInfo(identifiers={(DOMAIN, "map5000")}, manufacturer="Bosch", model="MAP5000", name="MAP5000")

        reg.async_add_listener(self._on_update)

    @property
    def device_info(self): return self._device_info
    @property
    def is_on(self): return self._is_on
    @property
    def extra_state_attributes(self): return self._attrs

    @callback
    def _on_update(self, siid, payload):
        if siid!=self._dev.siid: 
            return
        res=payload.get("resource", {}) or {}

        self._attrs["siid"] = self._dev.siid
        self_link = res.get("@self")
        if isinstance(self_link, str):
            self._attrs["sid"] = self_link.split("/")[-1]
        else:
            self._attrs["sid"] = self._dev.siid

        # availability
        self._attr_available = (res.get("opState") == "OK") and bool(res.get("enabled", True))
        val=self._reg.state_of(self._dev, res, self._mapping)
        if val is not None:
            self._is_on = bool(val)
        for k in ("opState","enabled","incs","name"):
            if k in res: self._attrs[k]=res[k]
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        body = self._mapping.get("turn_on", {"@cmd":"ON"})
        await self._client.post(f"/{self._dev.siid}", body)
        try:
            res = await self._client.get(f"/{self._dev.siid}")
            self._on_update(self._dev.siid, {"resource": res})
        except Exception:
            pass

    async def async_turn_off(self, **kwargs):
        body = self._mapping.get("turn_off", {"@cmd":"OFF"})
        await self._client.post(f"/{self._dev.siid}", body)
        try:
            res = await self._client.get(f"/{self._dev.siid}")
            self._on_update(self._dev.siid, {"resource": res})
        except Exception:
            pass


class MapBypassOffNormalDevicesSwitch(SwitchEntity):
    """Config switch: bypass all off-normal devices before arming."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:shield-check"

    #def __init__(self, hass: HomeAssistant, entry: ConfigEntry, panel) -> None:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry = entry
        #self._panel = panel

        # Name wird in Kombination mit Device-Name dargestellt (has_entity_name)
        self._attr_name = "Bypass off-normal devices"

        # Stabiler unique_id
        #panel_id = getattr(panel, "panel_id", entry.unique_id or entry.entry_id)
        self._attr_unique_id = f"bypass_off_normal_devices"

        # Device-Zuordnung: dieses Switch-Entity soll am Panel-Device hängen
        """ self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"panel_{panel_id}")},
            manufacturer="Bosch",
            model="MAP 5000",
            name=getattr(panel, "name", "Bosch MAP5000"),
            configuration_url=f"http://{getattr(panel, 'host', '')}",
        ) """
        self._device_info = DeviceInfo(identifiers={(DOMAIN, "map5000")}, manufacturer="Bosch", model="MAP5000", name="MAP5000")

    @property
    def is_on(self) -> bool:
        """Return current option state."""
        return self._entry.options.get(
            CONF_BYPASS_OFF_NORMAL_DEVICES,
            DEFAULT_BYPASS_OFF_NORMAL_DEVICES,
        )

    async def async_turn_on(self, **kwargs) -> None:
        await self._update_option(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._update_option(False)

    async def _update_option(self, value: bool) -> None:
        """Persist option in config_entry.options and update state."""
        new_options = dict(self._entry.options)
        new_options[CONF_BYPASS_OFF_NORMAL_DEVICES] = value

        # Persistieren: options in ConfigEntry aktualisieren
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)

        # HA UI sofort aktualisieren
        self.async_write_ha_state()

class MapSensorBypassSwitch(SwitchEntity):

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coord: OIICoordinator, reg: MapRegistry, client, dev: DeviceEntry):
        self._coord=coord 
        self._reg=reg 
        self._client=client 
        self._dev=dev
        self._is_on=None
        self._attrs={}
        self._attr_unique_id=f"{DOMAIN}_{dev.siid}_bypass"
        self._attr_name=dev.name or dev.siid
        self._attr_available=True
        self._device_info = DeviceInfo(identifiers={(DOMAIN, "map5000")}, manufacturer="Bosch", model="MAP5000", name="MAP5000")

        reg.async_add_listener(self._on_update)

    @property
    def device_info(self): return self._device_info
    @property
    def is_on(self): return self._is_on
    @property
    def extra_state_attributes(self): return self._attrs

    @callback
    def _on_update(self, siid, payload):
        if siid!=self._dev.siid: 
            return
        res=payload.get("resource", {}) or {}

        self._attrs["siid"] = self._dev.siid
        self_link = res.get("@self")
        if isinstance(self_link, str):
            self._attrs["sid"] = self_link.split("/")[-1]
        else:
            self._attrs["sid"] = self._dev.siid

        # availability
        self._attr_available = (res.get("opState") == "OK") and bool(res.get("enabled", True))

        val=res.get("bypassed", True)
        if val is not None:
            self._is_on = bool(val)
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        body = self._mapping.get("turn_on", {"@cmd":"BYPASS"})
        await self._client.post(f"/{self._dev.siid}", body)
        try:
            res = await self._client.get(f"/{self._dev.siid}")
            self._on_update(self._dev.siid, {"resource": res})
        except Exception:
            pass

    async def async_turn_off(self, **kwargs):
        body = self._mapping.get("turn_off", {"@cmd":"UNBYPASS"})
        await self._client.post(f"/{self._dev.siid}", body)
        try:
            res = await self._client.get(f"/{self._dev.siid}")
            self._on_update(self._dev.siid, {"resource": res})
        except Exception:
            pass