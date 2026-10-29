# 워커 단독 구현 벤치마크 — 2026-10-29 — tag: impl-all-nohooks
- 워커: `/home/ljy/claude-local-worker-kit/bin/claude-worker -P impl` (프로필 impl), 훅: 끔, 시간 제한 1200s/태스크, --max-turns 60, 권한: acceptEdits + 명령 허용 목록
- 채점: tests/ 보존 + 공개 테스트 + 숨은 테스트 전부 통과 = PASS. 숨은 테스트는 워커에게 보이지 않는다.

| 태스크 | 결과 | 공개 테스트 | 숨은 테스트 | tests/ 보존 | 턴 | 시간 | 워커 마지막 말 |
|---|---|---|---|---|---|---|---|
| B1_bugfix | **FAIL** | 5 passed in 0.00s | 1 failed, 7 passed in 0.01s | 예 | 7 | 66s | `git diff --stat`: `stats.py / 4 +++-` |
| B2_signature | **PASS** | 6 passed in 0.00s | 15 passed in 0.01s | 예 | 6 | 74s | - Raises `ValueError` for: empty string, unknown unit, number without  |
| B3_cli_flag | **PASS** | 2 passed in 0.06s | 5 passed in 0.14s | 예 | 6 | 71s | ``` |
| B4_refactor | **PASS** | 3 passed in 0.00s | 6 passed in 0.01s | 예 | 10 | 90s | ``` |
| B5_module_spec | **PASS** | 6 passed in 0.00s | 11 passed in 0.01s | 예 | 4 | 111s | - `stats()` returns `{"hits", "misses", "evictions", "expirations"}` a |
| B6_module_skeleton | **PASS** | 6 passed in 0.00s | 11 passed in 0.01s | 예 | 5 | 74s | / `clear` / Clears `_data`, preserves stats / |
| H1_expr_parser | **FAIL** | 6 passed in 0.00s | 2 failed, 18 passed in 0.03s | 예 | 5 | 302s | **Files changed:** `expr.py` (new, 166 lines, stdlib only) |
| H2_scheduler | **PASS** | 4 passed in 0.00s | 12 passed in 0.01s | 예 | 7 | 152s | - Simulation: at each decision point, assigns ready tasks (alphabetica |
| H3_json_patch | **PASS** | 4 passed in 0.00s | 19 passed in 0.01s | 예 | 19 | 821s | **Result**: `4 passed in 0.00s` |
| H4_multifile_txn | **PASS** | 4 passed in 0.12s | 9 passed in 0.36s | 예 | 26 | 310s | Test output: `4 passed in 0.10s` |
