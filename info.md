# Selve NG – Home Assistant Integration

Local control of Selve USB-RF gateways and covers (Commeo/Iveo/Groups) via `python-selve-new`.

## Features
- Direct USB control, no cloud required
- Cover entities for shutters, blinds, and awnings (Commeo, Iveo, Groups)
- Auto-discovery of devices and serial ports
- 99 services covering the complete Selve USB-RF Gateway protocol
- Gateway management (firmware, LED, events, duty cycle, RF, forwarding)
- Device, sensor, sender, and senSim management
- Group and Iveo controller support
- Position control with tilt support for Commeo devices
- Option to invert cover position semantics

## Requirements
- Home Assistant Core/Supervised/OS with access to the Selve USB-RF stick
- USB port visible to HA (e.g., `/dev/ttyUSB0`)
