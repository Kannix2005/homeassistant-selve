"""
Support for Selve cover - shutters etc.
"""
from .const import DOMAIN
import logging
import asyncio
from selve import Selve, PortError

import voluptuous as vol

from homeassistant.const import CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import PlatformNotReady
from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    ATTR_POSITION,
    CoverEntityFeature,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry
from homeassistant.const import ATTR_ENTITY_ID
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN

DEPENDENCIES = ["selve"]

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_POS1 = "selve_set_pos1"
SERVICE_SET_POS2 = "selve_set_pos2"

SELVE_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
    }
)

SELVE_CLASSTYPES = {
    0: None,
    1: CoverDeviceClass.SHUTTER,
    2: CoverDeviceClass.BLIND,
    3: CoverDeviceClass.AWNING,
    4: "switch",
    5: "switch",
    6: "switch",
    7: "switch",
    8: "climate",
    9: "climate",
    10: "switch",
    11: "gateway",
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
):
    selve: Selve = hass.data[DOMAIN][config_entry.data[CONF_PORT]].controller
    # try:
    #     await selve.discover()
    # except PortError as ex:
    #     _LOGGER.exception("Error when trying to connect to the selve gateway")
    #     raise PlatformNotReady(f"Connection error while connecting to gateway: {ex}") from ex

    devicelist = []
    for id in selve.devices["device"]:
        devicelist.append(SelveCover(selve.devices["device"][id], selve, config_entry))

    for id in selve.devices["iveo"]:
        devicelist.append(SelveCover(selve.devices["iveo"][id], selve, config_entry))

    for id in selve.devices["group"]:
        devicelist.append(SelveCover(selve.devices["group"][id], selve, config_entry))

    async_add_entities(devicelist, True)


async def update_listener(hass, config_entry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


class SelveCover(CoverEntity):
    """Representation a Selve Cover."""

    def __init__(self, device, selve, config_entry) -> None:
        self.selve_device = device
        self.selve_device.openState = 50
        self.selve = selve
        self._config_entry = config_entry
        self._name = str(self.selve_device.name)

    @property
    def open_close_fix(self) -> bool:
        """Return True if the open/close boundary fix is enabled."""
        return self._config_entry.options.get("open_close_fix", False)

    @property
    def unique_id(self):
        """Return the unique id base on the id returned by gateway."""
        return str(self.selve_device.device_type.value) + str(self.selve_device.id)

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        return {"selve_device_id": self.selve_device.id}

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        if self.isCommeo:
            await self.selve.updateCommeoDeviceValuesAsync(self.selve_device.id)

        self.selve.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        self.selve.remove_callback(self.async_write_ha_state)

    async def async_update(self):
        """Update method. Not needed when using callbacks."""

        # self.controller.state = self.controller.gatewayState()

        # self.controller.updateAllDevices()

        if self.isCommeo:
            await self.selve.updateCommeoDeviceValuesAsync(self.selve_device.id)

    @property
    def isCommeo(self):
        return self.selve_device.communicationType.name == "COMMEO"

    @property
    def isIveo(self):
        return self.selve_device.communicationType.name == "IVEO"

    @property
    def isGroup(self):
        return self.selve_device.device_type.name == "GROUP"

    @property
    def should_poll(self):
        # Disable polling when using push
        return False

    @property
    def supported_features(self):
        """Flag supported features."""
        if self.isGroup:
            return (
                CoverEntityFeature.OPEN
                | CoverEntityFeature.CLOSE
                | CoverEntityFeature.STOP
            )

        if self.isCommeo:
            return (
                CoverEntityFeature.OPEN
                | CoverEntityFeature.CLOSE
                | CoverEntityFeature.STOP
                | CoverEntityFeature.SET_POSITION
                | CoverEntityFeature.OPEN_TILT
                | CoverEntityFeature.CLOSE_TILT
                | CoverEntityFeature.STOP_TILT
            )
        elif self.isIveo:
            return (
                CoverEntityFeature.OPEN
                | CoverEntityFeature.CLOSE
                | CoverEntityFeature.STOP
                | CoverEntityFeature.SET_POSITION
            )
        else:
            return ()

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        # fwV = self.controller.getGatewayFirmwareVersion()
        # gId = self.controller.getGatewaySerial()
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.unique_id)
            },
            name=self.name,
            manufacturer="Selve",
            model=self.selve_device.communicationType,
            sw_version=1,
            via_device=(DOMAIN, self.selve.gateway_id),
        )

    @property
    def current_cover_position(self):
        """
        Return current position of cover.
        0 is closed, 100 is fully open.
        When open_close_fix is enabled, values 0-1 are clamped to 0 (closed)
        and values 99-100 are clamped to 100 (open) to fix incorrect state
        reporting for covers that report 99 when fully open or 1 when fully closed.
        """
        if self.isGroup:
            return 50

        value = self.selve_device.value
        if self.open_close_fix:
            value = (
                0 if value < 2
                else 100 if value > 98
                else value
            )
        return 100 - value

    @property
    def current_cover_tilt_position(self):
        """
        Return current position of cover.
        2 is closed, 98 is fully open. Can be reversed by options.
        """
        # if self.isCommeo:

        if self.isGroup:
            return 50

        value = (
            2
            if self.selve_device.value < 2
            else 98
            if self.selve_device.value > 98
            else self.selve_device.value
        )
        # if self.controller.config.get("switch_dir"):
        #    return value

        return 100 - value

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        if self.current_cover_position is not None:
            #    if self.controller.config.get("switch_dir"):
            #        return self.current_cover_position == 100

            return self.current_cover_position == 0
        return None

    @property
    def is_opening(self):
        if self.isGroup:
            return None
        return self.selve_device.state.name == "UP_ON"

    @property
    def is_closing(self):
        if self.isGroup:
            return None
        return self.selve_device.state.name == "DOWN_ON"

    @property
    def device_class(self):
        """Return the class of the device."""
        return SELVE_CLASSTYPES.get(self.selve_device.device_sub_type.value)

    @property
    def extra_state_attributes(self):
        gatewayState = ""

        # try:
        #     self.controller.gatewayState()

        # except Exception as e:
        #     _LOGGER.exception(f"Error when trying to get the gateway state:  {e}")

        # if self.controller.state:
        #     if self.controller.state.name:
        #         gatewayState = self.controller.state.name

        if self.isGroup:
            return {
                "value": 50,
                "tiltValue": 0,
                "targetValue": 50,
                "communicationType": self.selve_device.communicationType.name
                if self.selve_device.communicationType.name
                else "",
                "gatewayState": gatewayState,
            }

        return {
            "value": self.selve_device.value,
            "tiltValue": self.current_cover_tilt_position,
            "targetValue": self.selve_device.targetValue,
            "communicationType": self.selve_device.communicationType.name
            if self.selve_device.communicationType.name
            else "",
            "gatewayState": gatewayState,
        }

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        if self.isGroup:
            await self.selve.moveGroupUp(self.selve_device)
            return
        await self.selve.moveDeviceUp(self.selve_device)

    async def async_open_cover_tilt(self, **kwargs):
        """Open the cover."""
        await self.selve.moveDevicePos1(self.selve_device)

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        if self.isGroup:
            await self.selve.moveGroupDown(self.selve_device)
            return
        await self.selve.moveDeviceDown(self.selve_device)

    async def async_close_cover_tilt(self, **kwargs):
        """Close the cover."""
        await self.selve.moveDevicePos2(self.selve_device)

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        if self.isGroup:
            await self.selve.stopGroup(self.selve_device)
            return
        await self.selve.stopDevice(self.selve_device)

    async def async_stop_cover_tilt(self, **kwargs):
        """Stop the cover."""
        await self.selve.stopDevice(self.selve_device)

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""

        if self.isCommeo:
            _current_cover_position = 100 - kwargs.get(ATTR_POSITION)
            await self.selve.moveDevicePos(
                self.selve_device, _current_cover_position
            )
        else:
            if kwargs.get(ATTR_POSITION) >= 50:
                await self.selve.moveDeviceUp(self.selve_device)
            else:
                await self.selve.moveDeviceDown(self.selve_device)
