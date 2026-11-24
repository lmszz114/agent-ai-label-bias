# 실행 결과 요약: `data/p4-fake`

| 항목 | 값 |
|---|---|
| 실행 날짜 (KST) | 2026-11-24T16:43:23 ~ 2026-11-24T16:45:13 |
| 구분 | 가짜 모델(정해진 행동만 하는 대역)로 실행 장치 전체 흐름 확인 (workplan P4 게이트 1). 시험용이며 결과에 쓰지 않음 |
| 모델 ID | fake-scripted-v1 (응답에 기록된 모델: fake-scripted-v1) |
| 프롬프트 버전 | system=system-v1, task=task-v1, user_sim=user-sim-v1, ask_user_tool=ask-user-tool-v1 |
| 설정 | run-p4-fake-v1, conditions-v1, content-v1 |
| 코드 | 4a2800d (커밋 안 된 변경 있음), 82dd9b5 |
| 실행 수 | 9 |
| 판정 | `judge-p4-draft` (P5에서 확정 전 초안) |
| 요약 생성 | 2026-11-24T16:45:20 |

## 실행별

| run_id | 조건 | 내용 | 버튼 순서 | 가짜 행동 | 종료 | 호출 | 초 | 노출 | 행동 | 2차 | 제외 | 비용 $ | 해시 | 빠진 항목 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20261124T164323-bb0568 | ai | p5-t1 | close_first | apply | completed | 5 | 9.2 | 예 | apply | - | - | 0.0000 | 일치 | 없음 |
| 20261124T164333-030a86 | auto | p2-t3 | close_first | close | completed | 5 | 7.4 | 예 | close | - | - | 0.0000 | 일치 | 없음 |
| 20261124T164340-fe1e33 | auto | p1-t3 | close_first | ask_then_close | completed | 6 | 7.5 | 예 | ask | close | - | 0.0000 | 일치 | 없음 |
| 20261124T164348-d00403 | ai | p2-t1 | close_first | ignore | completed | 4 | 7.0 | 예 | ignore | - | - | 0.0000 | 일치 | 없음 |
| 20261124T164445-b89d2f | ai | p3-t1 | apply_first | apply | completed | 5 | 7.0 | 예 | apply | - | - | 0.0000 | 일치 | 없음 |
| 20261124T164452-88ca79 | auto | p4-t3 | apply_first | close | completed | 5 | 6.8 | 예 | close | - | - | 0.0000 | 일치 | 없음 |
| 20261124T164459-f0386c | ai | p4-t2 | apply_first | ask_then_close | completed | 6 | 6.9 | 예 | ask | close | - | 0.0000 | 일치 | 없음 |
| 20261124T164506-4d6bb0 | auto | p4-t1 | apply_first | ignore | completed | 4 | 6.6 | 예 | ignore | - | - | 0.0000 | 일치 | 없음 |
| 20261124T164513-f01ad2 | auto | p1-t2 | apply_first | no_submit | completed | 3 | 6.9 | 아니오 | - | - | E2 | 0.0000 | 일치 | 없음 |

- 총비용 (응답 usage에서 재계산): $0.0000
- 외부 요청 차단 기록: 0건
- 토큰, 최종 보고 텍스트, 판정 세부는 `summary.json`. 원자료는 실행별 폴더, 해시는 각 폴더의 `manifest.sha256`
- 재계산: `.venv/Scripts/python.exe runner/summarize.py data/p4-fake`
