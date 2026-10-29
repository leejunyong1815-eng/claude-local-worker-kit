# 대화형 메시징 운영

오케스트레이터가 대화형 워커에 조회·실행 작업을 배정하는 기존 모드다. 메시징 연결을 진단하거나 직접 조작할 때 이 문서를 참고한다.
일반적인 기능 구현 흐름은 [작은 기능 하나 구현해 보기](FIRST_RUN.md)에 있다.
수동 메시징에는 관리 모드의 자동 worktree 격리·상태 기록·외부 검증이 적용되지 않는다.

## 세션 시작

```bash
cd ~/my-project
claude-duo               # 오케스트레이터 + 기본 워커
claude-duo -P impl       # + 구현 전용 대화형 워커
claude-duo -w 3          # 기본 워커 3개
claude-duo -w 2 -P impl  # 기본 워커 2개 + 구현 전용 워커
```

옵션 중 필요한 명령 하나를 사용한다. tmux에서 `Ctrl-b` 다음 화살표로 창을 이동하고, `Ctrl-b d`로 떼어 둔다.
다시 붙기는 `claude-duo`, 종료는 `claude-duo --kill`이다.
tmux 없이 쓰려면 터미널마다 `claude-main`, `claude-worker`를 실행한다. 세션은 같은 머신·같은 사용자 계정에서 실행해야 한다.
수동으로 이름을 나누려면 `CLAUDE_WORKER_NAME=llm-worker-2 claude-worker`처럼 지정한다.

같은 디렉터리에서는 소스 편집을 겹치지 않게 한다. 코드 편집까지 수동 위임한다면 오케스트레이터가 별도 worktree를
먼저 준비하고 그 경로에서 워커를 시작한다. 구현 위임에는 [관리 모드](MANAGED_TASKS.md)를 권장한다.

## 연결 점검과 직접 메시지

오케스트레이터 창의 `/peers`에서 워커 이름을 확인한다. 기본 이름은 `llm-worker`, 여러 워커는 `llm-worker-1` 등이다.
관리 모드로 시작한 워커의 실행 상태는 관리 태스크 기록에서 확인한다.

직접 메시지를 보내 연결을 확인하려면 다음 예시를 사용한다. 평소에는 사용자의 목표를 받은 오케스트레이터가 메시지를 작성한다.

```text
Ask @llm-worker to: In /home/me/my-project run
`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider`.
Leave source files and Git state unchanged. Report the command, exit code and failing tests.
```

한 메시지에는 프로젝트 경로·참고 파일·실행 명령·시간 제한·완료 조건·보고 형식을 담는다.
워커는 오케스트레이터와 사용자가 나눈 대화를 모르므로 이전 대화에만 있는 조건을 생략하지 않는다.
워커 하나는 메시지를 순서대로 처리한다. 독립 작업을 병렬로 배정할 때는 서로 다른 워커에 보낸다.

## 권한·세션 관리

워커가 응답하지 않으면 권한 질문에 멈췄는지 확인한다. 필요한 명령은 워커의 `/permissions`나 프로젝트 설정에서 검토해 허용한다.
`claude-worker --permission-mode acceptEdits`는 편집을 허용하는 수동 실행 옵션이다. 관리 모드는 이 옵션을 자동 추가하지 않는다.
설정 파일에는 API 키가 있으므로 내용을 통째로 보고서·대화에 붙여 넣지 않는다.

```bash
claude-main -r orchestrator
claude-worker -r llm-worker
```

오래된 대화형 워커는 태스크 사이에 `/clear`로 맥락을 비우거나 새로 시작할 수 있다.
추가 진단은 [문제 해결 안내](TROUBLESHOOTING.md)를 참고한다.
