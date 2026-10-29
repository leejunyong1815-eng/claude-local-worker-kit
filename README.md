# claude-local-worker-kit

Claude가 작업을 지휘하고, 로컬 LLM 워커가 구현·실행을 맡는 도구 모음이다.

- **오케스트레이터** (`claude-main`): 진짜 Claude. 태스크를 정의·배정·검토·결정한다.
- **워커** (`claude-worker`): 같은 Claude Code 프로그램이지만 연구실 **로컬 LLM 서버**에 연결된다.
  코드 수정, 테스트, 실험 실행 같은 손이 많이 가는 일을 맡는다. Claude 토큰을 쓰지 않는다.

대화형 모드에서는 둘이 같은 머신·같은 사용자에서 Unix 소켓으로 직접 대화한다. 오케스트레이터 창에
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

할 일에 따라 실행 방식을 고른다.

| 할 일 | 실행 방식 | 작업 공간과 완료 판정 |
|---|---|---|
| 질문, 조사, 테스트 실행·결과 확인 | `claude-duo` + `Ask @llm-worker to …` | 수동 메시징. 같은 디렉터리에서 코드 편집을 겹치지 않게 하고, 메인이 결과를 검토한다 |
| 코드 수정 위임 | `worker-task` 관리 CLI | 태스크·시도별 worktree에서 별도 워커를 실행하고, 경로 검사와 외부 검증으로 성공을 판정한다 |

처음이면 [대화형 연결 시운전](docs/FIRST_RUN.md)을 진행한다. 코드 수정을 맡기려면 아래
[관리 모드 빠른 시작](#관리-모드로-코드-수정-맡기기)과 [상세 사용법](docs/MANAGED_TASKS.md)을 따른다.
관리 모드는 이미 떠 있는 대화형 워커에 메시지를 보내는 방식과 별개다.

빠른 이동: [설치](#2-설치) · [관리 태스크](#관리-모드로-코드-수정-맡기기) · [수동 메시징](#수동-메시징으로-조회실행-맡기기) · [설정 변경](#6-설정-변경) · [검사·문제 해결](#8-문제-해결제거)

## 1. 요구 사항

| 항목 | 조건 |
|---|---|
| Claude Code | ≥ 2.1.224 (`claude --version`). 설치: `curl -fsSL https://claude.ai/install.sh \| bash` |
| Claude 계정 | 오케스트레이터용. 터미널에서 `claude` 를 한 번 실행해 로그인해 둔다 |
| 로컬 LLM 서버 | Anthropic Messages API(`/v1/messages`)를 제공하는 서버. 연구실 기본 접속점은 `http://1.233.219.134:4000` (LiteLLM)이며 모델·백엔드 구성은 아래 4·7절 참고 |
| 공통 도구 | python3, curl. Git은 저장소 설치와 관리 모드에 필요. tmux(대화형 동시 실행), rsync·ssh(원격 노드)는 선택 |
| 수동 모드 OS | Linux, WSL2, macOS. 세션 간 메시징은 **같은 머신, 같은 사용자 계정**에서 사용 |
| 관리 모드 환경 | **Linux/WSL2**, `/proc`, Git worktree, 로컬 파일시스템. macOS·NFS 공유 실행·submodule은 현재 지원하지 않음 |
| 오프라인 검사 | 관리 모드 테스트는 Python·Git, 기존 selftest의 훅 검사는 pytest도 필요. ShellCheck는 선택 |

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
| 모델 id | Enter 로 `qwen3.8-flash-next`. 설치기가 LiteLLM 의 모델 목록을 출력한다. 목록의 `-oai` 변형은 OpenAI 형식으로 변환하는 경로라 사고 블록이 버려진다 → 접미사 없는 이름을 쓴다. 새 모델(예: GLM-5.3-Flash)이 등록되면 목록에 보이는 그 이름을 넣으면 된다 |
| 컨텍스트 창 | Enter. 설치기가 LiteLLM 이 알려 주는 값(현재 `qwen3.8-flash-next` = 262144)을 기본으로 보여 준다. 요청 하나가 쓸 수 있는 크기여야 한다 |
| 워커 이름 | Enter 로 `llm-worker` |
| 원격 노드 ssh 별칭 | `~/.ssh/config` 의 Host 이름. 없으면 Enter |

끝에 `llm-probe` 가 서버를 점검한다. 마지막 줄이 **"판정: 직접 연결 가능"** 이면 설치 완료.
FAIL 이 있으면 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) 의 표를 본다.

질문 없이 설치하려면 (연구실 기본값):

```bash
./install.sh --non-interactive
```

다른 서버를 쓰려면 환경변수로 값을 준다: `LLM_BASE_URL=http://host:port LLM_MODEL=<id> ./install.sh --non-interactive`.
대화형 설치는 구현 전용 프로필 `impl`(기본 Y)과 보조 모델 프로필 `vega`(기본 N, 게이트웨이의 `qwen3.6-35b-a3b`) 생성 여부를 묻는다.
비대화 설치에서 `impl`도 만들려면 `WITH_IMPL=1 ./install.sh --non-interactive`를 쓴다.
나중에 `./install.sh --profile impl` 또는 `./install.sh --profile vega`로 추가할 수 있다.
다른 모델용 워커는 `./install.sh --profile <이름>`으로 목록에서 골라 만든다 (아래 4절).

설치되는 것:

| 경로 | 내용 |
|---|---|
| `~/.local/bin/claude-main`, `claude-worker`, `claude-duo` | 실행기 |
| `~/.local/bin/llm-probe` | 서버 점검 |
| `~/.local/bin/worker-task` | 선택적 태스크 관리·worktree 격리·외부 검증 (Linux) |
| `~/.local/bin/remote-{info,sync,run,submit,fetch}` | 원격 노드 실행 (COMPUTE_HOST 설정 시) |
| `~/.config/claude-worker/env` (, `env.impl`, `env.vega` …) | 워커의 서버·모델·토큰 (권한 0600). 프로필마다 하나 |
| `~/.config/claude-worker/worker.md` (, `worker.impl.md` …) | 워커 시스템 프롬프트 (env 에서 자동 생성) |

`~/.local/bin` 이 PATH 에 없다는 경고가 나오면 `~/.bashrc` 에 `export PATH="$HOME/.local/bin:$PATH"` 를 넣고 새 셸을 연다.

## 3. 대화형 세션 실행

질문·조사·실행 결과 확인에 쓰는 수동 모드다. 코드 수정 위임은 4절의 관리 모드를 권장한다.

```bash
cd ~/my-project
claude-duo               # 오케스트레이터 + 기본 워커
claude-duo -P impl       # + 구현 전용 워커 @llm-worker-impl (설치 때 만든 프로필)
claude-duo -P impl,vega  # + 보조 모델 워커 @llm-worker-vega (vega 프로필을 만들었을 때, 느림)
```

tmux 창이 열린다. 왼쪽이 오케스트레이터, 오른쪽이 워커다. 창 사이 이동은 `Ctrl-b` 다음 화살표,
떼어 두기는 `Ctrl-b d`, 다시 붙기는 `claude-duo`, 끝내기는 `claude-duo --kill`.

tmux 없이 쓰려면 터미널마다 `claude-main`, `claude-worker`(, `claude-worker -P impl`)를 띄운다.
같은 프로젝트 디렉터리는 조회·실행 용도로 공유할 수 있다. 코드 편집까지 수동 위임한다면 메인이 먼저 별도 worktree를
준비하고 그 경로에서 워커를 시작한다. 메인과 워커가 상대의 작업 공간을 편집하지 않게 한다.

처음 여는 프로젝트 디렉터리면 두 세션 모두 "이 폴더를 신뢰하느냐"고 묻는다. 둘 다 예.

워커 창 상단에 로컬 모델 이름이 보이면 정상이다. "Model … isn't recognized · context assumed to be 200k" 는
경고일 뿐이며, 실제 컨텍스트 창을 설정에 적어 주면 사라진다(아래 6절).

## 4. 일 시키기

### 관리 모드로 코드 수정 맡기기

설치 후 코드가 들어 있는 Git 저장소로 이동한다. [명세 예시](config/task.example.json)를 복사해
실제 파일·지시·검증 명령에 맞게 편집한 뒤 등록한다.

```bash
cd ~/my-project
cp ~/claude-local-worker-kit/config/task.example.json /tmp/worker-task.json
# /tmp/worker-task.json을 편집한다. repository의 "."은 등록 명령의 현재 디렉터리다.
TASK=$(worker-task submit /tmp/worker-task.json)
worker-task run "$TASK"       # 전경 실행. 기존 프로필로 새 워커 프로세스를 시작한다.
worker-task status "$TASK"
worker-task result "$TASK"    # 검증 종료 코드, 변경 파일, 로그·diff 경로 확인
```

다른 터미널에서 `worker-task cancel <task ID>`로 해당 실행을 취소할 수 있다.
재시도는 결과를 검토한 뒤 `worker-task run "$TASK" --retry`로 명시한다. 이전 시도와 worktree는 보존된다.
`claude-duo`나 대화형 워커를 미리 띄울 필요는 없으며, `profile`에는 설치된 프로필 이름을 적는다
(`""`은 기본 프로필, `"impl"`은 구현 전용 프로필).

**기준 커밋에 포함된 코드만 전달된다.** 원본의 staged·unstaged·미추적 변경은 포함되지 않는다.
방금 작성한 스켈레톤·테스트에 의존한다면 `depends_on_uncommitted: true`로 실행을 차단하고,
필요한 입력의 기준 커밋을 사용자가 준비한 뒤 새로 등록한다. 워커의 완료 보고나 종료 코드 0만으로 성공 처리하지 않는다.
최종 검증 결과와 diff를 메인이 검토하고 반영 방법을 결정한다.

검증 명령은 캐시·빌드 산출물을 worktree에 남기지 않도록 작성한다. 관리 모드는 ignored 파일도 검사한다.
worktree는 편집 충돌을 줄이는 장치이며 보안 샌드박스는 아니다. 권한 설정, 보호 경로, 복구·로그 보존은
[관리 모드 상세 문서](docs/MANAGED_TASKS.md)에 설명한다.

### 수동 메시징으로 조회·실행 맡기기

대화형 오케스트레이터 창에서 다음처럼 요청한다. 실패한 코드를 수정하는 일은 별도의 관리 태스크로 등록한다.

```
Ask @llm-worker to: In /home/me/my-project run
`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider`.
Leave source files and Git state unchanged. Report the command, exit code and failing tests for a separate implementation task.
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

### 구현 태스크 준비와 검토

로컬 모델은 "짧은 명세를 받아 채우고, 돌리고, 고치는" 일은 잘하지만 **설계 판단과 긴 맥락 유지에는 약하다**.
그래서 킷은 구현 작업을 다음처럼 나누도록 오케스트레이터를 지도한다 (`agents/ORCHESTRATOR.md`).

| 단계 | 누가 | 내용 |
|---|---|---|
| 설계·분해 | 오케스트레이터(Claude) | 파일·함수 경계, 데이터 흐름 |
| 스켈레톤·테스트 | 오케스트레이터 | 시그니처·docstring 이 든 스켈레톤과 테스트 파일을 **직접** 쓴다 |
| 채우기·실행·반복 | 구현 워커 | 관리 모드에서는 실행기가 준비한 worktree의 본문을 채우고 수정본을 남긴다. 수동 모드는 오케스트레이터가 별도 작업 공간을 먼저 준비한다 |
| 검토 | 오케스트레이터 | 외부 검증 기록과 diff를 검토하고 반영을 결정한다. 같은 태스크가 두 번 실패하면 직접 구현(승격) |

스켈레톤과 테스트가 기준 커밋에 들어 있는지 확인한 뒤 관리 태스크를 등록한다. 메인은 워커가 작업하는 동안
그 worktree를 편집하지 않는다. 다음 도구와 양식을 함께 쓴다.

- **편집 후 자동 검사 훅** — `project-init` 이 넣는 `.claude/settings.json` 이 파일을 고칠 때마다 `agents/hooks/post-edit-check.sh` 를 돌린다
  (문법 → lint). 오류 출력이 워커의 다음 턴에 바로 들어간다. 편집마다 테스트까지 돌리는 모드(`check.conf` 의 `TEST_CMD="auto"`)도 있지만
  기본은 끔이다: 벤치마크에서 반쯤 쓴 모듈에 테스트 실패를 계속 들이밀면 어려운 태스크를 더 못 풀었다(아래 표). 오케스트레이터 세션에도 같은 훅이 걸린다.
- **구현 전용 워커 `@llm-worker-impl`** — 같은 모델이지만 시스템 프롬프트에 구현 규칙(지정 파일만 읽기, 테스트 수정 금지, 편집마다 검사 결과 반영, 세 번 막히면 보고)이 붙는다.
  설치 때 생성하거나 `install.sh --profile impl`로 추가한다. 수동 모드는 `claude-duo -P impl`, 관리 모드는 명세의 `profile: "impl"`로 선택한다.
- **구현 태스크 양식** `agents/tasks/T_impl_template.md` — 기준 커밋, 참고·허용·보호 경로, 채울 함수 표, 검증 명령, 시간 제한을 적는다. 지시문은 관리 명세의 `task_file`로 전달할 수 있다.
- **벤치마크** `bench/run.sh` — 워커 혼자 구현 태스크 10개(기본 6 + 어려운 4)를 풀게 하고 숨은 테스트로 채점한다. 모델·서버·프롬프트를 바꿨을 때
  "어디까지 맡길 수 있는지"를 숫자로 본다. 결과는 `bench/results/`. 자세한 것은 [bench/README.md](bench/README.md).

  2026-10-29 실측 (`qwen3.6-35b-a3b`, impl 프로필, 각 조건 1회):

  | 조건 | 기본 6개 | 어려운 4개 | 비고 |
  |---|---|---|---|
  | 훅이 편집마다 테스트까지 실행 | 5/6 | 0/4 | 파서는 20분 초과, 나머지는 숨은 테스트 1~2개 차이 |
  | 훅 없음 | 5/6 | 3/4 | 파서만 실패(숨은 테스트 18/20). 태스크당 시간도 짧음 |

  한 모듈짜리 명확한 명세는 혼자서도 풀고(LRU 캐시는 스켈레톤 없이도 통과), 놓치는 것은 명세의 구석 조항(오류 조건, stderr, 경계)이다.
  그래서 Claude 가 테스트를 촘촘히 써 주는 분업이 효과가 있고, 편집마다 테스트를 들이미는 것은 역효과였다.

  같은 날 저녁 GB10 의 `qwen3.8-flash-next` 로 재측정(훅 기본 = 문법·lint): **10/10 통과**, 숨은 테스트까지 전부. 3.6 이 두 번 놓친 B1 과 H1(파서)도 한 번에 풀었다.
  태스크당 1~5분, 턴 6~17 (`bench/results/2026-10-29_flash-next.md`). 분업 규칙은 그대로 두되, 이 모델에는 모듈 하나 통째로 맡겨도 된다.

사고(thinking) 조절에 대해: Claude Code 2.1.312 는 모든 요청에 `thinking: adaptive` 를 보내고 `MAX_THINKING_TOKENS` 는 무시한다(0 이면 필드만 빠지고 백엔드는 그래도 사고한다).
`effort` 값도 백엔드가 무시한다. 사고량을 제한하려면 **서버 쪽**(llama.cpp `--reasoning-budget`, vLLM 의 reasoning 옵션)에서 해야 한다 — 7절 관리자 항목.

### 모델·경로 나눠 쓰기

모든 워커는 게이트웨이(:4000)만 바라본다. 게이트웨이에는 모델 이름이 둘 있고, 이름이 **우선 백엔드**를 고른다(다른 쪽은 그 백엔드가 실패할 때의 자동 대체).

| 워커 | 모델 이름 | 우선 백엔드 | 특징 | 보낼 일 |
|---|---|---|---|---|
| `@llm-worker` (기본) | `qwen3.8-flash-next` | GB10 노드 | 컨텍스트 262144, 프롬프트 캐시 됨, 16 동시 요청 OK | 테스트 실행, 결과 수집, 실험, 파일 정리 |
| `@llm-worker-impl` | 같은 이름, 구현 규칙 프롬프트 | GB10 노드 | | 스켈레톤 채우기, 테스트 통과시키기 |
| `@llm-worker-vega` (선택) | `qwen3.6-35b-a3b` | LLM 서버 llama.cpp (AMD Vega 2장) | 컨텍스트 131072, 생성 17 tok/s 로 느림 | 기본 워커가 바쁠 때 가벼운 수집 작업 보조 |

```bash
~/claude-local-worker-kit/install.sh --profile vega    # 보조 프로필 (설치 때 안 만들었으면)
~/claude-local-worker-kit/install.sh --profile glm     # 새 모델이 게이트웨이에 등록되면: 목록에서 이름을 고르고 컨텍스트는 자동
claude-duo -P impl,vega                                # 기본 + 구현 전용 + 보조 워커
```

`-oai` 접미사 이름은 같은 백엔드를 OpenAI 형식으로 변환해 넘기는 경로다(사고 블록이 버려짐). 구성원은 쓰지 않는다.

모두 `Ask @이름 to …` 로 똑같이 부른다. `templates/project/agents/ORCHESTRATOR.md` 에 배분 규칙이 들어 있어 오케스트레이터가 고른다.

### 속도와 컨텍스트 (2026-10-29 실측)

| 경로 | 프롬프트 처리 | 토큰 생성 | 요청당 컨텍스트 | Bash 한 번짜리 워커 왕복 |
|---|---|---|---|---|
| LiteLLM `:4000` 의 `qwen3.8-flash-next` (GB10, 2026-10-29) | 약 6,000~12,000 tok/s (34k 토큰 2.8초, 240k 토큰 37초) | 약 35 tok/s (16 동시 요청 합계 약 130 tok/s) | 262144 | 약 15초 |
| (참고, 이전) LiteLLM 의 `qwen3.6-35b-a3b` (GB10) | 약 5,500 tok/s | 약 90 tok/s | 131072 | 수 초 ~ 20초 |
| LiteLLM `:4000` 의 `qwen3.6-35b-a3b` (`vega` 프로필, LLM 서버 llama.cpp 우선) | 약 200~350 tok/s | 약 17 tok/s | 131072 | 약 3분 |

이 측정에서 `qwen3.8-flash-next`는 간단한 질문에 사고 100 토큰 안팎을 사용했고, `thinking: disabled`와 긴 입력 캐시도 동작했다.
우선 백엔드가 실패하면 게이트웨이가 다른 쪽으로 넘기므로 **같은 작업도 어떤 턴은 느릴 수 있다**. 고장이 아니다. 단, 기본 워커의 요청이 131072 토큰을 넘은 상태에서
대체 백엔드(llama.cpp)로 넘어가면 400 이 난다 — 긴 작업은 `/clear` 로 자주 새로 시작한다.
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

관리 모드는 각기 다른 task ID를 별도 터미널에서 `worker-task run <ID>`으로 실행한다.
태스크마다 worktree·결과가 나뉘며, 같은 태스크의 중복 실행은 거절된다.

수동 메시징에서는 워커 세션 하나가 받은 메시지를 **순서대로** 처리한다. 조회·실행 요청 세 개를 동시에
처리하려면 대화형 워커도 세 개 띄운다.

```bash
claude-duo -w 3          # 기본 워커 3개: llm-worker-1, llm-worker-2, llm-worker-3
claude-duo -w 2 -P impl  # 기본 워커 2개 + 구현 전용 워커 1개
```

오케스트레이터에서 `Ask @llm-worker-1 to …`, `Ask @llm-worker-2 to …` 로 나눠 보낸다.
수동으로 띄우려면 터미널마다 `CLAUDE_WORKER_NAME=llm-worker-2 claude-worker`.
동시 처리량은 게이트웨이와 실제 백엔드 설정에 따라 달라진다. 위 속도 표의 수치는 측정 당시 결과이며 처리량 보장은 아니다.
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
값을 바꾼 뒤 `LLM_CONTEXT_WINDOW`도 새 모델의 요청당 크기에 맞게 확인한다. `--render`는 프롬프트를 재생성하며 컨텍스트 크기를 자동 조회하지 않는다.
프로필을 더 만들려면 `./install.sh --profile <이름>` (`impl` = 같은 모델의 구현 전용 워커, `vega` = 게이트웨이에서 LLM 서버 llama.cpp 우선, 그 외 이름 = 다른 모델을 목록에서 고름).

## 7. 서버 쪽 구성 (관리자용)

```
구성원 PC: claude-main (Claude) ⇄ claude-worker ──HTTP──▶ LLM 서버 1.233.219.134
                                                      LiteLLM :4000 ─┬─▶ (ssh 터널 :18000) GB10 노드 1.233.218.218   ← qwen3.8-flash-next 우선
                                                                     └─▶ llama.cpp 127.0.0.1:8080 (같은 호스트, Vega)  ← qwen3.6-35b-a3b 우선
                                                      (각 이름은 다른 쪽을 자동 대체로 가진다)
```

LiteLLM 설정·실행 방법은 [proxy/README.md](proxy/README.md). 모델을 추가·교체할 때는 6절에 따라 `LLM_MODEL`과 컨텍스트 크기를 함께 확인한다.
LiteLLM 이 죽었을 때는 관리자에게 알린다. 최후 수단(직접 접속)은 docs/TROUBLESHOOTING.md 에 있다.

**사고 토큰 상한(관리자)** — 실측(2026-10-29): 클라이언트의 `effort` 는 백엔드가 무시하고, `thinking.budget_tokens` 는 지키지만 Claude Code 가 그 필드를 보내지 않으며,
LiteLLM `litellm_params` 에 `thinking` 을 넣어도 요청 값(adaptive)이 이긴다. 따라서 과도한 사고를 줄이려면 엔진에서 제한한다:
llama.cpp 는 `--reasoning-budget <토큰>`, vLLM/SGLang 은 reasoning parser 의 budget 옵션. 코딩 태스크 기준 2k~8k 토큰이 보통 충분하다.

## 8. 문제 해결·제거

증상별 해결은 [문제 해결 안내](docs/TROUBLESHOOTING.md), 관리 태스크의 실패·복구·권한 설정은
[관리 모드 문서](docs/MANAGED_TASKS.md)를 참고한다.

키트 디렉터리에서 다음 검사를 실행한다. 두 검사 모두 모의 Claude를 사용하며 실제 모델을 호출하지 않는다.

```bash
bash tests/selftest.sh
python3 -B -m unittest discover -s tests -p 'test_worker_task.py' -v
```

`bash tests/selftest.sh --real-cli`는 설치된 Claude CLI의 버전도 확인한다. 모델·서버와의 실제 연동은
`llm-probe`와 작은 관리 태스크로 별도 확인한다. 관리 모드 1차 구현은 오프라인 테스트로 검증했으며 실제 모델 연동은 아직 검증하지 않았다.

제거는 `./uninstall.sh`, 프로필 설정까지 지우려면 `./uninstall.sh --purge`를 쓴다.
관리 태스크의 worktree·결과 저장소는 제거기가 삭제하지 않는다.

## 파일 구성

```
install.sh / uninstall.sh      설치·제거 (--profile NAME: 다른 모델용 워커, --render: 프롬프트만 재생성)
bin/                           실행기·점검·원격 스크립트, project-init(프로젝트에 규칙·훅 넣기)
config/worker.env.example      설정 키 설명
config/task.example.json       편집해서 등록하는 관리 태스크 명세 예시
prompts/*.tmpl                 워커 시스템 프롬프트 템플릿
proxy/                         LiteLLM 변환 프록시 (선택)
templates/project/             프로젝트용 AGENTS.md, 역할 파일, 구현 태스크 양식, 편집 후 검사 훅, 시작 프롬프트
bench/                         워커 단독 구현 벤치마크 (tasks/, run.sh, results/)
tests/selftest.sh              오프라인 자체 검사
tests/test_worker_task.py      모의 Claude + 임시 Git worktree 통합 검사
docs/FIRST_RUN.md              첫 실행 시운전
docs/MANAGED_TASKS.md          관리 태스크 등록·실행·검증·복구와 제한
docs/TROUBLESHOOTING.md        증상별 해결
docs/MIGRATION.md              기존 개인 구성(claude-glm / drl-*)에서 옮기기
PLAN.md                        배포 계획과 결정 사항
```
