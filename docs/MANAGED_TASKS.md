# 관리형 구현 태스크 (1차)

이 문서는 오케스트레이터가 사용하는 CLI와 사용자가 직접 상태를 조사하는 방법을 설명한다.
일반적인 시작은 [작은 기능 하나 구현해 보기](FIRST_RUN.md)다. 사용자는 기능과 완료 조건을 요청하고,
아래 명세 작성·등록·실행·결과 확인은 운영 규칙을 읽은 오케스트레이터가 수행할 수 있다.

`claude-main`, `claude-worker`, `claude-duo`와 `Ask @이름 to …`는 그대로 쓴다.
수동 메시징은 질문·조사·작은 실행에 적합하다. 수동 세션에는 이 문서의 자동 격리·상태·검증이 적용되지 않는다.
**코드를 수정하는 위임에는 `worker-task` 관리 모드**를 권장한다. 별도 서버 없이 기존 `claude-worker`를
새 프로세스로 실행하며, 이미 떠 있는 대화형 워커에 내부 소켓 메시지를 보내지 않는다.

## 등록 → 실행 → 확인

설치/업데이트: 현재 키트에서 `./install.sh` (기존 설정을 유지할 수 있다).
대화형 워커나 `claude-duo`를 미리 띄울 필요는 없다. 관리 명령이 기존 `claude-worker`를 새로 실행한다.

코드가 있는 Git 저장소로 이동하고 [명세 예시](../config/task.example.json)를 복사한다.
예시의 목적·파일·검증 명령을 실제 프로젝트에 맞게 편집한다. `repository: "."`은 등록 명령을 실행하는
현재 디렉터리를 뜻한다. 명세 파일을 `/tmp`에 두면 태스크 등록용 파일이 원본 저장소의 미추적 파일로 섞이지 않는다.

```bash
cd ~/my-project
cp ~/claude-local-worker-kit/config/task.example.json /tmp/worker-task.json
# /tmp/worker-task.json을 편집한 다음 아래 명령으로 등록한다.
```

명세의 구조는 다음과 같다.

```json
{
  "purpose": "duration 파서의 빈 입력 처리 구현",
  "repository": ".",
  "base_commit": "HEAD",
  "profile": "",
  "compute_backend": "local",
  "instructions": "src/durations.py의 parse를 구현한다. 공개 시그니처와 테스트는 바꾸지 않는다. 테스트는 verify에 적힌 캐시 없는 명령으로 실행한다.",
  "references": ["src/durations.py", "tests/test_durations.py"],
  "allowed_paths": ["src/durations.py"],
  "protected_paths": ["tests/", "pyproject.toml", "scripts/verify.sh"],
  "verify": ["PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_durations.py"],
  "timeout": 1200,
  "verify_timeout": 120,
  "depends_on_uncommitted": false
}
```

```bash
TASK=$(worker-task submit /tmp/worker-task.json)  # stdout에는 ID 하나만
worker-task run "$TASK"                         # 전경 실행; 종료까지 기다림
worker-task status "$TASK"                      # 상태·이유·시도·프로세스
worker-task result "$TASK"                      # 검증·변경 파일·로그·diff 경로
```

`profile: ""`이면 기본 프로필, `impl`이면 기존 `env.impl`과 `worker.impl.md`를 사용한다.
`impl`이 없다면 키트 디렉터리에서 `./install.sh --profile impl`로 생성하거나 기본 프로필을 쓴다.
`profile: "impl"`로 등록했다면 `worker-task run "$TASK" -P impl`로 프로필 일치를 확인하며 실행할 수도 있다.
`-P`는 등록된 프로필을 바꾸는 옵션이 아니며, 다른 이름을 주면 실행을 거절한다.
프로필이나 명세를 바꾸려면 새 태스크로 등록한다. `instructions` 대신 또는 추가로 `task_file`을 지정할 수 있다.
태스크 파일 경로는 JSON 파일 디렉터리 기준이고, **등록 시 내용을 복사**한다.
`repository`는 등록 명령의 현재 디렉터리 기준이다. `references`는 기준 커밋 안의 상대 경로/패턴이다.
기준 커밋에 참고 파일이 없으면 워커 시작 전에 실패한다.

취소·명시적 재시도:

```bash
# 다른 터미널에서 submit이 출력한 실제 ID를 입력한다.
read -r -p '취소할 task ID: ' TASK
worker-task cancel "$TASK"
```

실패·취소·중단 결과를 검토한 뒤 `worker-task run "$TASK" --retry`로 재시도한다.
재시도는 같은 기준 커밋과 명세를 쓰며, 이전 시도의 수정은 가져오지 않는다. 이전 시도·로그·worktree는 남는다.
독립 태스크는 별도 터미널 또는 셸의 `&`로 동시에 실행할 수 있다. 중복 `run`은 잠금으로 거절된다.
관리 모드는 권한 우회·`acceptEdits`·도구 허용 목록을 자동 추가하지 않는다. 기존 Claude 권한을 유지하므로,
비대화 권한 부족은 워커 실패 또는 시간 초과로 나타날 수 있다. 필요한 권한은 사용자가 별도로 검토·설정한다.

## 미커밋 입력과 격리

등록 때 `HEAD` 등을 실제 커밋 해시로 고정한다. 실행할 때마다 detached Git worktree를 만들고,
프로세스의 `cwd`를 그 경로로 지정한다. 원래 체크아웃에서 checkout·add·stash·commit하지 않는다.
worktree 등록을 위한 공용 Git 메타데이터만 추가하며 원본 브랜치·HEAD·인덱스·작업 파일은 유지한다.
Git checkout 훅은 관리 명령에서 실행하지 않는다.

**새 worktree에는 원본의 staged·unstaged·미추적 파일이 포함되지 않는다.** 더러운 상태는 경고하고 결과에 기록한다.
`depends_on_uncommitted: true`인데 등록 또는 실행 시 원본에 변경이 있으면 해당 태스크 실행을 차단한다.
스켈레톤·테스트를 방금 작성했다면 특히 이 플래그를 켠다. 필요한 변경만 사용자가 검토해 별도 기준 커밋으로
준비하거나, 별도 체크아웃에서 필요한 입력을 커밋한 뒤 그 저장소/커밋으로 **새로 등록**한다.
실행기가 자동으로 stash·commit하거나, 미커밋 입력을 포함한 척 실행하지 않는다. 의존성을 자동 추론하지는 못한다.

worktree는 **동시 편집 충돌을 줄이는 장치이며 보안 샌드박스가 아니다**. 워커와 검증 명령은 같은 사용자 권한으로
동작하며, 절대 경로·공유 Git refs·네트워크·다른 프로세스에 접근할 수 있다. 악의적인 명령의 원본 접근을 차단하거나
검증 자체의 안전성을 증명하지 않는다. 엄격한 차단에는 별도 OS 사용자/컨테이너가 필요하다. 원본은 관리 모드의
입력으로만 취급하고 메인도 배정된 worktree를 편집하지 않는다. 관리 명령은 이 규칙을 지키지만 수동 편집은 차단하지 못한다.

## 상태·복구·결과

상태 전이:

```text
queued → running → verifying → succeeded
            └────────┴──────→ failed / cancelled / interrupted
```

`run`은 성공 0, 실행/검증 실패·취소·중단 1, 잘못된 요청·중복 실행·의존성 차단 2로 종료한다.
`run`이 0으로 끝난 뒤 `result`의 `state: succeeded`, `verification_valid: true`,
`artifacts_complete: true`와 모든 검증 종료 코드 0을 확인한다. 이어서 변경 파일과 `diff_path`의 내용을 검토한다.
`status`와 `result`는 동일한 최신 JSON 기록을 보여 준다. 상태를 읽을 때 살아 있지 않은 실행기를 확인하면
`interrupted / runner_lost`로 복구한다. Linux의 PID·프로세스 시작 시각·boot ID를 대조하며 PID 재사용을 생존으로 보지 않는다.
재시작 후 자동 실행/재시도는 없다. 살아 있는 자식 세션이 남으면 재시도를 거절한다. `surviving_processes`를
확인하고 `cancel`로 해당 세션을 종료한 후 명시적으로 재시도한다. 정상 SIGINT/SIGTERM도 자식을 정리하고 `interrupted`로 남긴다.
현재 관리 모드는 **Linux(/proc, WSL2 포함)** 전용이다. 기존 수동 실행 모드의 지원 범위는 유지된다.
계산 backend는 기본 `local`(현재 컴퓨터/WSL)이다. `compute_backend`를 생략해도 같으며, 관리 모드는 현재 다른 backend를 거절한다.
LLM 서버는 추론 접속점일 뿐 계산 노드가 아니다. 새 워커 프로세스에는 부모 Claude의 세션 ID 표지만 전달하지 않으며,
기존 프로필·권한 설정은 유지한다.

기본 저장 위치는 `${XDG_STATE_HOME:-~/.local/state}/claude-worker/tasks`다.
`WORKER_TASK_HOME` 또는 모든 명령 앞의 `--state-dir /별도/경로`로 바꿀 수 있다. **원본 체크아웃 안의 저장 위치는 거절**한다.
로컬 파일시스템에서 태스크별 `flock`과 임시 파일→원자적 rename을 사용한다(NFS 공유 실행은 지원하지 않는다).
태스크/시도 ID별 경로를 쓰며 실패·취소 결과도 자동 삭제하지 않는다. 제거기 역시 태스크 저장소는 지우지 않는다.

```text
<state>/<task ID>/spec.json                 등록 시 복사한 원본 명세
                 state.json                최신 상태
                 attempts/0001/result.json  해당 시도 기록
                               baseline.json
                               worktree/
                               worker.stdout.log / worker.stderr.log
                               verification.log / verification.stderr.log
                               changes.diff
```

결과에는 task/attempt ID, 기준 커밋, worktree, 프로필, 원본 dirty 여부, 변경 파일(추가/삭제/수정),
워커 종료 코드, 각 검증 종료 코드, 단계별 timeout 여부, 전체 실행 시간, 로그·diff 경로와 실패 이유가 들어간다.
`worker_timeout`, `worker_exit_nonzero`, `model_error`, `invalid_worker_result`, `path_policy_violation`,
`verification_timeout`, `verification_exit_nonzero`, `changed_during_verification`, `execution_error` 등을 구분한다.
시작 실패·비정상 강제 종료처럼 코드/로그가 존재하지 않는 경우에는 값이 null 또는 파일이 없을 수 있다.
`artifacts_complete`가 false이면 최종 diff 수집이 끝나지 않은 기록이다. 실행기가 죽고 자식이 남았으면
먼저 `cancel`로 정지한 뒤 변경 파일과 diff를 수집한다. 그 결과는 검증 성공으로 승격하지 않는다.
프로세스 정리는 실행기가 만든 세션/그룹을 대상으로 한다. 스스로 새 세션으로 이탈하는 데몬은 지원하지 않는다.

## 외부 검증의 범위

- 워커는 기존 래퍼의 `-p … --output-format json --max-turns 60`으로 실행된다. 정상 종료와 CLI JSON의 성공 응답은
  **검증 시작 조건**이다. 모델의 “테스트 통과” 문구로 성공을 결정하지 않는다.
- 기준 worktree의 파일 해시와 최종 파일을 비교한다. 자체 커밋 여부, Git 인덱스, 편집 도구와 무관하게
  추가·수정·삭제·실행 비트·symlink 변경을 검사한다. 미추적 파일과 **ignored 파일도 포함**한다.
- 허용/보호 경로는 저장된 명세에서 읽는다. 파일 경로, 디렉터리 접두사(`src/`), Python `fnmatch` 패턴을 지원한다.
  `*`는 `/`도 포함한다. 보호 경로가 우선이며 `tests/`, `config/`, `.claude/`, worktree의 `.git` 포인터는 항상 보호한다.
  프로젝트 루트의 설정·검증 스크립트도 반드시 `protected_paths`에 추가한다.
- 실제 Git 메타데이터 디렉터리는 코드 해시에서 제외하며, worktree의 `.git` 포인터 파일은 무결성을 검사한다.
  submodule은 현재 지원하지 않으며 실행 전에 실패한다.
  심볼릭 링크는 링크 자체를 비교하며 링크 대상의 외부 파일은 검증하지 않는다.
- 명세의 검증 명령은 worktree에서 `bash -o pipefail -c`로 순차 실행하고 **실제 종료 코드**가 모두 0이어야 한다.
  `verify_timeout`은 각 명령별 제한이다. 워커와 검증 명령에는 별도 프로세스 세션/시간 제한을 적용한다.
- 검증 전후 파일 해시가 달라지면 실패한다. 따라서 검증은 소스를 수정하지 않아야 한다. 캐시·빌드 산출물도 비교에
  포함하므로 `pytest -p no:cacheprovider`처럼 저장하지 않는 명령을 사용하거나 산출물을 worktree 밖에 둔다.
  Python bytecode 생성은 실행기가 끈다. 이미 워커가 만든 허용 범위 내 산출물은 변경 파일에 표시된다.
  이 버전의 편집 후 훅은 캐시 없는 문법 검사를 쓰며, 관리 모드에서는 worktree 안의 `last-check.log`를 만들지 않는다.
  기존 프로젝트의 오래된 훅은 `project-init`이 덮어쓰지 않으므로 직접 비교해 업데이트한다.
- 성공 후 `status`·`result`에서 현재 파일 해시와 명세 해시를 다시 검사한다. 달라졌으면
  `failed / changed_after_verification`으로 무효화한다. 검증 뒤 수동 수정한 코드는 이전 성공 증거로 제출하지 않는다.
  조회 직후의 추가 편집까지 원자적으로 막지는 못하므로 검증된 worktree를 검토 동안 보존하고 편집하지 않는다.

환경/설정 전체와 API 키를 결과에 저장하지 않는다. 표준 환경변수 및 생성된 프로필 env의 알려진 API 키 값은 로그·diff에서
가린다. 태스크 명세에 알려진 키가 들어 있으면 등록을 거절한다. 임의의 코드/로그에 포함된 모든 비밀을 탐지하는 기능은
아니므로 명세·태스크 파일·참고 소스에 비밀을 넣지 않는다. 상태 디렉터리와 결과는 사용자 전용 권한으로 만든다.

자동 merge·commit·push·PR, 원격 실험 스케줄링, 자동 모델 선택은 구현하지 않는다.
오케스트레이터가 검증 기록과 diff를 검토한 뒤 반영 방법을 직접 결정한다.

## 오프라인 검증과 실제 연결 확인

```bash
bash tests/selftest.sh                                     # mock CLI, 모델/네트워크 불필요
python3 -B -m unittest discover -s tests -p 'test_worker_task.py' -v
bash tests/selftest.sh --real-cli                          # 설치된 CLI 버전 확인; 모델 호출 없음
```

두 번째 명령은 실제 Git worktree와 기존 `claude-worker` 래퍼를 사용하고 `claude`만 모의 실행기로 대체한다.
관리 모드 테스트는 Python 표준 라이브러리와 Git만 필요하다. 기존 selftest의 훅 검사에는 `pytest`도 필요하며 ShellCheck는 선택 사항이다.
실제 연결은 사용자가 별도로 `llm-probe -P impl` 및 작은 관리 태스크로 확인한다. 프로브도 모델 요청을 보내므로
오프라인 테스트에 포함하지 않는다. 기존 `bench/run.sh`는 별도의 모델 벤치마크이며 관리 모드의 완료 증거를 대신하지 않는다.
