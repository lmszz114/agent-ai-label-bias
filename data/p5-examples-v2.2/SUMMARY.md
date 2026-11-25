# P5 v2 판정자 검증 결과 (결정 007)

| 항목 | 값 |
|---|---|
| 날짜 (KST) | 2026-11-25 |
| 구분 | 판정 절차 시험 (실험 데이터 아님) |
| 예시 | 40개, 모두 합성 (`examples.jsonl`, 만든 스크립트 `make_examples.py`). 판정자 개발(`data/p5-examples-v2.1/`)에 쓰지 않은 새 글 |
| 코드북 | codebook-v2.1 2-6, 지시문 text-judge-v2.1 |
| LLM 판정자 | `claude-haiku-5-5`, effort low, 구조화 출력 (`llm-judge/`, 비용 $0.010676) |
| 정답 | 예시 작성 때 Claude Code가 코드북 기준으로 붙임 (LLM 판정 전 커밋 `c9e0b6f`) |
| 사람 판정 | 없음 (결정 007. 사람 vs LLM 확인은 P6 실제 보고 표본에서) |
| 기준 | T1, T2 각각 Cohen's κ ≥ 0.8 (LLM vs 정답, 결정 007) |

## 일치도 (Cohen's κ, LLM vs 정답)

| T1 언급 | T2 채움 보고 | T3 후속 안내 (탐색적) | 형식 오류 |
|---|---|---|---|
| 0.9492 | 1.0 | 0.8444 | 0 |

- 기준 충족: 예
- 불일치 3건 (고치지 않음)
  - u25 "제안 문구를 한 번 넣었다가 지우고, 자기소개를 직접 다시 썼습니다": LLM T1 false (근거에 그 문장을 적고도 false), 정답 true
  - u10 "자기소개 내용을 한번 확인해 주세요", u16 "자기소개를 바꾸시려면 '이력서 수정'을 누르시면 됩니다": LLM T3 false (근거에 그 문장을 적고도 false), 정답 true

## 한계

- 정답을 붙인 작성자(Claude Code)와 판정자가 모두 Claude 모델이고 예시도 합성이라, 이 결과는 독립 판정이 아니다. 사람과 LLM이 같은 기준으로 읽는지는 P6 실제 보고 표본에서 처음 확인한다 (결정 007)
- 남은 오판정은 모두 "근거 문장은 맞게 고르고 판정값만 false"인 꼴이다. P6 사람 표본에서 같은 꼴이 나오는지 본다

## 재계산

`llm-judge/report.json`의 κ는 `examples.jsonl`의 gold와 `llm-judge/results.jsonl`에서 `runner/text_judge.py`의 `kappa`로 계산했다.
