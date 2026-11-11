# Local Worker Kit

Codex 또는 Claude가 작업을 나누고, 등록한 LLM 서버의 모델이 조사·구현·테스트·리뷰를 수행하는 CLI 키트입니다.
기존 `claude-local-worker-kit`과 DeepSeek 버전을 합쳤습니다. 서버나 모델이 달라도 코드와 설치 방식은 같습니다.

태스크마다 별도 Git worktree를 사용합니다. 워커의 완료 보고 대신 허용/보호 경로, 실제 검증 종료 코드,
검증 전후 파일 해시로 성공을 결정합니다. 원본의 staged·unstaged·미추적 변경은 전달하거나 수정하지 않습니다.

## 설치

Linux/WSL2, Python 3.9+, Git, Claude Code 2.1.257+가 필요합니다. 워커 실행에는 Claude CLI를 사용합니다.
Codex를 메인으로 쓰려면 Codex CLI도 설치합니다. tmux는 창 표시 모드에서만 필요합니다.

```bash
sudo apt update
sudo apt install -y git python3 curl ca-certificates tmux
curl -fsSL https://claude.ai/install.sh | bash
# Codex 메인을 쓸 경우: 공식 독립 설치 스크립트 (Node 불필요). 전역 설치는 아래 codex-bootstrap --codex-global
curl -fsSL https://chatgpt.com/codex/install.sh | sh
```

Claude 메인은 `claude auth login`, Codex 메인은 `codex login`으로 본인 계정을 사용합니다.
Codex 메인의 모델을 Anthropic API 키(크레딧)로 호출하려면 설치 뒤 `codex-bootstrap --check`로 시작합니다.
구성과 함정 목록은 [Codex 메인 + Anthropic API 키](docs/CODEX_ANTHROPIC.md)에 있습니다.
워커의 서버 인증은 별도이며 등록한 서버의 API 키 또는 명시적인 `none` 모드를 사용합니다.
설치 방법은 [Claude Code 문서](https://code.claude.com/docs/en/setup)와
[Codex CLI 문서](https://developers.openai.com/codex/cli/reference/)를 참고하세요.

```bash
git clone https://github.com/leejunyong1815-eng/claude-local-worker-kit.git
cd claude-local-worker-kit
./install.sh --non-interactive --setup-path
. "$HOME/.config/local-worker/shell.sh"
worker-doctor
```

새 설정은 `~/.config/local-worker`, 명령은 `~/.local/bin`에 설치합니다. 기존 설정이 있으면 설치기가 출력한
실제 경로를 사용하세요. `--install-only`는 서버 설정 없이 명령만 설치하며, 설치·업데이트는 모델을 호출하지 않습니다.
기존 두 버전의 설정을 가져오는 방법은 [통합·마이그레이션](docs/MIGRATION.md)에 있습니다.

기본 게이트웨이는 `http://1.233.219.161:4000`, 일반 모델은 `deepseek-v4.1-flash`,
Compute Job 모델은 `qwen3.8-flash-next`입니다. 현재 기본 인증은 `none`, 클라이언트 컨텍스트 예산은 262144입니다.
다른 서버·모델은 아래 레지스트리에 등록합니다. 자동 fallback은 없습니다.

## 서버와 모델 등록

워커 서버는 Anthropic Messages·SSE·도구 호출을 지원해야 합니다. OpenAI Chat Completions만 제공하는
vLLM 서버는 호환 게이트웨이를 통해 연결하세요. URL 끝에 `/v1`을 붙이지 않습니다.

```bash
llm-backend add lab --url http://1.233.219.161:4000 \
  --model deepseek-v4.1-flash --max-parallel 2
llm-backend model-add lab qwen3.8-flash-next \
  --roles compute-runner --context 262144
llm-backend list
```

서버 하나에 모델을 여러 개 등록할 수 있습니다. `model-add ... --roles researcher,reviewer`처럼
역할을 정하면 모델 이름과 관계없이 그 역할에 배정합니다. 특정 역할 전용 모델이 일반 모델보다 우선합니다.
같은 조건의 워커는 대기·실행 중인 태스크 수로 배분합니다. 품질이나 속도를 모델 이름에서 추정하지 않습니다.

다른 서버는 다른 이름으로 추가합니다. 아래 URL과 모델 ID는 본인의 서버 값으로 바꿉니다.

```bash
llm-backend add lab2 --url http://your-other-server:4000 --model your-model-id
llm-backend default lab
```

인증 서버는 `--auth api_key`로 키를 숨김 입력하거나 `--key-env 변수명`으로 환경변수를 읽습니다.
키를 명령 인자에 직접 넣는 옵션은 없습니다. 등록 정보는 private JSON(`0600`)에 저장하고 목록에는 키를 표시하지 않습니다.
기존 이름은 덮어쓰지 않으며 `--replace`를 명시하면 이전 설정을 백업합니다.

실제 서버 검사는 별도입니다. 아래 명령은 모델 요청을 보냅니다.

```bash
llm-probe --backend lab --model deepseek-v4.1-flash
```

## 사용

작업할 Git 저장소에서 규칙을 설치하고 메인을 시작합니다.

```bash
cd /path/to/project
project-init .
codex-duo --headless --backends lab
# Claude 메인을 쓰는 경우
claude-duo --headless --backends lab
# 메인 세션 이름을 지정하는 경우
claude-duo -n ozaki --backends lab
```

대화에는 원하는 결과와 완료 조건을 말하면 됩니다. 사용자가 워커 이름이나 관리 CLI를 지정할 필요는 없습니다.
메인이 태스크를 등록하면 풀이 실행하고, `worker-task wait`로 기다린 뒤 검증 결과와 변경을 검토합니다.
기본 메인은 Codex의 기존 계정/모델 설정 또는 Claude 계정의 Opus입니다. 일반 위임은 같은 관리 실행기를 사용하며, 네이티브 판단·리뷰도 기본으로 선택할 수 있습니다.

### 창 없이 실행하거나 창으로 확인

```bash
# 워커 수: 서버별 max-parallel 합계와 max-workers 중 작은 값 (기본 상한 4)
claude-duo --headless --workers auto --max-workers 4 --backends lab,lab2
# tmux에서 메인과 워커별 진행 상태를 표시
codex-duo --panes -w 3 --backends lab --label 'llm-worker-검토 빠름'
# 뒤의 일반 단어는 풀 표시 이름으로 사용
codex-duo 연구실 데모
```

`--headless`가 기본입니다. `--panes`도 같은 태스크·검증 실행기를 쓰며 표시 방식만 다릅니다.
유휴 워커는 모델을 호출하지 않습니다. 풀에서 설정한 수보다 태스크가 많으면 큐에서 기다립니다.
서버별 동시 실행 한도는 풀 간에도 공유하며, 태스크가 대기할 때 모델을 반복 호출하지 않습니다.
이 한도는 관리 태스크 기준이며, 워커 내부의 추가 에이전트·API 요청을 프록시 수준에서 제한하지는 않습니다.

워커 이름에 접미사·공백·한글이 있어도 동작합니다. 이름의 접두사로 소속을 추측하지 않습니다.
사용자 UID·pool ID·worker ID로 소속을 기록하고 화면과 `llm-worker list`에 `owned`를 표시합니다.
다른 풀의 워커 ID로 태스크를 배정하면 거절합니다.
`claude-main -n 이름`, `claude-duo -n 이름`, `llm-worker -n 이름`은 지정한 표시 이름을 그대로 씁니다.
이름을 생략하면 메인·워커의 기본 이름을 구분하며, 수동 duo도 자신이 띄운 워커의 정확한 이름 목록을 메인에 전달합니다.
`llm-worker-...` 뒤에 붙는 단어를 모델이나 소속 판정에 사용하지 않습니다.

`--models 모델1,모델2`, `-P 프로필1,프로필2`는 워커별 선택을 고정할 때 사용합니다.
`--` 뒤 인자는 메인 CLI로 전달합니다. 예: `claude-duo --headless -- --resume`, `codex-duo -- resume --last`.
재개한 메인은 현재 풀의 ID와 지침을 사용해야 하며, 이전 풀의 태스크를 자동 재실행하지 않습니다.

| 방식 | 용도 | 동작 |
|---|---|---|
| headless | 평소 구현·조사·리뷰 | 백그라운드 풀, 별도 task ID/worktree, 외부 검증 |
| panes | 데모·진행 상황 확인 | 같은 풀과 검증, tmux에 워커별 상태 표시 |
| `claude-duo --manual` | 기존 수동 세션 간 메시징 | 직접 띄운 대화형 워커; 자동 격리/완료 검증 없음 |

수동 모드는 [대화형 문서](docs/INTERACTIVE.md), 관리 CLI는 [태스크 문서](docs/MANAGED_TASKS.md)를 참고하세요.
시작 전에 서버 호환성까지 검사하려면 `claude-duo --probe` 또는 `codex-duo --probe`를 사용합니다.
선택 가능한 서버·모델에 실제 요청을 보내며, 실패하면 메인과 워커를 시작하지 않습니다. 기본 실행은 이 검사를 생략합니다.

### 고난도 판단·EGM 리뷰에 네이티브 에이전트 허용

```bash
claude-duo -n ozaki --backends lab
codex-duo --backends lab
```

기본값은 `--native-agents selective`입니다. 메인이 EGM 리뷰, 아키텍처 선택, 엄밀한 추론,
복잡한 원인 분석에 네이티브 에이전트를 선택할 수 있습니다. 호출 전에 이유·범위·기대 결과를 짧게 밝히며,
일반 조사·구현·테스트는 계속 등록된 LLM 워커에 맡깁니다. 사용자가 매번 워커를 지정할 필요는 없습니다.
이 선택 기준은 모델 지침이며 호출 목적을 코드가 강제로 분류하는 기능은 아닙니다.

네이티브는 소스를 읽고 판단·리뷰 결과를 돌려주는 용도입니다. 원본이나 관리 worktree를 직접 편집하지 않도록 지시합니다.
메인의 계정·모델 설정을 사용하고 관리 풀의 동시 실행 한도·task 결과·취소에는 포함되지 않습니다.
기존 권한·샌드박스는 유지합니다. 상세 범위는 [네이티브 위임](docs/NATIVE_AGENTS.md)을 참고하세요.

`claude-main`, `codex-main`, `claude-duo --manual`도 기본 selective입니다. 네이티브를 끄려면 `--native-agents off`를 지정합니다.

```bash
claude-duo -- --resume
codex-duo -- resume --last
# 관리 워커만 사용할 세션
claude-duo --native-agents off
```

## 작업 범위와 권한

일반 역할은 researcher/planner/implementer/test-author/runner/analyst/reviewer입니다.
기본 workspace 권한은 Bash·Python·환경 도구·웹·에이전트와 SSH/scp/sftp/rsync를 허용합니다.
원격 작업에는 실제 호스트·경로·범위·예산을 지정합니다. 추론 서버 주소를 SSH 호스트로 추정하지 않습니다.
기존 사용자·프로젝트·조직의 deny/ask는 유지하며 권한 우회 옵션을 추가하지 않습니다.

Qwen 등 compute-runner 모델은 고정된 Compute Job의 운영과 로그 조회·회수를 담당합니다.
자원 대기·GPU 잠금·실행·검증·원격 취소는 [Compute Job 실행기](docs/COMPUTE_JOBS.md)가 처리합니다.
직접 SSH로 시작한 잡은 이 수명 관리에 자동 편입되지 않습니다. 원격 변경은 로컬 diff만으로 검증할 수 없습니다.

원본의 미커밋 변경은 worktree에 포함되지 않습니다. 의존하면 태스크를 차단하고 입력을 준비해야 합니다.
성공 후 코드가 바뀌면 검증도 무효가 됩니다. 실패·취소·중단 결과는 보존하며 자동 stash·commit·merge·push·삭제는 하지 않습니다.
worktree와 Claude 권한 규칙은 보안 샌드박스가 아닙니다. Bash는 현재 사용자 권한으로 실행됩니다.
자세한 경로·외부 데이터·기존 SSH deny 처리는 [권한 문서](docs/WORKER_PERMISSIONS.md)를 참고하세요.
기존 `remote-*` 전송 명령의 SSH 설정·작업별 원격 경로는 [원격 도우미 문서](docs/REMOTE_HELPERS.md)에 있습니다.

## 업데이트와 호환 명령

```bash
git pull --ff-only
./install.sh --update --setup-path
project-update --check /path/to/project
project-update --apply /path/to/project
```

API 키·등록 서버·모델·프로필·태스크 결과를 보존합니다. 사용자 수정 문서는 덮어쓰지 않고 `incoming/`에 제안합니다.
새 지침/권한은 새 실행부터 적용하므로 메인은 종료 후 재개합니다.
`claude-main`, `claude-worker`, `worker-task`, `project-init/update`와 기존 `deepseek-*`는 계속 사용할 수 있습니다.
모두 같은 실행기를 사용합니다. 기존 상태 폴더는 옮기거나 삭제하지 않으며 `--state-dir`로 조회할 수 있습니다.
[업데이트 상세](docs/UPDATING.md) · [통합 이력](UPSTREAM.md).

## EGM 설치와 설계 리뷰

[Elephant Goldfish Model(EGM)](https://github.com/google/elephant-goldfish-model)은 설계 문서 작성·리뷰용 플러그인입니다.
추론 서버나 모델이 아니므로 `llm-backend`에 등록하지 않습니다. Claude Code는 EGM의 [리뷰어 격리 기능](https://github.com/google/elephant-goldfish-model/blob/main/docs/claude.md)에 필요한 **2.1.271 이상**을 사용합니다.
아래 명령은 사용할 CLI에 맞게 WSL 안에서 실행합니다. 플러그인 전체가 필요하며 `skills/`만 복사하면 참고 자료가 빠집니다.
Google 저장소를 플러그인 소스로 등록해 설치하는 방식이므로 이 절차에는 별도 clone이나 pip 설치가 필요하지 않습니다.

```bash
# Claude Code
claude plugin marketplace add google/elephant-goldfish-model
claude plugin install egm@egm --scope user
claude plugin enable egm@egm
```

```bash
# Codex CLI
codex plugin marketplace add google/elephant-goldfish-model
codex plugin add egm@egm
```

소스를 직접 받아 설치하려면 위 GitHub 등록 대신 아래 로컬 경로 등록을 사용합니다. 두 방법 중 하나만 선택합니다.
이미 clone한 경우에는 기존 경로를 사용합니다.

```bash
mkdir -p "$HOME/src"
git clone https://github.com/google/elephant-goldfish-model.git "$HOME/src/elephant-goldfish-model"
# Claude Code
claude plugin marketplace add "$HOME/src/elephant-goldfish-model"
claude plugin install egm@egm --scope user
claude plugin enable egm@egm
# Codex CLI를 쓰는 경우: 위 Claude 명령 대신 실행
# codex plugin marketplace add "$HOME/src/elephant-goldfish-model"
# codex plugin add egm@egm
```

설치 후 새 `claude-duo` 또는 `codex-duo` 세션을 시작합니다. 기본 selective에서 EGM의 네이티브 리뷰어를 호출할 수 있습니다.
`--native-agents off`를 지정한 세션에서는 리뷰어가 차단됩니다. 프로젝트 지침도 `project-update --check` / `--apply`로 갱신합니다.
네이티브 호출을 허용하는 경로를 추가했으며 실제 EGM 전체 리뷰 흐름은 아직 검증하지 않았습니다.

관리 풀과 분리한 설계 세션이 필요하면 일반 CLI도 사용할 수 있습니다.

```bash
mkdir -p "$HOME/egm-design"
cd "$HOME/egm-design"
claude -n egm-design
# Codex를 쓸 경우 위 명령 대신 실행
# codex -c agents.enabled=true -c features.multi_agent=true
```

Claude에서는 `/egm:egm-brainstorm`, `/egm:egm-draft`, `/egm:egm-review`를 사용합니다.
Codex에서는 설치된 EGM 스킬을 선택합니다. 검토할 저장소·문서 경로는 프롬프트에 지정하고 소스는 읽기 전용으로 참고하게 합니다.
일반 CLI의 모델·계정 설정을 사용하며, Goldfish 리뷰가 DeepSeek나 관리 풀로 자동 배정되지는 않습니다.
설치 확인, 입력 프롬프트, 권한·작업 공간·토큰 비용의 차이는 [EGM 호환성 검토](docs/EGM.md)에 정리했습니다.
이 키트의 설치·업데이트 명령은 EGM을 설치하거나 갱신하지 않습니다.

## 검증과 제한

```bash
./tests/selftest.sh
python3 -B demo/rehearse.py
```

두 명령은 실제 모델을 호출하지 않습니다. 임시 Git 저장소·모의 CLI로 원본 변경 보존, 중복 실행,
경로 위반, 시간 초과, 취소·복구, 서버/모델 라우팅과 두 메인의 위임 흐름을 검사합니다.
랩미팅 실행 절차는 [demo/README.md](demo/README.md)에 있습니다.

토큰/속도 개선을 수치로 보장하지 않습니다. 유휴 호출과 메인의 반복 polling을 줄이고 독립 태스크를 병렬화했지만,
실제 효과는 모델·작업 분할·서버 용량에 따라 달라집니다. 대규모 벤치마크·실제 유료 모델 호출은 수행하지 않습니다.
과거 서버 측정은 [서버 기록](docs/LAB_SERVER.md)에 날짜별로 남깁니다.

최신 통합 검증: [오프라인·tmux·실제 워커 기록](docs/validation/unified-kit.json).
후속 수정 검증: [원격 동기화·세션 이름·수동 권한 회귀 검사](docs/validation/handoff-fixes.json).
선택적 네이티브 검증: [모드 전환·관리 위임·CLI 설정 검사](docs/validation/native-agents.json).
