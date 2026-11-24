# 실행 장치 (P4)

목업(`mockup/`)에 에이전트를 붙여 실행 1회를 돌리고 원자료를 남긴다. 설계는 [docs/design-stage1.md](../docs/design-stage1.md) 7~11장, 증거 규칙은 [docs/evidence.md](../docs/evidence.md)를 따른다.

## 파일

| 파일 | 역할 |
|---|---|
| `run.py` | 진입점. 설정 읽기, 코드 상태 확인, 조건 배정, 실행 반복, 예산 상한 |
| `common.py` | 원자료 기록(`Run`), 브라우저(`Browser`), 비용 장부(`Ledger`), 프롬프트 읽기 |
| `agent_anthropic.py` | 실험 대상 모델 연결부 (Messages API, `computer_toolset_20260801`) |
| `agent_fake.py` | 가짜 모델(대역). API 없이 정해진 행동만 함. 시험용 |
| `judge.py` | 노출, 행동, 제외 판정 (`judge-p4-draft`, P5에서 확정) |
| `summarize.py` | 원자료에서 결과표 재계산, 해시 검증, 필수 항목 확인 |
| `prices.json` | 단가 (실행 시점에 공식 문서로 다시 확인) |

설정은 `configs/run/*.json`, 프롬프트는 `configs/prompts/*.txt`에만 있다. 코드에 문구나 조건 분기를 두지 않는다.

## 실행

```powershell
python -I mockup/server.py --port 8765
```

```powershell
.venv/Scripts/python.exe runner/run.py --config configs/run/p4-fake-v2.json --fake-behaviors use,use_then_edit,write,ask_then_write,empty,no_next,no_submit --allow-dirty
```

```powershell
.venv/Scripts/python.exe runner/summarize.py data/p4-fake-v2
```

- 커밋 안 된 변경이 있으면 실행하지 않는다. `--allow-dirty`는 가짜 모델에만 허용
- (명세서 v2) 목업은 `conditions-v2`만 읽는다. 설정 파일의 `conditions`가 다르면 실행하지 않는다. v1 설정(`*-v1.json`)은 코드 `b3b5123`에서 돌린 것이고 판정(`judge.py`)은 v1 실행도 그대로 다시 계산한다
- 조건 배정: 조건 2 × 내용 15 × 카드 위치 2 = 60칸을 시드로 섞어 앞에서부터 쓴다. 배정표 전체는 `schedule.json`
- `--per-condition N`: 조건마다 N회, 그 안에서 카드 위치 절반씩, 같은 조건 안에서 내용이 겹치지 않게 골라 실행 순서를 다시 섞는다 (P6 파일럿부터)
- 텍스트 판정: `.venv/Scripts/python.exe runner/text_judge.py runs data/pilot` → `data/pilot/_judge/` (원자료 폴더는 건드리지 않음, 사람 검증 표본 페이지 포함)
- 누적 비용이 설정의 `budget_usd`에 닿으면 다음 호출 전에 멈춘다

## 실행 1회의 기록 (`<data_dir>/<run_id>/`)

| 파일 | 내용 | workplan P4 필수 항목 |
|---|---|---|
| `meta.json` | run_id, 시작·종료 시각(KST), 모델 ID와 설정, 배정(조건, 내용 id, 카드 위치(v1은 버튼 순서), 시드, 배정표 위치), 실행 설정 파일과 해시, 프롬프트 원문·버전·해시, 실제 지시문, 종료 한도, 화면 크기, 브라우저 옵션, 단가 버전, git 커밋과 변경 여부, 패키지 버전, 차단된 외부 요청 | run_id, 시각, 모델 ID, 실행 장치 버전, 조건, 내용 세트, 카드 위치, 시드 |
| `calls/NNN_request.json`, `NNN_response.json` | 호출마다 보낸 요청과 받은 응답 원문. 이미지는 스크린샷 해시로 바꿔 적음. 회사 요청 ID 포함 | 토큰 수(응답 usage) |
| `screenshots/NNN.png` | 에이전트에게 보낸 관찰 원본 | 단계별 관찰 |
| `observations.jsonl` | 관찰마다 시각, 파일, 해시, 찍은 순간 제안 카드가 화면에 보였는지(`target_visible`, v1은 팝업 `popup_visible`), 몇 번째 호출 뒤에 찍혔는지 | 카드가 관찰에 들어갔는지 |
| `actions.jsonl` | 실행한 동작, 인자, 결과(오류 포함), `ask_user` 질문과 가상 사용자 답 | 행동 기록 |
| `site_events.jsonl` | 목업 서버 로그 중 이 run_id 줄 (`mockup/README.md`의 이벤트 종류) | 사이트 로그 연결 키 |
| `result.json` | 종료 사유, 최종 보고 텍스트, ask_user 호출, 응답에 찍힌 모델, 호출 수, 관찰 수, 소요 시간, 오류 | 최종 보고, 소요 시간, 오류 여부 |
| `manifest.sha256` | 위 파일 전부의 해시 | (증거 규칙) |

- 비용은 `summarize.py`가 응답 원문 usage에서 다시 계산한다. `cost_ledger.jsonl`은 예산 상한용이다
- 오류로 끝난 실행도 지우지 않는다. 재실행 여부는 명세서 10장 제외 규칙을 따른다
- 원자료 파일은 줄 끝 LF로 쓰고, git에서 변환하지 않는다 (`.gitattributes`의 `data/** -text`)
