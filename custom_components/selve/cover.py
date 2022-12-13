"""
Support for Selve cover - shutters etc.
"""
from .const import DOMAIN
import logging
from selve import Selve, PortError

import voluptuous as vol

from homeassistant.const import CONF_PORT
from homeassistant.exceptions import PlatformNotReady
from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    ATTR_POSITION,
    CoverEntityFeature,
)
from homeassistant.helpers.entity import DeviceInfo

from . import SelveDevice

from homeassistant.const import ATTR_ENTITY_ID
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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


async def async_setup_platform(hass, config, async_add_entities: AddEntitiesCallback, discovery_info=None):
    """Set up Selve covers."""

    serial_port = config[CONF_PORT]
    try:
        selve = Selve(serial_port, False, logger = _LOGGER)
        selve.discover()
    except PortError as ex:
        _LOGGER.exception("Error when trying to connect to the selve gateway")
        raise PlatformNotReady(f"Connection error while connecting to {serial_port}: {ex}") from ex

    devicelist = []
    for id in selve.devices["device"]:
        devicelist.append(SelveCover(selve.devices["device"][id], selve))

    for id in selve.devices["iveo"]:
        devicelist.append(SelveCover(selve.devices["iveo"][id], selve))
    
    async_add_entities(devicelist, True)



async def async_setup_entry(hass, config_entry, async_add_entities: AddEntitiesCallback):
    config = hass.data[DOMAIN][config_entry.entry_id]

    serial_port = config[CONF_PORT]
    try:
        selve = Selve(serial_port, False, logger = _LOGGER)
        selve.discover()
    except PortError:
        _LOGGER.exception("Error when trying to connect to the selve gateway")
        raise PlatformNotReady(f"Connection error while connecting to {serial_port}: {ex}") from ex
    
    devicelist = []
    for id in selve.devices["device"]:
        devicelist.append(SelveCover(selve.devices["device"][id], selve))

    for id in selve.devices["iveo"]:
        devicelist.append(SelveCover(selve.devices["iveo"][id], selve))
    
    async_add_entities(devicelist, True)
    


class SelveCover(SelveDevice, CoverEntity):
    """Representation a Selve Cover."""


    def __init__(self, device, controller) -> None:
        super().__init__(device, controller)
        self.selve_device.openState = 50
        
        if self.isCommeo():
            self.controller.updateCommeoDeviceValuesAsync(self.selve_device.id)

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        self.controller.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        self.controller.remove_callback(self.async_write_ha_state)

    async def async_update(self):
        """Update method. Not needed when using callbacks."""

        self.controller.state = self.controller.gatewayState()

        #self.controller.updateAllDevices()

        if self.isCommeo():
            self.controller.updateCommeoDeviceValuesAsync(self.selve_device.id)
            _LOGGER.debug("Value: " + str(self.selve_device.name))
            _LOGGER.debug("Value: " + str(self.selve_device.value))

    def isCommeo(self):
        return self.selve_device.communicationType.name == "COMMEO"

    def isIveo(self):
        return self.selve_device.communicationType.name == "IVEO"


    @property
    def should_poll(self):
        # Disable polling when using push
        return False

    @property
    def supported_features(self):
        """Flag supported features."""
        if self.isCommeo():
            return (
                CoverEntityFeature.OPEN
                | CoverEntityFeature.CLOSE
                | CoverEntityFeature.STOP
                | CoverEntityFeature.SET_POSITION
                | CoverEntityFeature.OPEN_TILT
                | CoverEntityFeature.CLOSE_TILT
                | CoverEntityFeature.STOP_TILT
            )
        elif self.isIveo():
            return (
                CoverEntityFeature.OPEN
                | CoverEntityFeature.CLOSE
                | CoverEntityFeature.STOP
            )
        else:
            return ()


    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        fwV = 0 #self.controller.getGatewayFirmwareVersion()
        gId = self.controller.getGatewaySerial()
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.unique_id)
            },
            name=self.name,
            manufacturer="Selve",
            model=self.selve_device.communicationType,
            sw_version=fwV,
            via_device=(DOMAIN, gId),
        )

    @property
    def current_cover_position(self):
        """
        Return current position of cover.
        0 is closed, 100 is fully open.
        """
        #if self.isCommeo():
        return 100 - self.selve_device.value

    @property
    def current_cover_tilt_position(self):
        """
        Return current position of cover.
        0 is closed, 100 is fully open.
        """
        #if self.isCommeo():
        return 100 - self.selve_device.value

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        if self.current_cover_position is not None:
            return self.current_cover_position == 0
        return None

    @property
    def is_opening(self):
        return self.selve_device.state.name == "UP_ON"

    @property
    def is_closing(self):
        return self.selve_device.state.name == "DOWN_ON"

    @property
    def device_class(self):
        """Return the class of the device."""
        return SELVE_CLASSTYPES.get(self.selve_device.device_sub_type.value)
    
    @property
    def extra_state_attributes(self):
        return {
            "value": self.selve_device.value,
            "targetValue": self.selve_device.targetValue,
            "communicationType": self.selve_device.communicationType.name,
            "gatewayState": self.controller.state.name
        }

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        self.controller.moveDeviceUp(self.selve_device)
        
    async def async_open_cover_tilt(self, **kwargs):
        """Open the cover."""
        self.controller.moveDevicePos1(self.selve_device)

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        self.controller.moveDeviceDown(self.selve_device)
        
    async def async_close_cover_tilt(self, **kwargs):
        """Close the cover."""
        self.controller.moveDevicePos2(self.selve_device)

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        self.controller.stopDevice(self.selve_device)
        
    async def async_stop_cover_tilt(self, **kwargs):
        """Stop the cover."""
        self.controller.stopDevice(self.selve_device)

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        _current_cover_position = 100 - kwargs.get(ATTR_POSITION)
        self.controller.moveDevicePos(self.selve_device, _current_cover_position)
