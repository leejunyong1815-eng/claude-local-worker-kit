# claude-local-worker-kit

Claude Code 세션 두 개를 짝지어 쓰는 구성이다.

- **오케스트레이터** (`claude-main`): 진짜 Claude. 태스크를 정의·배정·검토·결정한다.
- **워커** (`claude-worker`): 같은 Claude Code 프로그램이지만 연구실 **로컬 LLM 서버**에 연결된다.
  코드 수정, 테스트, 실험 실행 같은 손이 많이 가는 일을 맡는다. Claude 토큰을 쓰지 않는다.

둘은 같은 머신·같은 사용자에서 Unix 소켓으로 직접 대화한다. 오케스트레이터 대화창에서
`Ask @llm-worker to ...` 라고 쓰면 워커에게 전달되고, 워커의 보고가 돌아온다.

```
 ┌──────────────────────┐   Ask @llm-worker to …   ┌──────────────────────┐
 │ claude-main          │ ───────────────────────▶ │ claude-worker        │
 │ (Claude, Anthropic)  │ ◀─────────────────────── │ (Claude Code UI,     │
 │ 계획·검토·결정        │        보고               │  로컬 LLM 서버 모델)  │
 └──────────────────────┘                          └──────────┬───────────┘
                                                               │ remote-run / remote-submit
                                                               ▼
                                                   ┌──────────────────────┐
                                                   │ 원격 계산 노드 (ssh)  │
                                                   │ GPU 실험, 긴 작업     │
                                                   └──────────────────────┘
```

## 요구 사항

| 항목 | 조건 |
|---|---|
| Claude Code | ≥ 2.1.224 (`claude --version`). 설치: `curl -fsSL https://claude.ai/install.sh \| bash` |
| Claude 계정 | 오케스트레이터용. `claude` 한 번 실행해 로그인 |
| 로컬 LLM 서버 | Anthropic Messages API(`/v1/messages`) 제공. vLLM·SGLang·llama.cpp·Ollama(≥0.14)·LiteLLM 모두 가능 |
| 기타 | python3, curl 필수. tmux(동시 실행), rsync·ssh(원격 노드)는 선택 |
| OS | Linux, WSL2, macOS |

## 설치 (5분)

```bash
git clone <이 저장소> ~/claude-local-worker-kit     # 또는 공유 경로에서 복사
cd ~/claude-local-worker-kit
./install.sh
```

질문 네 개에 답한다: 서버 주소(`/v1` 없이), 토큰, 모델 id, 원격 노드 ssh 별칭(없으면 Enter).
설치 끝에 `llm-probe` 가 서버를 점검한다. **판정: 직접 연결 가능** 이 나오면 끝.

질문 없이 설치하려면:

```bash
LLM_BASE_URL=http://llm-host:8000 LLM_API_KEY=none LLM_MODEL=Qwen3-Coder \
  ./install.sh --non-interactive
```

설치되는 것:

| 경로 | 내용 |
|---|---|
| `~/.local/bin/claude-main, claude-worker, claude-duo` | 실행기 |
| `~/.local/bin/llm-probe` | 서버 점검 |
| `~/.local/bin/remote-{info,sync,run,submit,fetch}` | 원격 노드 실행 (COMPUTE_HOST 설정 시) |
| `~/.config/claude-worker/env` | 서버·모델·토큰 (0600) |
| `~/.config/claude-worker/worker.md` | 워커 시스템 프롬프트 (env 에서 생성) |

## 사용

```bash
cd ~/my-project
claude-duo            # tmux: 왼쪽 오케스트레이터, 오른쪽 워커
```

tmux 가 싫으면 터미널 두 개에서 각각 `claude-main`, `claude-worker`.

오케스트레이터 창에서:

```
Ask @llm-worker to: In /home/me/my-project run `python -m pytest -q`, then fix any failing test
without changing public function signatures, and report the diff summary and final test output.
```

규칙은 하나다. **한 번의 Ask = 완결된 태스크 하나.** 워커는 오케스트레이터 대화를 모른다.
경로·명령·수용 기준·보고 양식을 지시에 다 넣는다. 자세한 운영 규칙은 `templates/project/` 를
프로젝트에 복사해서 쓴다:

```bash
cp -r ~/claude-local-worker-kit/templates/project/{AGENTS.md,agents,KICKOFF_PROMPT.md} ~/my-project/
```

`KICKOFF_PROMPT.md` 를 오케스트레이터에 붙여 넣으면 캠페인이 시작된다.

### 원격 계산 노드

`~/.ssh/config` 에 별칭이 있고 키 인증이 되면 `COMPUTE_HOST` 에 그 별칭을 적는다.
워커가 `remote-run "python train.py"` 로 프로젝트를 `~/claude-work/<프로젝트>` 에 동기화해 실행하고
`outputs/` 를 가져온다. 긴 작업은 `remote-submit <job> "<명령>"` (원격 tmux, 로그 `outputs/<job>.log`).
프로젝트의 `CLAUDE.md` 에 연구실 서버 목록·GPU 예약 규칙이 있으면 워커는 그것을 따른다.

### 설정 변경

```bash
nano ~/.config/claude-worker/env
~/claude-local-worker-kit/install.sh --render     # 프롬프트 재생성
llm-probe                                        # 재점검
```

## 서버가 Anthropic API 를 지원하지 않을 때

`llm-probe` 가 2)~4) 에서 FAIL 이고 9) 에서 "OpenAI 형식은 동작" 이면 `proxy/README.md` 대로
LiteLLM 프록시를 띄우고 `LLM_BASE_URL` 을 프록시로 바꾼다. 연구실에서 한 대만 띄워 공용으로 써도 된다.

## 문제 해결

`docs/TROUBLESHOOTING.md`. 자체 검사는 `tests/selftest.sh` (네트워크 불필요).

## 파일 구성

```
install.sh / uninstall.sh      설치·제거 (--render: 프롬프트만 재생성)
bin/                           실행기·점검·원격 스크립트
config/worker.env.example      설정 키 설명
prompts/*.tmpl                 워커 시스템 프롬프트 템플릿
proxy/                         LiteLLM 변환 프록시 (선택)
templates/project/             프로젝트용 AGENTS.md, 역할 파일, 보고 양식, 시작 프롬프트
tests/selftest.sh              오프라인 자체 검사
docs/                          문제 해결, 설계 메모
PLAN.md                        배포 계획과 결정 사항
```
