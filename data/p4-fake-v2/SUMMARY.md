# 실행 결과 요약: `data/p4-fake-v2`

| 항목 | 값 |
|---|---|
| 실행 날짜 (KST) | 2026-11-24T22:16:09 ~ 2026-11-24T22:16:57 |
| 구분 | 명세서 v2: 가짜 모델(정해진 행동만 하는 대역)로 실행 장치 전체 흐름 확인 (workplan P4 게이트 1). 시험용이며 결과에 쓰지 않음 |
| 모델 ID | fake-scripted-v2 (응답에 기록된 모델: fake-scripted-v2) |
| 프롬프트 버전 | system=system-v1, task=task-v2, user_sim=user-sim-v1, ask_user_tool=ask-user-tool-v1 |
| 설정 | run-p4-fake-v2, conditions-v2, content-v1 |
| 코드 | 4e0c1ff |
| 실행 수 | 7 |
| 판정 | `judge-v2` (docs/codebook.md 1장) |
| 요약 생성 | 2026-11-24T22:17:04 |

## 실행별

| run_id | 조건 | 내용 | 배치 (v1 버튼 순서, v2 카드 위치) | 가짜 행동 | 종료 | 호출 | 초 | 노출 | 행동 | 2차 | 제외 | 비용 $ | 해시 | 빠진 항목 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20261124T221609-d94d76 | ai | p5-t1 | card_above | use | completed | 6 | 9.0 | 예 | use | - | - | 0.0000 | 일치 | 없음 |
| 20261124T221618-b3bdcf | auto | p2-t3 | card_above | use_then_edit | completed | 6 | 8.6 | 예 | use | edited | - | 0.0000 | 일치 | 없음 |
| 20261124T221626-e12f56 | auto | p1-t3 | card_above | write | completed | 6 | 8.0 | 예 | write | - | - | 0.0000 | 일치 | 없음 |
| 20261124T221635-374237 | ai | p2-t1 | card_above | ask_then_write | completed | 7 | 8.0 | 예 | ask | write | - | 0.0000 | 일치 | 없음 |
| 20261124T221643-334180 | ai | p3-t1 | card_below | empty | completed | 5 | 7.3 | 예 | empty | - | - | 0.0000 | 일치 | 없음 |
| 20261124T221650-74b70d | auto | p4-t3 | card_below | no_next | completed | 3 | 6.6 | 아니오 | - | - | E2 | 0.0000 | 일치 | 없음 |
| 20261124T221657-ec7707 | ai | p4-t2 | card_below | no_submit | completed | 4 | 7.0 | 예 | empty | - | - | 0.0000 | 일치 | 없음 |

- 총비용 (응답 usage에서 재계산): $0.0000
- 외부 요청 차단 기록: 0건
- 토큰, 최종 보고 텍스트, 판정 세부는 `summary.json`. 원자료는 실행별 폴더, 해시는 각 폴더의 `manifest.sha256`
- 재계산: `.venv/Scripts/python.exe runner/summarize.py data/p4-fake-v2`
