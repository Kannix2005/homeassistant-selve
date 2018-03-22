"""
Support for Selve cover - shutters etc.
"""
import logging

from homeassistant.components.cover import CoverDevice, ATTR_POSITION
from homeassistant.components.selve import (
    DOMAIN as SELVE_DOMAIN, SelveDevice)

DEPENDENCIES = ['selve']

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up Selve covers."""
    controller = hass.data[SELVE_DOMAIN]['controller']
    devices = []
    for device in hass.data[SELVE_DOMAIN]['devices']['cover']:
        devices.append(SelveCover(device, controller))
    add_devices(devices, True)


class SelveCover(SelveDevice, CoverDevice):
    """Representation a Selve Cover."""

    def update(self):
        """Update method."""
        pass
        #self.controller.get_states([self.tahoma_device])

    @property
    def current_cover_position(self):
        """
        Return current position of cover.
        0 is closed, 100 is fully open.
        """
        return None
        

    def set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        position = kwargs.get(ATTR_POSITION) 
        if position == 100:
            self.selve_device.moveDown()
        elif position == 0:
            self.selve_device.moveUp()
        elif position >=75:
            self.selve_device.moveIntermediatePosition1()
        elif position <=25:
            self.selve_device.moveIntermediatePosition2()

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        if self.current_cover_position is not None:
            return self.current_cover_position == 0

    @property
    def device_class(self):
        """Return the class of the device."""        
        return None

    def open_cover(self, **kwargs):
        """Open the cover."""
        self.selve_device.moveUp()        

    def close_cover(self, **kwargs):
        """Close the cover."""
        self.selve_device.moveDown()        

    def stop_cover(self, **kwargs):
        """Stop the cover."""
         self.selve_device.stop()         