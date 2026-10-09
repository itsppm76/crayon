#!/bin/sh
# Stdlib supervisor records disabled, failed, ready and exited startup outcomes.
set -eu
cd "$(dirname "$0")"
umask 077
mkdir -p "$HOME/.config/crayon"
pgrep -f '^python3 -u computer_boot.py$' >/dev/null && exit 0
setsid nohup python3 -u computer_boot.py </dev/null >"$HOME/.config/crayon/boot-supervisor.log" 2>&1 &
