"""
Support for Selve devices.
"""

from __future__ import annotations
from homeassistant.components import discovery
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant, callback
from .const import DOMAIN, SELVE_TYPES
from collections import defaultdict
import logging
import voluptuous as vol
from homeassistant.const import CONF_PORT
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_registry import (
    async_get_registry as async_get_entity_registry,
)
from selve import Selve
from selve import SelveDevice as SD
from selve import IveoDevice as ID


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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Forward the setup to the cover platform.
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "cover")
    )
    return True


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Selve component."""
    # Ensure our name space for storing objects is a known type. A dict is
    # common/preferred as it allows a separate instance of your class for each
    # instance that has been created in the UI.
    hass.data.setdefault(DOMAIN, {})

    return True


def map_selve_device(selve_device):
    """Map Selve device types to Home Assistant components."""
    return SELVE_TYPES.get(selve_device.device_type.value)


class SelveDevice(Entity):
    """Representation of a Selve device entity."""

    def __init__(self, selve_device, controller):
        """Initialize the device."""
        self.selve_device = selve_device
        self.controller: Selve = controller
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
