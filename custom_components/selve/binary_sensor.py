from .const import DOMAIN
import logging
import asyncio
from selve import Selve, PortError

from homeassistant.const import CONF_PORT
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.exceptions import PlatformNotReady
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo

DEPENDENCIES = ["selve"]

_LOGGER = logging.getLogger(__name__)


BINARY_SENSORS_TYPES: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="unreachable",
        name="Unreachable",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    BinarySensorEntityDescription(
        key="overload",
        name="Shutter overloaded",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    BinarySensorEntityDescription(
        key="alarm",
        name="Alarm",
        device_class=BinarySensorDeviceClass.TAMPER,
    ),
    BinarySensorEntityDescription(
        key="lostSensor",
        name="Sensor lost",
    ),
    BinarySensorEntityDescription(key="automaticMode", name="Automatic Mode"),
    BinarySensorEntityDescription(key="gatewayNotLearned", name="Gateway not learned"),
    BinarySensorEntityDescription(key="windAlarm", name="Wind Alarm"),
    BinarySensorEntityDescription(key="rainAlarm", name="Rain Alarm"),
    BinarySensorEntityDescription(key="freezingAlarm", name="Freezing Alarm"),
    BinarySensorEntityDescription(key="dayMode", name="Day Mode"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
):
    selve: Selve = hass.data[DOMAIN][config_entry.data[CONF_PORT]].controller
    # try:
    #     selve.pingGateway() #gateway should already be discovered by cover platform, just ping to make sure
    # except PortError as ex:
    #     _LOGGER.exception("Error when trying to connect to the selve gateway")
    #     raise PlatformNotReady(f"Connection error while connecting to gateway: {ex}") from ex

    devicelist = []
    # Sensors can only be available for commeo devices, due to lack of return channel on iveo
    for id in selve.devices["device"]:
        for description in BINARY_SENSORS_TYPES:
            try:
                devicelist.append(
                    SelveSensor(selve.devices["device"][id], selve, description)
                )
            except Exception as e:
                pass
    async_add_entities(devicelist, True)


class SelveSensor(BinarySensorEntity):
    def __init__(
        self, device, controller, description: BinarySensorEntityDescription
    ) -> None:
        self.selve_device = device
        self._name = f"{str(self.selve_device.name)}  {description.name}"
        self.controller = controller
        self.description = description

        self._unit_of_measurement = None
        self._state = None

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        self.controller.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        self.controller.remove_callback(self.async_write_ha_state)

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (
                    DOMAIN,
                    str(self.selve_device.device_type.value)
                    + str(self.selve_device.id),
                )
            },
            name=str(self.selve_device.name),
            manufacturer="Selve",
            model=self.selve_device.communicationType,
            sw_version=1,
            via_device=(DOMAIN, self.controller._port),
        )

    @property
    def should_poll(self) -> bool:
        """Data update is triggered from Selve."""
        return False

    @property
    def unique_id(self):
        """Return the unique id base on the id returned by gateway."""
        return (
            str(self.selve_device.device_type.value)
            + str(self.selve_device.id)
            + self.description.key
        )

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def isCommeo(self):
        return self.selve_device.communicationType.name == "COMMEO"

    @property
    def isIveo(self):
        return self.selve_device.communicationType.name == "IVEO"

    @property
    def state(self):
        """Return the state of the sensor.

        The return type of this call depends on the attribute that
        is configured.
        """
        attr = getattr(self.selve_device, self.description.key, None)
        _LOGGER.debug("Attr " + str(self.description.key) + " : " + str(attr))
        return attr

    @property
    def device_class(self):
        return self.description.device_class if self.description.device_class else None

    @property
    def unit_of_measurement(self) -> str:
        """Get the unit of measurement."""
        return self._unit_of_measurement

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        return {"selve_device_id": self.selve_device.id}
