"""
Support for Selve devices.
"""

from __future__ import annotations
import asyncio
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback, ServiceResponse, SupportsResponse
from .const import DOMAIN
from collections import defaultdict
import logging
import voluptuous as vol
from homeassistant.const import CONF_PORT
from homeassistant.helpers import config_validation as cv, entity_platform, service
from homeassistant.helpers.entity import Entity
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers import device_registry as dr
from selve import Selve, PortError, DutyCycleResponse, SenderEventResponse, CommeoDeviceEventResponse, SensorEventResponse, LogEventResponse, SenderTeachResultResponse, SensorTeachResultResponse, DeviceScanResultResponse


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
    await selvegat.async_setup()
    return True

 
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    controller = hass.data[DOMAIN][entry.data[CONF_PORT]]
    platforms = ["cover", "binary_sensor"]
    unloaded = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
                if platform in platforms
            ]
        )
    )

    await controller.async_reset()
    if unloaded:
        hass.data[DOMAIN].pop(entry.data[CONF_PORT])
    return unloaded


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
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
        self.gatewayId = None
        self.gatewayFW = None

    @property
    def port(self):
        """Return the host of this bridge."""
        return self.config_entry.data[CONF_PORT]

    @property
    def available(self):
        return asyncio.run_coroutine_threadsafe(
            self.controller.pingGateway(), self.hass.loop
        ).result()

    async def async_setup(self):
        port = self.port
        hass = self.hass
        loop=asyncio.get_running_loop()


        try:
            self.controller = Selve(port=port, logger=_LOGGER, loop=loop)
            await self.controller.setup(discover=True)
        except PortError as ex:
            _LOGGER.exception("Error when trying to connect to the selve gateway - trying autodetection")
            try:
                self.controller = Selve(port=port, logger=_LOGGER)
                await self.controller.setup(discover=True)
            except Exception as e:
                _LOGGER.exception("Error when trying to connect to the selve gateway - also failed with autodetection")

            return False

        self.gatewayId = await self.controller.getGatewaySerial()
        self.gatewayFW = await self.controller.getGatewayFirmwareVersion()

        device_registry = dr.async_get(hass)
        device_registry.async_get_or_create(
            config_entry_id=self.config_entry.entry_id,
            connections={},
            identifiers={(DOMAIN, self.gatewayId)},
            manufacturer="Selve",
            suggested_area="",
            name="Selve USB-RF Gateway",
            model="USB",
            model_id=self.gatewayId,
            sw_version=self.gatewayFW,
            hw_version="1",
        )

        self.config_entry.add_update_listener(self.update_listener)

        self.controller.register_event_callback(self._event_callback)

        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(self.config_entry, "cover")
        )

        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(
                self.config_entry, "binary_sensor"
            )
        )



        hass.services.async_register(DOMAIN, 'teach_start', self.teach_start)
        hass.services.async_register(DOMAIN, 'teach_state', self.teach_state)
        hass.services.async_register(DOMAIN, 'reset', self.reset)
        hass.services.async_register(DOMAIN, 'set_led', self.set_led, supports_response=SupportsResponse.ONLY)


        return True

    #Services
    async def teach_start(
            self, service: ServiceCall
    ) -> None:
        """Start teaching"""
        return await self.controller.senderTeachStart()
        

    async def teach_state(
            self, service: ServiceCall
    ) -> None:
        """Get teaching state"""
        return await self.controller.senderTeachResult()


    async def reset(
            self, service: ServiceCall
    ) -> None:
        """Reset GW"""
        return await self.controller.resetGateway()


    async def set_led(
            self, service: ServiceCall
    ) -> ServiceResponse:
        """Set LED"""
        state = service.data["state"]
        await self.controller.setLED(state)
        response = await self.controller.getLED()

        return {
            "state": response.ledmode,
        }


    #Listeners
    async def update_listener(self, hass: HomeAssistant, entry: ConfigEntry):
        """Handle options update."""
        if entry.options.switch_dir is True:
            flag = 1
        else:
            flag = 0
        self.controller.updateOptions(flag)
        await self.controller.updateAllDevices()
        await hass.config_entries.async_reload(entry.entry_id)

    #Callbacks

    @callback
    def _event_callback(self, response):
        """Is called when an event arrives."""

        event_data = {}

        if isinstance(response, SenderEventResponse):

            event_data = {
                "device_id": self.gatewayId,
                "type": "sender_event",
                "senderName": response.senderName,
                "id": response.id,
                "event": response.event,
                "parameters": response.parameters
            }

        
        if isinstance(response, DutyCycleResponse):
            
            event_data = {
                "device_id": self.gatewayId,
                "type": "dutycycle_event",
                "mode": response.mode,
                "traffic": response.traffic
            }

        if isinstance(response, CommeoDeviceEventResponse):
            
            event_data = {
                "device_id": self.gatewayId,
                "type": "commeo_event",
                "parameters": response.parameters,
                "actorState": response.actorState,
                "alarm": response.alarm,
                "automaticMode": response.automaticMode,
                "dayMode": response.dayMode,
                "deviceType": response.deviceType,
                "freezingAlarm": response.freezingAlarm,
                "gatewayNotLearned": response.gatewayNotLearned,
                "id": response.id,
                "lostSensor": response.lostSensor,
                "name": response.name,
                "obstructed": response.obstructed,
                "overload": response.overload,
                "rainAlarm": response.rainAlarm,
                "targetValue": response.targetValue,
                "value": response.value,
                "unreachable": response.unreachable,
                "windAlarm": response.windAlarm
            }

        if isinstance(response, SensorEventResponse):
            
            event_data = {
                "device_id": self.gatewayId,
                "type": "sensor_event",
                "dayLightAnalog": response.dayLightAnalog,
                "id": response.id,
                "lightDigital": response.lightDigital,
                "name": response.name,
                "parameters": response.parameters,
                "rainDigital": response.rainDigital,
                "sensorState": response.sensorState,
                "sun1Analog": response.sun1Analog,
                "sun2Analog": response.sun2Analog,
                "sun3Analog": response.sun3Analog,
                "tempAnalog": response.tempAnalog,
                "tempDigital": response.tempDigital,
                "windAnalog": response.windAnalog,
                "windDigital": response.windDigital
            }

        if isinstance(response, LogEventResponse):
            
            event_data = {
                "device_id": self.gatewayId,
                "type": "log_event",
                "parameters": response.parameters,
                "logCode": response.logCode,
                "logDescription": response.logDescription,
                "logStamp": response.logStamp,
                "logType": response.logType,
                "logValue": response.logValue,
                "name": response.name
            }
        

        if isinstance(response, SenderTeachResultResponse):
            
            event_data = {
                "device_id": self.gatewayId,
                "type": "sender_teach_event",
                "parameters": response.parameters,
                "name": response.name,
                "senderEvent": response.senderEvent,
                "senderId": response.senderId,
                "teachState": response.teachState,
                "timeLeft": response.timeLeft
            }

        if isinstance(response, SensorTeachResultResponse):
            
            event_data = {
                "device_id": self.gatewayId,
                "type": "sensor_teach_event",
                "parameters": response.parameters,
                "foundId": response.foundId,
                "name": response.name,
                "teachState": response.teachState,
                "timeLeft": response.timeLeft
            }

        if isinstance(response, DeviceScanResultResponse):
            
            event_data = {
                "device_id": self.gatewayId,
                "type": "device_scan_event",
                "parameters": response.parameters,
                "name": response.name,
                "foundIds": response.foundIds,
                "noNewDevices": response.noNewDevices,
                "scanState": response.scanState
            }
        
        if not event_data:
            event_data = {
                "device_id": self.gatewayId,
                "type": "unknown_event"
            }


        self.hass.bus.async_fire("selve_event", event_data)


    async def async_reset(self):
        if self.port is None:
            return True

        if self.controller is None:
            return True

        await self.hass.config_entries.async_forward_entry_unload(
            self.config_entry, "binary_sensor"
        )

        await self.hass.config_entries.async_forward_entry_unload(
            self.config_entry, "cover"
        )

        await self.controller.stopGateway()
