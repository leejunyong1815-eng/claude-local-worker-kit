# PLAN — Claude 오케스트레이터 + 로컬 LLM 워커 배포판

작성: 2026-10-28. 대상: 연구실 구성원. 현재 ljy 환경(`~/bin/claude-glm`, `~/bin/claude-main`,
`~/bin/drl-*`, `~/.claude/prompts/glm-worker.md`)을 **서버 독립적인 설치 패키지**로 재구성한다.

## 1. 현재 구조 (as-is)

| 구성요소 | 역할 | 문제점 |
|---|---|---|
| `claude-main` | 진짜 Claude(Fable)로 오케스트레이터 세션 시작, `--remote-control` | 그대로 써도 됨 |
| `claude-glm` | 두 번째 Claude Code 프로세스를 기존 외부 LLM 서버(LiteLLM 프록시)에 연결, `--name glm-worker`, `crossSessionInbound: accept` | URL·모델명·토큰 경로가 하드코딩 |
| `~/.claude/prompts/glm-worker.md` | 워커 시스템 프롬프트 | DRL 노드(A6000×2, FPGA, 계정 jyl)가 하드코딩 |
| `drl-sync/run/submit/fetch/info` | 원격 GPU 노드에 rsync + ssh 실행 | 호스트 `DRL`, 경로 `/home/jyl/claude-work` 하드코딩 |
| 프로젝트 `AGENTS.md`, `agents/SUBAGENT_*_GLM.md`, `HANDOFF_TEMPLATE.md` | 역할·보고 양식 | qcfd 프로젝트 전용 내용 포함 |
| 오케스트레이터 → 워커 위임 | 메인 대화에서 `Ask @glm-worker to ...` | 유지 |

## 2. 목표 구조 (to-be)

```
claude-local-worker-kit/
├── install.sh / uninstall.sh      설치·제거 (설정 질문 → ~/.config/claude-worker/env 작성, bin 복사)
├── config/worker.env.example      LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, WORKER_NAME, COMPUTE_HOST ...
├── bin/claude-main                오케스트레이터 (변경 없음, ANTHROPIC_* 환경 제거 후 실행)
├── bin/claude-worker              로컬 LLM 워커 (env 파일에서 서버·모델 읽음)
├── bin/claude-duo                 tmux 한 창에 오케스트레이터 + 워커 동시 실행
├── bin/llm-probe                  서버 점검: /v1/models, /v1/messages, 스트리밍, tool_use, count_tokens
├── bin/remote-{info,sync,run,submit,fetch}   drl-* 일반화 (COMPUTE_HOST / COMPUTE_WORK_DIR)
├── prompts/worker.md.tmpl         워커 시스템 프롬프트 템플릿 (설치 시 값 치환)
├── proxy/                         서버가 /v1/messages 를 지원하지 않을 때 쓰는 LiteLLM 프록시
├── templates/project/             새 프로젝트용 AGENTS.md, 역할 파일, HANDOFF, KICKOFF 템플릿
├── tests/selftest.sh              문법 검사 + 설정 검사 + 서버 점검
└── README.md, docs/               설치·사용·문제해결
```

## 3. 결정 사항

1. **API 형식**: Claude Code는 Anthropic Messages API(`/v1/messages`)만 쓴다. 2026년 현재
   vLLM, SGLang, llama.cpp, Ollama(≥0.14) 모두 이 엔드포인트를 자체 제공하므로 **기본은 직접 연결**.
   `llm-probe` 가 실패하면 `proxy/` 의 LiteLLM 으로 감싼다(OpenAI chat/completions → messages 변환).
2. **모델 계층 매핑**: `ANTHROPIC_DEFAULT_{OPUS,SONNET,HAIKU}_MODEL` 을 모두 `LLM_MODEL` 로 묶어
   백그라운드 호출(제목 생성 등)이 서버가 모르는 모델명으로 가지 않게 한다.
3. **설정 위치**: `~/.config/claude-worker/env` (0600). 토큰은 여기만. 스크립트에는 값이 없다.
4. **원격 계산 노드**: 선택 사항. `COMPUTE_HOST` 가 비어 있으면 워커 프롬프트에서 원격 절이 빠진다.
   채워져 있으면 ssh 별칭 하나로 `remote-*` 가 동작한다. 연구실 서버 목록·GPU 예약 규칙은
   프로젝트 `CLAUDE.md` 가 담당한다(패키지에 복제하지 않는다).
5. **크로스 세션 메시징**: 워커는 `--name $WORKER_NAME` + `crossSessionInbound: accept`.
   같은 머신·같은 사용자에서 두 세션을 띄운다. `claude-duo` 가 tmux 로 이를 한 번에 한다.
6. **버전 고정**: Claude Code ≥ 2.1.300 (현재 2.1.312) 을 요구한다. `--name`, `--settings`,
   `--append-system-prompt`, 크로스 세션이 이 범위에서 확인됨.

## 4. 작업 단계

- [x] 현재 구성 수집 및 분석
- [x] 서버별 Anthropic API 지원 조사 (vLLM/SGLang/llama.cpp/Ollama/LiteLLM)
- [x] `config/worker.env.example`, `bin/claude-worker`, `bin/claude-main`, `bin/claude-duo`
- [x] `bin/llm-probe`
- [x] `bin/remote-*` 일반화
- [x] `prompts/worker.md.tmpl`
- [x] `proxy/` (LiteLLM docker-compose + config)
- [x] `templates/project/`
- [x] `install.sh`, `uninstall.sh`, `tests/selftest.sh`
- [x] `README.md`, `docs/TROUBLESHOOTING.md`
- [x] 자기 환경에서 설치 테스트: 임시 prefix 에 설치, `-p` 응답·Bash 도구 호출·`--bg` 워커에 크로스 세션 메시지 전달까지 GLM 서버로 확인 (2026-10-28)
- [x] 연구실 LLM 서버(1.233.219.134:8080, llama.cpp docker, `qwen3.6-35b-a3b`) 확인 → 기본값·프롬프트 반영 (2026-10-28)
- [x] ssh 터널(127.0.0.1:18080 → LLM:8080)로 `llm-probe` 8/8 OK, `claude-worker -p` 일반 응답·Bash 도구 호출 OK (2026-10-28)
- [x] 서버가 0.0.0.0:8080 으로 열림 → 터널 없이 `llm-probe` 8/8 OK, `claude-worker -p` Bash 도구 호출 OK (2026-10-28, 4e)
- [x] git init (초기 커밋)
- [ ] 태그, 연구실 공유 경로(`/mnt/148TB/LJY/...`) 또는 git 저장소로 배포

## 4b. 검증 결과 (2026-10-28, 기존 외부 서버 기준)

- `tests/selftest.sh` 31/31 통과.
- `llm-probe`: 스트리밍·tool_use·tool_result 왕복·thinking·count_tokens OK. 비스트리밍·cache_control 은 기존 서버의
  상위 백엔드 요청 한도("Request limit exceeded")로 간헐 실패 → 프로브에 재시도 추가. 기능 미지원 아님.
- `claude-worker -p` : 일반 응답 OK, `--allowedTools Bash` 로 도구 호출 OK.
- `claude-worker --bg` 로 띄운 워커가 `ListAgents` 에 보이고, `SendMessage` 로 보낸 태스크를 로컬 모델이 Bash 로 수행해 정확한 결과를 회신 (왕복 확인).
- `remote-info` 가 DRL 노드 현황을 가져옴.
- 발견: Claude Code 가 모르는 모델은 컨텍스트 200k 가정 → `LLM_CONTEXT_WINDOW` 키 추가 (`CLAUDE_CODE_MAX_CONTEXT_TOKENS`).

## 4c. 검증 결과 (2026-10-28, 연구실 llama.cpp 서버 `qwen3.6-35b-a3b`)

- `llm-probe`: 모델 목록·비스트리밍·SSE·tool_use·tool_result 왕복·cache_control·thinking·count_tokens 전부 OK.
  (비스트리밍 응답 텍스트가 비어 있던 것은 사고 토큰이 max_tokens 32 를 소진한 것. 서버 문제 아님.)
- `claude-worker -p`: 일반 응답 OK, `--allowedTools Bash` 로 `wc -c` 실행 결과 정확.
- `LLM_CONTEXT_WINDOW` 설정으로 "context assumed to be 200k" 경고 사라짐. (당시 131072 로 넣었으나 4e 에서 슬롯당 32768 로 정정.)
- 서버 `chat_template_caps`: tools, parallel tool calls, system role, preserve_reasoning 지원. reasoning_effort 미지원.

## 4d. 프로필(여러 모델) 구성 (2026-10-28)

- 워커 프로필: `env.<이름>` + `worker.<이름>.md`. `claude-worker -P x`, `claude-duo -P x`, `llm-probe -P x`, `install.sh --profile x`.
  프로필은 COMPUTE_* 를 기본 env 에서 물려받는다.
- 처음엔 두 번째 모델로 Qwen3.8-27B(:8081, 프로필 `27b`)를 가정했으나 **사용자 결정으로 폐기**(2026-10-28 저녁).
  대신 LLM 서버에 LiteLLM 게이트웨이를 두고 GB10 노드를 그 뒤에 붙인다 → 4f.

## 4e. 직접 연결 재검증 (2026-10-28, 서버 `--host 0.0.0.0` 전환 후)

- 서버 인자(호스트 `ps`): `--ctx-size 131072 --parallel 4 --no-kv-unified --cache-prompt --cache-ram 40960 --jinja`, Vulkan0+Vulkan1 layer split, 빌드 b11946.
  `/props`·`/slots`: 슬롯 4개, **슬롯당 n_ctx 32768**. 39,796 토큰 요청 → 즉시 400 `exceed_context_size_error` 확인.
  → `LAB_DEFAULT_CTX`/`LAB_27B_CTX`/env 예시/README 를 32768 로 정정. (27b 서버는 뜨면 같은 방식으로 확인.)
- 실측 속도(16.9k 토큰 프롬프트): 프롬프트 처리 352 tok/s, 생성 16.7 tok/s. `claude-worker -p` 한 번짜리 Bash 왕복 3분 19초.
- `llm-probe http://1.233.219.134:8080 qwen3.6-35b-a3b none` 8/8 OK. 8081 은 아직 닫힘(연결 거부).
- 사용자 계정은 docker 그룹이 아니라 `docker ps` 불가. 서버 인자는 `ps -eo args | grep llama-server` 로 본다.

## 4f. LiteLLM 게이트웨이 + GB10 (2026-10-28, 사용자 결정)

- 구성원 접속점 = `http://1.233.219.134:4000` (LiteLLM). 백엔드 1 = 같은 호스트 llama.cpp `127.0.0.1:8080` (`qwen3.6-35b-a3b`),
  백엔드 2 = GB10 노드(모델·주소 미정). `proxy/` 를 관리자용 서버측 설정으로 재작성 (docker compose `network_mode: host`, 또는 pip).
- 키트 기본값: `LAB_DEFAULT_PORT=4000`, 모델 `qwen3.6-35b-a3b`, 컨텍스트 32768. `LAB_GB10_MODEL`/`LAB_GB10_CTX` 는 등록 후 채움(프로필 `gb10`).
  템플릿(ORCHESTRATOR/AGENTS/KICKOFF)은 `@llm-worker` 기본 + `@llm-worker-gb10`(있을 때) 로 일반화.
- 임시 우회: LiteLLM 장애 시 `LLM_BASE_URL=…:8080`, `LLM_API_KEY=none` 으로 llama.cpp 직접 접속 (TROUBLESHOOTING).
- 검증(2026-10-28~29, 내 PC 에 LiteLLM 1.x venv 로 띄워 연구실 llama.cpp 에 연결, master_key 사용):
  `anthropic/` 패스스루와 `openai/` 변환 둘 다 `llm-probe` 8/8. 패스스루는 thinking 블록·cache_read_input_tokens 보존,
  변환 경로는 사고를 버리고 본문만 전달(본문에 `<think>` 누출 없음). `claude-worker -p` Bash 왕복: 변환 2분 47초, 패스스루도 OK.
  → `proxy/litellm.config.yaml` 기본은 `anthropic/`. LLM 서버는 Python 3.8 이라 pip 설치 불가 → docker compose(network_mode: host).

## 4g. 게이트웨이 부하 시험 (2026-10-29)

- LiteLLM `/model/info`: `qwen3.6-35b-a3b` 에 배포 2개 — `127.0.0.1:18000`(docker 안 `ssh -N` 터널 → GB10 1.233.218.218) 과 `127.0.0.1:8080`(LLM 서버 Vega llama.cpp).
  `-oai` 도 같은 두 백엔드(hosted_vllm/, openai/). `/health` 4개 모두 healthy.
- 동시 20개(2k 프롬프트, 300 생성): 전부 성공, 지연 11.5/12.9/17.1초(min/median/max), 16개가 먼저 끝나고 4개가 뒤에 → GB10 엔진 동시 슬롯 16개로 추정.
  동시 20개(thinking off, 120 생성): 전부 성공·정답 20/20, 지연 3.1/4.6/5.1초. 동시 40개(200 생성): 전부 성공·정답 40/40, 지연 4.0/17.8/25.4초, 합계 약 270~330 tok/s.
- 세 번 모두 LLM 서버 llama.cpp 의 `prompt_tokens_total` 변화 0, 슬롯 점유 0 → **Vega 배포는 트래픽을 전혀 받지 않는다**(GB10 이 꽉 차도 대기열로 처리).
- 재시험(같은 날, llama.cpp `--parallel 16` 으로 재기동 후): 20/20/40 전부 성공·정답, 지연 중앙값 13.0/9.6/18.9초, 역시 Vega 0건.
  순차 단건 12+10+10건도 Vega 0건. `/router/settings`: `simple-shuffle`, `allowed_fails 3`, `cooldown_time 5`, `enable_pre_call_checks true`.
  **원인 = `litellm_params.order`**: GB10 배포 `order: 1`, Vega `order: 2`. LiteLLM 은 order 가 낮은 배포가 건강하면 그것만 쓰고
  실패·쿨다운 때만 다음 order 로 넘어간다. 즉 Vega 는 의도된 **대기(fallback) 노드**이고, 40 동시 요청까지는 GB10 혼자 처리한다.
  LiteLLM 의 `/health` 는 Vega 에 실제 요청을 보낸다(llama.cpp 카운터 +16) → 장애 전환 경로는 살아 있음. 실제 전환은 관리자가 GB10 터널을 잠시 내려 확인하면 된다.

## 4h. 라우팅 변경 후 (2026-10-29, `order` 제거 → weight 1:1 simple-shuffle)

- 같은 요청 14회 순차: GB10 6건 / Vega 8건으로 분산 확인. 응답 시간 GB10 0.8초, Vega 4초(프롬프트 캐시 적중 상태).
- 출력 동일성(temperature 0, thinking 끔, max_tokens 200): GB10 은 6건 중 5가지 문구(내용은 같고 표현만 다름) → **temperature 0 이어도 결정적이지 않다**.
  Vega 는 8건 모두 본문이 비어 있었다 → 그 llama.cpp 빌드는 `thinking: disabled` 를 무시하고 사고를 출력해 200 토큰을 다 쓴 것(직접 접속 때의 프로브 2) 과 같은 현상).
  Claude Code 는 사고를 켠 채 큰 max_tokens 로 요청하므로 영향 없음. 사용자 요청으로 지속 부하·추가 조사는 여기서 중단하고 배포 상태로 커밋.

## 4i. 워커의 "복잡한 코드 작성" 약점 보완 (2026-10-29 오후, 사용자: 모델 교체 빼고 전부 반영)

반영한 것 (templates/project, bin, install.sh, bench):
1. **분업 규칙** — ORCHESTRATOR.md/AGENTS.md/KICKOFF: 설계·스켈레톤·테스트는 Claude 가 직접 쓰고 워커는 채우기만. 읽을 파일 목록 명시, 태스크 ≤ 20k 토큰.
   구현 태스크 양식 `agents/tasks/T_impl_template.md`. ROLE_IMPLEMENTER 는 "지정 파일만, 테스트 수정 금지, 세 번 막히면 보고".
2. **편집 후 자동 검사 훅** `agents/hooks/post-edit-check.sh` (PostToolUse Edit|Write|MultiEdit; 문법→lint→pytest -x; 실패 시 exit 2 로 모델에 되돌림;
   `check.conf` 로 명령·시간 제한 조절; `last-check.log`). `.claude/settings.json` 과 함께 `bin/project-init` 이 프로젝트에 넣는다(기존 파일 보존).
3. **브랜치 격리 + diff 검토** — 태스크마다 `task/<T>`, 오케스트레이터는 diff 를 읽고 테스트를 직접 돌린다. `tests/` 변경은 반려.
4. **승격 규칙** — 같은 태스크 2회 실패 → Claude 가 직접 구현, CAMPAIGN_LOG 에 기록.
5. **구현 전용 프로필 `impl`** — 같은 모델, `WORKER_ROLE=impl` → `prompts/role-impl.md.tmpl` 이 시스템 프롬프트에 붙음. 설치 때 기본 생성(Y/n), `claude-duo -P impl`.
   사고 예산은 조절 불가로 판명(아래) → 프로필은 이름·프롬프트만 다르다.
6. **벤치마크 `bench/`** — 기본 6 + 어려움 4 태스크, 숨은 테스트 채점, `bench/run.sh -P impl [--tier hard] [--no-hooks]`. 기준 해답으로 숨은 테스트 전부 검증함.

사고(thinking) 조절 실측 (Claude Code 2.1.312, 가짜 서버로 요청 본문 캡처 + 게이트웨이 응답 비교):
- Claude Code 는 모든 요청에 `thinking:{type:adaptive}`, `output_config.effort:high` 를 보낸다. `MAX_THINKING_TOKENS` 는 무시(0 이면 thinking 필드만 빠짐).
  `CLAUDE_CODE_EFFORT_LEVEL=low|medium` 또는 `--settings '{"effortLevel":"low"}'` 로 effort 는 바뀌지만 **백엔드가 effort 를 무시**(출력 토큰 차이 없음).
- 백엔드는 `thinking.budget_tokens` 는 지킨다(256 → 출력 261 토큰). `disabled` 는 GB10 만 지키고 Vega 는 무시. 그러나 Claude Code 가 예산을 보내지 않는다.
- LiteLLM `litellm_params.thinking` 주입(로컬 LiteLLM 1.106.6 으로 시험)도 요청의 adaptive 에 밀려 효과 없음.
- 결론: 과도한 사고 제한은 엔진 쪽(llama.cpp `--reasoning-budget`, vLLM reasoning 옵션)에서만 가능 → 관리자 항목(README 7절, proxy/README).
- "ultracode"(Workflow 다중 에이전트)는 Claude Code 클라이언트 기능이라 워커 세션에서도 호출은 되지만 Qwen 이 Qwen 서브에이전트를 지휘하는 꼴이 되어 약점을 배가함.
  킷의 대응물은 Claude 가 워커 N 개를 지휘하는 `claude-duo -w N`. 워커에 켜지 않음.

벤치마크 결과 (2026-10-29, `bench/results/2026-10-29_impl-all.md`, 프로필 impl, 훅 켬, 게이트웨이 1:1 라우팅):

| 태스크 | 결과 | 숨은 테스트 | 턴 | 시간 | 놓친 것 |
|---|---|---|---|---|---|
| B1_bugfix | FAIL | 7/8 | 7 | 66s | docstring 의 "빈 입력 → ValueError" 를 구현 안 함 |
| B2_signature | PASS | 15/15 | 8 | 132s | |
| B3_cli_flag | PASS | 5/5 | 5 | 109s | |
| B4_refactor | PASS | 6/6 | 9 | 125s | |
| B5_module_spec (스켈레톤 없음) | PASS | 11/11 | 4 | 100s | |
| B6_module_skeleton | PASS | 11/11 | 5 | 128s | |
| H1_expr_parser | FAIL | 12/20 | 시간 초과 | 1200s | 우결합·오류 위치·함수 호출 — 20분 안에 못 끝냄 |
| H2_scheduler | FAIL | 10/12 | 11 | 225s | 의존성 준비 여부를 무시하고 배정(공개 테스트로는 안 잡힘) |
| H3_json_patch | FAIL | 18/19 | 11 | 214s | 스칼라를 지나는 add 를 오류 대신 무시 |
| H4_multifile_txn | FAIL | 8/9 | 14 | 186s | 원자성·종료 코드는 맞췄으나 stderr 에 오류 메시지를 안 씀 |

읽기: 기본 태스크(한 모듈, 명세 명확)는 5/6 통과, LRU 캐시는 스켈레톤 없이도 통과 → "전체 코드 작성" 자체가 못 하는 일은 아니다.
어려운 태스크는 0/4 지만 H2~H4 는 숨은 테스트 1~2개 차이의 근접 실패이고, 놓친 것은 전부 **명세의 구석 조항**(오류 조건·stderr·준비 여부)이다 →
Claude 가 테스트를 촘촘히 써 주면(분업 규칙 1) 잡히는 유형. H1(파서)은 진짜 설계 문제라 승격 규칙 대상.
실행 비용: 태스크당 2~4분, 턴 4~14. 워커가 테스트 파일을 고친 경우는 없었다.

## 5. 미결 사항 (사용자 확인 필요)

- 새 LLM 서버: 1.233.219.134:8080, llama.cpp `server-vulkan` docker, 모델 `Qwen3.6-35B-A3B-UD-Q4_K_M` (별칭 `qwen3.6-35b-a3b`),
  `--ctx-size 131072 --parallel 4 --no-kv-unified`(슬롯당 32768), Vulkan0+Vulkan1 layer split. 2026-10-28 오후부터 **0.0.0.0:8080** 으로 열려
  외부에서 바로 붙는다 (터널 불필요; 터널 안내는 TROUBLESHOOTING 에 일반 사례로 남김).
  관리자에게 제안할 것: `--kv-unified` 로 바꾸면 한 요청이 131072 전체를 쓸 수 있어 Claude Code 의 긴 작업에 유리하다(동시 요청은 풀을 나눠 씀).
  (같은 호스트의 기존 Ollama 0.34.2 는 쓰지 않는다. 참고: 그 Ollama 는 Vulkan 백엔드 + AMD Vega 2장 분할 상태에서 30B 이상 모델 출력이 깨졌다.)
- (해결 2026-10-29) LiteLLM 이 LLM 서버 docker 로 가동. 포트 4000, **키 없음**(처음 master_key 가 걸려 있다가 제거됨).
  등록 모델: `qwen3.6-35b-a3b`(패스스루) → `llm-probe` 8/8. `qwen3.6-35b-a3b-oai`(변환) → 프로브 4) tool_use FAIL
  (사고 토큰이 max_tokens 256 을 소진) → 문서에서 "고르지 말 것". LiteLLM 이 광고하는 `max_input_tokens: 131072` 는 llama.cpp 슬롯당 32768 과 불일치 →
  (아래 정정) 2026-10-29 재측정: 게이트웨이의 `qwen3.6-35b-a3b` 는 5.5k 토큰 1.2초, 39.8k 토큰 7.2초(≈5,500 tok/s), 생성 ≈93 tok/s, 39.8k 요청 수용 →
  Vega llama.cpp(352 tok/s, 32k 거절)가 아닌 **다른 백엔드(GB10 으로 추정, ssh 미연결로 미확인)**. `max_input_tokens: 131072` 가 맞는 값.
  `LLM_CONTEXT_WINDOW=32768` 로 워커를 돌리니 "Autocompact is thrashing" 발생, 131072 로 올리니 Bash 왕복 2.9초 정상.
  → install.sh 가 `/v1/models` 의 `max_input_tokens` 를 읽어 기본값으로 쓰도록 변경. llm-probe 도 모델 옆에 컨텍스트 표시.
- 2026-10-29 서버 패치(사용자): llama.cpp 를 `--kv-unified --flash-attn` 으로 재기동 → 슬롯당 n_ctx 131072. LiteLLM 도 재기동.
  같은 5.5k 요청: :8080 직접 29.3초(llama.cpp prompt_tokens_total +5522), :4000 게이트웨이 1.1초(카운터 +0) → 게이트웨이의
  `qwen3.6-35b-a3b` 는 LLM 서버 llama.cpp 가 아닌 다른 백엔드가 응답 → 4g 에서 GB10(ssh 터널 :18000) 으로 확인. 키트 폴백 기본값 LAB_DEFAULT_CTX=131072 로 통일.
- GB10 노드: 엔진(llama.cpp CUDA arm64 / SGLang / vLLM), 모델 id, 요청당 컨텍스트 → `proxy/litellm.config.yaml` 의 gb10 항목과 `install.sh` 의 LAB_GB10_* 채움.
- 연구실 구성원이 쓰는 원격 계산 노드 규약(계정, 작업 디렉터리). 기본값 `~/claude-work/<project>`.
