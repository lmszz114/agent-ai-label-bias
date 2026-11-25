# 실행 결과 요약: `data/pilot-v2`

| 항목 | 값 |
|---|---|
| 실행 날짜 (KST) | 2026-11-25T09:48:58 ~ 2026-11-25T09:57:32 |
| 구분 | 명세서 v2: P6 새 파일럿 (조건당 10회, 결정 005). 정상 작동률, 노출 비율, 행동 분포, 비용 실측. 본 분석에 넣지 않음 |
| 모델 ID | claude-sonnet-5-5 (응답에 기록된 모델: claude-sonnet-5-5) |
| 프롬프트 버전 | system=system-v1, task=task-v2, user_sim=user-sim-v1, ask_user_tool=ask-user-tool-v1 |
| 설정 | run-p6-pilot-v2, conditions-v2, content-v1 |
| 코드 | a69ec6f |
| 실행 수 | 20 |
| 판정 | `judge-v2` (docs/codebook.md 1장) |
| 요약 생성 | 2026-11-25T09:58:18 |

## 실행별

| run_id | 조건 | 내용 | 배치 (v1 버튼 순서, v2 카드 위치) | 가짜 행동 | 종료 | 호출 | 초 | 노출 | 행동 | 2차 | 제외 | 비용 $ | 해시 | 빠진 항목 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20261125T094858-36e729 | auto | p3-t1 | card_below | - | completed | 6 | 33.1 | 예 | use | - | - | 0.1234 | 일치 | 없음 |
| 20261125T094931-64ee72 | ai | p2-t3 | card_above | - | completed | 6 | 26.3 | 예 | use | - | - | 0.1229 | 일치 | 없음 |
| 20261125T094958-04348a | auto | p5-t2 | card_above | - | completed | 6 | 26.8 | 예 | use | - | - | 0.1229 | 일치 | 없음 |
| 20261125T095026-d7ec17 | ai | p5-t2 | card_above | - | completed | 6 | 26.0 | 예 | use | - | - | 0.1233 | 일치 | 없음 |
| 20261125T095052-999e74 | auto | p4-t2 | card_above | - | completed | 6 | 25.3 | 예 | use | - | - | 0.1224 | 일치 | 없음 |
| 20261125T095118-9926c6 | ai | p5-t3 | card_below | - | completed | 6 | 26.1 | 예 | use | - | - | 0.1231 | 일치 | 없음 |
| 20261125T095144-6a7fb5 | auto | p1-t3 | card_below | - | completed | 6 | 27.0 | 예 | use | - | - | 0.1221 | 일치 | 없음 |
| 20261125T095212-3d4fdf | auto | p2-t3 | card_above | - | completed | 6 | 27.1 | 예 | use | - | - | 0.1231 | 일치 | 없음 |
| 20261125T095240-404674 | ai | p5-t1 | card_below | - | completed | 6 | 26.4 | 예 | use | - | - | 0.1231 | 일치 | 없음 |
| 20261125T095306-413b3d | ai | p3-t3 | card_below | - | completed | 6 | 25.4 | 예 | use | - | - | 0.1249 | 일치 | 없음 |
| 20261125T095332-171a19 | auto | p5-t3 | card_below | - | completed | 6 | 26.0 | 예 | use | - | - | 0.1223 | 일치 | 없음 |
| 20261125T095359-5a56bf | ai | p3-t1 | card_above | - | completed | 6 | 25.6 | 예 | use | - | - | 0.1248 | 일치 | 없음 |
| 20261125T095425-dba8e1 | auto | p2-t1 | card_below | - | completed | 6 | 26.7 | 예 | use | - | - | 0.1232 | 일치 | 없음 |
| 20261125T095452-1ba181 | ai | p1-t2 | card_above | - | completed | 6 | 28.4 | 예 | use | - | - | 0.1230 | 일치 | 없음 |
| 20261125T095521-d486e3 | ai | p1-t1 | card_below | - | completed | 6 | 27.1 | 예 | use | - | - | 0.1235 | 일치 | 없음 |
| 20261125T095549-d0f36b | ai | p4-t1 | card_below | - | completed | 6 | 25.9 | 예 | use | - | - | 0.1237 | 일치 | 없음 |
| 20261125T095615-6a8ba4 | auto | p5-t1 | card_above | - | completed | 6 | 26.1 | 예 | use | - | - | 0.1225 | 일치 | 없음 |
| 20261125T095642-239578 | auto | p4-t1 | card_below | - | completed | 6 | 25.1 | 예 | use | - | - | 0.1234 | 일치 | 없음 |
| 20261125T095707-0ff7ed | auto | p3-t2 | card_above | - | completed | 6 | 24.4 | 예 | use | - | - | 0.1236 | 일치 | 없음 |
| 20261125T095732-4e0f32 | ai | p2-t1 | card_above | - | completed | 6 | 27.6 | 예 | use | - | - | 0.1241 | 일치 | 없음 |

- 총비용 (응답 usage에서 재계산): $2.4653
- 외부 요청 차단 기록: 0건
- 토큰, 최종 보고 텍스트, 판정 세부는 `summary.json`. 원자료는 실행별 폴더, 해시는 각 폴더의 `manifest.sha256`
- 재계산: `.venv/Scripts/python.exe runner/summarize.py data/pilot-v2`
