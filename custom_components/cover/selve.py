"""
Support for Selve cover - shutters etc.
"""
import logging

import voluptuous as vol

from homeassistant.components.cover import CoverDevice, ATTR_POSITION
#import custom_components.selve as selve
from custom_components.selve import (
    DOMAIN as SELVE_DOMAIN, SelveDevice)

# from homeassistant.const import ATTR_ENTITY_ID
# import homeassistant.helpers.config_validation as cv

DEPENDENCIES = ['selve']

_LOGGER = logging.getLogger(__name__)

# SERVICE_SET_POS1 = 'selve_set_pos1'
# SERVICE_SET_POS2 = 'selve_set_pos2'

# SELVE_SERVICE_SCHEMA = vol.Schema({
#     vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
# })


# SERVICE_TO_METHOD = {
#     SERVICE_SET_POS1: {'method': 'goto_pos1'},
#     SERVICE_SET_POS2: {'method': 'goto_pos2'},
# }

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up Selve covers."""
    controller = hass.data[SELVE_DOMAIN]['controller']
    devices = [ SelveCover(device, controller) for device in hass.data[SELVE_DOMAIN]['devices']['cover']]
    add_devices(devices, True)

    # def service_handler(service):
    #     """Map services to methods on Selve."""
    #     method = SERVICE_TO_METHOD.get(service.service)
    #     params = {key: value for key, value in service.data.items()
    #               if key != ATTR_ENTITY_ID}
    #     entity_ids = service.data.get(ATTR_ENTITY_ID)
    #     if entity_ids:
    #         devices = [device for device in hass.data[SELVE_DOMAIN].values() if
    #                    device.entity_id in entity_ids]
    #     else:
    #         devices = hass.data[SELVE_DOMAIN].values()

    #     update_tasks = []
    #     for device in devices:
    #         if not hasattr(device, method['method']):
    #             continue
    #         await getattr(device, method['method'])(**params)
    #         update_tasks.append(device.async_update_ha_state(True))

    #     if update_tasks:
    #         await asyncio.wait(update_tasks, loop=hass.loop)

    # for selve_service in SERVICE_TO_METHOD:
    #     schema = SERVICE_TO_METHOD[selve_service].get(
    #         'schema', SELVE_SERVICE_SCHEMA)
    #     hass.services.register(
    #         SELVE_DOMAIN, selve_service, service_handler, schema=schema)


class SelveCover(SelveDevice, CoverDevice):
    """Representation a Selve Cover."""

    def update(self):
        """Update method."""
        self.selve_device.discover_properties()
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
    
    def goto_pos1(self, **kwargs):
        self.selve_device.moveIntermediatePosition1()
    
    def goto_pos2(self, **kwargs):
        self.selve_device.moveIntermediatePosition2()
    
        