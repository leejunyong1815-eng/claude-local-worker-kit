# 첫 실행 시운전 (10분)

설치 직후 모든 조각이 맞물리는지 빈 디렉터리에서 한 번 확인한다. 각 단계에서 무엇이 보여야 하는지 적어 두었다.

## 0. 준비 확인

```bash
claude --version          # 2.1.224 이상
llm-probe                 # 마지막 줄: 판정: 직접 연결 가능
mkdir -p ~/kit-test && cd ~/kit-test && echo hello > a.txt
```

## 1. 두 세션 띄우기

```bash
claude-duo
```

- 왼쪽 창: Claude Code 로고 아래 모델이 Claude 계열(Fable/Opus 등)로 표시된다. 로그인이 안 되어 있으면 로그인 절차가 뜬다.
- 오른쪽 창: 모델이 설정한 로컬 모델 id 로 표시된다. 그 아래 "Model … isn't recognized · context assumed to be 200k" 경고가 있을 수 있다. 정상이다.
- 두 창 모두 "Do you trust the files in this folder?" 를 물으면 Yes.

워커 창에 로컬 모델이 아니라 Claude 모델이 보이면 설정 파일을 못 읽은 것이다. `cat ~/.config/claude-worker/env` 확인.

## 2. 연결 확인

왼쪽(오케스트레이터) 창에서:

```
/peers
```

목록에 `llm-worker` 가 보여야 한다. 안 보이면 오른쪽 창이 아직 뜨는 중이거나, 두 세션이 다른 사용자 계정으로 떠 있다.

## 3. 첫 위임

왼쪽 창에서:

```
Ask @llm-worker to: In the current directory, run `wc -c a.txt` with the Bash tool and reply with the exact output.
```

- 오른쪽 창에 메시지가 도착하고 워커가 Bash 실행 허가를 묻는다. 허락한다.
- 몇 초 뒤 왼쪽 창에 워커의 답(`6 a.txt` 같은 내용)이 나타난다.

여기까지 되면 구성은 끝났다.

## 4. 실제 작업 모양

실제 프로젝트에서는 지시가 길어진다. 아래 모양을 기준으로 삼는다.

```
Ask @llm-worker to: First read /home/me/proj/agents/ROLE_RUNNER.md and act as RUNNER.
Task file: /home/me/proj/agents/tasks/T1_baseline.md.
In /home/me/proj run `remote-run "bash scripts/setup_env.sh && python train.py --config configs/small.yaml --tag smoke"`.
Save results under results/t1_smoke/ and write results/t1_smoke/REPORT.md in the format of agents/HANDOFF_TEMPLATE.md.
Acceptance: training finishes without error, final loss < 1.0, GPU model and commit hash recorded. Budget 30 min.
If it fails, halve the batch size once and retry, then report what happened.
```

경로는 절대 경로로, 성공 조건은 숫자로, 실패 시 행동까지 적는다. 오케스트레이터에게 이 양식을 지키게 하려면
`templates/project/` 를 프로젝트에 복사하고 `KICKOFF_PROMPT.md` 를 붙여 넣는다.

## 5. 끝내기

```bash
claude-duo --kill
rm -rf ~/kit-test
```

## 자주 겪는 첫 실행 문제

| 증상 | 원인·조치 |
|---|---|
| 워커 창이 Claude 모델로 뜬다 | 설정 파일 없음 또는 `LLM_API_KEY` 비어 있음 |
| 워커가 401 / Invalid API key | 토큰 틀림. 인증 없는 서버라도 빈 값은 안 됨 |
| `/peers` 에 워커가 없다 | 다른 사용자 계정·다른 머신에서 띄움, 또는 아직 시작 중 |
| Ask 를 보냈는데 워커가 조용하다 | 워커 창에서 권한 질문에 멈춰 있음. 허락하거나 `/permissions` 조정 |
| 워커가 400 오류로 멈춘다 | 서버가 모르는 요청 필드. `docs/TROUBLESHOOTING.md` 의 400 항목 |
