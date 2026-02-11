<div align="center">

# Selve NG – Home Assistant Integration

[![Version](https://img.shields.io/badge/version-3.3.1-blue.svg)](https://github.com/Kannix2005/homeassistant-selve/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Local control of Selve USB-RF gateways and covers (Commeo/Iveo/Groups) via `python-selve-new`.

</div>

## Overview
- Direct USB control, no cloud required.
- Cover support (shutters/blinds/awnings), groups, positions, and Commeo tilt.
- Auto-discovery of devices and serial ports.
- Option `open_close_fix` to clamp near-boundary cover positions for correct open/closed reporting.
- Extra attributes (gateway state, target value, communication type).
- Services for gateway info, LED control, and device refresh.

## Requirements
- Home Assistant Core/Supervised/OS with access to the Selve USB-RF stick.
- Python dependency: `python-selve-new` (installed by HACS).
- USB port visible to HA (e.g., `/dev/ttyUSB0` or Windows COM port).

## Installation (HACS recommended)
1. In HACS → Integrations → add custom repository: `https://github.com/Kannix2005/homeassistant-selve` (type: Integration).
2. Find and install “Selve NG”.
3. Restart Home Assistant if prompted.

### Manual install
1. Copy `custom_components/selve` from this repo into your HA config directory.
2. Restart Home Assistant.

## Setup
1. In HA: Settings → Devices & Services → “Add integration” → “Selve NG”.
2. Choose **Autodiscovery** or select the USB port manually.
3. Finish: cover entities are created per device/group.

### Options
- `open_close_fix`: Clamp cover positions near boundaries for correct state reporting.
	- Off (default): Raw position values from the gateway are used as-is.
	- On: Values 0–1 % are reported as 0 % (fully closed) and 99–100 % as 100 % (fully open). Useful when covers report 99 instead of 100 when fully opened, or 1 instead of 0 when fully closed. See [#41](https://github.com/Kannix2005/homeassistant-selve/issues/41).

## Usage
- **Cover control**: standard cover entities support `set_cover_position`; Commeo devices also support tilt.
- **Services** (Developer Tools → Services): see tables below. Cover movement uses standard HA cover services.

### Gateway services
| Service | Purpose |
| --- | --- |
| `selve.ping_gateway` | Check connectivity to the gateway. |
| `selve.gateway_state` | Read current gateway state. |
| `selve.get_gateway_serial` | Return the gateway serial number. |
| `selve.get_gateway_firmware_version` | Return the gateway firmware version. |
| `selve.get_gateway_spec` | Return gateway spec details. |
| `selve.set_led` | Set LED mode on the gateway. |
| `selve.get_led` | Read LED mode from the gateway. |
| `selve.set_forward` / `selve.get_forward` | Configure/query forwarding. |
| `selve.set_events` / `selve.get_events` | Enable/inspect event subscriptions. |
| `selve.get_duty` / `selve.get_rf` | Read duty cycle / RF info. |
| `selve.set_duty` / `selve.set_rf` | Set duty cycle mode / RF base address. |
| `selve.get_temperature` | Read internal gateway temperature. |
| `selve.firmware_get_version` | Read firmware version from gateway. |
| `selve.firmware_update` | Trigger firmware update (use with caution). |
| `selve.command_result` | Retrieve pending command result. |
| `selve.update_all_devices` | Refresh values for all known devices. |
| `selve.reset` / `selve.factory_reset_gateway` | Reset gateway (factory reset is destructive). |

### Device services
| Service | Purpose |
| --- | --- |
| `selve.device_scan_start` / `selve.device_scan_stop` / `selve.device_scan_result` / `selve.device_save` | Scan for devices and persist results. |
| `selve.device_get_ids` / `selve.device_get_info` / `selve.device_get_values` | Inspect device list, info, and live values. |
| `selve.device_set_function` | Set device function (install/select/program...). |
| `selve.device_set_label` / `selve.device_set_type` | Update naming and type. |
| `selve.device_delete` | Delete a device. |
| `selve.device_write_manual` | Manually write a device definition (id/address/name/type). |
| `selve.device_update_values` | Refresh values for a device. |
| `selve.device_set_value` / `selve.device_set_target_value` / `selve.device_set_state` | Manually override current/target/state. |
| `selve.device_move_up` / `selve.device_move_down` / `selve.device_move_pos1` / `selve.device_move_pos2` / `selve.device_move_pos` / `selve.device_move_stop` | Movement commands (Commeo/Iveo). |
| `selve.device_move_step_up` / `selve.device_move_step_down` | Step/tilt movement (degrees). |
| `selve.device_save_pos1` / `selve.device_save_pos2` | Save current position as Pos1/Pos2. |

### Group services
| Service | Purpose |
| --- | --- |
| `selve.group_read` / `selve.group_get_ids` | Read group config / list groups. |
| `selve.group_write` | Write group membership and name. |
| `selve.group_delete` | Delete a group. |
| `selve.group_move_up` / `selve.group_move_down` / `selve.group_stop` | Group movement commands. |

### Iveo services
| Service | Purpose |
| --- | --- |
| `selve.iveo_set_repeater` / `selve.iveo_get_repeater` | Configure/query repeater mode. |
| `selve.iveo_set_label` / `selve.iveo_set_type` / `selve.iveo_get_type` | Update/query Iveo label/type. |
| `selve.iveo_get_ids` | List Iveo devices. |
| `selve.iveo_factory_reset` | Factory reset Iveo device (destructive). |
| `selve.iveo_teach` / `selve.iveo_learn` | Teaching/learning procedures. |
| `selve.iveo_command_manual` / `selve.iveo_command_automatic` | Manual/automatic commands (STOP/UP/DOWN/POS1/POS2/etc.). |
| `selve.iveo_command_result` | Retrieve pending Iveo command result. |

### senSim services
| Service | Purpose |
| --- | --- |
| `selve.sensim_get_ids` | List senSim devices. |
| `selve.sensim_get_config` / `selve.sensim_set_config` | Read/write senSim configuration. |
| `selve.sensim_get_values` / `selve.sensim_set_values` | Read/write senSim sensor values. |
| `selve.sensim_get_test` / `selve.sensim_set_test` | Read/write senSim test mode. |
| `selve.sensim_set_label` | Update senSim label. |
| `selve.sensim_drive` / `selve.sensim_store` | Drive/store senSim commands. |
| `selve.sensim_delete` | Delete a senSim device. |
| `selve.sensim_factory` | Factory reset senSim device. |

### Sensor services
| Service | Purpose |
| --- | --- |
| `selve.sensor_teach_start` / `selve.sensor_teach_stop` / `selve.sensor_teach_result` | Sensor teaching workflow. |
| `selve.sensor_get_ids` / `selve.sensor_get_info` / `selve.sensor_get_values` | List/read sensor info and values. |
| `selve.sensor_set_label` | Update sensor label. |
| `selve.sensor_delete` | Delete a sensor. |
| `selve.sensor_write_manual` | Manually create/write a sensor definition. |
| `selve.sensor_update_values` | Refresh sensor values. |

### Sender services
| Service | Purpose |
| --- | --- |
| `selve.sender_teach_start` / `selve.sender_teach_stop` / `selve.sender_teach_result` | Sender teaching workflow. |
| `selve.sender_get_ids` / `selve.sender_get_info` / `selve.sender_get_values` | List/read sender info and values. |
| `selve.sender_set_label` | Update sender label. |
| `selve.sender_delete` | Delete a sender. |
| `selve.sender_write_manual` | Manually create/write a sender definition (id/address/channel/reset count/name). |
| `selve.sender_update_values` | Refresh sender values. |

## Troubleshooting
- No devices found: verify the USB port is available and not locked by another process.
- Wrong position shown: enable `open_close_fix` in the integration options if your covers report 99/1 instead of 100/0 at the limits.
- Logs: filter HA logs for `custom_components.selve`.

## Notes
- Tested with `python-selve-new` 2.5.0.
- 99 services covering the complete Selve USB-RF Gateway protocol.
- Contributions and issues welcome via the GitHub issue tracker.

## Known limitations
- Only covers (and related groups) are exposed as entities; other device types may be available via services but not as native HA entities.
- Gateway must be reachable via a local serial/USB port; no network transport is supported.
- Iveo support is command-based (one-way); state reporting is limited compared to Commeo.
