"""Config flow for selvetest integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PORT
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from selve import Selve
from selve.util.errors import PortError

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

port = "Unknown"


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for selve."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler()

    async def async_step_user(self, user_input=None):
        """Give initial instructions for setup."""

        errors = {}
        data = {}

        if user_input is not None:
            if user_input["autodiscovery"] is True:
                try:
                    gateway = Selve(None, discover=False, logger=_LOGGER)
                    await gateway.setup(discover=False, fromConfigFlow=True)
                    data[CONF_PORT] = gateway._port
                    return self.async_create_entry(title="Selve Gateway", data=data)
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

                except GatewayNotReadyError:
                    _LOGGER.exception("Gateway not ready")
                    errors["base"] = "gateway_not_ready"

                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected exception")
                    errors["base"] = "unknown"

            else:
                try:
                    gateway = Selve(None, discover=False, logger=_LOGGER)

                    if user_input[CONF_PORT] == "None":
                        _LOGGER.exception("Invalid port")
                        errors["base"] = "invalid_port"
                    else:
                        if await gateway.check_port(user_input[CONF_PORT]):
                            gateway = Selve(
                                user_input[CONF_PORT], discover=False, logger=_LOGGER
                            )
                            await gateway.setup(discover=False, fromConfigFlow=True)
                            data[CONF_PORT] = user_input[CONF_PORT]
                            return self.async_create_entry(
                                title="Selve Gateway", data=data
                            )
                        else:
                            _LOGGER.exception("Invalid port")
                            errors["base"] = "invalid_port"

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

                except GatewayNotReadyError:
                    _LOGGER.exception("Gateway not ready")
                    errors["base"] = "gateway_not_ready"

                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected exception")
                    errors["base"] = "unknown"

        list = []
        list.append("None")
        gateway = Selve(None, discover=False, logger=_LOGGER)
        ports = gateway.list_ports()
        for p in ports:
            list.append(p.device)
        data_schema = {
            vol.Required("autodiscovery", default=True): bool,
            vol.Optional(CONF_PORT, default="None"): vol.In(list),
        }

        return self.async_show_form(
            step_id="user", errors=errors, data_schema=vol.Schema(data_schema)
        )


class OptionsFlowHandler(config_entries.OptionsFlow):

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
                        "open_close_fix",
                        default=self.config_entry.options.get("open_close_fix", False),
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
