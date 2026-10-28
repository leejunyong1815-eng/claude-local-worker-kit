# claude-local-worker-kit

Claude Code 세션 두 개를 짝지어 쓰는 구성이다.

- **오케스트레이터** (`claude-main`): 진짜 Claude. 태스크를 정의·배정·검토·결정한다.
- **워커** (`claude-worker`): 같은 Claude Code 프로그램이지만 연구실 **로컬 LLM 서버**에 연결된다.
  코드 수정, 테스트, 실험 실행 같은 손이 많이 가는 일을 맡는다. Claude 토큰을 쓰지 않는다.

둘은 같은 머신·같은 사용자에서 Unix 소켓으로 직접 대화한다. 오케스트레이터 창에
`Ask @llm-worker to ...` 라고 쓰면 워커에게 전달되고, 워커가 일을 마치면 보고가 오케스트레이터 창에 돌아온다.

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

처음이면 **[docs/FIRST_RUN.md](docs/FIRST_RUN.md)** 를 따라 10분짜리 시운전을 한 번 하고 오는 것이 가장 빠르다.

## 1. 요구 사항

| 항목 | 조건 |
|---|---|
| Claude Code | ≥ 2.1.224 (`claude --version`). 설치: `curl -fsSL https://claude.ai/install.sh \| bash` |
| Claude 계정 | 오케스트레이터용. 터미널에서 `claude` 를 한 번 실행해 로그인해 둔다 |
| 로컬 LLM 서버 | 연구실 서버 `1.233.219.134` (llama.cpp `llama-server`, docker). 포트·모델명은 서버 관리자 공지를 따른다. 다른 서버도 Anthropic Messages API(`/v1/messages`)만 제공하면 된다(vLLM·SGLang·llama.cpp·Ollama ≥0.14·LiteLLM) |
| 기타 | python3, curl 필수. tmux(동시 실행), rsync·ssh(원격 노드)는 선택 |
| OS | Linux, WSL2, macOS. 두 세션은 반드시 **같은 머신, 같은 사용자 계정**에서 띄운다 |

## 2. 설치

```bash
git clone https://github.com/leejunyong1815-eng/claude-local-worker-kit.git ~/claude-local-worker-kit
cd ~/claude-local-worker-kit
./install.sh
```

질문에 답한다.

| 질문 | 넣을 값 |
|---|---|
| LLM 서버 주소 | 연구실 서버는 `http://1.233.219.134:<포트>` (기본값 8080). **끝에 `/v1` 을 붙이지 않는다** |
| API 토큰 | 서버를 `--api-key` 없이 띄웠으면 Enter (`none`). 인증하는 서버면 받은 토큰 |
| 모델 id | 설치기가 서버의 모델 목록을 출력한다. 그중 하나를 적는다 |
| 컨텍스트 창 | 서버의 `--max-model-len`. 모르면 Enter |
| 워커 이름 | Enter 로 `llm-worker` |
| 원격 노드 ssh 별칭 | `~/.ssh/config` 의 Host 이름. 없으면 Enter |

끝에 `llm-probe` 가 서버를 점검한다. 마지막 줄이 **"판정: 직접 연결 가능"** 이면 설치 완료.
FAIL 이 있으면 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) 의 표를 본다.

질문 없이 설치하려면:

```bash
LLM_BASE_URL=http://1.233.219.134:8080 LLM_API_KEY=none LLM_MODEL=<모델 id> ./install.sh --non-interactive
```

설치되는 것:

| 경로 | 내용 |
|---|---|
| `~/.local/bin/claude-main`, `claude-worker`, `claude-duo` | 실행기 |
| `~/.local/bin/llm-probe` | 서버 점검 |
| `~/.local/bin/remote-{info,sync,run,submit,fetch}` | 원격 노드 실행 (COMPUTE_HOST 설정 시) |
| `~/.config/claude-worker/env` | 서버·모델·토큰 (권한 0600) |
| `~/.config/claude-worker/worker.md` | 워커 시스템 프롬프트 (env 에서 자동 생성) |

`~/.local/bin` 이 PATH 에 없다는 경고가 나오면 `~/.bashrc` 에 `export PATH="$HOME/.local/bin:$PATH"` 를 넣고 새 셸을 연다.

## 3. 실행

```bash
cd ~/my-project
claude-duo
```

tmux 창이 열린다. 왼쪽이 오케스트레이터, 오른쪽이 워커다. 창 사이 이동은 `Ctrl-b` 다음 화살표,
떼어 두기는 `Ctrl-b d`, 다시 붙기는 `claude-duo`, 끝내기는 `claude-duo --kill`.

tmux 가 싫으면 터미널 두 개에서 각각 `claude-main`, `claude-worker` 를 **같은 프로젝트 디렉터리**에서 띄운다.

처음 여는 프로젝트 디렉터리면 두 세션 모두 "이 폴더를 신뢰하느냐"고 묻는다. 둘 다 예.

워커 창 상단에 로컬 모델 이름이 보이면 정상이다. "Model … isn't recognized · context assumed to be 200k" 는
경고일 뿐이며, 실제 컨텍스트 창을 설정에 적어 주면 사라진다(아래 6절).

## 4. 일 시키기

오케스트레이터 창에 평소처럼 말한다. 워커에게 넘길 일은 이렇게 쓴다.

```
Ask @llm-worker to: In /home/me/my-project run `python -m pytest -q`. If any test fails, fix it
without changing public function signatures, re-run, and report the diff summary and the final test output.
```

워커 창에 메시지가 도착해 작업이 시작되고, 끝나면 보고가 오케스트레이터 창에 나타난다.
그 사이 오케스트레이터에게 다른 말을 걸어도 된다.

규칙은 하나다. **한 번의 Ask = 완결된 태스크 하나.** 워커는 오케스트레이터와 나눈 대화를 전혀 모른다.
그래서 지시 안에 다음을 전부 넣는다.

- 프로젝트 경로, 읽을 역할 파일·태스크 파일
- 실행할 명령과 설정값
- 시간·규모 예산
- 수용 기준(어떤 숫자가 나와야 통과인지)
- 보고 양식

"알아서 해 줘" 식 지시는 로컬 모델이 엉뚱한 곳을 헤매게 한다.
오케스트레이터에게 이 규칙을 지키게 하려면 `templates/project/` 를 프로젝트에 복사한다.

```bash
cp -r ~/claude-local-worker-kit/templates/project/{AGENTS.md,agents,KICKOFF_PROMPT.md} ~/my-project/
```

`AGENTS.md` 와 `agents/ROLE_*.md` 를 프로젝트에 맞게 고친 뒤, `KICKOFF_PROMPT.md` 내용을 오케스트레이터 창에
붙여 넣으면 오케스트레이터가 규칙을 읽고 태스크를 배정하기 시작한다.

### 워커가 멈춰 있을 때

워커 창을 본다. 대개 Bash 명령 실행 허가를 묻고 있다. 매번 허락하기 귀찮으면

- 워커 창에서 `/permissions` 로 자주 쓰는 명령을 허용하거나,
- 워커를 `claude-worker --permission-mode acceptEdits` 로 띄우거나(파일 편집은 자동 허용, 명령은 질문),
- 프로젝트의 `.claude/settings.local.json` 에 allow 규칙을 둔다. 예:
  `{"permissions":{"allow":["Bash(python3 *)","Bash(pytest *)","Bash(remote-* *)"]}}`

### 병렬로 돌리기

워커 세션 하나는 받은 메시지를 **순서대로** 처리한다. 동시에 세 작업을 돌리려면 워커를 세 개 띄운다.

```bash
claude-duo -w 3          # 워커 이름: llm-worker-1, llm-worker-2, llm-worker-3
```

오케스트레이터에서 `Ask @llm-worker-1 to …`, `Ask @llm-worker-2 to …` 로 나눠 보낸다.
수동으로 띄우려면 터미널마다 `CLAUDE_WORKER_NAME=llm-worker-2 claude-worker`.
오케스트레이터에서 `/peers` 를 치면 지금 연결 가능한 워커 목록이 보인다.

### 세션 이어 가기

```bash
claude-main -r orchestrator      # 어제 오케스트레이터 대화 이어 가기
claude-worker -r llm-worker      # 워커도 마찬가지
```

워커는 오래 쓰면 로컬 모델의 컨텍스트가 차서 느려지거나 실패한다. 태스크 몇 개마다 워커 창에서 `/clear`
하거나 새로 띄우는 편이 낫다. 어차피 워커는 대화 맥락에 의존하지 않도록 지시를 보낸다.

## 5. 원격 계산 노드

`~/.ssh/config` 에 별칭이 있고 키 인증(`ssh 별칭` 이 비밀번호 없이 붙음)이 되면 설치 때 `COMPUTE_HOST` 에 적는다.
그러면 워커가 다음 명령을 쓸 수 있다.

| 명령 | 하는 일 |
|---|---|
| `remote-info` | 노드의 CPU·RAM·GPU 사용 현황 |
| `remote-run "<명령>"` | 프로젝트를 원격 `~/claude-work/<프로젝트>` 로 동기화 → 실행 → `outputs/` 회수 |
| `remote-submit <job> "<명령>"` | 원격 tmux 에서 장시간 실행. 로그는 `outputs/<job>.log` |
| `remote-fetch` | `outputs/` 만 다시 내려받기 |
| `remote-sync` | 동기화만 |

로컬 소스가 원본이고 원격은 복사본이다. `.git`, `.venv`, `outputs/` 는 동기화에서 빠지며,
더 빼고 싶은 것은 프로젝트 루트의 `.remoteignore` 에 적는다.
연구실 서버 목록·GPU 예약 규칙이 프로젝트 `CLAUDE.md` 에 있으면 워커는 그것을 따른다.

## 6. 설정 변경

```bash
nano ~/.config/claude-worker/env                  # 서버·모델·토큰·컨텍스트 창·원격 노드
~/claude-local-worker-kit/install.sh --render     # 워커 프롬프트 재생성
llm-probe                                         # 재점검
```

설정 키 설명은 `config/worker.env.example` 에 있다. 서버를 바꿀 때는 `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`
세 줄만 고치면 된다.

## 7. 서버가 Anthropic API 를 지원하지 않을 때

`llm-probe` 가 2)~4) 에서 FAIL 이고 9) 에서 "OpenAI 형식은 동작" 이면 [proxy/README.md](proxy/README.md) 대로
LiteLLM 프록시를 띄우고 `LLM_BASE_URL` 을 프록시 주소로 바꾼다. 연구실에서 한 대만 띄워 공용으로 써도 된다.

## 8. 문제 해결·제거

증상별 해결은 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md). 자체 검사는 `tests/selftest.sh` (네트워크 불필요).
제거는 `./uninstall.sh` (설정까지 지우려면 `--purge`).

## 파일 구성

```
install.sh / uninstall.sh      설치·제거 (--render: 프롬프트만 재생성)
bin/                           실행기·점검·원격 스크립트
config/worker.env.example      설정 키 설명
prompts/*.tmpl                 워커 시스템 프롬프트 템플릿
proxy/                         LiteLLM 변환 프록시 (선택)
templates/project/             프로젝트용 AGENTS.md, 역할 파일, 보고 양식, 시작 프롬프트
tests/selftest.sh              오프라인 자체 검사
docs/FIRST_RUN.md              첫 실행 시운전
docs/TROUBLESHOOTING.md        증상별 해결
docs/MIGRATION.md              기존 개인 구성(claude-glm / drl-*)에서 옮기기
PLAN.md                        배포 계획과 결정 사항
```
