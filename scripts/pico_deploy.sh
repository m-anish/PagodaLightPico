#!/usr/bin/env bash
set -euo pipefail

# Simple deploy script for MicroPython on Raspberry Pi Pico W using mpremote
# - Detects serial device automatically (or use PORT=/dev/ttyACM0)
# - Uploads project files recursively (excluding common junk)
# - Soft resets the board so main.py runs
#
# Requirements: mpremote (install with: python3 -m pip install --user mpremote)
# Usage:
#   ./scripts/pico_deploy.sh          # auto-detect port, upload, reset
#   PORT=/dev/ttyACM0 ./scripts/pico_deploy.sh
#   NO_RESET=1 ./scripts/pico_deploy.sh  # upload without resetting

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
PORT="${PORT:-}"
NO_RESET="${NO_RESET:-}"

# Auto-detect a likely serial device if PORT not provided
if [[ -z "${PORT}" ]]; then
  PORT=$(ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null | head -n1 || true)
fi

if [[ -z "${PORT}" ]]; then
  echo "[deploy] ERROR: No serial device found (expected something like /dev/ttyACM0)." >&2
  echo "         Plug in the Pico W (with MicroPython) and try again." >&2
  exit 1
fi

echo "[deploy] Using serial device: ${PORT}"

# Verify mpremote availability
if ! command -v mpremote >/dev/null 2>&1; then
  echo "[deploy] ERROR: mpremote not found. Install with:"
  echo "         python3 -m pip install --user mpremote"
  exit 1
fi

cd "${ROOT_DIR}"

# Build list of files to upload (only relevant runtime files)
# - Top-level app files: main.py, boot.py (if present)
# - JSON config/data: *.json (e.g., config.json, sun_times.json)
# - Library code: lib/**/*.py
FILES=()

# Top-level Python entry points
for f in main.py boot.py; do
  if [[ -f "$f" ]]; then FILES+=("./$f"); fi
done

# Top-level JSON files
while IFS= read -r -d '' f; do FILES+=("${f}"); done < <(find . -maxdepth 1 -type f -name '*.json' -print0)

# lib/**/*.py
if [[ -d ./lib ]]; then
  while IFS= read -r -d '' f; do FILES+=("${f}"); done < <(find ./lib -type f -name '*.py' -print0)
fi

# Optional: include vendor libs like umqtt already under lib/

# Filter out caches and temp files, just in case
FILTERED=()
for f in "${FILES[@]}"; do
  case "$f" in
    *"/__pycache__"/*|*.pyc|*.pyo|*.swp|*.tmp)
      ;; # skip
    *)
      FILTERED+=("$f")
      ;;
  esac
done
FILES=("${FILTERED[@]}")

if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "[deploy] No files to upload."
  exit 0
fi

echo "[deploy] Uploading ${#FILES[@]} files to Pico W (Python + JSON only)..."

# Ensure directories exist on device and copy files
for f in "${FILES[@]}"; do
  # Strip leading ./
  rel="${f#./}"
  dest_dir=":/$(dirname "$rel")"
  # Create destination directory (ignore errors if exists)
  if [[ -n "${DRY_RUN:-}" ]]; then
    echo "[deploy][DRY_RUN] mkdir ${dest_dir} && cp $rel -> :/${rel}"
  else
    mpremote connect "${PORT}" fs mkdir "${dest_dir}" >/dev/null 2>&1 || true
    # Copy the file
    mpremote connect "${PORT}" fs cp "$f" ":/${rel}"
    echo "[deploy] Copied $rel"
  fi
done

if [[ -z "${NO_RESET}" && -z "${DRY_RUN:-}" ]]; then
  echo "[deploy] Soft resetting device..."
  mpremote connect "${PORT}" exec 'import machine; machine.reset()'
  echo "[deploy] Done. Device reset; main.py should run."
else
  echo "[deploy] Upload complete (NO_RESET=1 set; not resetting)."
fi
