# 기존 GLM 구성에서 옮기기 (ljy 환경 기준)

| 기존 | 새 키트 | 비고 |
|---|---|---|
| `~/bin/claude-main` | `claude-main` | 동일. `--remote-control` 은 필요할 때 인자로 (`claude-main --remote-control`) |
| `~/bin/claude-glm` | `claude-worker` | 서버·모델·토큰이 `~/.config/claude-worker/env` 로 이동 |
| `~/.config/glm/env` (`GLM_TOKEN`) | `LLM_API_KEY` | |
| `~/.claude/prompts/glm-worker.md` | `~/.config/claude-worker/worker.md` | 템플릿에서 생성. DRL 하드코딩 → `COMPUTE_HOST/COMPUTE_DESC` |
| `drl-info/sync/run/submit/fetch` | `remote-info/sync/run/submit/fetch` | 호스트 `DRL`, 경로 `/home/jyl/claude-work` → env 의 `COMPUTE_HOST`, `COMPUTE_WORK_DIR` |
| `Ask @glm-worker to …` | `Ask @llm-worker to …` | `WORKER_NAME` 으로 바꿀 수 있다. 기존 이름을 유지하려면 `WORKER_NAME=glm-worker` |
| `agents/SUBAGENT_*_GLM.md` | `agents/ROLE_*.md` | 프로젝트 파일. 내용은 그대로 두고 참조 경로만 바꾸면 된다 |

현재 GLM 서버 값으로 그대로 설치하려면:

```bash
source ~/.config/glm/env
LLM_BASE_URL=http://133.186.146.224:8081 LLM_API_KEY="$GLM_TOKEN" LLM_MODEL=GLM-5.3-Flash \
WORKER_NAME=glm-worker COMPUTE_HOST=DRL COMPUTE_DESC="RTX A6000 48GB x2, 503G RAM" \
  ./install.sh --non-interactive
```

새 서버로 바꿀 때는 `~/.config/claude-worker/env` 의 `LLM_*` 세 줄만 고치고 `./install.sh --render && llm-probe`.

기존 `~/bin/claude-glm`, `~/bin/drl-*` 는 지우지 않아도 충돌하지 않는다(이름이 다르다).
