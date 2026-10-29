# 워커 단독 구현 벤치마크 — 2026-10-29 — tag: flash-next
- 워커: `/home/ljy/claude-local-worker-kit/bin/claude-worker -P impl` (프로필 impl), 훅: 켬, 시간 제한 1200s/태스크, --max-turns 60, 권한: acceptEdits + 명령 허용 목록
- 채점: tests/ 보존 + 공개 테스트 + 숨은 테스트 전부 통과 = PASS. 숨은 테스트는 워커에게 보이지 않는다.

| 태스크 | 결과 | 공개 테스트 | 숨은 테스트 | tests/ 보존 | 턴 | 시간 | 워커 마지막 말 |
|---|---|---|---|---|---|---|---|
| B1_bugfix | **PASS** | 5 passed in 0.00s | 8 passed in 0.01s | 예 | 7 | 41s | ``` |
| B2_signature | **PASS** | 6 passed in 0.00s | 15 passed in 0.01s | 예 | 9 | 108s | - Uppercase units (e.g. `"2D"`) are treated as unknown units → `ValueE |
| B3_cli_flag | **PASS** | 2 passed in 0.06s | 5 passed in 0.15s | 예 | 12 | 75s | **Test suite last line**: `2 passed in 0.06s` |
| B4_refactor | **PASS** | 3 passed in 0.00s | 6 passed in 0.01s | 예 | 9 | 95s | All work was local; nothing to report as unverified. |
| B5_module_spec | **PASS** | 6 passed in 0.01s | 11 passed in 0.01s | 예 | 6 | 77s | - Tests untouched; nothing could not be verified. Spec details honored |
| B6_module_skeleton | **PASS** | 6 passed in 0.00s | 11 passed in 0.01s | 예 | 7 | 75s | **Test result (last line):** `6 passed in 0.01s` — exit status 0. All  |
| H1_expr_parser | **PASS** | 6 passed in 0.01s | 20 passed in 0.01s | 예 | 10 | 209s | **Judgment call to flag** (untested, ambiguous edge): `min()`/`max()`  |
| H2_scheduler | **PASS** | 4 passed in 0.00s | 12 passed in 0.01s | 예 | 13 | 206s | Last line of the test run: `4 passed in 0.00s` |
| H3_json_patch | **PASS** | 4 passed in 0.01s | 19 passed in 0.01s | 예 | 16 | 325s | - `remove` at path `""` (whole document) raises `PatchError`; `replace |
| H4_multifile_txn | **PASS** | 4 passed in 0.09s | 9 passed in 0.35s | 예 | 17 | 219s | **Test output last line:** `4 passed in 0.09s` |
