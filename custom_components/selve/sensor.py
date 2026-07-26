"""Selve gateway diagnostic sensors."""
from __future__ import annotations

import logging

from selve import Selve, DutyCycleResponse
from selve.util.protocol import DutyMode

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PORT, PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

DEPENDENCIES = ["selve"]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
):
    selve: Selve = hass.data[DOMAIN][config_entry.data[CONF_PORT]].controller
    async_add_entities([SelveDutyCycleSensor(selve)])


class SelveDutyCycleSensor(SensorEntity):
    """Gateway RF duty-cycle utilization.

    The 868 MHz band has a ~1% airtime limit; once the gateway's duty cycle is
    exhausted it silently drops further telegrams. This sensor surfaces the
    current utilization so multi-cover scenes can be diagnosed, and exposes a
    ``sending_blocked`` attribute for automations.
    """

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:radio-tower"
    _attr_should_poll = False

    def __init__(self, selve: Selve) -> None:
        self.selve = selve
        self._attr_unique_id = f"{selve.gateway_id}_duty_cycle"
        self._attr_name = "RF duty cycle"

    async def async_added_to_hass(self) -> None:
        """Subscribe to gateway events (duty-cycle updates arrive here)."""
        self.selve.register_event_callback(self._on_event)

    async def async_will_remove_from_hass(self) -> None:
        self.selve.remove_event_callback(self._on_event)

    @callback
    def _on_event(self, response) -> None:
        """Write state only on duty-cycle events, not on every gateway event."""
        if isinstance(response, DutyCycleResponse):
            self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Bind availability to the gateway connection."""
        connected = getattr(self.selve, "connected", None)
        if connected is None:
            return True
        return bool(connected)

    @property
    def native_value(self):
        return self.selve.utilization

    @property
    def extra_state_attributes(self):
        return {
            "sending_blocked": self.selve.sendingBlocked == DutyMode.BLOCKED,
        }

    @property
    def device_info(self) -> DeviceInfo:
        """Attach to the gateway device."""
        return DeviceInfo(identifiers={(DOMAIN, self.selve.gateway_id)})
