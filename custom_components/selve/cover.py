"""
Support for Selve cover - shutters etc.
"""
import logging

import voluptuous as vol

from homeassistant.components.cover import (
    CoverEntity, ATTR_POSITION, SUPPORT_OPEN, SUPPORT_CLOSE, SUPPORT_STOP,
    SUPPORT_OPEN_TILT, SUPPORT_CLOSE_TILT, SUPPORT_STOP_TILT, SUPPORT_SET_POSITION, SUPPORT_SET_TILT_POSITION,
    DEVICE_CLASS_WINDOW, DEVICE_CLASS_BLIND, DEVICE_CLASS_AWNING, DEVICE_CLASS_SHUTTER)
from custom_components.selve import (
    DOMAIN as SELVE_DOMAIN, SelveDevice)

from homeassistant.const import ATTR_ENTITY_ID
import homeassistant.helpers.config_validation as cv

DEPENDENCIES = ['selve']

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_POS1 = 'selve_set_pos1'
SERVICE_SET_POS2 = 'selve_set_pos2'

SELVE_SERVICE_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
})

SELVE_CLASSTYPES = {
    0:None,
    1:DEVICE_CLASS_SHUTTER,
    2:DEVICE_CLASS_BLIND,
    3:DEVICE_CLASS_SHUTTER,
    4:'cover',
    5:'cover',
    6:'cover',
    7:'cover',
    8:'cover',
    9:'cover',
    10:'cover',
    11:'cover',
}


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up Selve covers."""
    controller = hass.data[SELVE_DOMAIN]['controller']
    devices = [ SelveCover(device, controller) for device in hass.data[SELVE_DOMAIN]['devices']['cover']]
    add_devices(devices, True)


class SelveCover(SelveDevice, CoverEntity):
    """Representation a Selve Cover."""

    def update(self):
        """Update method."""
        self.selve_device.discover_properties()
    
    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_OPEN | SUPPORT_CLOSE | SUPPORT_STOP | SUPPORT_SET_POSITION | SUPPORT_OPEN_TILT | SUPPORT_CLOSE_TILT | SUPPORT_SET_TILT_POSITION

    @property
    def current_cover_position(self):
        """
        Return current position of cover.
        0 is closed, 100 is fully open.
        """
        return self.selve_device.openState
    
    @property
    def current_cover_tilt_position(self):
        """
        Return current position of cover.
        0 is closed, 100 is fully open.
        """
        return self.selve_device.openState
 
    @property
    def is_closed(self):
        """Return if the cover is closed."""
        # if self.current_cover_position is not None:
        #     return self.current_cover_position == 0
        return None

    @property
    def device_class(self):
        """Return the class of the device.""" 
        return SELVE_CLASSTYPES.get(self.selve_device.device_type.value)
    

    def open_cover(self, **kwargs):
        """Open the cover."""
        self.selve_device.moveUpIveo() 
        self.selve_device.openState = 100

    def open_cover_tilt(self, **kwargs):
        """Open the cover."""
        self.selve_device.moveIntermediatePosition1()        
        self.selve_device.openState = 100

    def close_cover(self, **kwargs):
        """Close the cover."""
        self.selve_device.moveDown()  
        self.selve_device.openState = 0

    def close_cover_tilt(self, **kwargs):
        """Open the cover."""
        self.selve_device.moveIntermediatePosition2()     
        self.selve_device.openState = 0   

    def stop_cover(self, **kwargs):
        """Stop the cover."""
        self.selve_device.stop()
        self.selve_device.openState = 50
    
    def stop_cover_tilt(self, **kwargs):
        """Stop the cover."""
        self.selve_device.stop()
        self.selve_device.openState = 50
    
        