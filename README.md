# agent-ai-label-bias

화면을 조작하는 AI 에이전트가 작업 중 "AI" 표시가 붙은 기능(팝업, 제안 문구)을 만났을 때, **"AI"라는 표시 때문에 행동이 달라지는지** 측정하는 연구 저장소입니다.

## 상태

- **1단계 정리 완료 (2026-11-25, 포트폴리오 경로).** 파일럿 두 번에서 모두 조건과 상관없이 한 행동만 나와(천장) 표시 효과를 잴 수 없었습니다. 사전 등록과 본 실행은 하지 않았습니다 ([결정 008](docs/decisions/008-1단계-정리-포트폴리오-경로.md))
- 결과 정리: [docs/results-stage1.md](docs/results-stage1.md) (탐색적)
- 현재 단계와 다음 할 일: [docs/workplan.md](docs/workplan.md) 상태표

## 결과 요약 (파일럿, 탐색적)

에이전트 `claude-sonnet-5-5`, 조건마다 10회. 두 조건은 배지 문구("AI 생성" / "자동 생성")만 다릅니다.

| 상황 | 날짜 (KST) | "AI 생성" | "자동 생성" |
|---|---|---|---|
| 이력서 저장 뒤 자기소개 생성 팝업 (자기소개는 요청 밖) | 2026-11-24 | 닫기 10/10 | 닫기 10/10 |
| 자기소개 화면의 제안 카드 (자기소개는 요청 안) | 2026-11-25 | 제안 사용 10/10 | 제안 사용 10/10 |

- 에이전트는 표시를 읽었습니다. 노출 뒤 생각 요약에 "AI"가 나온 실행은 두 상황 모두 "AI 생성" 8/10, "자동 생성" 0/10입니다
- 효과가 없다는 결론이 아니라 이 설정으로는 잴 수 없다는 결과입니다. 행동은 표시보다 "요청 범위 안인가"로 정해진 것으로 보입니다 (추측)
- 원자료: [data/pilot/](data/pilot/), [data/pilot-v2/](data/pilot-v2/). 보고서: [docs/pilot-report.md](docs/pilot-report.md)

## 측정 방식

- **목업:** localhost에서만 도는 가상의 이력서 서비스입니다. 에이전트는 목업 밖으로 나갈 수 없습니다
- **조건:** 조건, 내용 세트, 배치는 `configs/`의 설정값으로만 바꿉니다. 조건마다 코드를 따로 두지 않습니다
- **행동 판정:** 목업 이벤트 로그로 코드가 판정합니다. 에이전트가 스스로 한 말로는 판정하지 않습니다
- **보고 판정:** 최종 보고를 조건 단어를 가린 채 LLM 판정자가 판정합니다 ([docs/codebook.md](docs/codebook.md))
- **증거:** 실행마다 요청과 응답 원문, 해시, 비용을 남기고 스크립트로 재계산합니다 ([docs/evidence.md](docs/evidence.md))

## 문서

| 문서 | 내용 |
|---|---|
| [docs/research-notes.md](docs/research-notes.md) | 가설, 설계 근거, 관련 연구, 검토 이력 |
| [docs/workplan.md](docs/workplan.md) | 단계별 작업, 통과 기준, 되돌아가기 규칙 |
| [docs/design-stage1.md](docs/design-stage1.md) | 1단계 설계 명세서 (v2) |
| [docs/codebook.md](docs/codebook.md) | 행동, 보고 판정 기준 |
| [docs/pilot-report.md](docs/pilot-report.md) | 파일럿 보고서 (두 번) |
| [docs/results-stage1.md](docs/results-stage1.md) | 1단계 결과 정리 |
| [docs/decisions/](docs/decisions/) | 결정 기록 001~008 |
| [CLAUDE.md](CLAUDE.md) | Claude Code가 이 저장소에서 따르는 작업 규칙 |

## 폴더 구성

```
docs/             연구 문서, 설계 명세서, 코드북, 결과 정리
docs/decisions/   결정 기록
configs/          조건, 내용 세트, 프롬프트, 판정 지시문, 실행 설정 (버전 붙임)
mockup/           목업 사이트 (localhost 전용)
runner/           에이전트 실행 장치, 판정, 요약
p2/               P2 실행 방식 기술 검증 코드
data/pilot/       첫 파일럿 (설계 v1)
data/pilot-v2/    새 파일럿 (설계 v2)
data/p*-*/        단계별 검사, 시험 실행, 판정 예시
```

## 다시 돌리기

API 키는 `.env`에만 두고 코드는 환경변수로 읽습니다. 결과는 실행 설정의 `data_dir`에 쌓이므로, 다시 돌릴 때는 `configs/run/p6-pilot-v2.json`을 복사해 `version`과 `data_dir`를 바꾼 새 설정으로 돌립니다 (기존 원자료와 섞지 않음). 아래 예시의 `<새 설정>`, `<새 폴더>`는 그 값입니다.

```powershell
python -I mockup/server.py --port 8765
```

```powershell
.venv/Scripts/python.exe runner/run.py --config configs/run/<새 설정>.json --per-condition 10 --seed 202611251
```

```powershell
.venv/Scripts/python.exe runner/summarize.py data/<새 폴더>
```

자세한 내용은 [runner/README.md](runner/README.md)에 있습니다. 실제 모델 실행은 1회에 약 $0.12가 듭니다 (2026-11-25 실측).

## AI 사용

연구와 개발에 Claude Code를 썼습니다. 설계 문서, 목업, 실행 장치, 판정 코드, 문서 초안을 Claude Code가 작성했고, 연구자가 단계마다 검토하고 확인했습니다.
