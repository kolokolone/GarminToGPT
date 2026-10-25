#!/bin/sh
set -eu

CONFIG_ROOT="${CONFIG_ROOT:-/home/app/.config}"
LEGACY_GARMIN="${LEGACY_GARMIN:-/legacy/garmin}"
LEGACY_GARMINTOGPT="${LEGACY_GARMINTOGPT:-/legacy/garmintogpt}"

mkdir -p "$CONFIG_ROOT/garmin" "$CONFIG_ROOT/garmintogpt"
mkdir -p /app/logs /app/runtime 2>/dev/null || true

# One-time migration from the named volumes used by <= 1.1.2. Existing files
# in the bind mount win; missing files are copied from the legacy volume.
for pair in "garmin:$LEGACY_GARMIN" "garmintogpt:$LEGACY_GARMINTOGPT"; do
    target="$CONFIG_ROOT/${pair%%:*}"
    legacy="${pair#*:}"
    if [ -d "$legacy" ]; then
        cp -an "$legacy"/. "$target"/ 2>/dev/null || true
    fi
done

# Bind mounts created by Docker may be root-owned on Linux. Fix ownership
# without making startup fail on platforms where chown is not permitted.
chown -R app:app "$CONFIG_ROOT" /app/logs /app/runtime 2>/dev/null || true

exec gosu app "$@"
