# 기존 개인 구성에서 옮기기 (ljy 환경 기준)

| 기존 | 새 키트 | 비고 |
|---|---|---|
| `~/bin/claude-main` | `claude-main` | 동일. `--remote-control` 은 필요할 때 인자로 (`claude-main --remote-control`) |
| `~/bin/claude-glm` | `claude-worker` | 서버·모델·토큰이 `~/.config/claude-worker/env` 로 이동 |
| `~/.config/glm/env` (`GLM_TOKEN`) | `LLM_API_KEY` | |
| `~/.claude/prompts/glm-worker.md` | `~/.config/claude-worker/worker.md` | 템플릿에서 생성. DRL 하드코딩 → `COMPUTE_HOST/COMPUTE_DESC` |
| `drl-info/sync/run/submit/fetch` | `remote-info/sync/run/submit/fetch` | 호스트 `DRL`, 경로 `/home/jyl/claude-work` → env 의 `COMPUTE_HOST`, `COMPUTE_WORK_DIR` |
| `Ask @glm-worker to …` | `Ask @llm-worker to …` | `WORKER_NAME` 으로 바꿀 수 있다. 기존 이름을 유지하려면 `WORKER_NAME=glm-worker` |
| `agents/SUBAGENT_*_GLM.md` | `agents/ROLE_*.md` | 프로젝트 파일. 내용은 그대로 두고 참조 경로만 바꾸면 된다 |

연구실 LLM 서버(1.233.219.134, llama.cpp) 값으로 설치하려면:

```bash
LLM_BASE_URL=http://1.233.219.134:4000 LLM_API_KEY=none LLM_MODEL=qwen3.8-flash-next \
WORKER_NAME=glm-worker COMPUTE_HOST=DRL COMPUTE_DESC="RTX A6000 48GB x2, 503G RAM" \
  ./install.sh --non-interactive
```

(`WORKER_NAME=glm-worker` 는 기존 프로젝트 문서의 `Ask @glm-worker` 를 그대로 쓰기 위한 것이다. 새 프로젝트면 생략한다.)
서버나 모델을 바꿀 때는 `~/.config/claude-worker/env`의 `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`과
`LLM_CONTEXT_WINDOW`를 확인한 뒤 `./install.sh --render && llm-probe`로 프롬프트 재생성과 연결 확인을 한다.
`--render`는 컨텍스트 크기를 자동 조회하지 않는다. API 키가 있는 설정 파일 전체를 보고서·대화에 붙여 넣지 않는다.

코드 수정 위임은 [관리 모드](MANAGED_TASKS.md)를 사용할 수 있다. 기존 프로필과 대화형 메시징은 그대로 유지되며,
관리 태스크는 기록된 기준 커밋에서 새 worktree로 실행한다. 원본의 미커밋 변경은 자동으로 전달되지 않는다.

기존 `~/bin/claude-glm`, `~/bin/drl-*` 는 지우지 않아도 충돌하지 않는다(이름이 다르다).
