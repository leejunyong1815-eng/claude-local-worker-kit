#!/usr/bin/env bash
# agents/hooks/post-edit-check.sh — Claude Code PostToolUse 훅 (Edit|Write|MultiEdit 뒤에 실행).
# 고친 파일을 바로 검사(문법 → lint → 테스트)하고, 실패하면 그 출력을 모델에게 돌려준다
# (종료 코드 2 → stderr 가 모델의 다음 턴에 들어간다). 로컬 모델이 "테스트 돌리기"를 잊어도 훅은 잊지 않는다.
# 설정: agents/hooks/check.conf (쉘 문법, 없으면 기본값). 결과 로그: agents/hooks/last-check.log
set -uo pipefail
ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)}"
IN="$(cat)"
FILE="$(printf '%s' "$IN" | python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))
except Exception: print("")' 2>/dev/null)"
[ -n "$FILE" ] && [ -f "$FILE" ] || exit 0
case "$FILE" in "$ROOT"/*) ;; *) exit 0 ;; esac          # 프로젝트 밖 파일은 검사하지 않는다

CONF="$ROOT/agents/hooks/check.conf"
# shellcheck disable=SC1090
[ -f "$CONF" ] && source "$CONF"
LINT_PY="${LINT_PY:-auto}"          # auto | ruff | pyflakes | none
TEST_CMD="${TEST_CMD:-none}"        # none(기본: 문법·lint 만) | auto(tests/ 가 있으면 pytest -x -q) | "<명령>"
                                    # 기본이 none 인 이유: 2026-10-29 벤치마크에서 편집마다 테스트를 돌려 주면 어려운 태스크 성적이 오히려 나빠졌다
                                    # (반쯤 쓴 모듈의 첫 실패를 쫓느라 설계를 못 끝냄). 테스트는 워커가 스스로 돌린다. 필요하면 check.conf 에서 auto.
TEST_ON="${TEST_ON:-\.py$}"         # 이 정규식에 맞는 파일을 고쳤을 때만 테스트를 돌린다
TEST_TIMEOUT="${TEST_TIMEOUT:-120}" # 초. 넘기면 실패로 치지 않고 로그에만 남긴다
TAIL_LINES="${TAIL_LINES:-40}"
LOG="$ROOT/agents/hooks/last-check.log"
# Managed mode already collects process logs outside the worktree. Do not create
# an ignored but out-of-policy log alongside the source or persist raw secrets.
[ "${WORKER_TASK_MANAGED:-0}" = 1 ] && LOG=/dev/null

fail=0; out=""
case "$FILE" in
  *.py)
    msg="$(python3 -c 'import sys; compile(open(sys.argv[1], "rb").read(), sys.argv[1], "exec")' "$FILE" 2>&1)" || { fail=1; out+="[syntax] $msg"$'\n'; }
    if [ $fail -eq 0 ]; then
      if [ "$LINT_PY" = auto ]; then
        if command -v ruff >/dev/null 2>&1; then LINT_PY=ruff
        elif python3 -c 'import pyflakes' >/dev/null 2>&1; then LINT_PY=pyflakes
        else LINT_PY=none; fi
      fi
      case "$LINT_PY" in
        ruff)     msg="$(ruff check --quiet "$FILE" 2>&1)" || { fail=1; out+="[ruff] $msg"$'\n'; } ;;
        pyflakes) msg="$(python3 -m pyflakes "$FILE" 2>&1)" || { fail=1; out+="[pyflakes] $msg"$'\n'; } ;;
      esac
    fi ;;
  *.sh)   msg="$(bash -n "$FILE" 2>&1)" || { fail=1; out+="[bash -n] $msg"$'\n'; } ;;
  *.json) msg="$(python3 -c 'import sys,json; json.load(open(sys.argv[1]))' "$FILE" 2>&1)" || { fail=1; out+="[json] $msg"$'\n'; } ;;
  *.yaml|*.yml)
    if python3 -c 'import yaml' >/dev/null 2>&1; then
      msg="$(python3 -c 'import sys,yaml; yaml.safe_load(open(sys.argv[1]))' "$FILE" 2>&1)" || { fail=1; out+="[yaml] $msg"$'\n'; }
    fi ;;
esac

timed_out=0
if [ $fail -eq 0 ] && [ "$TEST_CMD" != none ] && printf '%s' "$FILE" | grep -Eq "$TEST_ON"; then
  if [ "$TEST_CMD" = auto ]; then
    if [ -d "$ROOT/tests" ] || ls "$ROOT"/test_*.py >/dev/null 2>&1; then TEST_CMD="python3 -m pytest -x -q -p no:cacheprovider"
    else TEST_CMD=none; fi
  fi
  if [ "$TEST_CMD" != none ]; then
    msg="$(cd "$ROOT" && timeout "$TEST_TIMEOUT" bash -c "$TEST_CMD" 2>&1)"; rc=$?
    if [ $rc -eq 124 ]; then timed_out=1
    elif [ $rc -ne 0 ]; then fail=1; out+="[tests: $TEST_CMD] exit $rc"$'\n'"$(printf '%s\n' "$msg" | tail -n "$TAIL_LINES")"$'\n'; fi
  fi
fi

{ printf '%s  %s  ' "$(date +%FT%T)" "${FILE#"$ROOT"/}"
  if [ $fail -ne 0 ]; then echo "FAIL"; printf '%s\n' "$out"
  elif [ $timed_out -ne 0 ]; then echo "TIMEOUT (${TEST_TIMEOUT}s) — TEST_CMD 를 agents/hooks/check.conf 에서 더 빠른 부분 집합으로 바꾸세요"
  else echo "ok"; fi; } >> "$LOG" 2>/dev/null

if [ $fail -ne 0 ]; then
  printf 'post-edit-check FAILED for %s\n%s\nFix this before moving on or reporting. Do not weaken or delete tests.\n' "${FILE#"$ROOT"/}" "$out" >&2
  exit 2
fi
exit 0
