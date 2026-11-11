# Codex 메인 + Anthropic API 키 (OpenCodex 경유)

Codex CLI를 오케스트레이터로 쓰면서 메인 모델을 Anthropic API 키(크레딧)로 호출하는 구성이다.
워커는 그대로 등록된 LLM 서버를 쓴다. Claude Code는 이 경로를 거치지 않고 본인 계정으로 직접 쓴다.

## 왜 이 경로인가

- Anthropic API 크레딧은 Claude API 직접 호출에만 적용되고 Claude Code에는 적용되지 않는다.
  따라서 Claude Code를 메인으로 쓰는 `claude-duo`로는 크레딧을 소비할 수 없다.
- Codex CLI의 `wire_api`는 Responses만 지원하므로 Anthropic 엔드포인트에 직접 붙일 수 없다.
  OpenCodex(`ocx`)가 로컬 프록시(127.0.0.1:10100)에서 Responses 요청을 Anthropic Messages로 변환한다.
- Codex 설정(`~/.codex/config.toml`)에 OpenCodex가 `openai_base_url`과 모델 카탈로그를 주입하고,
  모델 ID는 `anthropic-apikey/<model>` 형식으로 라우팅된다.

## 구성 요소와 위치

| 요소 | 위치 | 비고 |
|---|---|---|
| Codex CLI | `/usr/local/bin/codex` (전역) 또는 `~/.local/bin/codex` | 공식 설치 스크립트. 로그인은 sudo 없이 본인 계정으로 |
| OpenCodex | `~/.local/opt/opencodex/ocx`, 심링크 `~/.local/bin/ocx` | 릴리스 tar(sha256 검증). Node 불필요 |
| API 키 파일 | `~/.config/opencodex/keys.env` (0600, `KEY=VALUE`) | `ANTHROPIC_API_KEY` 이름은 쓰지 않는다 |
| 공급자 | `ocx provider add anthropic-apikey --api-key '${ANTHROPIC_API_KEY_PRIMARY}'` | 값이 아니라 변수 참조를 저장하고 요청 시점에 프록시가 해석 |
| 프록시 서비스 | systemd 유저 유닛 `opencodex-proxy.service` | 드롭인 `EnvironmentFile=%h/.config/opencodex/keys.env` |
| Codex 프로파일 | `~/.codex/orch.config.toml` | `model`, `model_reasoning_effort`, `sandbox_mode = "workspace-write"` |
| 프로파일 선택 | `<설정 디렉터리>/codex-profile` 파일, 키트 `shell.sh`가 `LLM_CODEX_PROFILE`로 export | `codex-main`이 `-p <이름>`을 붙인다. 직접 실행은 `codex -p orch`. `shell.sh`는 `./install.sh --setup-path`가 생성 |

## 설치: codex-bootstrap

```bash
./install.sh --install-only          # 키트 명령을 ~/.local/bin에 복사
codex-bootstrap --check              # 상태와 계획만 출력, 변경 없음
codex-bootstrap                      # 사용자 권한 단계 수행, root 단계는 명령만 출력
codex-bootstrap --sudo               # root 단계(전역 Codex, AppArmor, linger)까지 수행
codex-bootstrap --probe              # 설정 뒤 과금되는 요청 1건으로 경로 확인
```

동작 원칙은 네 가지다.

1. **감지 후 분기**: 배포판·버전·아키텍처, systemd 유저 매니저, WSL, AppArmor의 사용자 네임스페이스 제한과
   실제 `bwrap` 동작, 기존 `codex`/`ocx` 설치를 먼저 읽고 필요한 단계만 수행한다. 두 번 실행해도 변경이 없다.
2. **sudo 경계**: root가 필요한 단계는 `--sudo`를 줄 때만 실행하고, 아니면 정확한 명령을 출력한다.
3. **비밀 비접촉**: 키 값은 읽지도 출력하지도 않는다. `keys.env`는 변수명만 든 0600 템플릿으로 만들고 사용자가 편집한다.
   공급자 등록은 `${변수}` 참조로, 두 번째 키는 `ocx account add-key` stdin 절차를 안내한다.
4. **검증 내장**: 서비스 기동 후 헬스 체크, 프록시 프로세스 환경에 변수 이름이 있는지(`/proc`), 모델 탐색이 401 없이 되는지 확인한다.

기본 모델과 reasoning effort는 대화형 실행에서 먼저 묻는다(모델: Fable 5.2 / Opus 5.5 / 직접 입력, effort: low~max).
`--model <id>`, `--effort <level>`로 지정하면 묻지 않고, 비대화형(`--yes`)이면 Fable 5.2와 high를 쓴다.
두 값은 프로파일의 시작 기본값일 뿐이며 이후 TUI의 `/model`, `codex -m <id>`, `-c model_reasoning_effort=...`,
또는 `codex-bootstrap --model <id> --effort <level> --force`로 바꿀 수 있다.

OpenCodex 버전은 이 키트로 검증한 2.99.0을 권장한다. 대화형이면 y/n으로 고정 버전 또는 최신 릴리스를 고르고,
비대화형(`--yes`)이면 고정 버전을 쓴다. `--opencodex-version <버전|latest>`로 직접 지정할 수 있다.

`keys.env`를 채운 뒤 다시 실행하면 서비스 재시작 없이도 다음 요청부터 참조가 해석된다(프록시는 요청 시점에 변수를 읽는다).
단, 변수는 프록시 프로세스 환경에 있어야 하므로 파일을 처음 채웠다면 `systemctl --user restart opencodex-proxy`가 필요하다.

## 운영

```bash
ocx status                 # 프록시·서비스·Codex 주입 상태
ocx logs                   # 요청 로그 (모델, 상태 코드, 지연)
ocx usage                  # 토큰 사용량 (과금 영수증은 아님)
ocx account list anthropic-apikey   # 키 풀과 활성 키
systemctl --user status opencodex-proxy
codex-duo                  # 키트 오케스트레이터 (LLM_CODEX_PROFILE 적용)
```

- 활성 키 전환: `ocx account use anthropic-apikey <id>`. 어느 워크스페이스에 과금되는지는 활성 키가 정한다.
- 매 턴 Codex가 보내는 도구 정의가 약 19K 토큰이다. 캐시 쓰기/읽기 요금이 적용되므로 Console의 Cost에서 실제 차감을 확인한다.
- Anthropic은 제3자 프록시 경유 계정을 제한할 수 있다(OpenCodex README 경고). 본인 책임 하에 사용한다.

## 겪은 함정과 원인

| 증상 | 원인 | 해결 |
|---|---|---|
| 모델 탐색 HTTP 401 | 변수 없는 셸에서 `ocx start`를 띄워 `${...}` 참조가 빈 값으로 해석됨 | 서비스 드롭인 `EnvironmentFile`로 공급. 수동 기동은 `set -a; . keys.env; set +a; ocx start` |
| `codex-duo`가 바로 종료, `Ignoring --add-dir ... effective permissions` | 샌드박스 기본값 read-only에서 풀 디렉터리 추가 쓰기 경로를 거부 | 프로파일에 `sandbox_mode = "workspace-write"` |
| 프로파일을 넣었는데 여전히 같은 오류 | 변수 없는 터미널이거나, 저장소 `bin/`만 고치고 `~/.local/bin` 복사본을 갱신하지 않음 | 새 터미널, `./install.sh --install-only` |
| `config.toml`의 `model` 줄이 사라짐 | `ocx stop`/`ocx restore`가 라우팅 모델 줄을 지우고 재기동 때 복원하지 않음 | 모델은 프로파일 파일에 둔다 |
| `legacy profile = "..." config is no longer supported` | Codex 0.167은 `config.toml`의 `profile` 키를 거부 | `-p <이름>`만 사용 (`LLM_CODEX_PROFILE`) |
| 명령마다 승인 요청, 시작 시 bubblewrap 경고 | Ubuntu 24.04 `apparmor_restrict_unprivileged_userns=1`로 `bwrap`이 네임스페이스를 못 만듦 | `apparmor-profiles`의 `bwrap-userns-restrict` 프로파일 로드. 25.04 이상은 기본 포함 |
| `~/.codex/shell_snapshots/*.sh`에 키 평문 | `.bashrc`에서 키를 export하면 Codex가 셸 환경을 스냅샷 | `.bashrc`에서 keys.env source 제거. 서비스가 파일을 직접 읽음 |
| `~/.claude/agents/ocx-*.md`가 생김 | OpenCodex의 Claude Code 연동이 기본 켜짐 | `ocx integration native claude off` (켜면 다시 생성됨) |
| `codex exec`가 출력 없이 대기 | 프롬프트 인자가 있어도 stdin을 추가 입력으로 읽음 | `< /dev/null` |
| 두 번째 키가 `config.json`에 평문 | `ocx account add-key`는 값을 저장(0600) | 참조 형태를 원하면 공급자의 첫 키만 `${변수}`로 등록 |

## 확인된 버전

Codex CLI 0.167.0, OpenCodex 2.99.0, Ubuntu 24.04, systemd 255. 다른 버전에서는 `codex-bootstrap --check`로 상태를 먼저 본다.
