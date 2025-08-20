# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [Unreleased]

## [0.3.0] - 2025-08-21

### Changed
- UI (Homepage Controllers table): increase horizontal scroll fade width by ~50% (24px -> 36px) on both left and right edges for clearer scroll affordance on small screens.
- Keep fades pinned to container edges during horizontal scrolling by using an inner `.table-scroll` element and toggling visibility classes (`.has-left`, `.has-right`) on the outer `.table-responsive` wrapper.

### Notes
- No changes to backend logic or APIs. Pure UX refinement for mobile usability.

## [0.2.2] - 2025-08-21

### Changed
- Homepage ("/"): implement streamed response writer to significantly reduce RAM usage during page generation. Response is sent in small chunks without `Content-Length` and closes the connection when finished.
- Added async `_awrite()` helper and `stream_main_page()`; request handler updated to use streaming for the root path.

### Notes
- Other endpoints keep the previous buffered responses for now.

## [0.2.1] - 2025-08-21

### Added
- Homepage: lightweight Unicode symbols for key labels (time, config version, WiFi, MQTT, controllers, footer actions).

### Changed
- Homepage: broadened font stack to include emoji-capable system fonts for reliable symbol rendering, without adding external assets.
- Reverted previous inline SVG sprite approach to avoid memory pressure on Pico W during page generation.

### Notes
- Medium-term improvement tracked in `TODO.md`: implement streamed response writer for "/" to further reduce RAM usage during page generation.

## [0.2.0] - 2025-08-21

### Added
- Main page: display the running configuration version.
- Footer: reorganized into a 4-column layout (Status | Upload | Download | Restart) with stacked links for Upload/Download.

### Changed
- Web server responses now set Content-Length based on UTF-8 encoded byte length and include charset in headers for all endpoints.
- Response sending logic updated to write the entire response in a loop to avoid partial socket sends.

### Fixed
- Eliminated browser `net::ERR_CONTENT_LENGTH_MISMATCH` that caused clocks and countdown timers to stop updating on the main page.

### Validation/Security
- Enforce strict major.minor version prefix validation for uploaded `config.json` and `sun_times.json` files, based on the currently running config version. Uploads without a semantic version or with an incompatible major.minor are rejected.

### Documentation
- Updated `README.md` to document strict version enforcement and the displayed config version on the main page.

## [0.1.4] - 2025-08-20

### Added
- Homepage: show all Controllers including inactive (disabled) ones with an orange background. Section renamed from "PWM Controllers" to "Controllers".

### Changed
- Homepage: replaced "WiFi: Connected" with "WiFi: <SSID>, <IP>" in the same row.
- Homepage: removed redundant "Web Server: Running" status block.
- Network: increased WiFi/network health check interval from 30s to 120s to reduce unnecessary checks.

### Fixed
- Homepage: fixed a rendering error caused by an invalid f-string default expression.

## [0.1.3] - 2025-08-20

### Documentation
- Consolidated all essential docs into a single concise `README.md`:
  - Added sections: Networking (mDNS), Notifications (MQTT), Troubleshooting, Developer Quickstart.
- Marked the following files for removal as redundant/outdated (content merged or obsolete):
  - `ASYNC_MIGRATION.md`
  - `HARDWARE.md`
  - `INSTALL_MDNS.md`
  - `MDNS_SETUP.md`
  - `MQTT_BROKERS.md`
  - `PUSH_NOTIFICATIONS.md`
  - `TIMEOUT_TROUBLESHOOTING.md`
  - `WARP.md`
  - `system_architecture.md`
  - `QWEN.md`

### Notes
- Runtime behavior unchanged. This release focuses on documentation simplification.

## [0.1.2] - 2025-08-20

### Removed
- Deleted unused modules with zero references:
  - `lib/gpio_utils.py`
  - `lib/network_diagnostics.py`
  - `lib/config_validator.py`

### Documentation
- Updated `TIMEOUT_TROUBLESHOOTING.md` to remove references to automatic diagnostics and clarify what to look for in logs.
- Updated `MDNS_SETUP.md` to remove a non-existent standalone test script and provide manual verification steps for mDNS.

### Notes
- No functional/runtime behavior changes intended. Core modules like `lib/web_server.py`, `lib/config_manager.py`, `lib/mqtt_notifier.py`, and `lib/rtc_module.py` remain unchanged.
- This release focuses on codebase cleanup and documentation accuracy.
