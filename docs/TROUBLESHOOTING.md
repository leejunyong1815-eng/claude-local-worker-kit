# 문제 해결

증상별로 본다. 먼저 `llm-probe` 를 돌려 어느 항목이 FAIL 인지 확인한다.

## 설치·실행

**`claude-worker: 설정 파일이 없습니다`** — `install.sh` 를 안 돌렸다. 또는 `CLAUDE_WORKER_CONF_DIR` 가 다른 곳을 가리킨다.

**`command not found: claude-worker`** — `~/.local/bin` 이 PATH 에 없다. `~/.bashrc` 에
`export PATH="$HOME/.local/bin:$PATH"` 추가 후 새 셸.

**`LLM_BASE_URL 끝의 /v1 을 떼세요`** — Claude Code 가 `/v1/messages` 를 스스로 붙인다. `http://host:8000` 까지만.

**워커가 "Invalid API key" / 401** — 서버가 인증을 하면 `LLM_API_KEY` 를 맞춘다. 인증을 안 하는 서버라도 빈 값은 안 된다(`none` 등 아무 문자열).

**워커가 claude.ai 에 로그인하라고 한다** — `ANTHROPIC_AUTH_TOKEN` 이 비었다. env 파일의 `LLM_API_KEY` 확인.

**오케스트레이터가 로컬 모델로 뜬다** — 셸에 `ANTHROPIC_BASE_URL` 등이 export 되어 있다. `claude-main` 은 이를 지우고 실행하지만,
`claude` 를 직접 띄우면 영향을 받는다. `.bashrc` 에서 `ANTHROPIC_*` export 를 제거한다.

## 서버 호환성 (`llm-probe` 항목별)

| 항목 | FAIL 의미 | 조치 |
|---|---|---|
| 1) /v1/models 연결 실패 | 주소·포트·방화벽 | 서버에서 `curl localhost:PORT/v1/models`. 127.0.0.1 에만 바인딩됐으면 `ssh -L 8000:localhost:8000 host` 터널 후 `LLM_BASE_URL=http://localhost:8000` |
| 2) /v1/messages | 서버가 Anthropic API 미지원 | vLLM/SGLang/llama.cpp/Ollama 를 최신으로 올리거나 `proxy/` 사용 |
| 3) 스트리밍 | SSE 미지원 또는 중간 프록시가 버퍼링 | nginx 등 앞단이 있으면 `proxy_buffering off`. 아니면 `proxy/` |
| 4) tool_use | 모델 또는 서버가 함수 호출 미지원 | **필수.** 도구 호출 되는 모델(Qwen3-Coder, GLM-4.x/5.x, DeepSeek-V3 계열 등)과 서버 옵션(vLLM: `--enable-auto-tool-choice --tool-call-parser <모델에 맞는 파서>`) |
| 5) tool_result 왕복 | 멀티턴 변환 버그 | 서버 업그레이드 또는 `proxy/` |
| 6) cache_control (WARN) | 서버가 필드 거부 | env `LLM_DISABLE_PROMPT_CACHING=1` |
| 7) thinking (WARN) | 서버가 필드 거부 | env `LLM_MAX_THINKING_TOKENS=0` |
| 8) count_tokens (WARN) | 선택 기능 | 무시해도 됨 (`/context` 가 추정치 사용) |

일시적 오류("rate limit", "limit exceeded", 5xx)는 프로브가 5초 뒤 한 번 재시도한다. 계속 나오면 서버 쪽 한도·과부하다.

**Claude Code 가 400 을 내며 멈춘다** — 서버가 모르는 요청 필드. 순서대로 시도:
`LLM_DISABLE_BETAS=1`(기본) → `LLM_DISABLE_PROMPT_CACHING=1` → `LLM_MAX_THINKING_TOKENS=0`. 그래도 안 되면 `proxy/`
(LiteLLM 의 `drop_params: true` 가 모르는 필드를 버린다).

**vLLM 에서 새 Claude Code 버전이 거부된다 (role 오류)** — Claude Code 가 보내는 메시지 역할을 구버전 vLLM 이 모를 수 있다.
vLLM 을 올리거나 `proxy/` 로 우회.

**"doesn't recognize the model … assumes a context window of 200k"** — 경고일 뿐 동작은 한다. 실제 창이 다르면 env `LLM_CONTEXT_WINDOW=<토큰 수>`
(서버의 `--max-model-len`) 로 알려 준다. 그러면 Claude Code 가 그 경계에서 자동 압축한다.

**컨텍스트 길이 초과** — 로컬 모델의 컨텍스트가 짧으면 긴 작업에서 실패한다. 태스크를 더 잘게 나눠 보내고,
워커 세션을 자주 새로 시작한다(`/clear`). 서버의 `--max-model-len` 도 확인.

## 크로스 세션 메시징

**`Ask @llm-worker` 가 전달되지 않는다** —
- 두 세션이 **같은 머신, 같은 OS 사용자** 인가. 다른 사용자·다른 머신 간에는 안 된다(Remote Control 은 로컬 LLM 워커에 쓸 수 없다).
- 워커 세션이 떠 있는가. 오케스트레이터에서 `/peers` 로 보이는지 확인.
- 이름이 맞는가. env 의 `WORKER_NAME` 과 Ask 의 `@이름`.
- 워커가 `crossSessionInbound: accept` 로 떴는가 (`claude-worker` 가 자동으로 넣는다. `claude` 를 직접 띄우면 안 들어간다).

**워커가 답을 하지 않고 멈춘다** — 워커 창을 본다. 권한 질문에 멈춰 있을 수 있다. 워커 세션에서 `/permissions` 로 자주 쓰는 명령을 허용하거나,
프로젝트 `.claude/settings.local.json` 에 allow 규칙을 둔다.

## 원격 노드

**`remote: COMPUTE_HOST 가 비어 있습니다`** — env 에 ssh 별칭 지정 후 `install.sh --render`.

**ssh 가 비밀번호를 묻는다** — `remote-*` 는 `BatchMode=yes` 라 키 인증만 된다. `ssh-copy-id <alias>`.

**원격 경로가 이상하다** — `COMPUTE_WORK_DIR` 가 상대 경로면 원격 홈 기준(`~/claude-work/<프로젝트>`). 절대 경로도 된다.

**동기화에서 빠져야 할 큰 디렉터리** — 프로젝트 루트에 `.remoteignore` (rsync exclude 문법) 를 둔다. `.git`, `.venv`, `outputs/` 는 기본 제외.
