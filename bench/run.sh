#!/usr/bin/env bash
# bench/run.sh — 워커(로컬 모델)에게 구현 태스크를 혼자 풀게 하고 숨은 테스트로 채점한다.
# 사용: bench/run.sh [-P 프로필] [--no-hooks] [--tag 이름] [--timeout 초] [--tier base|hard] [B1_bugfix ...]
#   -P 프로필     claude-worker -P 와 같다 (impl 프로필 권장). 없으면 기본 워커.
#   --no-hooks    편집 후 자동 검사 훅 없이 돌린다 (훅 효과 비교용)
#   --tag 이름    결과 파일 이름에 붙는다. 기본: 프로필+훅 여부
#   결과: bench/results/<날짜>_<tag>.md (표), 작업 복사본·원본 JSON: $BENCH_WORK (기본 /tmp/claude-bench)
# 채점: (1) tests/ 를 건드리지 않았는가 (2) 공개 테스트 통과 (3) 숨은 테스트(hidden/) 통과. 셋 다 되어야 PASS.
set -uo pipefail
KIT="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
PROFILE=""; HOOKS=1; TAG=""; TO=1800; TIER=""; TASKS=()
while [ $# -gt 0 ]; do
    case "$1" in
        -P|--profile) PROFILE="$2"; shift 2 ;;
        --no-hooks) HOOKS=0; shift ;;
        --tag) TAG="$2"; shift 2 ;;
        --timeout) TO="$2"; shift 2 ;;
        --tier) TIER="$2"; shift 2 ;;      # base (B*) | hard (H*) | 비우면 전부
        -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
        *) TASKS+=("$1"); shift ;;
    esac
done
case "$TIER" in base) PAT="B*" ;; hard) PAT="H*" ;; "") PAT="[BH]*" ;; *) echo "--tier 는 base|hard" >&2; exit 2 ;; esac
[ ${#TASKS[@]} -gt 0 ] || TASKS=($(cd "$KIT/bench/tasks" && ls -d $PAT))
[ -n "$TAG" ] || TAG="${PROFILE:-default}${TIER:+-$TIER}$([ $HOOKS -eq 1 ] && echo "" || echo "-nohooks")"
WORK="${BENCH_WORK:-/tmp/claude-bench}/$TAG"; mkdir -p "$WORK" "$KIT/bench/results"
OUT="$KIT/bench/results/$(date +%F)_$TAG.md"
command -v claude-worker >/dev/null 2>&1 && CW=claude-worker || CW="$KIT/bin/claude-worker"
# 워커에게 허용하는 도구: 파일 읽기·편집과 아래 명령만 (권한 프롬프트 없이 비대화로 돌리기 위함)
ALLOWED="Read,Edit,Write,MultiEdit,Glob,Grep,Bash(python3:*),Bash(python:*),Bash(pytest:*),Bash(git:*),Bash(ls:*),Bash(cat:*),Bash(head:*),Bash(tail:*),Bash(grep:*),Bash(wc:*),Bash(sed:*),Bash(diff:*)"
PARGS=(); [ -n "$PROFILE" ] && PARGS=(-P "$PROFILE")

{ echo "# 워커 단독 구현 벤치마크 — $(date +%F) — tag: $TAG"
  echo "- 워커: \`$CW ${PARGS[*]:-}\` (프로필 ${PROFILE:-기본}), 훅: $([ $HOOKS -eq 1 ] && echo 켬 || echo 끔), 시간 제한 ${TO}s/태스크, --max-turns 60, 권한: acceptEdits + 명령 허용 목록"
  echo "- 채점: tests/ 보존 + 공개 테스트 + 숨은 테스트 전부 통과 = PASS. 숨은 테스트는 워커에게 보이지 않는다."
  echo; echo "| 태스크 | 결과 | 공개 테스트 | 숨은 테스트 | tests/ 보존 | 턴 | 시간 | 워커 마지막 말 |"; echo "|---|---|---|---|---|---|---|---|"; } > "$OUT"

for T in "${TASKS[@]}"; do
    SRC="$KIT/bench/tasks/$T"; [ -d "$SRC/fixture" ] || { echo "no such task: $T" >&2; continue; }
    W="$WORK/$T"; rm -rf "$W"; cp -r "$SRC/fixture" "$W"
    find "$W" -name __pycache__ -type d -prune -exec rm -rf {} +
    printf '__pycache__/\n.pytest_cache/\n.claude/\nagents/\n' > "$W/.gitignore"
    ( cd "$W" && git init -q && git add -A && git -c user.name=bench -c user.email=bench@localhost commit -qm fixture && git branch -M main )
    if [ $HOOKS -eq 1 ]; then
        mkdir -p "$W/agents" "$W/.claude"; cp -r "$KIT/templates/project/agents/hooks" "$W/agents/"; cp "$KIT/templates/project/.claude/settings.json" "$W/.claude/"
    fi
    PROMPT="$(cat "$SRC/TASK.md")

Work in the current directory ($W); it is a git repository on branch main. You may run shell commands, read and edit files."
    echo "== $T  ($(date +%T))"
    t0=$(date +%s)
    ( cd "$W" && timeout "$TO" "$CW" "${PARGS[@]}" -p "$PROMPT" --permission-mode acceptEdits --allowedTools "$ALLOWED" --output-format json --max-turns 60 ) > "$W.json" 2> "$W.err"; rc=$?
    el=$(( $(date +%s) - t0 ))
    turns="$(python3 -c 'import sys,json
try: d=json.load(open(sys.argv[1])); print(d.get("num_turns","?"))
except Exception: print("?")' "$W.json")"
    last="$(python3 -c 'import sys,json
try: d=json.load(open(sys.argv[1])); r=str(d.get("result","")).strip().splitlines(); print((r[-1] if r else "")[:70].replace("|","/"))
except Exception: print("(no json; rc='"$rc"')")' "$W.json")"
    # 채점
    # tests/ 보존: 워커가 커밋했을 수도 있으므로 fixture 커밋(main 의 첫 커밋)과 비교. 추적되지 않는 새 파일도 위반.
    base="$(cd "$W" && git rev-list --max-parents=0 HEAD)"
    if ( cd "$W" && git diff --quiet "$base" -- tests/ ) && [ -z "$(cd "$W" && git status --porcelain -- tests/)" ]; then keep="예"; else keep="**아니오**"; fi
    vis="$(cd "$W" && python3 -m pytest -q -p no:cacheprovider tests 2>&1 | tail -1)"
    mkdir -p "$W/tests"; cp "$SRC"/hidden/*.py "$W/tests/" 2>/dev/null
    hid="$(cd "$W" && python3 -m pytest -q -p no:cacheprovider tests 2>&1 | tail -1)"
    ok=PASS
    [ "$keep" = "예" ] || ok=FAIL
    printf '%s' "$vis" | grep -Eq '^[0-9]+ passed' && ! printf '%s' "$vis" | grep -Eq 'failed|error' || ok=FAIL
    printf '%s' "$hid" | grep -Eq '^[0-9]+ passed' && ! printf '%s' "$hid" | grep -Eq 'failed|error' || ok=FAIL
    [ $rc -eq 124 ] && last="(시간 초과 ${TO}s) $last"
    echo "| $T | **$ok** | $vis | $hid | $keep | $turns | ${el}s | $last |" >> "$OUT"
    echo "   $ok  vis[$vis] hid[$hid] keep=$keep turns=$turns ${el}s"
done
echo; echo "결과 표: $OUT"; cat "$OUT"
