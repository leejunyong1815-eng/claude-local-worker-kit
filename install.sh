#!/usr/bin/env bash
# install.sh — Claude 오케스트레이터 + 로컬 LLM 워커 키트 설치
# 사용: ./install.sh [--prefix DIR] [--non-interactive] [--skip-probe]
#       ./install.sh --profile NAME [--non-interactive] [--skip-probe]   다른 모델용 워커 프로필 추가 (env.NAME, 예: gb10)
#       ./install.sh --render                                            설정 변경 후 워커 프롬프트만 재생성 (모든 프로필)
#   --prefix DIR        실행 파일 설치 위치 (기본 ~/.local/bin)
#   --non-interactive   질문 없이 환경변수로 설정: LLM_BASE_URL LLM_API_KEY LLM_MODEL LLM_CONTEXT_WINDOW
#                       WORKER_NAME COMPUTE_HOST COMPUTE_WORK_DIR COMPUTE_DESC  (기존 파일 덮어쓰기: FORCE_ENV=1)
set -euo pipefail

KIT="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
PREFIX="${PREFIX:-$HOME/.local/bin}"
CONF_DIR="${CLAUDE_WORKER_CONF_DIR:-$HOME/.config/claude-worker}"
INTERACTIVE=1; PROBE=1; RENDER_ONLY=0; PROFILE=""
MIN_CLAUDE="2.1.224"   # 크로스 세션 메시징 최소 버전

# 연구실 기본값 — 서버가 바뀌면 여기만 고친다.
# 접속점은 LLM 서버의 LiteLLM 게이트웨이. 그 뒤에 같은 호스트의 llama.cpp(qwen3.6-35b-a3b)와 GB10 노드가 붙는다 (proxy/ 참고).
LAB_HOST="http://1.233.219.134"
LAB_DEFAULT_PORT=4000                 # LiteLLM. (LiteLLM 이 죽었을 때 임시 우회: 8080 = llama.cpp 직접)
LAB_DEFAULT_MODEL="qwen3.6-35b-a3b"   # LiteLLM model_name = llama.cpp 별칭
# 컨텍스트는 "요청 하나가 쓸 수 있는 크기"다. 설치기는 먼저 서버 /v1/models 의 max_input_tokens(LiteLLM 이 알려 줌)를 쓰고,
# 없을 때만 아래 값을 쓴다. 아래 값 = LLM 서버 llama.cpp 직접 접속 때의 크기 (--ctx-size 131072 --kv-unified, 2026-10-29 패치 후).
LAB_DEFAULT_CTX=131072
# GB10 노드 모델이 LiteLLM 에 등록되면 채운다 → 프로필 gb10 의 기본값. 비어 있으면 설치기가 서버 모델 목록을 보여 주고 묻는다.
LAB_GB10_MODEL="";  LAB_GB10_CTX=""

while [ $# -gt 0 ]; do
    case "$1" in
        --prefix) PREFIX="$2"; shift 2 ;;
        --non-interactive) INTERACTIVE=0; shift ;;
        --skip-probe) PROBE=0; shift ;;
        --render) RENDER_ONLY=1; shift ;;
        --profile) PROFILE="$2"; shift 2 ;;
        -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
        *) echo "알 수 없는 옵션: $1" >&2; exit 2 ;;
    esac
done
[[ -z "$PROFILE" || "$PROFILE" =~ ^[A-Za-z0-9_-]+$ ]] || { echo "프로필 이름은 영문·숫자·-_ 만: $PROFILE" >&2; exit 2; }

say() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }
ver_ge() { [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -1)" = "$2" ]; }

render_prompt() { # render_prompt <env파일> <출력 md>
    # shellcheck disable=SC1090
    ( source "$1"; export WORKER_NAME COMPUTE_HOST COMPUTE_WORK_DIR COMPUTE_DESC LLM_MODEL LLM_CONTEXT_WINDOW
      python3 - "$KIT/prompts" "$2" <<'PY'
import os, sys
from string import Template
tdir, out = sys.argv[1], sys.argv[2]
env = {k: os.environ.get(k, "") for k in
       ("WORKER_NAME", "COMPUTE_HOST", "COMPUTE_WORK_DIR", "COMPUTE_DESC", "LLM_MODEL", "LLM_CONTEXT_WINDOW")}
env["WORKER_NAME"] = env["WORKER_NAME"] or "llm-worker"
env["COMPUTE_WORK_DIR"] = env["COMPUTE_WORK_DIR"] or "claude-work"
env["LLM_MODEL"] = env["LLM_MODEL"] or "a local model"
env["CONTEXT_LINE"] = (f"Your context window is about {int(env['LLM_CONTEXT_WINDOW']):,} tokens."
                       if env["LLM_CONTEXT_WINDOW"].isdigit() else "Your context window is limited.")
env["COMPUTE_DESC_LINE"] = f" ({env['COMPUTE_DESC']})" if env["COMPUTE_DESC"] else ""
if env["COMPUTE_HOST"]:
    remote = Template(open(os.path.join(tdir, "remote-section.md.tmpl")).read()).safe_substitute(env)
else:
    remote = "\n(No remote compute node is configured. Run everything locally and\nsay so in the report if a task needs more compute than this machine has.)\n"
env["REMOTE_SECTION"] = remote
text = Template(open(os.path.join(tdir, "worker.md.tmpl")).read()).safe_substitute(env)
open(out, "w").write(text)
print(f"    worker prompt → {out}")
PY
    )
}

render_all() {
    [ -f "$CONF_DIR/env" ] && render_prompt "$CONF_DIR/env" "$CONF_DIR/worker.md"
    for f in "$CONF_DIR"/env.*; do
        [ -f "$f" ] || continue
        render_prompt "$f" "$CONF_DIR/worker.${f##*/env.}.md"
    done
}

detect_ctx() { # detect_ctx <url> <key> <model> → 서버가 /v1/models 에 적어 둔 max_input_tokens (없거나 연결 실패면 빈 출력, 항상 성공)
    { curl -s -m 8 -H "Authorization: Bearer $2" -H "x-api-key: $2" "$1/v1/models" 2>/dev/null || true; } | python3 -c '
import sys, json
try:
    for m in json.load(sys.stdin).get("data", []):
        if m.get("id") == sys.argv[1] and str(m.get("max_input_tokens", "")).isdigit():
            print(m["max_input_tokens"]); break
except Exception:
    pass' "$3" 2>/dev/null || true
}

write_env() { # write_env <env파일> <기본URL> <기본모델> <기본ctx> <기본워커이름> <COMPUTE 상속 env|빈값>
    local file="$1" d_url="$2" d_model="$3" d_ctx="$4" d_name="$5" inherit="$6"
    local url="${LLM_BASE_URL:-}" key="${LLM_API_KEY:-}" model="${LLM_MODEL:-}" ctx="${LLM_CONTEXT_WINDOW:-}" name="${WORKER_NAME:-}"
    local chost="${COMPUTE_HOST:-}" cdir="${COMPUTE_WORK_DIR:-}" cdesc="${COMPUTE_DESC:-}"
    local d_key="none" d_key_label="none"
    if [ -n "$inherit" ] && [ -f "$inherit" ]; then   # 프로필은 기본 env 의 서버 주소·키·원격 노드 설정을 물려받는다 (모델만 다름)
        # shellcheck disable=SC1090
        eval "$(grep -E '^export (COMPUTE_(HOST|WORK_DIR|DESC)|LLM_BASE_URL|LLM_API_KEY)=' "$inherit" | sed 's/^export /ih_/')"
        chost="${chost:-${ih_COMPUTE_HOST:-}}"; cdir="${cdir:-${ih_COMPUTE_WORK_DIR:-}}"; cdesc="${cdesc:-${ih_COMPUTE_DESC:-}}"
        d_url="${ih_LLM_BASE_URL:-$d_url}"; d_key="${ih_LLM_API_KEY:-none}"
        [ "$d_key" = "none" ] || d_key_label="기본 env 와 같은 키"
    fi
    if [ $INTERACTIVE -eq 1 ]; then
        echo "    (Enter 는 괄호 안 기본값)"
        read -r -p "    LLM 서버 주소, /v1 없이 [$d_url]: " url;  url="${url:-$d_url}"
        read -r -p "    API 토큰 (LiteLLM 키 sk-… / 인증 없으면 아무 문자열) [$d_key_label]: " key; key="${key:-$d_key}"
        echo "    서버 모델 목록:"
        "$PREFIX/llm-probe" --models "$url" "?" "$key" 2>/dev/null | grep -E '^\s+- ' || echo "      (목록을 못 읽음 — 서버가 아직 안 떠 있을 수 있다)"
        while :; do
            read -r -p "    모델 id${d_model:+ [$d_model]}: " model; model="${model:-$d_model}"
            [ -n "$model" ] && break; echo "    모델 id 는 비울 수 없습니다. 위 목록에서 고르세요."
        done
        det="$(detect_ctx "$url" "$key" "$model")"
        [ -n "$det" ] && { d_ctx="$det"; echo "    (서버가 알려 준 이 모델의 컨텍스트: $det 토큰)"; }
        read -r -p "    모델 컨텍스트 창 토큰 수 [$d_ctx]: " ctx; ctx="${ctx:-$d_ctx}"
        read -r -p "    워커 세션 이름 [$d_name]: " name; name="${name:-$d_name}"
        if [ -z "$inherit" ]; then
            read -r -p "    원격 계산 노드 ssh 별칭 (없으면 비움): " chost
            if [ -n "$chost" ]; then
                read -r -p "    원격 작업 디렉터리 [claude-work]: " cdir
                read -r -p "    노드 설명 한 줄 (예: A6000 48GB x2) []: " cdesc
            fi
        fi
    else
        url="${url:-$d_url}"; key="${key:-$d_key}"; model="${model:-$d_model}"; name="${name:-$d_name}"
        [ -n "$ctx" ] || ctx="$(detect_ctx "${url%/v1}" "$key" "$model")"; ctx="${ctx:-$d_ctx}"
        [ -n "$model" ] || die "LLM_MODEL 이 필요합니다 (이 프로필의 기본 모델이 아직 정해지지 않음). 예: LLM_MODEL=gb10 ./install.sh --profile gb10 --non-interactive"
    fi
    url="${url%/}"; url="${url%/v1}"
    cat > "$file" <<ENV
# claude-worker 설정 — $(date +%F) install.sh 작성. 설명은 키트의 config/worker.env.example 참고.
export LLM_BASE_URL="$url"
export LLM_API_KEY="$key"
export LLM_MODEL="$model"
export LLM_CONTEXT_WINDOW="$ctx"
export LLM_DISABLE_BETAS=1
export LLM_DISABLE_PROMPT_CACHING=0
export LLM_MAX_THINKING_TOKENS=""
export LLM_CAPABILITIES="${LLM_CAPABILITIES:-}"
export WORKER_NAME="$name"
export COMPUTE_HOST="$chost"
export COMPUTE_WORK_DIR="${cdir:-claude-work}"
export COMPUTE_DESC="$cdesc"
ENV
    chmod 0600 "$file"
    echo "    작성됨: $file (0600)"
}

if [ $RENDER_ONLY -eq 1 ]; then
    [ -f "$CONF_DIR/env" ] || die "설정 파일이 없습니다: $CONF_DIR/env"
    say "워커 프롬프트 재생성"; render_all; exit 0
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
for f in "$KIT"/bin/*; do install -m 0755 "$f" "$PREFIX/$(basename "$f")"; done
chmod 0644 "$PREFIX/remote-common.sh"
case ":$PATH:" in
    *":$PREFIX:"*) ;;
    *) warn "$PREFIX 가 PATH 에 없습니다. ~/.bashrc 에 추가: export PATH=\"$PREFIX:\$PATH\"" ;;
esac

# ── 3. 설정 파일 ──────────────────────────────────────────────────────────
mkdir -p "$CONF_DIR"; chmod 0700 "$CONF_DIR"
if [ -n "$PROFILE" ]; then
    ENV_FILE="$CONF_DIR/env.$PROFILE"
    say "워커 프로필 '$PROFILE' → $ENV_FILE"
    [ -f "$CONF_DIR/env" ] || warn "기본 설정($CONF_DIR/env)이 없습니다. 먼저 ./install.sh 를 돌리는 것이 보통입니다."
    D_URL="$LAB_HOST:$LAB_DEFAULT_PORT"; D_MODEL=""; D_CTX="$LAB_DEFAULT_CTX"   # 같은 LiteLLM, 모델은 다른 것
    if [ "$PROFILE" = "gb10" ] && [ -n "$LAB_GB10_MODEL" ]; then D_MODEL="$LAB_GB10_MODEL"; D_CTX="${LAB_GB10_CTX:-$LAB_DEFAULT_CTX}"; fi
    D_NAME="llm-worker-$PROFILE"; INHERIT="$CONF_DIR/env"
else
    ENV_FILE="$CONF_DIR/env"
    say "설정 → $ENV_FILE"
    D_URL="$LAB_HOST:$LAB_DEFAULT_PORT"; D_MODEL="$LAB_DEFAULT_MODEL"; D_CTX="$LAB_DEFAULT_CTX"; D_NAME="llm-worker"; INHERIT=""
fi
WRITE_ENV=1
if [ -f "$ENV_FILE" ]; then
    if [ $INTERACTIVE -eq 1 ]; then
        read -r -p "    설정 파일이 이미 있습니다. 다시 작성할까요? [y/N] " a
        [[ "$a" =~ ^[Yy]$ ]] || WRITE_ENV=0
    else
        [ "${FORCE_ENV:-0}" = "1" ] || WRITE_ENV=0
    fi
fi
if [ $WRITE_ENV -eq 1 ]; then write_env "$ENV_FILE" "$D_URL" "$D_MODEL" "$D_CTX" "$D_NAME" "$INHERIT"
else echo "    기존 설정 유지"; fi

# ── 4. 워커 프롬프트 ──────────────────────────────────────────────────────
say "워커 프롬프트 생성"
render_prompt "$ENV_FILE" "$CONF_DIR/worker${PROFILE:+.$PROFILE}.md"

# ── 5. 서버 점검 ──────────────────────────────────────────────────────────
if [ $PROBE -eq 1 ]; then
    say "서버 점검 (llm-probe)"
    if ! CLAUDE_WORKER_CONF_DIR="$CONF_DIR" "$PREFIX/llm-probe" ${PROFILE:+-P "$PROFILE"}; then
        warn "서버 점검에 실패한 항목이 있습니다. docs/TROUBLESHOOTING.md 를 보세요."
    fi
fi

# ── 6. 다른 모델(GB10) 안내 (기본 설치 때만) ──────────────────────────────
if [ -z "$PROFILE" ] && [ -n "$LAB_GB10_MODEL" ] && [ ! -f "$CONF_DIR/env.gb10" ]; then
    if [ $INTERACTIVE -eq 1 ]; then
        read -r -p "    GB10 노드 모델($LAB_GB10_MODEL) 워커 프로필 'gb10' 도 만들까요? [Y/n] " a
        if [[ ! "$a" =~ ^[Nn]$ ]]; then
            unset LLM_BASE_URL LLM_API_KEY LLM_MODEL LLM_CONTEXT_WINDOW WORKER_NAME
            say "워커 프로필 'gb10' → $CONF_DIR/env.gb10"
            write_env "$CONF_DIR/env.gb10" "$LAB_HOST:$LAB_DEFAULT_PORT" "$LAB_GB10_MODEL" "${LAB_GB10_CTX:-$LAB_DEFAULT_CTX}" "llm-worker-gb10" "$CONF_DIR/env"
            render_prompt "$CONF_DIR/env.gb10" "$CONF_DIR/worker.gb10.md"
            [ $PROBE -eq 1 ] && { CLAUDE_WORKER_CONF_DIR="$CONF_DIR" "$PREFIX/llm-probe" -P gb10 || warn "gb10 모델 점검 실패 (아직 등록 전이면 정상)"; }
        fi
    else
        echo "    (GB10 프로필은 ./install.sh --profile gb10 --non-interactive 로 추가)"
    fi
fi

say "완료"
WN="$(grep -E '^export WORKER_NAME=' "$ENV_FILE" | sed -E 's/.*="(.*)"/\1/')"
cat <<MSG

다음 단계:
  1) 프로젝트 디렉터리로 이동
  2) claude-duo                 # tmux: 오케스트레이터(왼쪽) + 기본 워커(오른쪽)
     claude-duo -P gb10         # 기본 워커 + GB10 모델 워커 (프로필을 만들었을 때)
     또는 터미널마다  claude-main  /  claude-worker  /  claude-worker -P gb10
  3) 오케스트레이터 대화에서:  Ask @${WN} to <태스크 한 개의 완결된 지시>
  설정 변경 후:  nano $CONF_DIR/env  (또는 env.<프로필>)  &&  $KIT/install.sh --render
MSG
