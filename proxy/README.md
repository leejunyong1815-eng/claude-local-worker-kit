# proxy/ — LLM 서버의 LiteLLM 게이트웨이 (관리자용)

구성원 PC 의 `claude-worker` 는 `http://1.233.219.134:4000` 하나만 바라본다. LiteLLM 이 모델 이름을 보고
같은 호스트의 llama.cpp(`qwen3.6-35b-a3b`)나 GB10 노드로 넘긴다. 백엔드가 Anthropic `/v1/messages` 를 지원하면
(`anthropic/` 항목) 그대로 넘겨 사고 블록과 프롬프트 캐시가 보존되고, 아니면 (`openai/` 항목) OpenAI 형식으로 변환한다.
두 경로 모두 2026-10-28 에 `llm-probe` 8/8 과 `claude-worker` 도구 호출 왕복으로 확인했다.

```
구성원 ──▶ LiteLLM :4000 ─┬─▶ llama.cpp 127.0.0.1:8080  (qwen3.6-35b-a3b)
                          └─▶ GB10 노드 http://<gb10>:<port>/v1  (등록 후)
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

## GB10 노드 추가

1. GB10 에서 엔진을 띄운다 (aarch64 CUDA 이미지: llama.cpp `ghcr.io/ggml-org/llama.cpp:server-cuda` arm64, 또는 NVIDIA 의 Spark 용 SGLang/vLLM).
   OpenAI 호환 `/v1/chat/completions` 와 tool calling 이 켜져 있어야 한다 (vLLM: `--enable-auto-tool-choice --tool-call-parser <모델용>`).
2. `.env` 의 `GB10_BASE_URL`(`anthropic/` 면 `/v1` 없이, `openai/` 면 `/v1` 까지), `GB10_MODEL`(엔진이 아는 id), `GB10_API_KEY` 를 채운다.
3. `litellm.config.yaml` 의 `gb10` 항목 주석을 풀고 `max_input_tokens` 를 그 엔진의 요청당 컨텍스트로 맞춘다. `docker compose restart`.
4. 구성원 PC 에서 `llm-probe http://1.233.219.134:4000 gb10 <키>` 가 8/8 이면 끝. 키트 `install.sh` 상단 `LAB_GB10_MODEL="gb10"`, `LAB_GB10_CTX` 를 채워 커밋하면
   설치기가 `gb10` 프로필을 기본으로 제안한다.

## 검증

구성원 PC 에서:

```bash
llm-probe http://1.233.219.134:4000 qwen3.6-35b-a3b <키>     # 8/8 OK 여야 한다
llm-probe --models                                           # 등록된 모델 이름 목록
```

## 다른 용도: Anthropic API 가 없는 서버 앞에 개인용으로

`llm-probe` 가 2)~4) 에서 FAIL 이고 9) "OpenAI 형식은 동작" 이면 같은 설정을 자기 PC 에 띄우고 `model_list` 의 `api_base` 를 그 서버로 바꾼 뒤
env 의 `LLM_BASE_URL="http://localhost:4000"` 으로 쓴다. vLLM / SGLang / llama.cpp / Ollama(≥0.14) 최신판은 `/v1/messages` 를 자체 지원하므로 보통 필요 없다.
