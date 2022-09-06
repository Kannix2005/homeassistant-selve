"""Config flow for selvetest integration."""
from __future__ import annotations
from collections import OrderedDict

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from selve import *

from .const import (DOMAIN)
from homeassistant.const import (CONF_PORT)

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
data_schema = OrderedDict()
data_schema[vol.Required(CONF_PORT, default="port")] = str
STEP_USER_DATA_SCHEMA = vol.Schema(data_schema)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # TODO validate the data can be used to set up a connection.

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data["username"], data["password"]
    # )
    
    
    try:
        gateway = Gateway(data[CONF_PORT])
    except Exception as e:
        _LOGGER.exception(e)
        raise ConnectionError


    #if not await gateway.gatewayReady():
    #    raise GatewayNotReadyError

    #known_devices = gateway.list_devices()

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    #return {CONF_PORT: data[CONF_PORT]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for selve."""

    VERSION = 1
    
    async def async_step_user(self, user_input=None):
        """Give initial instructions for setup."""
        if user_input is not None:
            return await self.async_step_initial_options()

        return self.async_show_form(step_id="user")

    async def async_step_initial_options(
        self, user_input = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
        
            try:
                await validate_input(self.hass, user_input)
                return self.async_create_entry(title=DOMAIN, data=user_input)
            except GatewayNotReadyError:
                _LOGGER.exception("gateway not ready")
                errors["base"] = "gateway_not_ready"
            except ConnectionError:
                _LOGGER.exception("invalid port")
                errors["base"] = "invalid_port"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            except AlreadyConfigured:
                return self.async_abort(reason="already_configured")

        return self.async_show_form(
            step_id="initial_options", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )



class AlreadyConfigured(HomeAssistantError):
    """Error to indicate this device is already configured."""

class GatewayNotReadyError(HomeAssistantError):
    """Error to indicate we cannot connect."""

class ConnectionError(HomeAssistantError):
    """Error to indicate there is invalid auth."""
