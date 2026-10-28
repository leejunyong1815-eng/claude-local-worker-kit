# proxy/ — LiteLLM 변환 프록시 (필요할 때만)

`llm-probe` 가 2)·3)·4) 항목에서 FAIL 이고 9) OpenAI 형식은 동작한다고 하면 이 프록시를 쓴다.
vLLM / SGLang / llama.cpp / Ollama(≥0.14) 최신판은 `/v1/messages` 를 자체 지원하므로 보통 필요 없다.

```bash
cd proxy
cp .env.example .env && nano .env          # UPSTREAM_* 와 PROXY_MASTER_KEY 채움
docker compose up -d
curl -s localhost:4000/health/liveliness
```

그다음 `~/.config/claude-worker/env` 에서

```
LLM_BASE_URL="http://localhost:4000"
LLM_API_KEY="<PROXY_MASTER_KEY 값>"
LLM_MODEL="<UPSTREAM_MODEL 값>"
```

로 바꾸고 `llm-probe` 를 다시 돌린다.

프록시를 연구실 공용으로 한 대에 띄우면 각자 `LLM_BASE_URL` 만 그 주소로 두면 된다.
docker 없이 쓰려면 `pip install 'litellm[proxy]'` 후
`litellm --config litellm.config.yaml --port 4000` (같은 환경변수를 export 해 둔다).
