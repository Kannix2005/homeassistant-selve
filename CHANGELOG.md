# Changelog

All notable changes to this project will be documented in this file.

## [3.3.14] - 2026-07-26

### Fixed
- **Home Assistant retries the setup again**: `async_setup_entry` raised `PlatformNotReady`, which HA only handles on platform level — on entry level it meant the integration stayed dead after a failed start (e.g. gateway briefly missing from the USB bus) until someone reloaded it by hand. It now raises `ConfigEntryNotReady`.
- **Cover commands report failures**: open/close/stop/set position now raise `HomeAssistantError` with the device name instead of letting a library exception surface as a bare "unknown error" and aborting automations with a raw traceback.
- **Group covers no longer claim a position they don't have**: groups reported a hardcoded 50%, which made `is_closed` permanently `False` — every automation or template checking a Selve group was silently wrong. Groups now report an unknown position. Commands are unaffected.
- Adding the same serial port twice is rejected (`unique_id`), instead of creating a second entry fighting over the same gateway.
- Changing the port in the options no longer triggers two overlapping reloads on the same port.
- Binary sensors expose `selve_device_id` again (`device_state_attributes` has been ignored by HA since 2021.12); the same dead property was removed from covers.
- `async_migrate_entry` passes the new version to `async_update_entry` instead of assigning `config_entry.version` directly.

### Changed
- Requires python-selve-new 2.5.16 (correct gateway acknowledgements, response-to-request matching, link-state notifications).

## [3.3.13] - 2026-07-26

### Fixed
- **Reloading the integration works again**: `async_unload_entry` and the gateway's `async_reset()` both unloaded all three platforms — the second unload made every reload fail with `require_restart` and left all entities unavailable until a full Home Assistant restart. Platforms now unload exactly once.
- **Entities go unavailable when the gateway is dead** instead of showing frozen state: availability of covers, sensors and binary sensors is now bound to `Selve.connected` (python-selve-new 2.5.15). During the 2026-07-25 gateway hang, covers showed a stale "opening" for 12+ hours and swallowed commands without any visible failure — that state is now visibly "unavailable".
- Cover position handles the library's new "position unknown" (`None`) — no more phantom 50% jumps after stops, no crash on unknown positions.

### Changed
- Requires python-selve-new 2.5.15 (gateway-hang self-recovery — see its changelog).

## [3.3.12] - 2026-06-17

### Added
- **More reliable IVEO covers** (python-selve-new 2.5.14): IVEO is one-way (no motor feedback), so a lost RF telegram silently left the shutter where it was while HA showed it moved — the cause of "kitchen sometimes doesn't react". IVEO drive commands now repeat the telegram (handsender-style), check the gateway's send acknowledgement, and wait out a blocked duty cycle instead of firing into it.
- **Gateway RF duty-cycle sensor** (diagnostic): exposes the 868 MHz airtime utilization with a `sending_blocked` attribute, so multi-cover scenes hitting the duty limit are visible and usable in automations.

### Fixed
- Unload path only ever unloaded the `cover` platform (it iterated `PLATFORMS=["cover"]`), so `binary_sensor` entities were never properly torn down on reload. All platforms (`cover`, `binary_sensor`, `sensor`) now unload correctly.

## [3.3.11] - 2026-06-12

### Fixed
- Device registry deprecation warnings ("passes a non-string value of type CommunicationType as model"): `device_info` now passes `model` as string (`.name`) and `sw_version` as string. The enum values would stop working in Home Assistant 2026.12.

## [3.3.10] - 2026-06-12

### Fixed
- **No more "Serial: no data for 60s — reconnecting" every minute**: python-selve-new 2.5.13 sends a keepalive ping after 30s of link silence, so the serial idle-reconnect only fires when the port is actually dead. This also closes a window in which gateway events (e.g. covers moved via physical remote) could be silently lost during the periodic reconnect.

## [3.3.9] - 2026-06-12

### Changed
- **python-selve-new 2.5.12**: response-paced serial transmission instead of a fixed 100ms delay per command — device discovery at startup is roughly 3x faster, commands run at gateway speed (~30-40ms). Gateway error replies no longer stall service calls for 10+ seconds.
- **Per-device state updates**: cover and binary_sensor entities now only write their state when *their own* device changed. Previously every gateway event triggered a state write on every Selve entity (N entities x M events during movement).
- Removed the redundant per-entity `DeviceGetValues` round-trip in `async_added_to_hass` — values are already fresh from gateway discovery at startup.
- Removed per-access debug logging in the binary_sensor `state` property (log spam, string building on every state machine read).

## [3.3.8] - 2026-05-13

### Fixed
- `selve_event` not JSON serializable: event data contained `untangle.Element` objects (e.g. `response.name` for log events), `LogType` / `ParameterType` enums, and similar non-JSON types. Added `_serialize_event_value` helper that converts enums to `.name`, untangle elements to `.cdata`, and recursively handles lists/tuples, so the HA recorder no longer logs `Type is not JSON serializable: Element` warnings.
- `device_scan_result` service always returning empty: `scanResult()` always times out because the library's dispatch loop intercepts `DeviceScanResultResponse` (to fire the event callback) and returns `True` instead of the response object, leaving the sync future unresolved. The fix caches the last scan result in `_event_callback` (`self._last_scan_result`) and returns it from the service when the direct poll fails.

## [3.3.7] - 2026-05-13

### Fixed
- `device_scan_result` service crash: `scanResult()` can return `False` when no scan is running; accessing `.foundIds` on a boolean caused `AttributeError`. Now guarded — returns empty idle result when response is not an object. (fixes #42)
- Iveo cover tilt/intermediate positions: `OPEN_TILT`, `CLOSE_TILT`, and `STOP_TILT` features were missing from `supported_features` for Iveo devices, so HA never exposed the tilt buttons. The underlying `moveDevicePos1` (POS1) and `moveDevicePos2` (POS2) commands were already implemented in python-selve-new. Removed misleading `SET_POSITION` from Iveo features (mapped to up/down only, not real positioning). (fixes #22)

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
