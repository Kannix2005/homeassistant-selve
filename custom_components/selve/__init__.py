"""
Support for Selve devices.
"""

from __future__ import annotations
from homeassistant.components import discovery
from homeassistant.core import HomeAssistant, callback
from .const import DOMAIN, SELVE_TYPES
from collections import defaultdict
import logging
import voluptuous as vol
from homeassistant.const import CONF_PORT
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity
from selve import Gateway

REQUIREMENTS = ["python-selve-new"]
PLATFORMS = ["cover", "switch", "light", "climate"]

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
    """Set up the Hello World component."""
    # Ensure our name space for storing objects is a known type. A dict is
    # common/preferred as it allows a separate instance of your class for each
    # instance that has been created in the UI.
    hass.data.setdefault(DOMAIN, {})

    serial_port = config[DOMAIN][CONF_PORT]
    try:
        selve = Gateway(serial_port, False)
    except:
        _LOGGER.exception("Error when trying to connect to the selve gateway")
        return False

    hass.data[DOMAIN] = {"controller": selve, "devices": defaultdict(list)}

    try:
        selve.discover()
        devices = list(selve.devices.values())
    except:
        _LOGGER.exception("Error when getting devices from the Selve API")
        return False

    hass.data[DOMAIN] = {"controller": selve, "devices": defaultdict(list)}

    for device in devices:
        _device = device
        device_type = map_selve_device(_device)
        if device_type is None:
            _LOGGER.warning(
                "Unsupported type %s for Selve device %s",
                _device.device_type,
                _device.name,
            )
            continue
        hass.data[DOMAIN]["devices"][device_type].append(_device)

    for platform in PLATFORMS:
        hass.async_create_task(
            discovery.async_load_platform(hass, platform, DOMAIN, {}, config)
        )
    return True


def map_selve_device(selve_device):
    """Map Selve device types to Home Assistant components."""
    return SELVE_TYPES.get(selve_device.device_type.value)


class SelveDevice(Entity):
    """Representation of a Selve device entity."""

    def __init__(self, selve_device, controller):
        """Initialize the device."""
        self.selve_device = selve_device
        self.controller = controller
        self._name = self.selve_device.name

    @callback
    def async_register_callbacks(self):
        """Register callbacks to update hass after device was changed."""

    @property
    def unique_id(self):
        """Return the unique id base on the id returned by gateway."""
        return self.selve_device.ID

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        return {"selve_device_id": self.selve_device.ID}
