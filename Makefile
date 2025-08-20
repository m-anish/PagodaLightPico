# Simple convenience targets for deploying to Raspberry Pi Pico W

PORT ?=
NO_RESET ?=
DRY_RUN ?=

.PHONY: deploy deploy-dry deploy-nr logs reboot

## deploy: Upload Python + JSON files to Pico W and soft-reset
deploy:
	@echo "[make] Deploying to Pico W..."
	@PORT=$(PORT) NO_RESET=$(NO_RESET) DRY_RUN=$(DRY_RUN) ./scripts/pico_deploy.sh

## deploy-dry: Preview what would be uploaded (no writes)
deploy-dry:
	@$(MAKE) deploy DRY_RUN=1

## deploy-nr: Upload without resetting the board
deploy-nr:
	@$(MAKE) deploy NO_RESET=1

## logs: Attach to MicroPython REPL to view prints/logs (Ctrl-] to quit)
logs:
	@PORT_DET=$${PORT:-$$(ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null | head -n1)}; \
	if [ -z "$$PORT_DET" ]; then \
	  echo "[make] ERROR: No serial device found. Set PORT=/dev/ttyACM0"; \
	  exit 1; \
	fi; \
	echo "[make] Connecting to $$PORT_DET (REPL)..."; \
	mpremote connect "$$PORT_DET" repl

## reboot: Soft-reset the device (Ctrl-D). Falls back to machine.reset().
reboot:
	@PORT_DET=$${PORT:-$$(ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null | head -n1)}; \
	if [ -z "$$PORT_DET" ]; then \
	  echo "[make] ERROR: No serial device found. Set PORT=/dev/ttyACM0"; \
	  exit 1; \
	fi; \
	echo "[make] Soft resetting $$PORT_DET..."; \
	if mpremote connect "$$PORT_DET" soft-reset >/dev/null 2>&1; then \
	  echo "[make] Soft reset OK."; \
	else \
	  echo "[make] soft-reset failed; trying machine.reset()..."; \
	  mpremote connect "$$PORT_DET" exec 'import machine; machine.reset()' >/dev/null 2>&1 || true; \
	  echo "[make] Reset command sent."; \
	fi
