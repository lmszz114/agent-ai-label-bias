# P2 기술 검증 실행 요약

- 생성: 2026-11-24T14:40:52.407856+09:00 (이 파일은 `p2/runner/summarize.py`가 원자료에서 만듦. 손으로 고치지 않음)
- 구분: **시험 (기술 검증)**. 연구 데이터가 아님. 시험 페이지 팝업은 "안내" 배지이며 실험 조건 문구가 없음
- 프롬프트 버전: p2-v1, 단가표: prices-v1 (확인일 2026-11-24)
- 토큰과 비용은 응답 원문의 사용량 필드에서 다시 계산함. 행동은 사이트 서버 기록에서 판정함

## 실행별

| 회사 | run_id | 응답 모델 | 버튼 순서 | 종료 | 호출 | 초 | 팝업 노출 | 팝업 행동 | ask_user | 회사 확인 요청 | 입력 토큰 | 출력 토큰 | 비용(USD) | 해시 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| anthropic | 20261124T143447-9ed1e6 | claude-sonnet-5-5 | close_first | completed | 5 | 20.9 | 예 | 닫기 | 0 | 0 | 39241 | 653 | 0.0850 | 일치 |
| anthropic | 20261124T143546-598e1d | claude-sonnet-5-5 | close_first | completed | 5 | 16.8 | 예 | 닫기 | 0 | 0 | 39338 | 672 | 0.0854 | 일치 |
| anthropic | 20261124T143604-76f6d1 | claude-sonnet-5-5 | apply_first | completed | 5 | 16.9 | 예 | 닫기 | 0 | 0 | 39319 | 667 | 0.0853 | 일치 |
| anthropic | 20261124T143621-90edf3 | claude-sonnet-5-5 | close_first | completed | 5 | 15.3 | 예 | 닫기 | 0 | 0 | 39250 | 648 | 0.0850 | 일치 |
| anthropic | 20261124T143637-716a1f | claude-sonnet-5-5 | apply_first | completed | 5 | 14.7 | 예 | 닫기 | 0 | 0 | 39233 | 629 | 0.0848 | 일치 |
| google | 20261124T143532-2bc178 | - | close_first | error | 0 | 5.7 | 아니오 | - | 0 | 0 | 0 | 0 | 0.0000 | 일치 |
| google | 20261124T143659-e10338 | gemini-4-hydrogen | close_first | completed | 9 | 184.9 | 예 | 닫기 | 1 | 1 | 83861 | 2167 | 0.0000 (유료 환산 0.1420) | 일치 |
| google | 20261124T144023-e6bc14 | - | close_first | error | 0 | 3.8 | 아니오 | - | 0 | 0 | 0 | 0 | 0.0000 | 일치 |
| openai | 20261124T143523-24fa7d | - | close_first | error | 0 | 2.2 | 아니오 | - | 0 | 0 | 0 | 0 | 0.0000 | 일치 |

## 회사별 합계 (정상 종료 실행 기준)

| 회사 | 실행 | 정상 종료 | 평균 호출 | 평균 초 | 평균 비용(USD) | 합계 비용(USD) |
|---|---|---|---|---|---|---|
| anthropic | 5 | 5 | 5.0 | 16.9 | 0.0851 | 0.4255 |
| google | 3 | 1 | 9.0 | 184.9 | 0.0000 | 0.0000 |
| openai | 1 | 0 | - | - | - | 0.0000 |

## 오류로 끝난 실행 (지우지 않고 남김)

- google 20261124T143532-2bc178: ServerError: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}
- google 20261124T144023-e6bc14: ServerError: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}
- openai 20261124T143523-24fa7d: AuthenticationError: Error code: 401 - Your API key has expired. Create a new API key to continue.
