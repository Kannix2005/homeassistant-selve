"""
Support for Selve light - lights etc.
"""
import logging

import voluptuous as vol

from homeassistant.components.climate import ClimateEntity
from custom_components.selve import DOMAIN as SELVE_DOMAIN, SelveDevice

from homeassistant.const import ATTR_ENTITY_ID
import homeassistant.helpers.config_validation as cv

DEPENDENCIES = ["selve"]

_LOGGER = logging.getLogger(__name__)

SELVE_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
    }
)

SELVE_CLASSTYPES = {
    0: None,
    1: None,
    2: None,
    3: None,
    4: None,
    5: None,
    6: None,
    7: None,
    8: "climate",
    9: "climate",
    10: None,
    11: None,
}
