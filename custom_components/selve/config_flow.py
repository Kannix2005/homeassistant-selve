"""Config flow for selve integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PORT
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from selve import Selve

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def _get_serial_ports() -> list[str]:
    """Return list of available serial port paths (sync, runs in executor)."""
    try:
        gateway = Selve(None, discover=False)
        return [p.device for p in gateway.list_ports()]
    except Exception:
        return []


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for selve."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            port = user_input[CONF_PORT].strip()
            return self.async_create_entry(title="Selve Gateway", data={CONF_PORT: port})

        ports = await self.hass.async_add_executor_job(_get_serial_ports)

        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PORT, default=ports[0] if ports else ""): SelectSelector(
                        SelectSelectorConfig(
                            options=ports,
                            custom_value=True,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )


class OptionsFlowHandler(config_entries.OptionsFlow):

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            new_port = user_input.get(CONF_PORT, "").strip()
            options_data = {k: v for k, v in user_input.items() if k != CONF_PORT}
            if new_port and new_port != self.config_entry.data.get(CONF_PORT, ""):
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={**self.config_entry.data, CONF_PORT: new_port},
                )
            return self.async_create_entry(title="", data=options_data)

        ports = await self.hass.async_add_executor_job(_get_serial_ports)
        current_port = self.config_entry.data.get(CONF_PORT, "")
        all_ports = list(dict.fromkeys([current_port] + ports)) if current_port else ports

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PORT, default=current_port): SelectSelector(
                        SelectSelectorConfig(
                            options=all_ports,
                            custom_value=True,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(
                        "open_close_fix",
                        default=self.config_entry.options.get("open_close_fix", False),
                    ): bool,
                }
            ),
        )
