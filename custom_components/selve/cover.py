"""
Support for Selve cover - shutters etc.
"""
from .const import DOMAIN
import logging
from selve import Selve, PortError

import voluptuous as vol

from homeassistant.const import CONF_PORT
from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    ATTR_POSITION,
    CoverEntityFeature,
)
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
    4: "cover",
    5: "cover",
    6: "cover",
    7: "cover",
    8: "cover",
    9: "cover",
    10: "cover",
    11: "cover",
}


async def async_setup_platform(hass, config, async_add_entities: AddEntitiesCallback, discovery_info=None):
    """Set up Selve covers."""

    serial_port = config[CONF_PORT]
    try:
        selve = Selve(serial_port, False, logger = _LOGGER)
        selve.discover()
    except PortError:
        _LOGGER.exception("Error when trying to connect to the selve gateway")
        return False

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
        return False
    
    devicelist = []
    for id in selve.devices["device"]:
        devicelist.append(SelveCover(selve.devices["device"][id], selve))

    for id in selve.devices["iveo"]:
        devicelist.append(SelveCover(selve.devices["iveo"][id], selve))
    
    async_add_entities(devicelist, True)
    


class SelveCover(SelveDevice, CoverEntity):
    """Representation a Selve Cover."""

    # Disable polling when using push
    should_poll = False

    def __init__(self, device, controller) -> None:
        super().__init__(device, controller)
        self.selve_device.openState = None

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        self.controller.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        self.controller.remove_callback(self.async_write_ha_state)

    async def async_update(self):
        """Update method."""

        self.controller.state = self.controller.gatewayState()

        if self.isCommeo():
            self.controller.updateCommeoDeviceValuesAsync(self.selve_device.id)
            _LOGGER.debug("Value: " + str(self.selve_device.name))
            _LOGGER.debug("Value: " + str(self.selve_device.value))

    def isCommeo(self):
        return self.selve_device.communicationType.name == "COMMEO"

    def isIveo(self):
        return self.selve_device.communicationType.name == "IVEO"

    @property
    def supported_features(self):
        """Flag supported features."""
        if self.isCommeo():
            return (
                CoverEntityFeature.OPEN
                | CoverEntityFeature.CLOSE
                | CoverEntityFeature.STOP
                | CoverEntityFeature.SET_POSITION
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
    def current_cover_position(self):
        """
        Return current position of cover.
        0 is closed, 100 is fully open.
        """
        if self.isCommeo():
            self.selve_device.openState = 100 - self.selve_device.value

        return self.selve_device.openState

    @property
    def current_cover_tilt_position(self):
        """
        Return current position of cover.
        0 is closed, 100 is fully open.
        """
        if self.isCommeo():
            self.selve_device.openState = 100 - self.selve_device.value

        return self.selve_device.openState

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        if self.current_cover_position is not None:
            return self.current_cover_position == 0

    @property
    def is_opening(self):
        if self.isCommeo():
            return self.selve_device.state.name == "UP_ON"
        return None

    @property
    def is_closing(self):
        if self.isCommeo():
            return self.selve_device.state.name == "DOWN_ON"
        return None

    @property
    def device_class(self):
        """Return the class of the device."""
        return SELVE_CLASSTYPES.get(self.selve_device.device_type.value)

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        self.controller.moveDeviceUp(self.selve_device)
        if self.isCommeo():
            self.controller.updateCommeoDeviceValuesAsync(self.selve_device.id)

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        self.controller.moveDeviceDown(self.selve_device)
        if self.isCommeo():
            self.controller.updateCommeoDeviceValuesAsync(self.selve_device.id)

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        self.controller.stopDevice(self.selve_device)
        if self.isCommeo():
            self.controller.updateCommeoDeviceValuesAsync(self.selve_device.id)

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        _position = 100 - kwargs.get(ATTR_POSITION)
        self.controller.moveDevicePos(_position)
        self.controller.updateCommeoDeviceValuesAsync(self.selve_device.id)
