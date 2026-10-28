# 에이전트 운영 규칙 (Claude 오케스트레이터 + 로컬 LLM 워커)

## 역할
| 역할 | 세션 | 프롬프트 | 책임 |
|---|---|---|---|
| Orchestrator | `claude-main` (Claude) | agents/ORCHESTRATOR.md | 목표·게이트 관리, 태스크 분해·배정, 결과 검토, 문서 갱신 |
| Implementer | `claude-worker` (로컬 LLM) | agents/ROLE_IMPLEMENTER.md | 코드 구현·수정, 테스트 |
| Runner | `claude-worker` (로컬 LLM) | agents/ROLE_RUNNER.md | 계산 노드에서 실험 실행, 로그·결과 저장 |
| Analyst | `claude-worker` (로컬 LLM) | agents/ROLE_ANALYST.md | 결과 집계, 그림 생성, 판정 초안 |

## 작업 단위
- 태스크는 `agents/tasks/*.md` 하나씩. 목적·입력·절차·산출물·수용 기준·반증 체크를 적는다.
- 결과는 `results/<exp>_<tag>/` 에 데이터 + `REPORT.md`(HANDOFF_TEMPLATE 형식).
- 모든 숫자에는 출처(스크립트, config, 커밋 해시, 노드, 날짜)가 붙는다. 숫자 없는 주장은 받지 않는다.

## 흐름
1. Orchestrator 가 태스크를 고르고 수용 기준을 확인한 뒤 워커에 배정: `Ask @llm-worker to ...`
2. 워커는 지시된 역할 파일을 먼저 읽고 수행, 실패 시 규모를 줄여 재시도 후 보고.
3. Orchestrator 가 검토: 숫자 재검산, 수용 기준 대조, 다음 태스크 결정, 문서 갱신.

## 금지·주의
- (프로젝트별 규칙을 여기에 적는다.)
