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
from selve.util.errors import *

from .const import DOMAIN
from homeassistant.const import CONF_PORT

_LOGGER = logging.getLogger(__name__)

port = "Unknown"


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for selve."""

    VERSION = 1

    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)
    
    async def async_step_user(self, user_input=None):
        """Give initial instructions for setup."""

        errors = {}
        data = {}

        try:
            gateway = Selve(None, discover=False, logger=_LOGGER)
            data[CONF_PORT] = gateway._port
            return self.async_create_entry(title="Selve Gateway", data=data)

        except GatewayNotReadyError:
            _LOGGER.exception("Gateway not ready")
            errors["base"] = "gateway_not_ready"
        except PortError:
            _LOGGER.exception("Invalid port")
            errors["base"] = "invalid_port"
        except ConnectionFailedError:
            _LOGGER.exception("Invalid port")
            errors["base"] = "invalid_port"
        except AlreadyConfigured:
            return self.async_abort(reason="already_configured")
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"

        return self.async_show_form(step_id="user", errors=errors)


class OptionsFlowHandler(config_entries.OptionsFlow):

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "switch_dir",
                        default=self.config_entry.options.get("switch_dir", False),
                    ): bool
                }
            ),
        )


class AlreadyConfigured(HomeAssistantError):
    """Error to indicate this device is already configured."""


class GatewayNotReadyError(HomeAssistantError):
    """Error to indicate we cannot connect."""


class ConnectionFailedError(HomeAssistantError):
    """Error to indicate there is invalid auth."""
