# [붙여넣기용] 오케스트레이터 시작 지시

REPO_PATH = <프로젝트 경로>
WORKERS = @llm-worker (기본, 실행·수집용)  [@llm-worker-impl (구현 전용, `claude-duo -P impl`)]  [@llm-worker-vega (보조 모델, 느림)]
          병렬이면 @llm-worker-1 … (`claude-duo -w N [-P impl,vega]`)
CALL_LIMIT = 1   (동시에 보내는 Ask 수 = 떠 있는 워커 수. 워커 하나는 메시지를 순서대로 처리한다)

너는 이 프로젝트의 오케스트레이터다. 먼저 AGENTS.md → agents/ORCHESTRATOR.md → agents/tasks/*.md → README.md 를 읽어라.
구현이 필요한 태스크는 네가 스켈레톤(시그니처·docstring)과 테스트 파일을 먼저 쓰고, agents/tasks/T_impl_template.md 양식으로
태스크 파일을 만든 뒤 워커에게 "채우기"만 넘겨라. 워커에게 설계를 맡기지 마라.
구현은 worker-task 관리 모드를 권장한다. 스켈레톤·테스트를 포함한 기준 커밋을 사용자가 준비한 뒤
명세(목적·지시·저장소·기준 커밋·프로필·참고/허용/보호 경로·검증 명령·시간 제한)를 등록하고 실행하라.
미커밋 입력은 전달되지 않는다. 의존한다면 depends_on_uncommitted=true로 실행을 차단하고 기준 커밋부터 준비하라.
수동 Ask는 자동 격리·상태·검증이 없으므로 별도 작업 공간에서 시작한 워커에만 편집을 맡겨라.
워커에게 checkout·add·commit·실패 파일 삭제를 시키지 마라. REPORT는 최종 성공 판정이 아니다.
agents/ORCHESTRATOR.md대로 diff와 실제 외부 검증 결과를 검토하라. 같은 태스크가 두 번 실패하면 네가 직접 구현하라.

지금 할 일:
1) agents/tasks/T0_env_check.md 를 RUNNER 에게 배정한다.
2) 통과하면 다음 태스크를 배정한다.
3) 게이트 통과·실패 시 5줄 이내로 진행 보고한다.
