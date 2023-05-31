"""
Support for Selve devices.
"""

from __future__ import annotations
import asyncio
from homeassistant.components import discovery
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant, callback
from .const import DOMAIN
from collections import defaultdict
import logging
import voluptuous as vol
from homeassistant.const import CONF_PORT
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.exceptions import PlatformNotReady
from selve import Selve, PortError


REQUIREMENTS = ["python-selve-new"]
PLATFORMS = ["cover"]  # , "switch", "light", "climate"]

DS_BOOTLOADER = "Bootloader loading"
DS_UPDATE = "Updating"
DS_STARTUP = "Startup"
DS_READY = "Ready"


_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_PORT): cv.string,
            }
        ),
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Selve component."""

    conf = config.get(DOMAIN)
    if conf is None:
        conf = {}

    hass.data[DOMAIN] = {}

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up platform from a ConfigEntry."""

    port = entry.data[CONF_PORT] if entry.data[CONF_PORT] is not None else "1"

    selvegat = SelveGateway(hass, entry)
    hass.data[DOMAIN][port] = selvegat
    
    return await selvegat.async_setup()


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    controller = hass.data[DOMAIN].pop(entry.data[CONF_PORT])
    return await controller.async_reset()


async def async_migrate_entry(hass, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:

        new = {**config_entry.data}

        config_entry.version = 2
        hass.config_entries.async_update_entry(config_entry, data=new)

    _LOGGER.info("Migration to version %s successful", config_entry.version)

    return True


class SelveGateway(object):
    """Manages a single selve gateway."""

    def __init__(self, hass, config_entry):
        """Initialize the system."""
        self.config_entry = config_entry
        self.hass = hass
        self.controller = None

    @property
    def port(self):
        """Return the host of this bridge."""
        return self.config_entry.data[CONF_PORT]

    @property
    def available(self):
        return self.controller.pingGateway()

    async def async_setup(self):
        port = self.port
        hass = self.hass

        try:
            self.controller = Selve(port=port, discover=False, logger = _LOGGER)
            if self.controller.gatewayReady() is not True:
                self.controller.resetGateway()
                while self.controller.gatewayReady() is not True:
                    asyncio.sleep(1)
            self.controller.setEvents(1, 1, 1, 1, 1) # activate events to enable values to be reported back
        except PortError as ex:
            _LOGGER.exception("Error when trying to connect to the selve gateway")
            return False
        
        hass.async_add_job(hass.config_entries.async_forward_entry_setup(
            self.config_entry, 'cover'))
        
        hass.async_add_job(hass.config_entries.async_forward_entry_setup(
            self.config_entry, 'binary_sensor'))

        return True


    async def async_reset(self):
        if self.port is None:
            return True
        
        if self.controller is None:
            return True

        self.controller.stopGateway()

        await self.hass.config_entries.async_forward_entry_unload(
            self.config_entry, 'cover')
    
        await self.hass.config_entries.async_forward_entry_unload(
            self.config_entry, 'binary_sensor')
    


class SelveDevice(Entity):
    """Representation of a Selve device entity."""

    def __init__(self, selve_device, controller):
        """Initialize the device."""
        self.selve_device = selve_device
        self._name = str(self.selve_device.name)

    @callback
    def async_register_callbacks(self):
        """Register callbacks to update hass after device was changed."""

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
