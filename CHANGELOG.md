# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [Unreleased]

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
