#!/bin/sh
# Explicit startup opt-in, no secrets printed, no install or budget changes.
set -eu
optin=${CRAYON_COMPUTER_AUTOSTART:-off}
if [ "$optin" = off ] && [ -r "$HOME/.config/crayon/autostart" ]; then
    optin=$(cat "$HOME/.config/crayon/autostart")
fi
[ "$optin" = on ] || exit 0
[ -r "$HOME/.config/crayon/bridge-token" ] || [ -n "${CRAYON_BRIDGE_TOKEN:-}" ] || exit 0
cd "$(dirname "$0")"
pgrep -f '^python3 computer_worker.py$' >/dev/null && exit 0
umask 077
# Keep the bounded worker independent of the short-lived postStart session.
setsid nohup python3 computer_worker.py </dev/null >"$HOME/.config/crayon/worker.log" 2>&1 &
