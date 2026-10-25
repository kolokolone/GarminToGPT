#!/bin/sh
set -eu

DATA_ROOT="${DATA_ROOT:-/appdata}"
APP_ROOT="${APP_ROOT:-/app}"
HOME_ROOT="${HOME_ROOT:-/home/app}"

mkdir -p \
    "$DATA_ROOT/config/garmin" \
    "$DATA_ROOT/config/garmintogpt" \
    "$DATA_ROOT/runtime" \
    "$DATA_ROOT/logs"
mkdir -p "$APP_ROOT" "$HOME_ROOT/.config"

# Route the app defaults (runtime/, logs/, ~/.config/garmin, ~/.config/garmintogpt)
# into the single persistent /appdata bind mount.
rm -rf "$HOME_ROOT/.config/garmin" "$HOME_ROOT/.config/garmintogpt"
ln -s "$DATA_ROOT/config/garmin" "$HOME_ROOT/.config/garmin"
ln -s "$DATA_ROOT/config/garmintogpt" "$HOME_ROOT/.config/garmintogpt"

rm -rf "$APP_ROOT/runtime" "$APP_ROOT/logs"
ln -s "$DATA_ROOT/runtime" "$APP_ROOT/runtime"
ln -s "$DATA_ROOT/logs" "$APP_ROOT/logs"

chown -R app:app "$DATA_ROOT" "$HOME_ROOT/.config" 2>/dev/null || true
export HOME="$HOME_ROOT"

exec gosu app "$@"
