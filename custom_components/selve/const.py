"""Constants for the selvetest integration."""

from homeassistant.helpers.device_registry import DeviceInfo

DOMAIN = "selve"


def via_gateway(selve) -> dict:
    """DeviceInfo fields linking a device to the gateway device.

    HA 2026.8 deprecated ``via_device`` (identifier tuple) in favour of
    ``via_device_id`` (registry id); ``via_device`` stops working in 2027.8.
    Older HA versions don't know ``via_device_id`` yet.
    """
    gateway = getattr(selve, "via_device", None)
    if "via_device_id" in DeviceInfo.__annotations__ and gateway is not None:
        return {"via_device_id": gateway.id}
    return {"via_device": (DOMAIN, selve.gateway_id)}

SELVE_TYPES = {
    0: None,
    1: "cover",
    2: "cover",
    3: "cover",
    4: "switch",
    5: "light",
    6: "switch",
    7: "switch",
    8: "climate",
    9: "climate",
    10: "switch",
    11: "switch",
}