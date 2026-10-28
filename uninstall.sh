#!/usr/bin/env bash
# uninstall.sh [--prefix DIR] [--purge]   (--purge: 설정 디렉터리까지 삭제)
set -euo pipefail
PREFIX="${PREFIX:-$HOME/.local/bin}"; CONF_DIR="${CLAUDE_WORKER_CONF_DIR:-$HOME/.config/claude-worker}"; PURGE=0
while [ $# -gt 0 ]; do case "$1" in --prefix) PREFIX="$2"; shift 2;; --purge) PURGE=1; shift;; *) echo "unknown: $1" >&2; exit 2;; esac; done
for f in claude-main claude-worker claude-duo llm-probe remote-common.sh remote-info remote-sync remote-fetch remote-run remote-submit; do
    [ -e "$PREFIX/$f" ] && { rm -f "$PREFIX/$f"; echo "removed $PREFIX/$f"; }
done
if [ $PURGE -eq 1 ]; then rm -rf "$CONF_DIR"; echo "removed $CONF_DIR"; else echo "설정은 남겨둠: $CONF_DIR (--purge 로 삭제)"; fi
