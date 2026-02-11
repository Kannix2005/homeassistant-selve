# Changelog

All notable changes to this project will be documented in this file.

## [3.3.0] - 2026-02-11

### Added
- **82+ new services** covering the complete Selve USB-RF Gateway protocol (99 total):
  - Firmware management: `firmware_get_version`, `firmware_update`
  - Gateway parameters: `get_temperature`, `set_duty`, `set_rf`, `command_result`
  - Device position saving: `device_save_pos1`, `device_save_pos2`
  - Device movement: `device_move_pos` (move to percentage)
  - Device state control: `device_set_value`, `device_set_target_value`, `device_set_state`
  - senSim support: `sensim_get_ids`, `sensim_get_config`, `sensim_set_config`, `sensim_get_values`, `sensim_set_values`, `sensim_get_test`, `sensim_set_test`, `sensim_set_label`, `sensim_drive`, `sensim_store`, `sensim_delete`, `sensim_factory`
  - IVEO enhancements: `iveo_command_result`, `iveo_set_config`, `iveo_get_config`
  - Sender management: `sender_teach_start`, `sender_teach_stop`, `sender_teach_result`, `sender_get_ids`, `sender_get_info`, `sender_get_values`, `sender_set_label`, `sender_delete`, `sender_write_manual`, `sender_update_values`
  - Sensor management: `sensor_teach_start`, `sensor_teach_stop`, `sensor_teach_result`, `sensor_get_ids`, `sensor_get_info`, `sensor_get_values`, `sensor_set_label`, `sensor_delete`, `sensor_write_manual`, `sensor_update_values`
- All services support `SupportsResponse.OPTIONAL` for return data
- Gateway event firing for device, sensor, sender, duty, and logging events

### Fixed
- **Group name bug**: Group discovery now correctly reads the actual group name instead of the XML-RPC method name (`selve.GW.group.read`)
- **IVEO teach/factory_reset**: Now correctly pass the device `id` parameter
- **Device set_value/target_value/state**: Added missing `await` for synchronous gateway operations
- **Group write**: Properly casts name to `str` before sending
- **Duty/RF responses**: Removed leaked XML method name from service response data
- **services.yaml**: Added 8 missing required fields (id, activity parameters)

### Changed
- Requires `python-selve-new==2.5.0`
- Removed bundled library approach (`sys.path` hack) — now relies on pip-installed dependency via HACS

### Removed
- **`switch_dir` option**: The direction reversal option has been removed as it did not work correctly

## [3.3.1] - 2026-02-11

### Added
- **`open_close_fix` option**: New integration option that clamps position values near boundaries — values 0–1% are reported as 0% (fully closed), 99–100% as 100% (fully open). Disabled by default. Fixes [#41](https://github.com/Kannix2005/homeassistant-selve/issues/41)

### Removed
- **`switch_dir` option**: Removed the broken direction reversal option from integration settings

## [3.2.0] - 2025-01-15

### Added
- Initial comprehensive service coverage
- Cover entities for Commeo, Iveo, and Group devices
- Auto-discovery via USB serial ports
- Position inversion option (`switch_dir`)

See git history for earlier changes.
