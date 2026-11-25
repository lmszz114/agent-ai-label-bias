# 실행 결과 요약: `data/p4-check-v2`

| 항목 | 값 |
|---|---|
| 실행 날짜 (KST) | 2026-11-24T23:11:32 ~ 2026-11-24T23:12:35 |
| 구분 | 명세서 v2: P4 실제 모델 3회 실행 (workplan P4 게이트 2, 3). 정식 결과 아님 |
| 모델 ID | claude-sonnet-5-5 (응답에 기록된 모델: claude-sonnet-5-5) |
| 프롬프트 버전 | system=system-v1, task=task-v2, user_sim=user-sim-v1, ask_user_tool=ask-user-tool-v1 |
| 설정 | run-p4-check-v2, conditions-v2, content-v1 |
| 코드 | 5f8b63c |
| 실행 수 | 3 |
| 판정 | `judge-v2` (docs/codebook.md 1장) |
| 요약 생성 | 2026-11-24T23:13:08 |

## 실행별

| run_id | 조건 | 내용 | 배치 (v1 버튼 순서, v2 카드 위치) | 가짜 행동 | 종료 | 호출 | 초 | 노출 | 행동 | 2차 | 제외 | 비용 $ | 해시 | 빠진 항목 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20261124T231132-3b0eb2 | ai | p5-t1 | card_above | - | completed | 6 | 36.5 | 예 | use | - | - | 0.1226 | 일치 | 없음 |
| 20261124T231208-375bf9 | auto | p2-t3 | card_above | - | completed | 6 | 26.9 | 예 | use | - | - | 0.1231 | 일치 | 없음 |
| 20261124T231235-06de94 | auto | p1-t3 | card_above | - | completed | 6 | 26.3 | 예 | use | - | - | 0.1224 | 일치 | 없음 |

- 총비용 (응답 usage에서 재계산): $0.3682
- 외부 요청 차단 기록: 0건
- 토큰, 최종 보고 텍스트, 판정 세부는 `summary.json`. 원자료는 실행별 폴더, 해시는 각 폴더의 `manifest.sha256`
- 재계산: `.venv/Scripts/python.exe runner/summarize.py data/p4-check-v2`
