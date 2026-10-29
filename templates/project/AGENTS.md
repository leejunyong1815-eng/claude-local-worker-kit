# 에이전트 운영 규칙 (Claude 오케스트레이터 + 로컬 LLM 워커)

## 역할
| 역할 | 세션 | 프롬프트 | 책임 |
|---|---|---|---|
| Orchestrator | `claude-main` (Claude) | agents/ORCHESTRATOR.md | 목표·게이트 관리, 태스크 분해, **스켈레톤·테스트 작성**, 결과 검토(diff·테스트 직접 확인), 문서 갱신 |
| Implementer | `@llm-worker-impl` (`claude-duo -P impl`, 없으면 `@llm-worker`) | agents/ROLE_IMPLEMENTER.md | 스켈레톤 채우기, 테스트 통과시키기, 작은 버그 수정 |
| Runner | `@llm-worker` (게이트웨이 모델) 또는 `@llm-worker-vega` (보조, 느림) | agents/ROLE_RUNNER.md | 계산 노드에서 실험 실행, 로그·결과 저장 |
| Analyst | `@llm-worker` (게이트웨이 모델) | agents/ROLE_ANALYST.md | 결과 집계, 그림 생성, 판정 초안 |

## 작업 단위
- 태스크는 `agents/tasks/*.md` 하나씩. 목적·읽을 파일·절차·산출물·수용 기준·반증 체크를 적는다. 구현 태스크는 `agents/tasks/T_impl_template.md` 양식.
- 구현 태스크는 브랜치 `task/<T>` 에서 한다. 오케스트레이터가 `git diff` 를 읽고 테스트를 직접 돌린 뒤 머지한다.
- 결과는 `results/<exp>_<tag>/` 에 데이터 + `REPORT.md`(HANDOFF_TEMPLATE 형식).
- 모든 숫자에는 출처(스크립트, config, 커밋 해시, 노드, 날짜)가 붙는다. 숫자 없는 주장은 받지 않는다.

## 자동 검사
- `.claude/settings.json` 의 PostToolUse 훅이 파일을 고칠 때마다 `agents/hooks/post-edit-check.sh` 를 돌린다 (문법 → lint; 테스트는 기본 끔).
  실패하면 그 출력이 워커의 다음 턴에 들어간다. 편집마다 테스트까지 돌리려면 `agents/hooks/check.conf` 에 `TEST_CMD="auto"`.

## 흐름
1. Orchestrator 가 태스크를 고르고, 구현이면 스켈레톤과 테스트를 먼저 쓴 뒤 워커에 배정: `Ask @llm-worker-impl to ...`
   (병렬 실행은 워커 수만큼: `claude-duo -w N` → `@llm-worker-1` … `@llm-worker-N`)
2. 워커는 지시된 역할 파일을 먼저 읽고 수행, 실패 시 규모를 줄여 재시도 후 보고.
3. Orchestrator 가 검토: diff 읽기, 테스트 직접 실행, 숫자 재검산, 수용 기준 대조, 다음 태스크 결정, 문서 갱신.
4. 같은 태스크를 워커가 두 번 실패하면 Orchestrator 가 직접 구현한다 (승격 규칙, ORCHESTRATOR.md).

## 금지·주의
- 워커는 테스트 파일을 고치지 않는다. 테스트 변경은 Orchestrator 만 한다.
- (프로젝트별 규칙을 여기에 적는다.)
