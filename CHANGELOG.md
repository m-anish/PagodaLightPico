# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [Unreleased]

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
