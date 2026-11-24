# agent-ai-label-bias

화면을 조작하는 AI 에이전트가 작업 중 "AI" 표시가 붙은 기능(버튼, 팝업, 생성물)을 만났을 때, **"AI"라는 표시 때문에 행동이 달라지는지** 측정하는 연구 저장소입니다.

- 상태: 작업 기반 정리 단계, 실험 전 (현재 단계는 [docs/workplan.md](docs/workplan.md) 상태표)
- 가설: 방향을 정하지 않은 양방향 검정 (피하는 쪽 / 더 쓰는 쪽 모두 의미 있는 결과)
- 1단계: 모델 1개, 완료 후 팝업, "AI 생성" vs "자동 생성" 표시 비교

## 문서

- [연구 정리](docs/research-notes.md): 가설, 실험 설계 근거, 관련 연구, 검토 이력
- [상세 진행 순서](docs/workplan.md): 단계별 작업, 통과 기준, 되돌아가기 규칙
- [작업 규칙](CLAUDE.md): Claude Code가 이 저장소에서 따르는 규칙

## 폴더 구성

```
docs/             연구 문서, 설계 명세서, 코드북, 사전 등록
docs/decisions/   결정 기록
configs/          조건, 내용 세트, 프롬프트 (버전 붙임)
mockup/           목업 사이트 (localhost 전용)
runner/           에이전트 실행 장치
analysis/         판정, 통계 분석 스크립트
data/pilot/       파일럿 데이터 (본 분석에 쓰지 않음)
data/raw/         본 실행 원본 (수정 금지)
data/processed/   가공 결과
```

폴더는 해당 단계에서 만듭니다. 연구와 개발에 Claude Code를 사용합니다.
