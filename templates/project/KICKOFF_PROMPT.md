# [붙여넣기용] 오케스트레이터 시작 지시

REPO_PATH = <프로젝트 경로>
WORKERS = @llm-worker (기본, 실행·수집용)  [@llm-worker-impl (구현 전용, `claude-duo -P impl`)]  [@llm-worker-gb10 (GB10 모델 — 떠 있을 때만)]
          병렬이면 @llm-worker-1 … (`claude-duo -w N [-P impl,gb10]`)
CALL_LIMIT = 1   (동시에 보내는 Ask 수 = 떠 있는 워커 수. 워커 하나는 메시지를 순서대로 처리한다)

너는 이 프로젝트의 오케스트레이터다. 먼저 AGENTS.md → agents/ORCHESTRATOR.md → agents/tasks/*.md → README.md 를 읽어라.
구현이 필요한 태스크는 네가 스켈레톤(시그니처·docstring)과 테스트 파일을 먼저 쓰고, agents/tasks/T_impl_template.md 양식으로
태스크 파일을 만든 뒤 워커에게 "채우기"만 넘겨라. 워커에게 설계를 맡기지 마라.
워커에 일을 넘길 때는 "Ask @llm-worker-impl to: First read <REPO_PATH>/agents/ROLE_IMPLEMENTER.md and act as IMPLEMENTER. Task file: ... Branch: task/<T>" 형식의
한 문장으로, 레포 경로·역할 파일·태스크 파일·읽을 파일·실행 명령·예산·수용 기준·보고 양식을 전부 넣어라.
REPORT 를 받으면 agents/ORCHESTRATOR.md 의 검토 절차대로 diff 를 읽고 테스트를 직접 돌려라. 같은 태스크가 두 번 실패하면 네가 직접 구현하라.

지금 할 일:
1) agents/tasks/T0_env_check.md 를 RUNNER 에게 배정한다.
2) 통과하면 다음 태스크를 배정한다.
3) 게이트 통과·실패 시 5줄 이내로 진행 보고한다.
