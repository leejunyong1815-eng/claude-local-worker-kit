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
- 구현 위임은 `worker-task submit/run/status/result/cancel` 관리 모드를 권장한다. 실행기가 기준 커밋에서 별도 worktree를 준비한다. 워커는 그 안에서만 작업하고 checkout·add·commit하지 않는다.
- 미커밋 스켈레톤·테스트는 worktree에 포함되지 않는다. 의존한다면 `depends_on_uncommitted: true`로 차단하고, 사용자가 필요한 입력의 기준 커밋을 준비한 뒤 새로 등록한다.
- 수동 메시징은 자동 격리·상태·검증을 제공하지 않는다. 코드 편집 전 오케스트레이터가 독립 작업 공간을 준비하고 외부 검증을 수행한다. 서로의 작업 공간을 편집하지 않는다.
- 수동 실험 결과는 `results/<exp>_<tag>/`에 데이터 + `REPORT.md`(HANDOFF_TEMPLATE 형식).
- 관리 구현 태스크는 실행기가 worktree 밖에 결과·로그·diff를 저장한다. 워커는 지정된 허용 경로만 수정하고 보고는 응답으로 전달한다. `worker-task result <ID>`로 최종 기록을 확인한다.
- 모든 숫자에는 출처(스크립트, config, 커밋 해시, 노드, 날짜)가 붙는다. 숫자 없는 주장은 받지 않는다.

## 자동 검사
- `.claude/settings.json` 의 PostToolUse 훅이 파일을 고칠 때마다 `agents/hooks/post-edit-check.sh` 를 돌린다 (문법 → lint; 테스트는 기본 끔).
  실패하면 그 출력이 워커의 다음 턴에 들어간다. 편집마다 테스트까지 돌리려면 `agents/hooks/check.conf` 에 `TEST_CMD="auto"`.

## 흐름
1. Orchestrator 가 태스크를 고르고, 구현이면 스켈레톤과 테스트를 기준 커밋에 준비한 뒤 관리 모드로 배정한다. 수동 메시징: `Ask @llm-worker-impl to ...`
   (수동 메시징 병렬 실행: `claude-duo -w N` → `@llm-worker-1` … `@llm-worker-N`. 관리 모드는 서로 다른 task ID를 각각 실행한다.)
2. 워커는 지시된 역할 파일을 먼저 읽고 수행, 실패 시 규모를 줄여 재시도 후 보고.
3. Orchestrator 가 검토: diff 읽기, 테스트 직접 실행, 숫자 재검산, 수용 기준 대조, 다음 태스크 결정, 문서 갱신.
4. 같은 태스크를 워커가 두 번 실패하면 Orchestrator 가 직접 구현한다 (승격 규칙, ORCHESTRATOR.md).
5. 워커 정상 종료/보고는 완료 판정이 아니다. 실행기의 허용·보호 경로 검사와 실제 검증 종료 코드가 성공해야 한다. 실패·취소 시도는 보존하고 자동 merge·commit·삭제하지 않는다.

## 금지·주의
- 워커는 테스트 파일을 고치지 않는다. 테스트 변경은 Orchestrator 만 한다.
- (프로젝트별 규칙을 여기에 적는다.)
