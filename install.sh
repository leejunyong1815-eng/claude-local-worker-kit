#!/usr/bin/env bash
# install.sh — Claude 오케스트레이터 + 로컬 LLM 워커 키트 설치
# 사용: ./install.sh [--prefix DIR] [--non-interactive] [--skip-probe] [--render]
#   --prefix DIR        실행 파일 설치 위치 (기본 ~/.local/bin)
#   --non-interactive   질문 없이 환경변수(LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, WORKER_NAME,
#                       COMPUTE_HOST, COMPUTE_WORK_DIR, COMPUTE_DESC)로 설정 파일 작성
#   --skip-probe        설치 후 서버 점검 생략
#   --render            설정 파일을 바꾼 뒤 워커 프롬프트만 다시 생성
set -euo pipefail

KIT="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
PREFIX="${PREFIX:-$HOME/.local/bin}"
CONF_DIR="${CLAUDE_WORKER_CONF_DIR:-$HOME/.config/claude-worker}"
INTERACTIVE=1; PROBE=1; RENDER_ONLY=0
MIN_CLAUDE="2.1.224"   # 크로스 세션 메시징 최소 버전

while [ $# -gt 0 ]; do
    case "$1" in
        --prefix) PREFIX="$2"; shift 2 ;;
        --non-interactive) INTERACTIVE=0; shift ;;
        --skip-probe) PROBE=0; shift ;;
        --render) RENDER_ONLY=1; shift ;;
        -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
        *) echo "알 수 없는 옵션: $1" >&2; exit 2 ;;
    esac
done

say() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }
ver_ge() { [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -1)" = "$2" ]; }

render_prompt() {
    # shellcheck disable=SC1090
    source "$CONF_DIR/env"
    python3 - "$KIT/prompts" "$CONF_DIR/worker.md" <<'PY'
import os, sys
from string import Template
tdir, out = sys.argv[1], sys.argv[2]
env = {k: os.environ.get(k, "") for k in
       ("WORKER_NAME", "COMPUTE_HOST", "COMPUTE_WORK_DIR", "COMPUTE_DESC", "LLM_MODEL", "LLM_CONTEXT_WINDOW")}
env["LLM_MODEL"] = env["LLM_MODEL"] or "a local model"
env["CONTEXT_LINE"] = (f"Your context window is about {int(env['LLM_CONTEXT_WINDOW']):,} tokens."
                       if env["LLM_CONTEXT_WINDOW"].isdigit() else "Your context window is limited.")
env["WORKER_NAME"] = env["WORKER_NAME"] or "llm-worker"
env["COMPUTE_WORK_DIR"] = env["COMPUTE_WORK_DIR"] or "claude-work"
env["COMPUTE_DESC_LINE"] = f" ({env['COMPUTE_DESC']})" if env["COMPUTE_DESC"] else ""
if env["COMPUTE_HOST"]:
    remote = Template(open(os.path.join(tdir, "remote-section.md.tmpl")).read()).safe_substitute(env)
else:
    remote = "\n(No remote compute node is configured. Run everything locally and\nsay so in the report if a task needs more compute than this machine has.)\n"
env["REMOTE_SECTION"] = remote
text = Template(open(os.path.join(tdir, "worker.md.tmpl")).read()).safe_substitute(env)
open(out, "w").write(text)
print(f"worker prompt → {out}")
PY
}

if [ $RENDER_ONLY -eq 1 ]; then
    [ -f "$CONF_DIR/env" ] || die "설정 파일이 없습니다: $CONF_DIR/env"
    render_prompt; exit 0
fi

# ── 1. 필수 도구 ──────────────────────────────────────────────────────────
say "필수 도구 확인"
command -v claude >/dev/null 2>&1 || die "claude 가 없습니다. 설치: curl -fsSL https://claude.ai/install.sh | bash"
CV="$(claude --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || true)"
[ -n "$CV" ] || die "claude --version 을 읽을 수 없습니다"
ver_ge "$CV" "$MIN_CLAUDE" || die "Claude Code $CV 는 너무 오래됐습니다 (>= $MIN_CLAUDE 필요). claude update"
echo "    claude $CV"
for t in python3 curl; do command -v "$t" >/dev/null 2>&1 || die "$t 가 필요합니다"; done
for t in tmux rsync ssh; do command -v "$t" >/dev/null 2>&1 || warn "$t 없음 — claude-duo / remote-* 를 쓰려면 설치하세요"; done

# ── 2. 실행 파일 ──────────────────────────────────────────────────────────
say "실행 파일 설치 → $PREFIX"
mkdir -p "$PREFIX"
for f in "$KIT"/bin/*; do
    install -m 0755 "$f" "$PREFIX/$(basename "$f")"
done
chmod 0644 "$PREFIX/remote-common.sh"
case ":$PATH:" in
    *":$PREFIX:"*) ;;
    *) warn "$PREFIX 가 PATH 에 없습니다. ~/.bashrc 에 추가: export PATH=\"$PREFIX:\$PATH\"" ;;
esac

# ── 3. 설정 파일 ──────────────────────────────────────────────────────────
say "설정 → $CONF_DIR/env"
mkdir -p "$CONF_DIR"; chmod 0700 "$CONF_DIR"
WRITE_ENV=1
if [ -f "$CONF_DIR/env" ]; then
    if [ $INTERACTIVE -eq 1 ]; then
        read -r -p "    설정 파일이 이미 있습니다. 다시 작성할까요? [y/N] " a
        [[ "$a" =~ ^[Yy]$ ]] || WRITE_ENV=0
    else
        [ "${FORCE_ENV:-0}" = "1" ] || WRITE_ENV=0
    fi
fi
if [ $WRITE_ENV -eq 1 ]; then
    if [ $INTERACTIVE -eq 1 ]; then
        echo "    (값을 비우면 괄호 안 기본값)"
        read -r -p "    LLM 서버 주소, /v1 없이 [http://1.233.219.134:8080]: " LLM_BASE_URL
        LLM_BASE_URL="${LLM_BASE_URL:-http://1.233.219.134:8080}"
        read -r -p "    API 토큰 (인증 없으면 아무 문자열) [none]: " LLM_API_KEY
        LLM_API_KEY="${LLM_API_KEY:-none}"
        if [ -n "${LLM_BASE_URL:-}" ]; then
            echo "    서버 모델 목록:"
            "$PREFIX/llm-probe" --models "$LLM_BASE_URL" "?" "$LLM_API_KEY" 2>/dev/null | grep -E '^\s+- ' || echo "      (목록을 못 읽음)"
        fi
        read -r -p "    모델 id [qwen3.6-35b-a3b]: " LLM_MODEL
        LLM_MODEL="${LLM_MODEL:-qwen3.6-35b-a3b}"
        read -r -p "    모델 컨텍스트 창 토큰 수 [131072]: " LLM_CONTEXT_WINDOW
        LLM_CONTEXT_WINDOW="${LLM_CONTEXT_WINDOW:-131072}"
        read -r -p "    워커 세션 이름 [llm-worker]: " WORKER_NAME
        read -r -p "    원격 계산 노드 ssh 별칭 (없으면 비움): " COMPUTE_HOST
        if [ -n "${COMPUTE_HOST:-}" ]; then
            read -r -p "    원격 작업 디렉터리 [claude-work]: " COMPUTE_WORK_DIR
            read -r -p "    노드 설명 한 줄 (예: A6000 48GB x2) []: " COMPUTE_DESC
        fi
    fi
    : "${LLM_BASE_URL:?LLM_BASE_URL 이 필요합니다}"
    : "${LLM_MODEL:?LLM_MODEL 이 필요합니다}"
    LLM_BASE_URL="${LLM_BASE_URL%/}"; LLM_BASE_URL="${LLM_BASE_URL%/v1}"
    cat > "$CONF_DIR/env" <<ENV
# claude-worker 설정 — $(date +%F) install.sh 작성. 설명은 키트의 config/worker.env.example 참고.
export LLM_BASE_URL="$LLM_BASE_URL"
export LLM_API_KEY="${LLM_API_KEY:-none}"
export LLM_MODEL="$LLM_MODEL"
export LLM_DISABLE_BETAS=1
export LLM_DISABLE_PROMPT_CACHING=0
export LLM_MAX_THINKING_TOKENS=""
export LLM_CONTEXT_WINDOW="${LLM_CONTEXT_WINDOW:-131072}"
export LLM_CAPABILITIES="${LLM_CAPABILITIES:-}"
export WORKER_NAME="${WORKER_NAME:-llm-worker}"
export COMPUTE_HOST="${COMPUTE_HOST:-}"
export COMPUTE_WORK_DIR="${COMPUTE_WORK_DIR:-claude-work}"
export COMPUTE_DESC="${COMPUTE_DESC:-}"
ENV
    chmod 0600 "$CONF_DIR/env"
    echo "    작성됨 (0600)"
else
    echo "    기존 설정 유지"
fi

# ── 4. 워커 프롬프트 ──────────────────────────────────────────────────────
say "워커 프롬프트 생성"
render_prompt

# ── 5. 서버 점검 ──────────────────────────────────────────────────────────
if [ $PROBE -eq 1 ]; then
    say "서버 점검 (llm-probe)"
    if ! CLAUDE_WORKER_CONF_DIR="$CONF_DIR" "$PREFIX/llm-probe"; then
        warn "서버 점검에 실패한 항목이 있습니다. docs/TROUBLESHOOTING.md 를 보세요."
    fi
fi

say "완료"
cat <<MSG

다음 단계:
  1) 프로젝트 디렉터리로 이동
  2) claude-duo              # tmux 로 오케스트레이터(왼쪽) + 워커(오른쪽) 동시 실행
     또는 터미널 두 개에서  claude-main  /  claude-worker
  3) 오케스트레이터 대화에서:  Ask @${WORKER_NAME:-llm-worker} to <태스크 한 개의 완결된 지시>
  설정 변경 후:  nano $CONF_DIR/env && $KIT/install.sh --render
MSG
