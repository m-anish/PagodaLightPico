# Simple convenience targets for deploying to Raspberry Pi Pico W

PORT ?=
NO_RESET ?=
DRY_RUN ?=

.PHONY: deploy deploy-dry deploy-nr

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
