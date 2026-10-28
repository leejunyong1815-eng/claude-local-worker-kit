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

echo "4b) 프로필 (env.gb10) 생성·상속·렌더링"
printf 'export LLM_BASE_URL="http://127.0.0.1:9"\nexport LLM_API_KEY=k\nexport LLM_MODEL=m\nexport WORKER_NAME=w1\nexport COMPUTE_HOST="nodeX"\nexport COMPUTE_WORK_DIR="wd"\nexport COMPUTE_DESC="GPU"\n' > "$TMP/conf/env"
tn env LLM_BASE_URL="http://127.0.0.1:9" PREFIX="$TMP/bin" "$KIT/install.sh" --profile gb10 --non-interactive --skip-probe --prefix "$TMP/bin"   # 모델 없음 → 실패
t env LLM_MODEL="m27" PREFIX="$TMP/bin" "$KIT/install.sh" --profile gb10 --non-interactive --skip-probe --prefix "$TMP/bin"
t grep -q 'LLM_BASE_URL="http://127.0.0.1:9"' "$TMP/conf/env.gb10"       # 기본 env 에서 주소 상속
t grep -q 'LLM_API_KEY="k"' "$TMP/conf/env.gb10"                          # 기본 env 에서 키 상속
t test -f "$TMP/conf/env.gb10"
t grep -q 'LLM_MODEL="m27"' "$TMP/conf/env.gb10"
t grep -q 'WORKER_NAME="llm-worker-gb10"' "$TMP/conf/env.gb10"
t grep -q 'COMPUTE_HOST="nodeX"' "$TMP/conf/env.gb10"                  # 기본 env 에서 상속
t grep -q 'Ask @llm-worker-gb10 to' "$TMP/conf/worker.gb10.md"
t grep -q 'local model `m27`' "$TMP/conf/worker.gb10.md"
t env LLM_BASE_URL="http://127.0.0.1:9" LLM_MODEL="m" FORCE_ENV=1 PREFIX="$TMP/bin" "$KIT/install.sh" --render
t grep -q 'local model `m27`' "$TMP/conf/worker.gb10.md"
tn "$TMP/bin/claude-worker" -P nope                                     # 없는 프로필 → 종료 2

echo "5) /v1 접미사 거부"
printf 'export LLM_BASE_URL="http://x/v1"\nexport LLM_API_KEY=k\nexport LLM_MODEL=m\n' > "$TMP/conf/env"
tn "$TMP/bin/claude-worker"

echo "6) 제거"
t "$KIT/uninstall.sh" --prefix "$TMP/bin" --purge
tn test -e "$TMP/bin/claude-worker"
tn test -e "$TMP/conf"
tn test -e "$TMP/conf/env.gb10"

echo; echo "PASS=$PASS FAIL=$FAIL"; [ $FAIL -eq 0 ]
