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
from selve import Selve, PortError, DutyCycleResponse, SenderEventResponse, CommeoDeviceEventResponse, SensorEventResponse, LogEventResponse, SenderTeachResultResponse, SensorTeachResultResponse, DeviceScanResultResponse, DeviceFunctions, DeviceType, SelveTypes, MovementState
from selve import DeviceCommandType, DriveCommandIveo

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

        self.config_entry.async_on_unload(self.config_entry.add_update_listener(self.update_listener))

        self.controller.register_event_callback(self._event_callback)

        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(self.config_entry, "cover")
        )

        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(
                self.config_entry, "binary_sensor"
            )
        )


        # Gateway
        hass.services.async_register(DOMAIN, 'ping_gateway', self.ping_gateway, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'gateway_state', self.gateway_state, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'get_gateway_firmware_version', self.get_gateway_firmware_version, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'get_gateway_serial', self.get_gateway_serial, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'get_gateway_spec', self.get_gateway_spec, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'reset', self.reset, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'factory_reset_gateway', self.factory_reset_gateway, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'set_led', self.set_led, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'get_led', self.get_led, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'update_all_devices', self.update_all_devices)
        hass.services.async_register(DOMAIN, 'set_forward', self.set_forward, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'get_forward', self.get_forward, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'set_events', self.set_events, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'get_events', self.get_events, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'get_duty', self.get_duty, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'get_rf', self.get_rf, supports_response=SupportsResponse.OPTIONAL)

        #Devices
        hass.services.async_register(DOMAIN, 'device_scan_start', self.device_scan_start, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'device_scan_stop', self.device_scan_stop, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'device_scan_result', self.device_scan_result, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'device_save', self.device_save, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'device_get_ids', self.device_get_ids, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'device_get_info', self.device_get_info, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'device_get_values', self.device_get_values, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'device_set_function', self.device_set_function, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'device_set_label', self.device_set_label, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'device_set_type', self.device_set_type, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'device_delete', self.device_delete, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'device_write_manual', self.device_write_manual, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'device_update_values', self.device_update_values, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'device_set_value', self.device_set_value, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'device_set_target_value', self.device_set_target_value, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'device_set_state', self.device_set_state, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'device_move_up', self.device_move_up, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'device_move_down', self.device_move_down, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'device_move_pos1', self.device_move_pos1, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'device_move_pos2', self.device_move_pos2, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'device_move_pos', self.device_move_pos, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'device_move_stop', self.device_move_stop, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'device_move_step_up', self.device_move_step_up, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'device_move_step_down', self.device_move_step_down, supports_response=SupportsResponse.OPTIONAL)

        #Group
        hass.services.async_register(DOMAIN, 'group_read', self.group_read, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'group_write', self.group_write, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'group_get_ids', self.group_get_ids, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'group_delete', self.group_delete, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'group_move_up', self.group_move_up, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'group_move_down', self.group_move_down, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'group_stop', self.group_stop, supports_response=SupportsResponse.OPTIONAL)

        #Iveo
        hass.services.async_register(DOMAIN, 'iveo_set_repeater', self.iveo_set_repeater, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'iveo_get_repeater', self.iveo_get_repeater, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'iveo_set_label', self.iveo_set_label, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'iveo_set_type', self.iveo_set_type, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'iveo_get_type', self.iveo_get_type, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'iveo_get_ids', self.iveo_get_ids, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'iveo_factory_reset', self.iveo_factory_reset, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'iveo_teach', self.iveo_teach, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'iveo_learn', self.iveo_learn, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'iveo_command_manual', self.iveo_command_manual, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'iveo_command_automatic', self.iveo_command_automatic, supports_response=SupportsResponse.OPTIONAL)

        #Sensor
        hass.services.async_register(DOMAIN, 'sensor_teach_start', self.sensor_teach_start, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'sensor_teach_stop', self.sensor_teach_stop, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'sensor_teach_result', self.sensor_teach_result, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'sensor_get_ids', self.sensor_get_ids, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'sensor_get_info', self.sensor_get_info, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'sensor_get_values', self.sensor_get_values, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'sensor_set_label', self.sensor_set_label, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'sensor_delete', self.sensor_delete, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'sensor_write_manual', self.sensor_write_manual, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'sensor_update_values', self.sensor_update_values, supports_response=SupportsResponse.OPTIONAL)
        
        #Sender
        hass.services.async_register(DOMAIN, 'sender_teach_start', self.sender_teach_start, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'sender_teach_stop', self.sender_teach_stop, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'sender_teach_result', self.sender_teach_result, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'sender_get_ids', self.sender_get_ids, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'sender_get_info', self.sender_get_info, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'sender_get_values', self.sender_get_values, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'sender_set_label', self.sender_set_label, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'sender_delete', self.sender_delete, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'sender_write_manual', self.sender_write_manual, supports_response=SupportsResponse.OPTIONAL)
        hass.services.async_register(DOMAIN, 'sender_update_values', self.sender_update_values, supports_response=SupportsResponse.OPTIONAL)


        return True

    #Services

    
    async def ping_gateway(
            self, service: ServiceCall
    ) -> None:
        """Reset GW"""
        response = await self.controller.pingGateway()

        return {
            "state": response,
        }

    async def gateway_state(
            self, service: ServiceCall
    ) -> None:
        """Reset GW"""
        response = await self.controller.gatewayState()

        return {
            "state": response,
        }

    async def reset(
            self, service: ServiceCall
    ) -> None:
        """Reset GW"""
        response = await self.controller.resetGateway()

        return {
            "state": True,
        }

    
    async def get_gateway_firmware_version(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.getGatewayFirmwareVersion()

        return {
            "version": response,
        }
    
    async def get_gateway_serial(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.getGatewaySerial()

        return {
            "state": response,
        }
    
    async def get_gateway_spec(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.getGatewaySpec()

        return {
            "state": response,
        }
    
    async def factory_reset_gateway(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.factoryResetGateway()

        return {
            "state": response,
        }
    
    async def update_all_devices(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.updateAllDevices()

        return {
            "state": True,
        }
    
    async def set_forward(
            self, service: ServiceCall
    ) -> None:
        """"""
        state = service.data["state"]
        response = await self.controller.setForward(state)

        return {
            "state": response,
        }
    
    async def get_forward(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.getForward()

        return {
            "forwarding": response.forwarding,
        }
    
    async def set_events(
            self, service: ServiceCall
    ) -> None:
        """"""
        
        eventDevice = service.data["event_device"]
        eventSensor = service.data["event_sensor"]
        eventSender = service.data["event_sender"]
        eventLogging = service.data["event_logging"]
        eventDuty = service.data["event_duty"]
        response = await self.controller.setEvents(eventDevice, eventSensor, eventSender, eventLogging, eventDuty)

        return {
            "state": True,
        }
    
    async def get_events(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.getEvents()

        return {
            "eventDevice": response.eventDevice,
            "eventDuty": response.eventDuty,
            "eventLogging": response.eventLogging,
            "eventSender": response.eventSender,
            "eventSensor": response.eventSensor,
        }
    
    async def get_duty(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.getDuty()

        return {
            "dutyMode": response.dutyMode,
            "rfTraffic": response.rfTraffic,
            "name": response.name,
        }
    
    async def get_rf(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.getRF()

        return {
            "iveoResetCount": response.iveoResetCount,
            "name": response.name,
            "netAddress": response.netAddress,
            "parameters": response.parameters,
            "rfBaseId": response.rfBaseId,
            "rfIveoId": response.rfIveoId,
            "sensorNetAddress": response.sensorNetAddress,
            "rfSensorId": response.rfSensorId,
            "resetCount": response.resetCount,
        }
    
    async def device_scan_start(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.scanStart()

        return {
            "state": response,
        }
    
    async def device_scan_stop(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.scanStop()

        return {
            "state": response,
        }
    
    async def device_scan_result(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.scanResult()

        return {
            "foundIds": response.foundIds,
            "noNewDevices": response.noNewDevices,
            "scanState": response.scanState,
        }
    
    async def device_save(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.deviceSave()

        return {
            "state": response,
        }
    
    async def device_get_ids(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.deviceGetIds()

        return {
            "state": response.ids,
        }
    
    async def device_get_info(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        response = await self.controller.deviceGetInfo(id)

        return {
            "rfAddress": response.rfAddress,
            "deviceType": response.deviceType,
            "state": response.state,
        }
    
    async def device_get_values(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        response = await self.controller.deviceGetValues(id)

        return {
            "movementState": response.movementState,
            "value": response.value,
            "targetValue": response.targetValue,
            "unreachable": response.unreachable,
            "overload": response.overload,
            "obstructed": response.obstructed,
            "alarm": response.alarm,
            "lostSensor": response.lostSensor,
            "automaticMode": response.automaticMode,
            "gatewayNotLearned": response.gatewayNotLearned,
            "windAlarm": response.windAlarm,
            "rainAlarm": response.rainAlarm,
            "freezingAlarm": response.freezingAlarm,
            "dayMode": response.dayMode,
        }
    
    async def device_set_function(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        function = DeviceFunctions[service.data["function"]]
        response = await self.controller.deviceSetFunction(id, function)

        return {
            "state": response,
        }
    
    async def device_set_label(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        label = service.data["label"]
        response = await self.controller.deviceSetLabel(id, label)

        return {
            "state": response,
        }
    
    async def device_set_type(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        type = DeviceType[service.data["type"]]
        response = await self.controller.deviceSetType(id, type)

        return {
            "state": response,
        }
    
    async def device_delete(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        response = await self.controller.deviceDelete(id)

        return {
            "state": response,
        }
    
    async def device_write_manual(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        address = int(service.data["address"])
        name = service.data["name"]
        type = DeviceType[service.data["type"]]
        response = await self.controller.deviceWriteManual(id, address, name, type)

        return {
            "state": response,
        }
    
    async def device_update_values(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        await self.controller.updateCommeoDeviceValuesAsync(id)

        return {
            "state": True,
        }
    
    async def device_set_value(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        value = int(service.data["value"])
        type = SelveTypes[service.data["type"]]
        await self.controller.setDeviceValue(id, value, type)

        return {
            "state": True,
        }
    
    async def device_set_target_value(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        value = int(service.data["value"])
        type = SelveTypes[service.data["type"]]
        await self.controller.setDeviceTargetValue(id, value, type)

        return {
            "state": True,
        }
    
    async def device_set_state(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        state = MovementState[service.data["state"]]
        type = SelveTypes[service.data["type"]]
        await self.controller.setDeviceState(id, state, type)

        return {
            "state": True,
        }
    
    async def device_move_up(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        type = SelveTypes[service.data["type"]]
        command = DeviceCommandType[service.data["command"]]

        dev = self.controller.getDevice(id, type)
        await self.controller.moveDeviceUp(dev, command)

        return {
            "state": True,
        }
    
    async def device_move_down(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        type = SelveTypes[service.data["type"]]
        command = DeviceCommandType[service.data["command"]]

        dev = self.controller.getDevice(id, type)
        await self.controller.moveDeviceDown(dev, command)

        return {
            "state": True,
        }
    
    async def device_move_pos1(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        type = SelveTypes[service.data["type"]]
        command = DeviceCommandType[service.data["command"]]

        dev = self.controller.getDevice(id, type)
        await self.controller.moveDevicePos1(dev, command)

        return {
            "state": True,
        }
    
    async def device_move_pos2(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        type = SelveTypes[service.data["type"]]
        command = DeviceCommandType[service.data["command"]]

        dev = self.controller.getDevice(id, type)
        await self.controller.moveDevicePos2(dev, command)

        return {
            "state": True,
        }
    
    async def device_move_pos(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        type = SelveTypes[service.data["type"]]
        command = DeviceCommandType[service.data["command"]]

        dev = self.controller.getDevice(id, type)
        await self.controller.moveDevicePos(dev, command)

        return {
            "state": True,
        }
    
    async def device_move_stop(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        type = SelveTypes[service.data["type"]]
        command = DeviceCommandType[service.data["command"]]

        dev = self.controller.getDevice(id, type)
        await self.controller.stopDevice(dev, command)

        return {
            "state": True,
        }
    
    async def device_move_step_up(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        degrees = int(service.data["degrees"])
        type = SelveTypes[service.data["type"]]
        command = DeviceCommandType[service.data["command"]]

        dev = self.controller.getDevice(id, type)
        await self.controller.moveDeviceStepUp(dev, degrees, command)

        return {
            "state": True,
        }
    
    async def device_move_step_down(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        degrees = int(service.data["degrees"])
        type = SelveTypes[service.data["type"]]
        command = DeviceCommandType[service.data["command"]]

        dev = self.controller.getDevice(id, type)
        await self.controller.moveDeviceStepDown(dev, degrees, command)

        return {
            "state": True,
        }
    
    async def group_read(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        response = await self.controller.groupRead(id)

        return {
            "id": response.id,
            "mask": response.mask,
            "name": response.name,
        }
    
    async def group_write(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        ids = str(service.data["ids"]).split(",")
        iddict = dict(enumerate(ids, start=1))
        name = int(service.data["name"])
        response = await self.controller.groupWrite(id, iddict, name)

        return {
            "state": response,
        }
    
    async def group_get_ids(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.groupGetIds()

        return {
            "ids": response.ids,
        }
    
    async def group_delete(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        response = await self.controller.groupDelete(id)

        return {
            "state": response,
        }
    
    async def group_move_up(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        type = SelveTypes.GROUP
        command = DeviceCommandType[service.data["command"]]

        dev = self.controller.getDevice(id, type)
        await self.controller.moveGroupUp(dev, command)

        return {
            "state": True,
        }
    
    async def group_move_down(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        type = SelveTypes.GROUP
        command = DeviceCommandType[service.data["command"]]

        dev = self.controller.getDevice(id, type)
        await self.controller.moveGroupDown(dev, command)

        return {
            "state": True,
        }
    
    async def group_stop(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        type = SelveTypes.GROUP
        command = DeviceCommandType[service.data["command"]]

        dev = self.controller.getDevice(id, type)
        response = await self.controller.stopGroup(dev, command)

        return {
            "state": True,
        }
    
    async def iveo_set_repeater(
            self, service: ServiceCall
    ) -> None:
        """"""
        config = service.data["config"]
        conf = 0
        if config == "SINGLEREPEAT":
            conf = 1
        if config == "MULTIREPEAT":
            conf = 2
        response = await self.controller.iveoSetRepeater(conf)

        return {
            "state": response,
        }
    
    async def iveo_get_repeater(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.iveoGetRepeater()

        conf = "NONE"
        if response.repeaterState == 1:
            conf = "SINGLEREPEAT"
        if response.repeaterState == 2:
            conf = "MULTIREPEAT"


        return {
            "repeater_state": conf,
        }
    
    async def iveo_set_label(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        label = service.data["label"]
        response = await self.controller.iveoSetLabel(id, label)

        return {
            "state": response,
        }
    
    async def iveo_set_type(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        type = DeviceType[service.data["type"]]
        response = await self.controller.iveoSetType(id, type)

        return {
            "state": response,
        }
    
    async def iveo_get_type(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.iveoGetType()

        return {
            "name": response.name,
            "activity": response.activity,
            "device_type": response.deviceType,
        }
    
    async def iveo_get_ids(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.iveoGetIds()

        return {
            "ids": response.ids,
        }
    
    async def iveo_factory_reset(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.iveoFactoryReset()

        return {
            "state": response,
        }
    
    async def iveo_teach(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.iveoTeach()

        return {
            "state": response,
        }
    
    async def iveo_learn(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.iveoLearn()

        return {
            "state": response,
        }
    
    async def iveo_command_manual(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        command = DriveCommandIveo[service.data["command"]]
        response = await self.controller.iveoCommandManual(id, command)

        return {
            "state": response,
        }
    
    async def iveo_command_automatic(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        command = DriveCommandIveo[service.data["command"]]
        response = await self.controller.iveoCommandAutomatic(id, command)

        return {
            "state": response,
        }
    
    async def sensor_teach_start(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.sensorTeachStart()

        return {
            "state": response,
        }
    
    async def sensor_teach_stop(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.sensorTeachStop()

        return {
            "state": response,
        }
    
    async def sensor_teach_result(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.sensorTeachResult()

        return {
            "teach_state": response.teachState,
            "time_left": response.timeLeft,
            "found_id": response.foundId,
        }
    
    async def sensor_get_ids(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.sensorGetIds()

        return {
            "ids": response.ids,
        }
    
    async def sensor_get_info(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.sensorGetInfo()

        return {
            "name": response.name,
            "rf_address": response.rfAddress,
        }
    
    async def sensor_get_values(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.sensorGetValues()

        return {
            "wind_digital": response.windDigital,
            "rain_digital": response.rainDigital,
            "temp_digital": response.tempDigital,
            "light_digital": response.lightDigital,
            "sensor_state": response.sensorState,
            "temp_analog": response.tempAnalog,
            "wind_analog": response.windAnalog,
            "sun_1_analog": response.sun1Analog,
            "day_light_analog": response.dayLightAnalog,
            "sun_2_analog": response.sun2Analog,
            "sun_3_analog": response.sun3Analog,
        }
    
    async def sensor_set_label(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        label = service.data["label"]
        response = await self.controller.sensorSetLabel(id, label)

        return {
            "state": response,
        }
    
    async def sensor_delete(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        response = await self.controller.sensorDelete(id)

        return {
            "state": response,
        }
    
    async def sensor_write_manual(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        address = int(service.data["address"])
        name = service.data["name"]
        response = await self.controller.sensorWriteManual(id, address, name)

        return {
            "state": response,
        }
    
    async def sensor_update_values(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        await self.controller.updateSensorValuesAsync(id)

        return {
            "state": True,
        }
    
    async def sender_teach_start(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.senderTeachStart()

        return {
            "state": response,
        }
    
    async def sender_teach_stop(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.senderTeachStop()

        return {
            "state": response,
        }
    
    async def sender_teach_result(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.senderTeachResult()

        return {
            "name": response.name,
            "teach_state": response.teachState,
            "time_left": response.timeLeft,
            "sender_id": response.senderId,
            "sender_event": response.senderEvent,
        }
    
    async def sender_get_ids(
            self, service: ServiceCall
    ) -> None:
        """"""
        response = await self.controller.senderGetIds()

        return {
            "ids": response.ids,
        }
    
    async def sender_get_info(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        response = await self.controller.senderGetInfo(id)

        return {
            "name": response.name,
            "rf_address": response.rfAddress,
            "rf_channel": response.rfChannel,
            "rf_reset_count": response.rfResetCount,
        }
    
    async def sender_get_values(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        response = await self.controller.senderGetValues(id)

        return {
            "last_event": response.lastEvent,
        }
    
    async def sender_set_label(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        label = service.data["label"]
        response = await self.controller.senderSetLabel(id, label)

        return {
            "state": response,
        }
    
    async def sender_delete(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        response = await self.controller.senderDelete(id)

        return {
            "state": response,
        }
    
    async def sender_write_manual(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        address = int(service.data["address"])
        channel = int(service.data["channel"])
        reset_count = int(service.data["reset_count"])
        name = service.data["name"]
        response = await self.controller.senderWriteManual(id, address, channel, reset_count, name)

        return {
            "state": response,
        }
    
    async def sender_update_values(
            self, service: ServiceCall
    ) -> None:
        """"""
        id = int(service.data["id"])
        await self.controller.updateSenderValuesAsync(id)

        return {
            "state": True,
        }
    












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
        if entry.options["switch_dir"] is True:
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
