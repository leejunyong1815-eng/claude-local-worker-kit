# 연결·실행 문제 확인

- 새 WSL 설치: README의 필수 도구·HTTPS clone 절차부터 진행한다. 설치 전 `./install.sh --check`, 설치 후 `worker-doctor`로 확인한다.
- 명령을 못 찾음: `./install.sh --setup-path` 후 `. "$HOME/.config/local-worker/shell.sh"`로 현재 터미널에 적용한다.
- Windows의 Claude가 잡힘: WSL 안에서 Linux용 Claude Code를 설치하고 ~/.local/bin을 PATH 앞에 둔다.
- checkout 이동: 새 위치에서 `./install.sh --update`를 실행해 템플릿 경로를 갱신한다.
- 스크립트가 `Permission denied`로 실행되지 않음: `ls -l install.sh`로 실행 비트를 확인한다.
  비트만 빠졌다면 `chmod +x install.sh` 또는 `bash install.sh --update`로 설치한다. 설치 명령과 project-init은 복사한 실행 파일·훅의 실행 비트를 보정한다.
  `/mnt/c`, `/mnt/d`의 NTFS나 `noexec` 마운트라면 비트만 바꿔도 해결되지 않을 수 있다. 키트와 작업용 worktree를 WSL의 `~/` 아래 Linux 파일시스템에 둔다.

- 설정 없음: `./install.sh --install-only`는 도구만 설치한다. 서버 정보를 받은 뒤 `./install.sh`로 설정한다.
- shared gateway missing: 기존 설치는 `./install.sh --update`로 gateway.env를 생성한다. 프로필 env의 URL은 연결에 사용하지 않는다.
- 메인이 자체 에이전트를 호출함: 기본 selective에서는 EGM·고난도 판단에 허용된다. 일반 작업까지 대체하면 배정 기준을 재확인하거나 `--native-agents off`로 재시작한다. 기존 프로세스에 업데이트가 자동 적용되지는 않는다. 일반 claude나 이전 런처는 키트의 배정 지침을 적용하지 않는다.
- selective인데 native가 막힘: 실행 옵션과 프로젝트 지침 갱신, 추가 disallowedTools·사용자/조직 deny·실제 호스트 도구를 확인한다. 키트는 기존 deny를 제거하지 않는다. EGM 플러그인은 별도로 설치해야 한다.
- 401/403: 키와 서버 권한을 관리자에게 확인한다. 키를 채팅·로그·GitHub issue에 붙이지 않는다.
- 모델/컨텍스트 오류: 실제 등록 ID와 요청당 한도를 사용한다. 공식 API의 별칭이나 1M 한도를 가정하지 않는다.
- `/v1/messages`/SSE/tool_result 오류: Anthropic 호환 endpoint인지 확인한다. OpenAI 전용 URL은 지원하지 않는다.
- effort 거부: 키트는 effort 옵션·환경변수를 전달하지 않는다. 기존 env의 LLM_EFFORT 값도 적용하지 않는다. CLI가 기본 HTTP effort를 넣는 경우가 있으므로 CLI 버전과 gateway의 요청 호환성을 확인한다.
  HTTP 200만으로 max가 실제 적용됐다고 판단하지 않는다. thinking.budget_tokens로 상한을 강제한다고 주장하지 않는다.
- 워커 권한 거부: 최신 버전으로 --update한 뒤 result의 permission_denied_tools와 worker_settings_path를 확인한다. 기본 workspace 프로필은 일반 도구를 허용하지만 기존 deny/ask가 우선한다. 외부 데이터는 read_paths로 지정하고, 명시적 제안 규칙은 permissions_file로 등록한다. 자세한 내용은 WORKER_PERMISSIONS.md를 따른다.
- 수동 워커가 승인 질문에서 대기: 해당 pane에서 승인하거나 `--permission-profile workspace`를 명시해 새로 실행한다. 무인 운영은 관리 모드를 사용한다.
- 워커 이름의 접미사: 정상이다. 관리 모드는 pool/worker ID로 선택하고 수동 duo는 실제 이름 목록을 메인에 전달한다. `-n`으로 이름을 지정할 수 있지만 직접 중복 이름을 주면 세션 ID를 확인해야 한다.
- 원격 경로가 업데이트 후 바뀜: `remote-*`는 checkout 경로 해시를 붙여 다른 worktree와 분리한다. 이전 원격 복사본은 삭제하거나 옮기지 않는다. COMPUTE_HOST 등 설정은 REMOTE_HELPERS.md를 따른다.
- 훅 로그 때문에 dirty 상태: 최신 훅은 last-check.log를 만들지 않는다. `project-update --check` / `--apply`로 갱신한다. 이전 로그 파일은 자동 삭제하지 않으므로 기존 추적 여부와 내용을 확인해 직접 처리한다.
- 작업 실패: `worker-task result <ID>`의 reason·워커/검증 종료 코드·timeout·로그를 확인한다.
  worker_timeout과 verification_timeout, model_error와 path_policy_violation을 구분한다.
- runner_lost: `status`에서 interrupted와 살아 있는 프로세스를 확인한다. 필요하면 해당 ID만 cancel한다.
  불확실한 이전 실행을 자동 재실행하지 않는다. 확인 뒤 `run <ID> --retry`로 새 시도를 만든다.
- stale input: 생산 태스크가 변경되었거나 재시도되어 고정한 시도와 다르다. 검토·검증 후 소비 태스크를 새로 등록한다.
- 원본 미커밋 입력: 자동 포함되지 않는다. 필요한 기준 커밋을 사용자가 준비하거나 검증된 태스크 inputs로 전달한다.

오프라인 검사는 `./tests/selftest.sh`, 실제 연결 검사는 `llm-probe`로 구분한다.
후자는 명시적으로 모델 요청을 보낸다. 풀 시작 전 검사는 `claude-duo --probe` / `codex-duo --probe`로 요청한다.
실제 CLI 검증은 작은 관리 태스크로 추가 확인한다.

## Codex 메인 + OpenCodex 경로

- 모델 탐색이 401: 프록시 프로세스 환경에 키 변수가 없다. `codex-bootstrap --check`의 `service env` 행을 보고, 서비스 드롭인(`EnvironmentFile`) 뒤 `systemctl --user restart opencodex-proxy`.
- `codex-duo`가 `Ignoring --add-dir ... effective permissions`로 즉시 종료: 샌드박스가 read-only다. `~/.codex/orch.config.toml`의 `sandbox_mode = "workspace-write"`, 설정 디렉터리의 `codex-profile` 파일, 새 터미널에서 `echo $LLM_CODEX_PROFILE`을 확인하고, 저장소 `bin/`을 고쳤다면 `./install.sh --install-only`로 `~/.local/bin` 복사본을 갱신한다.
- 명령마다 승인 요청과 bubblewrap 경고: `bwrap --unshare-user --ro-bind / / /bin/true`가 실패하면 AppArmor 사용자 네임스페이스 제한이다. `codex-bootstrap --sudo`가 배포판에 맞는 조치를 수행하거나 명령을 출력한다.
- `ocx stop` 뒤 모델이 gpt로 돌아감: `config.toml`의 `model` 줄은 원복 때 지워진다. 모델은 프로파일 파일에 둔다.
- 자세한 원인·해결 표는 [CODEX_ANTHROPIC.md](CODEX_ANTHROPIC.md)에 있다.
