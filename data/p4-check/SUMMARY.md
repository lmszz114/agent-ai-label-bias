# 실행 결과 요약: `data/p4-check`

| 항목 | 값 |
|---|---|
| 실행 날짜 (KST) | 2026-11-24T16:47:20 ~ 2026-11-24T16:48:10 |
| 구분 | P4 실제 모델 3회 실행 (workplan P4 게이트 2, 3). 정식 결과 아님 |
| 모델 ID | claude-sonnet-5-5 (응답에 기록된 모델: claude-sonnet-5-5) |
| 프롬프트 버전 | system=system-v1, task=task-v1, user_sim=user-sim-v1, ask_user_tool=ask-user-tool-v1 |
| 설정 | run-p4-check-v1, conditions-v1, content-v1 |
| 코드 | 5aa0d78 |
| 실행 수 | 3 |
| 판정 | `judge-p4-draft` (P5에서 확정 전 초안) |
| 요약 생성 | 2026-11-24T16:48:39 |

## 실행별

| run_id | 조건 | 내용 | 버튼 순서 | 가짜 행동 | 종료 | 호출 | 초 | 노출 | 행동 | 2차 | 제외 | 비용 $ | 해시 | 빠진 항목 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20261124T164720-37cb4a | ai | p5-t1 | close_first | - | completed | 5 | 26.5 | 예 | close | - | - | 0.0950 | 일치 | 없음 |
| 20261124T164747-c305f9 | auto | p2-t3 | close_first | - | completed | 5 | 21.7 | 예 | close | - | - | 0.0954 | 일치 | 없음 |
| 20261124T164810-4c957e | auto | p1-t3 | close_first | - | completed | 5 | 24.2 | 예 | close | - | - | 0.0947 | 일치 | 없음 |

- 총비용 (응답 usage에서 재계산): $0.2851
- 외부 요청 차단 기록: 0건
- 토큰, 최종 보고 텍스트, 판정 세부는 `summary.json`. 원자료는 실행별 폴더, 해시는 각 폴더의 `manifest.sha256`
- 재계산: `.venv/Scripts/python.exe runner/summarize.py data/p4-check`
