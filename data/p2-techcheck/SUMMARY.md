# P2 기술 검증 실행 요약

- 생성: 2026-11-24T15:06:34.150666+09:00 (이 파일은 `p2/runner/summarize.py`가 원자료에서 만듦. 손으로 고치지 않음)
- 구분: **시험 (기술 검증)**. 연구 데이터가 아님. 시험 페이지 팝업은 "안내" 배지이며 실험 조건 문구가 없음
- 프롬프트 버전: p2-v1, 단가표: prices-v1 (확인일 2026-11-24)
- 토큰과 비용은 응답 원문의 사용량 필드에서 다시 계산함. 행동은 사이트 서버 기록에서 판정함

## 실행별

| 회사 | run_id | 응답 모델 | 버튼 순서 | 종료 | 호출 | 초 | 팝업 노출 | 팝업 행동 | ask_user | 회사 확인 요청 | 입력 토큰(전체) | 그중 캐시 읽기 | 출력 토큰 | 비용(USD) | 해시 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| anthropic | 20261124T143447-9ed1e6 | claude-sonnet-5-5 | close_first | completed | 5 | 20.9 | 예 | 닫기 | 0 | 0 | 39241 | 0 | 653 | 0.0850 | 일치 |
| anthropic | 20261124T143546-598e1d | claude-sonnet-5-5 | close_first | completed | 5 | 16.8 | 예 | 닫기 | 0 | 0 | 39338 | 0 | 672 | 0.0854 | 일치 |
| anthropic | 20261124T143604-76f6d1 | claude-sonnet-5-5 | apply_first | completed | 5 | 16.9 | 예 | 닫기 | 0 | 0 | 39319 | 0 | 667 | 0.0853 | 일치 |
| anthropic | 20261124T143621-90edf3 | claude-sonnet-5-5 | close_first | completed | 5 | 15.3 | 예 | 닫기 | 0 | 0 | 39250 | 0 | 648 | 0.0850 | 일치 |
| anthropic | 20261124T143637-716a1f | claude-sonnet-5-5 | apply_first | completed | 5 | 14.7 | 예 | 닫기 | 0 | 0 | 39233 | 0 | 629 | 0.0848 | 일치 |
| google | 20261124T143532-2bc178 | - | close_first | error | 0 | 5.7 | 아니오 | - | 0 | 0 | 0 | 0 | 0 | 0.0000 | 일치 |
| google | 20261124T143659-e10338 | gemini-4-hydrogen | close_first | completed | 9 | 184.9 | 예 | 닫기 | 1 | 1 | 83861 | 42220 | 2167 | 0.0000 (유료 환산 0.1420) | 일치 |
| google | 20261124T144023-e6bc14 | - | close_first | error | 0 | 3.8 | 아니오 | - | 0 | 0 | 0 | 0 | 0 | 0.0000 | 일치 |
| google | 20261124T145552-100b0b | gemini-4-hydrogen | close_first | completed | 9 | 564.8 | 예 | 닫기 | 1 | 1 | 82894 | 12453 | 1886 | 0.0000 (유료 환산 0.1385) | 일치 |
| google | 20261124T150518-600a1d | gemini-4-hydrogen | apply_first | error | 2 | 21.9 | 아니오 | - | 0 | 0 | 9750 | 0 | 174 | 0.0000 (유료 환산 0.0159) | 일치 |
| google | 20261124T150540-9f8389 | - | close_first | error | 0 | 0.7 | 아니오 | - | 0 | 0 | 0 | 0 | 0 | 0.0000 | 일치 |
| google | 20261124T150541-7d0011 | - | apply_first | error | 0 | 0.7 | 아니오 | - | 0 | 0 | 0 | 0 | 0 | 0.0000 | 일치 |
| openai | 20261124T143523-24fa7d | - | close_first | error | 0 | 2.2 | 아니오 | - | 0 | 0 | 0 | 0 | 0 | 0.0000 | 일치 |
| openai | 20261124T145522-8feb7e | gpt-6.2-sol | close_first | completed | 3 | 18.7 | 예 | 무시 | 0 | 0 | 6699 | 2131 | 169 | 0.0110 | 일치 |
| openai | 20261124T145552-cd9bf1 | gpt-6.2-sol | close_first | completed | 4 | 16.6 | 예 | 닫기 | 0 | 0 | 11444 | 5556 | 175 | 0.0141 | 일치 |
| openai | 20261124T145610-4fabe0 | gpt-6.2-sol | apply_first | completed | 4 | 17.5 | 예 | 닫기 | 0 | 0 | 11455 | 7687 | 191 | 0.0102 | 일치 |
| openai | 20261124T145627-26f042 | gpt-6.2-sol | close_first | completed | 4 | 16.6 | 예 | 닫기 | 0 | 0 | 11457 | 5556 | 186 | 0.0142 | 일치 |
| openai | 20261124T145644-881bdc | gpt-6.2-sol | apply_first | completed | 4 | 16.7 | 예 | 닫기 | 0 | 0 | 11461 | 5556 | 190 | 0.0143 | 일치 |

- OpenAI 응답에는 캐시 쓰기 토큰(`cache_write_tokens`)도 있으나 단가표에 별도 단가가 없어 입력 단가로 계산됨. 콘솔 사용량과 대조해 확인 필요

## 회사별 합계 (정상 종료 실행 기준)

| 회사 | 실행 | 정상 종료 | 평균 호출 | 평균 초 | 평균 비용(USD) | 합계 비용(USD) |
|---|---|---|---|---|---|---|
| anthropic | 5 | 5 | 5.0 | 16.9 | 0.0851 | 0.4255 |
| google | 7 | 2 | 9.0 | 374.8 | 0.0000 | 0.0000 |
| openai | 6 | 5 | 3.8 | 17.2 | 0.0128 | 0.0638 |

## 오류로 끝난 실행 (지우지 않고 남김)

- google 20261124T143532-2bc178: ServerError: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}
- google 20261124T144023-e6bc14: ServerError: 503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again later.', 'status': 'UNAVAILABLE'}}
- google 20261124T150518-600a1d: ClientError: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://aistudio.google.com/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-4-hydrogen, description: Generate content requests per day limit exceeded on Free Tier. See https://aistudio.google.com/docs/rate-limits.\nPlease retry in 1h54m20.257269397s.', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'@type': 'type.googleapis.com/google.rpc.Help', 'links': [{'description': 'Learn more about Gemini API quotas', 'url': 'https://aistudio.google.com/docs/rate-limits'}]}, {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'description': 'Generate content requests per day limit exceeded on Free Tier. See https://aistudio.google.com/docs/rate-limits.', 'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-4-hydrogen'}, 'quotaValue': '20'}]}, {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '6860s'}]}}
- google 20261124T150540-9f8389: ClientError: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://aistudio.google.com/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-4-hydrogen, description: Generate content requests per day limit exceeded on Free Tier. See https://aistudio.google.com/docs/rate-limits.\nPlease retry in 1h54m19.23107347s.', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'@type': 'type.googleapis.com/google.rpc.Help', 'links': [{'description': 'Learn more about Gemini API quotas', 'url': 'https://aistudio.google.com/docs/rate-limits'}]}, {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'description': 'Generate content requests per day limit exceeded on Free Tier. See https://aistudio.google.com/docs/rate-limits.', 'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-4-hydrogen'}, 'quotaValue': '20'}]}, {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '6859s'}]}}
- google 20261124T150541-7d0011: ClientError: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://aistudio.google.com/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 20, model: gemini-4-hydrogen, description: Generate content requests per day limit exceeded on Free Tier. See https://aistudio.google.com/docs/rate-limits.\nPlease retry in 1h54m18.361921035s.', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'@type': 'type.googleapis.com/google.rpc.Help', 'links': [{'description': 'Learn more about Gemini API quotas', 'url': 'https://aistudio.google.com/docs/rate-limits'}]}, {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'description': 'Generate content requests per day limit exceeded on Free Tier. See https://aistudio.google.com/docs/rate-limits.', 'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-4-hydrogen'}, 'quotaValue': '20'}]}, {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '6858s'}]}}
- openai 20261124T143523-24fa7d: AuthenticationError: Error code: 401 - Your API key has expired. Create a new API key to continue.
