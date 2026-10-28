#!/usr/bin/env bash
# tests/selftest.sh — 서버 없이 돌릴 수 있는 자체 검사. 네트워크 미사용.
set -uo pipefail
KIT="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
t() { if "$@" >/dev/null 2>&1; then PASS=$((PASS+1)); echo "  ok   $*"; else FAIL=$((FAIL+1)); echo "  FAIL $*"; fi; }
tn() { if ! "$@" >/dev/null 2>&1; then PASS=$((PASS+1)); echo "  ok   (expected failure) $*"; else FAIL=$((FAIL+1)); echo "  FAIL (should fail) $*"; fi; }

echo "1) 문법"
for f in "$KIT"/bin/* "$KIT"/install.sh "$KIT"/uninstall.sh; do t bash -n "$f"; done
if command -v shellcheck >/dev/null 2>&1; then
    t shellcheck -S warning "$KIT"/bin/claude-main "$KIT"/bin/claude-worker "$KIT"/bin/claude-duo "$KIT"/bin/llm-probe "$KIT"/bin/remote-* "$KIT"/install.sh "$KIT"/uninstall.sh
else echo "  skip shellcheck (미설치)"; fi

echo "2) 설정 없이 실행하면 안내하고 종료"
export CLAUDE_WORKER_CONF_DIR="$TMP/conf-none"
tn "$KIT/bin/claude-worker"
tn "$KIT/bin/remote-sync"
tn "$KIT/bin/llm-probe"

echo "3) 비대화 설치 (임시 prefix, 서버 점검 생략)"
export CLAUDE_WORKER_CONF_DIR="$TMP/conf"
t env PREFIX="$TMP/bin" LLM_BASE_URL="http://127.0.0.1:9/v1/" LLM_API_KEY="k" LLM_MODEL="m" WORKER_NAME="w1" \
     COMPUTE_HOST="node1" COMPUTE_WORK_DIR="work" COMPUTE_DESC="GPU x2" \
     "$KIT/install.sh" --non-interactive --skip-probe --prefix "$TMP/bin"
t test -x "$TMP/bin/claude-worker"
t test -f "$TMP/conf/env"
t grep -q 'LLM_BASE_URL="http://127.0.0.1:9"' "$TMP/conf/env"          # 끝의 /v1/ 제거
t grep -q 'Ask @w1 to' "$TMP/conf/worker.md"
t grep -q 'remote compute node `node1` (GPU x2)' "$TMP/conf/worker.md"
t grep -q 'work/<project-name>' "$TMP/conf/worker.md"
t test "$(stat -c %a "$TMP/conf/env")" = "600"

echo "4) 원격 노드 없이 재렌더링"
t env LLM_BASE_URL="http://127.0.0.1:9" LLM_MODEL="m" FORCE_ENV=1 PREFIX="$TMP/bin" "$KIT/install.sh" --non-interactive --skip-probe --prefix "$TMP/bin"
t grep -q 'No remote compute node is configured' "$TMP/conf/worker.md"
tn grep -q 'remote-run' "$TMP/conf/worker.md"
tn "$TMP/bin/remote-sync"                                             # COMPUTE_HOST 비어 있음 → 종료 2

echo "5) /v1 접미사 거부"
printf 'export LLM_BASE_URL="http://x/v1"\nexport LLM_API_KEY=k\nexport LLM_MODEL=m\n' > "$TMP/conf/env"
tn "$TMP/bin/claude-worker"

echo "6) 제거"
t "$KIT/uninstall.sh" --prefix "$TMP/bin" --purge
tn test -e "$TMP/bin/claude-worker"
tn test -e "$TMP/conf"

echo; echo "PASS=$PASS FAIL=$FAIL"; [ $FAIL -eq 0 ]
