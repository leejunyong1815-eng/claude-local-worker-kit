# remote-common.sh — remote-* 스크립트 공용. 직접 실행하지 않는다.
CONF="${CLAUDE_WORKER_CONF_DIR:-$HOME/.config/claude-worker}/env"
# shellcheck disable=SC1090
[ -f "$CONF" ] && source "$CONF"
COMPUTE_HOST="${COMPUTE_HOST:-}"
COMPUTE_WORK_DIR="${COMPUTE_WORK_DIR:-claude-work}"
if [ -z "$COMPUTE_HOST" ]; then
    echo "remote: COMPUTE_HOST 가 비어 있습니다. $CONF 에서 ssh 별칭을 지정하세요." >&2
    exit 2
fi
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
PROJECT="$(basename "$ROOT")"
REMOTE_ROOT="${COMPUTE_WORK_DIR%/}/$PROJECT"     # 상대 경로면 원격 홈 기준
SSH=(ssh -o BatchMode=yes "$COMPUTE_HOST")
