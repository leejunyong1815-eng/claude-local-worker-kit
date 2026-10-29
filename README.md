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
| 로컬 LLM 서버 | 연구실 서버 `1.233.219.134` 의 **LiteLLM 게이트웨이(포트 4000)**. 그 뒤에 같은 호스트의 llama.cpp(`qwen3.6-35b-a3b`)와 GB10 노드의 모델이 붙는다. 모델 이름 하나로 어느 백엔드든 고른다. 다른 서버도 Anthropic Messages API(`/v1/messages`)만 제공하면 된다(vLLM·SGLang·llama.cpp·Ollama ≥0.14·LiteLLM) |
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
| LLM 서버 주소 | Enter 로 연구실 LiteLLM `http://1.233.219.134:4000`. 다른 서버면 `http://호스트:포트`, **끝에 `/v1` 을 붙이지 않는다** |
| API 토큰 | Enter (`none`). 2026-10-29 현재 연구실 LiteLLM 은 키 인증이 없다. 나중에 관리자가 키를 걸면 받은 `sk-…` |
| 모델 id | Enter 로 `qwen3.6-35b-a3b`. 설치기가 LiteLLM 의 모델 목록을 출력한다. 목록의 `qwen3.6-35b-a3b-oai` 는 도구 호출 점검에 실패하므로 고르지 않는다 |
| 컨텍스트 창 | Enter. 설치기가 LiteLLM 이 알려 주는 값(현재 `qwen3.6-35b-a3b` = 131072)을 기본으로 보여 준다. 서버가 안 알려 주면 131072. 요청 하나가 쓸 수 있는 크기여야 한다 |
| 워커 이름 | Enter 로 `llm-worker` |
| 원격 노드 ssh 별칭 | `~/.ssh/config` 의 Host 이름. 없으면 Enter |

끝에 `llm-probe` 가 서버를 점검한다. 마지막 줄이 **"판정: 직접 연결 가능"** 이면 설치 완료.
FAIL 이 있으면 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) 의 표를 본다.

질문 없이 설치하려면 (연구실 기본값):

```bash
./install.sh --non-interactive
```

다른 서버를 쓰려면 환경변수로 값을 준다: `LLM_BASE_URL=http://host:port LLM_MODEL=<id> ./install.sh --non-interactive`.
GB10 모델이 LiteLLM 에 등록된 뒤 그 모델용 워커를 추가하려면 `./install.sh --profile gb10` (아래 4절).

설치되는 것:

| 경로 | 내용 |
|---|---|
| `~/.local/bin/claude-main`, `claude-worker`, `claude-duo` | 실행기 |
| `~/.local/bin/llm-probe` | 서버 점검 |
| `~/.local/bin/remote-{info,sync,run,submit,fetch}` | 원격 노드 실행 (COMPUTE_HOST 설정 시) |
| `~/.config/claude-worker/env` (, `env.gb10` …) | 워커의 서버·모델·토큰 (권한 0600). 프로필마다 하나 |
| `~/.config/claude-worker/worker.md` (, `worker.gb10.md` …) | 워커 시스템 프롬프트 (env 에서 자동 생성) |

`~/.local/bin` 이 PATH 에 없다는 경고가 나오면 `~/.bashrc` 에 `export PATH="$HOME/.local/bin:$PATH"` 를 넣고 새 셸을 연다.

## 3. 실행

```bash
cd ~/my-project
claude-duo               # 오케스트레이터 + 기본 워커
claude-duo -P impl       # + 구현 전용 워커 @llm-worker-impl (설치 때 만든 프로필)
claude-duo -P impl,gb10  # + GB10 모델 워커까지 (GB10 프로필을 만들었을 때)
```

tmux 창이 열린다. 왼쪽이 오케스트레이터, 오른쪽이 워커다. 창 사이 이동은 `Ctrl-b` 다음 화살표,
떼어 두기는 `Ctrl-b d`, 다시 붙기는 `claude-duo`, 끝내기는 `claude-duo --kill`.

tmux 가 싫으면 터미널마다 `claude-main`, `claude-worker`(, `claude-worker -P impl`) 를 **같은 프로젝트 디렉터리**에서 띄운다.

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
오케스트레이터에게 이 규칙을 지키게 하려면 프로젝트에 규칙 파일을 넣는다 (기존 파일은 덮어쓰지 않는다).

```bash
project-init ~/my-project     # AGENTS.md, KICKOFF_PROMPT.md, agents/(역할·태스크 양식·검사 훅), .claude/settings.json
```

`AGENTS.md` 와 `agents/ROLE_*.md` 를 프로젝트에 맞게 고친 뒤, `KICKOFF_PROMPT.md` 내용을 오케스트레이터 창에
붙여 넣으면 오케스트레이터가 규칙을 읽고 태스크를 배정하기 시작한다.

### 구현 작업을 워커에게 맡길 때

로컬 모델은 "짧은 명세를 받아 채우고, 돌리고, 고치는" 일은 잘하지만 **설계 판단과 긴 맥락 유지에는 약하다**.
그래서 킷은 구현 작업을 다음처럼 나누도록 오케스트레이터를 지도한다 (`agents/ORCHESTRATOR.md`).

| 단계 | 누가 | 내용 |
|---|---|---|
| 설계·분해 | 오케스트레이터(Claude) | 파일·함수 경계, 데이터 흐름 |
| 스켈레톤·테스트 | 오케스트레이터 | 시그니처·docstring 이 든 스켈레톤과 테스트 파일을 **직접** 쓴다 |
| 채우기·실행·반복 | `@llm-worker-impl` | 본문을 채워 테스트를 통과시킨다. 읽을 파일 목록을 받고, 브랜치 `task/<T>` 에서 일한다 |
| 검토 | 오케스트레이터 | `git diff` 를 읽고 테스트를 직접 돌린 뒤 머지. 같은 태스크가 두 번 실패하면 직접 구현(승격) |

이를 돕는 장치 네 가지.

- **편집 후 자동 검사 훅** — `project-init` 이 넣는 `.claude/settings.json` 이 파일을 고칠 때마다 `agents/hooks/post-edit-check.sh` 를 돌린다
  (문법 → lint → `pytest -x -q`). 실패 출력이 워커의 다음 턴에 바로 들어가므로, 모델이 "테스트 돌리기"를 잊어도 훅은 잊지 않는다.
  테스트 명령·시간 제한은 `agents/hooks/check.conf`. 오케스트레이터 세션에도 같은 훅이 걸린다.
- **구현 전용 워커 `@llm-worker-impl`** — 같은 모델이지만 시스템 프롬프트에 구현 규칙(지정 파일만 읽기, 테스트 수정 금지, 편집마다 검사 결과 반영, 세 번 막히면 보고)이 붙는다.
  설치 때 만들어지며(`install.sh --profile impl` 로도 추가), `claude-duo -P impl` 로 띄운다.
- **구현 태스크 양식** `agents/tasks/T_impl_template.md` — 읽을 파일, 채울 함수 표, 실행 명령, 수용 기준, 브랜치를 한 장에 적는다.
- **벤치마크** `bench/run.sh` — 워커 혼자 구현 태스크 10개(기본 6 + 어려운 4)를 풀게 하고 숨은 테스트로 채점한다. 모델·서버·프롬프트를 바꿨을 때
  "어디까지 맡길 수 있는지"를 숫자로 본다. 결과는 `bench/results/`. 자세한 것은 [bench/README.md](bench/README.md).

사고(thinking) 조절에 대해: Claude Code 2.1.312 는 모든 요청에 `thinking: adaptive` 를 보내고 `MAX_THINKING_TOKENS` 는 무시한다(0 이면 필드만 빠지고 백엔드는 그래도 사고한다).
`effort` 값도 백엔드가 무시한다. 사고량을 제한하려면 **서버 쪽**(llama.cpp `--reasoning-budget`, vLLM 의 reasoning 옵션)에서 해야 한다 — 7절 관리자 항목.

### 모델을 나눠 쓰기 (GB10 노드가 붙으면)

LiteLLM 뒤에는 모델이 여러 개 붙을 수 있다. 지금은 LLM 서버 자체의 Qwen3.6-35B-A3B 하나이고, GB10 노드의 큰 모델이
등록되면 `llm-probe --models` 에 이름이 하나 더 보인다. 그때 워커를 둘로 나눠 띄우고 일의 성격에 따라 보낸다.

| 워커 | 모델 | 특징 | 보낼 일 |
|---|---|---|---|
| `@llm-worker` (기본) | `qwen3.6-35b-a3b` (LLM 서버, AMD Vega 2장) | MoE, 활성 3B. 컨텍스트 32k | 테스트 실행, 로그·결과 수집, 실험 돌리기, 파일 정리처럼 **도구 호출이 많고 추론은 가벼운 일** |
| `@llm-worker-gb10` | GB10 노드 모델 (이름은 등록 후 확정) | 128GB 메모리라 큰 모델·긴 컨텍스트 | 기능 구현, 버그 원인 추적, 리팩터링처럼 **생각이 필요한 일** |

```bash
~/claude-local-worker-kit/install.sh --profile gb10   # 모델 목록에서 GB10 모델을 고르고 컨텍스트 창을 넣는다
claude-duo -P gb10                                     # 기본 워커 + GB10 워커
```

둘 다 `Ask @이름 to …` 로 똑같이 부른다. `templates/project/agents/ORCHESTRATOR.md` 에 이 배분 규칙이 들어 있어
오케스트레이터가 알아서 고른다. GB10 워커가 없으면 모든 일이 기본 워커로 간다.

### 속도와 컨텍스트 (실측)

| 경로 | 프롬프트 처리 | 토큰 생성 | 요청당 컨텍스트 | Bash 한 번짜리 워커 왕복 |
|---|---|---|---|---|
| LiteLLM `:4000` 의 `qwen3.6-35b-a3b` (2026-10-29) | 약 5,500 tok/s | 약 90 tok/s | 131072 | 수 초 ~ 20초 |
| LLM 서버 llama.cpp `:8080` 직접 (AMD Vega 2장, 우회용) | 약 200~350 tok/s | 약 17 tok/s | 131072 (`--kv-unified`, 동시 요청이 나눠 씀) | 약 3분 |

게이트웨이 뒤에 백엔드가 여럿이면 요청마다 다른 쪽으로 갈 수 있어 **같은 작업도 어떤 턴은 빠르고 어떤 턴은 느릴 수 있다**. 고장이 아니다.
`LLM_CONTEXT_WINDOW` 는 **실제 백엔드의 요청당 컨텍스트**와 같아야 한다. 작으면 Claude Code 가 쓸데없이 자동 압축을 반복하고
("Autocompact is thrashing"), 크면 서버가 400 을 낸다. 설치기가 LiteLLM 의 값을 읽어 넣어 준다.
워커에게는 여전히 **작은 태스크를 하나씩** 보내고, 긴 작업은 워커 창에서 `/clear` 로 새로 시작하는 편이 낫다.

### 워커가 멈춰 있을 때

워커 창을 본다. 대개 Bash 명령 실행 허가를 묻고 있다. 매번 허락하기 귀찮으면

- 워커 창에서 `/permissions` 로 자주 쓰는 명령을 허용하거나,
- 워커를 `claude-worker --permission-mode acceptEdits` 로 띄우거나(파일 편집은 자동 허용, 명령은 질문),
- 프로젝트의 `.claude/settings.local.json` 에 allow 규칙을 둔다. 예:
  `{"permissions":{"allow":["Bash(python3 *)","Bash(pytest *)","Bash(remote-* *)"]}}`

### 병렬로 돌리기

워커 세션 하나는 받은 메시지를 **순서대로** 처리한다. 동시에 세 작업을 돌리려면 워커를 세 개 띄운다.

```bash
claude-duo -w 3          # 기본 워커 3개: llm-worker-1, llm-worker-2, llm-worker-3
claude-duo -w 2 -P gb10  # 기본 워커 2개 + GB10 워커 1개
```

오케스트레이터에서 `Ask @llm-worker-1 to …`, `Ask @llm-worker-2 to …` 로 나눠 보낸다.
수동으로 띄우려면 터미널마다 `CLAUDE_WORKER_NAME=llm-worker-2 claude-worker`.
서버의 동시 슬롯은 4개(`--parallel 4`)라 연구실 전체에서 동시에 도는 워커 수가 그 이상이면 요청이 줄을 선다.
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
nano ~/.config/claude-worker/env                  # 기본 워커 (프로필은 env.<이름>)
~/claude-local-worker-kit/install.sh --render     # 모든 프로필의 워커 프롬프트 재생성
llm-probe                                         # 재점검 (프로필은 llm-probe -P <이름>)
```

설정 키 설명은 `config/worker.env.example` 에 있다. 서버를 바꿀 때는 `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`
세 줄만 고치면 된다. 프로필을 더 만들려면 `./install.sh --profile <이름>` (`impl` = 같은 모델의 구현 전용 워커, `gb10` = GB10 모델).

## 7. 서버 쪽 구성 (관리자용)

```
구성원 PC: claude-main (Claude) ⇄ claude-worker ──HTTP──▶ LLM 서버 1.233.219.134
                                                      LiteLLM :4000 ─┬─▶ llama.cpp :8080 (qwen3.6-35b-a3b, 같은 호스트)
                                                                     └─▶ GB10 노드 (큰 모델, 올라오면 등록)
```

LiteLLM 설정·실행 방법은 [proxy/README.md](proxy/README.md). 모델을 추가·교체할 때 구성원은 `LLM_MODEL` 만 바꾸면 된다.
LiteLLM 이 죽었을 때는 env 를 `LLM_BASE_URL=http://1.233.219.134:8080`, `LLM_API_KEY=none` 으로 바꾸면 LLM 서버의 llama.cpp 에 직접 붙는다(느리다).

**사고 토큰 상한(관리자)** — 실측(2026-10-29): 클라이언트의 `effort` 는 백엔드가 무시하고, `thinking.budget_tokens` 는 지키지만 Claude Code 가 그 필드를 보내지 않으며,
LiteLLM `litellm_params` 에 `thinking` 을 넣어도 요청 값(adaptive)이 이긴다. 따라서 과도한 사고를 줄이려면 엔진에서 제한한다:
llama.cpp 는 `--reasoning-budget <토큰>`, vLLM/SGLang 은 reasoning parser 의 budget 옵션. 코딩 태스크 기준 2k~8k 토큰이 보통 충분하다.

## 8. 문제 해결·제거

증상별 해결은 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md). 자체 검사는 `tests/selftest.sh` (네트워크 불필요).
제거는 `./uninstall.sh` (설정까지 지우려면 `--purge`).

## 파일 구성

```
install.sh / uninstall.sh      설치·제거 (--profile NAME: 다른 모델용 워커, --render: 프롬프트만 재생성)
bin/                           실행기·점검·원격 스크립트, project-init(프로젝트에 규칙·훅 넣기)
config/worker.env.example      설정 키 설명
prompts/*.tmpl                 워커 시스템 프롬프트 템플릿
proxy/                         LiteLLM 변환 프록시 (선택)
templates/project/             프로젝트용 AGENTS.md, 역할 파일, 구현 태스크 양식, 편집 후 검사 훅, 시작 프롬프트
bench/                         워커 단독 구현 벤치마크 (tasks/, run.sh, results/)
tests/selftest.sh              오프라인 자체 검사
docs/FIRST_RUN.md              첫 실행 시운전
docs/TROUBLESHOOTING.md        증상별 해결
docs/MIGRATION.md              기존 개인 구성(claude-glm / drl-*)에서 옮기기
PLAN.md                        배포 계획과 결정 사항
```
