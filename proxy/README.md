# proxy/ — LLM 서버의 LiteLLM 게이트웨이 (관리자용)

구성원 PC 의 `claude-worker` 는 `http://1.233.219.134:4000` 하나만 바라본다. LiteLLM 이 모델 이름을 보고 백엔드로 넘긴다.
2026-10-29 현재 모델 이름은 `qwen3.8-flash-next`(GB10 우선) 와 `qwen3.6-35b-a3b`(같은 호스트 llama.cpp 우선) 둘이고, 각 이름은 다른 쪽 백엔드를 `order: 2` 대체로 가진다
(`-oai` 접미사는 OpenAI 형식 변환 경로). 구성원은 게이트웨이만 쓴다. 백엔드가 Anthropic `/v1/messages` 를 지원하면
(`anthropic/` 항목) 그대로 넘겨 사고 블록과 프롬프트 캐시가 보존되고, 아니면 (`openai/` 항목) OpenAI 형식으로 변환한다.
두 경로 모두 2026-10-28 에 `llm-probe` 8/8 과 `claude-worker` 도구 호출 왕복으로 확인했다.

```
구성원 ──▶ LiteLLM :4000 ─┬─▶ ssh -N 터널 127.0.0.1:18000 ──▶ GB10 노드 1.233.218.218 (ctx 262144)   ← qwen3.8-flash-next 우선
                          └─▶ llama.cpp 127.0.0.1:8080 (AMD Vega 2장, ctx 131072)                   ← qwen3.6-35b-a3b 우선
```

## 띄우기 (LLM 서버에서)

docker:

```bash
git clone https://github.com/leejunyong1815-eng/claude-local-worker-kit.git && cd claude-local-worker-kit/proxy
cp .env.example .env && nano .env            # PROXY_MASTER_KEY 정하기 (GB10_* 는 나중에)
docker compose up -d                          # network_mode: host → 호스트 :4000
curl -s localhost:4000/health/liveliness
curl -s localhost:4000/v1/models -H "Authorization: Bearer $(grep PROXY_MASTER_KEY .env | cut -d= -f2 | cut -d' ' -f1)"
```

docker 없이 (pip, Python ≥ 3.9 필요 — 연구실 LLM 서버는 시스템 python 이 3.8 이라 **docker 로 띄운다**):

```bash
python3 -m venv ~/litellm && ~/litellm/bin/pip install 'litellm[proxy]'
set -a; source .env; set +a
~/litellm/bin/litellm --config litellm.config.yaml --host 0.0.0.0 --port 4000
```

(계속 띄워 두려면 tmux 나 systemd 유닛으로. 방화벽은 4000 만 열면 되고 8080 은 닫아도 된다. 다만 8080 을 열어 두면
LiteLLM 장애 때 구성원이 직접 붙을 수 있다 — 키트의 TROUBLESHOOTING 이 그 우회를 안내한다.)

## 모델 추가·교체 (예: GLM-5.3-Flash)

1. GB10 에서 새 모델을 띄운다(아래 엔진 조건). 2. `litellm.config.yaml` 에 `model_name` 항목을 추가하고 `max_input_tokens` 를 엔진의 요청당 컨텍스트로 맞춘다. `docker compose restart`.
3. 구성원 PC 에서 `llm-probe http://1.233.219.134:4000 <새 이름> none` 이 8/8 이면 된다. 구성원은 env 의 `LLM_MODEL` 을 바꾸거나 `install.sh --profile <이름>` 으로 두 번째 워커를 만든다.
4. 기본 모델을 바꿀 때는 키트 `install.sh` 상단 `LAB_DEFAULT_MODEL`/`LAB_DEFAULT_CTX` 와 README 의 설치 표·속도 표를 고쳐 커밋한다. 옛 이름을 지우면 그 이름으로 설치한 구성원은 400 "model not found" 를 본다(TROUBLESHOOTING 참고).

## GB10 노드 엔진 조건

- 엔진(llama.cpp CUDA arm64 / SGLang / vLLM)이 Anthropic `/v1/messages` 를 지원하면 `anthropic/` 항목으로 그대로 넘긴다(사고 블록·프롬프트 캐시 보존, 권장).
  OpenAI 형식만 있으면 `hosted_vllm/` 또는 `openai/` 항목으로 변환해 넘긴다(`api_base` 에 `/v1` 까지). tool calling 이 켜져 있어야 한다(vLLM: `--enable-auto-tool-choice --tool-call-parser <모델용>`).
- `.env` 의 `GB10_BASE_URL`(컨테이너 안에서 닿는 주소; 2026-10-29 운영은 ssh -N 터널 `http://127.0.0.1:18000`), `GB10_MODEL`(엔진이 아는 id), `GB10_API_KEY`.
- `model_info.max_input_tokens` 는 엔진의 요청당 컨텍스트. 구성원 설치기가 `/v1/models` 에서 이 값을 읽어 `LLM_CONTEXT_WINDOW` 로 쓴다. 틀리면 구성원 쪽에서 400 또는 자동 압축 반복이 난다.
- 과도한 사고가 문제면 엔진에서 제한한다(아래 "사고 토큰 상한"). 2026-10-29 의 `qwen3.8-flash-next` 는 사고가 짧아(간단한 질문 100 토큰 안팎) 제한이 필요 없었다.

## 검증

구성원 PC 에서:

```bash
llm-probe http://1.233.219.134:4000 qwen3.8-flash-next none   # 8/8 OK 여야 한다 (2026-10-29 확인: 패스스루·-oai 둘 다 8/8)
llm-probe --models                                           # 등록된 모델 이름 목록
```

## 다른 용도: Anthropic API 가 없는 서버 앞에 개인용으로

`llm-probe` 가 2)~4) 에서 FAIL 이고 9) "OpenAI 형식은 동작" 이면 같은 설정을 자기 PC 에 띄우고 `model_list` 의 `api_base` 를 그 서버로 바꾼 뒤
env 의 `LLM_BASE_URL="http://localhost:4000"` 으로 쓴다. vLLM / SGLang / llama.cpp / Ollama(≥0.14) 최신판은 `/v1/messages` 를 자체 지원하므로 보통 필요 없다.

## 사고 토큰 상한 (선택, 관리자)

워커 모델이 매 턴 길게 사고해 느리면 **엔진**에서 제한한다. 클라이언트(Claude Code 2.1.312) 는 `thinking: adaptive` 만 보내고 예산 필드를 보내지 않으며,
이 파일의 `litellm_params` 에 `thinking: {"type":"enabled","budget_tokens":N}` 을 넣어도 요청의 adaptive 가 이긴다(2026-10-29 로컬 LiteLLM 1.106.6 으로 확인).
`output_config.effort` 도 백엔드가 무시한다. llama.cpp 는 서버 인자 `--reasoning-budget N`(토큰), vLLM/SGLang 은 reasoning 관련 옵션을 쓴다.
코딩 태스크 기준 2k~8k 토큰이 보통 충분하다.
