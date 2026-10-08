#!/bin/sh
# Explicit startup opt-in, no secrets printed, no install or budget changes.
set -eu
[ "${CRAYON_COMPUTER_AUTOSTART:-off}" = on ] || exit 0
[ -r "$HOME/.config/crayon/bridge-token" ] || [ -n "${CRAYON_BRIDGE_TOKEN:-}" ] || exit 0
cd "$(dirname "$0")"
pgrep -f '^python3 computer_worker.py$' >/dev/null && exit 0
nohup python3 computer_worker.py >"$HOME/.config/crayon/worker.log" 2>&1 &
