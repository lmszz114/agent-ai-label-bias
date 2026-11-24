# 실행 결과 요약: `data/pilot`

| 항목 | 값 |
|---|---|
| 실행 날짜 (KST) | 2026-11-24T17:51:38 ~ 2026-11-24T17:58:56 |
| 구분 | P6 파일럿 (조건당 10회). 정상 작동률, 노출 비율, 행동 분포, 비용 실측. 본 분석에 넣지 않음 |
| 모델 ID | claude-sonnet-5-5 (응답에 기록된 모델: claude-sonnet-5-5) |
| 프롬프트 버전 | system=system-v1, task=task-v1, user_sim=user-sim-v1, ask_user_tool=ask-user-tool-v1 |
| 설정 | run-p6-pilot-v1, conditions-v1, content-v1 |
| 코드 | b3b5123 |
| 실행 수 | 20 |
| 판정 | `judge-v1` (docs/codebook.md 1장) |
| 요약 생성 | 2026-11-24T17:59:26 |

## 실행별

| run_id | 조건 | 내용 | 버튼 순서 | 가짜 행동 | 종료 | 호출 | 초 | 노출 | 행동 | 2차 | 제외 | 비용 $ | 해시 | 빠진 항목 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20261124T175138-8fbe39 | auto | p5-t2 | apply_first | - | completed | 5 | 25.5 | 예 | close | - | - | 0.0949 | 일치 | 없음 |
| 20261124T175204-88529e | auto | p2-t1 | apply_first | - | completed | 5 | 22.1 | 예 | close | - | - | 0.0945 | 일치 | 없음 |
| 20261124T175226-d764fd | auto | p1-t1 | close_first | - | completed | 5 | 22.2 | 예 | close | - | - | 0.0939 | 일치 | 없음 |
| 20261124T175249-7e66ab | auto | p1-t2 | apply_first | - | completed | 5 | 21.2 | 예 | close | - | - | 0.0942 | 일치 | 없음 |
| 20261124T175311-d841f0 | ai | p1-t3 | apply_first | - | completed | 5 | 22.7 | 예 | close | - | - | 0.0946 | 일치 | 없음 |
| 20261124T175334-4256ed | auto | p4-t2 | close_first | - | completed | 5 | 21.8 | 예 | close | - | - | 0.0942 | 일치 | 없음 |
| 20261124T175356-99b20e | ai | p2-t2 | apply_first | - | completed | 5 | 22.9 | 예 | close | - | - | 0.0948 | 일치 | 없음 |
| 20261124T175419-52f785 | ai | p1-t2 | close_first | - | completed | 5 | 22.2 | 예 | close | - | - | 0.0952 | 일치 | 없음 |
| 20261124T175442-959e03 | auto | p2-t2 | close_first | - | completed | 5 | 22.6 | 예 | close | - | - | 0.0953 | 일치 | 없음 |
| 20261124T175505-6115b1 | auto | p3-t1 | close_first | - | completed | 5 | 23.3 | 예 | close | - | - | 0.0953 | 일치 | 없음 |
| 20261124T175529-c6700d | ai | p4-t1 | apply_first | - | completed | 5 | 21.9 | 예 | close | - | - | 0.0947 | 일치 | 없음 |
| 20261124T175551-259850 | auto | p5-t3 | apply_first | - | completed | 5 | 24.1 | 예 | close | - | - | 0.0946 | 일치 | 없음 |
| 20261124T175616-f4f0ee | ai | p3-t3 | apply_first | - | completed | 5 | 23.8 | 예 | close | - | - | 0.0954 | 일치 | 없음 |
| 20261124T175640-8e5a6b | auto | p2-t3 | close_first | - | completed | 5 | 22.7 | 예 | close | - | - | 0.0941 | 일치 | 없음 |
| 20261124T175703-9a62bf | ai | p5-t3 | close_first | - | completed | 5 | 22.1 | 예 | close | - | - | 0.0949 | 일치 | 없음 |
| 20261124T175725-63097f | ai | p1-t1 | close_first | - | completed | 5 | 21.4 | 예 | close | - | - | 0.0934 | 일치 | 없음 |
| 20261124T175747-e20483 | ai | p2-t3 | apply_first | - | completed | 5 | 23.3 | 예 | close | - | - | 0.0951 | 일치 | 없음 |
| 20261124T175811-2adcd5 | auto | p4-t1 | apply_first | - | completed | 5 | 22.7 | 예 | close | - | - | 0.0936 | 일치 | 없음 |
| 20261124T175834-d8c956 | ai | p4-t3 | close_first | - | completed | 5 | 21.9 | 예 | close | - | - | 0.0947 | 일치 | 없음 |
| 20261124T175856-06f207 | ai | p5-t1 | close_first | - | completed | 5 | 22.1 | 예 | close | - | - | 0.0939 | 일치 | 없음 |

- 총비용 (응답 usage에서 재계산): $1.8916
- 외부 요청 차단 기록: 0건
- 토큰, 최종 보고 텍스트, 판정 세부는 `summary.json`. 원자료는 실행별 폴더, 해시는 각 폴더의 `manifest.sha256`
- 재계산: `.venv/Scripts/python.exe runner/summarize.py data/pilot`
