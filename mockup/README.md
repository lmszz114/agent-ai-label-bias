# 커리어노트 목업 (P3, 명세서 v2)

가상의 이력서 서비스 화면이다. 실존 서비스가 아니다. 설계는 [docs/design-stage1.md](../docs/design-stage1.md) 4~6장, 8장을 따른다.

## 구성

| 파일 | 역할 |
|---|---|
| `server.py` | 127.0.0.1 전용 서버. 화면 제공, 배정 풀기(`/api/session`), 이벤트 기록(`/event` → `runtime/events.jsonl`) |
| `session.py` | 실행 배정 파일 만들기(`create`), 화면 값 풀기(`resolve`), 공용 브라우저 옵션(`BROWSER_ARGS`) |
| `static/` | 화면 (HTML, CSS, JS). 외부 리소스 없음 |
| `check_equivalence.py` | 조건 동등성 자동 검사와 로그 일치 검사. 결과는 `data/p3-equivalence-v2/` (v1 결과는 `data/p3-equivalence/`) |
| `manual_check.py` | 사람이 직접 눌러 보는 검사 도우미 |
| `runtime/` | 배정 파일과 이벤트 로그 (git 제외. P4 실행 장치가 실행마다 run 폴더로 복사함) |

- 조건, 내용, 카드 위치는 `configs/conditions/conditions-v2.json`, `configs/content/content-v1.json`과 배정 파일 값으로만 바뀐다. 화면 코드에 조건 분기는 없다
- 주소에는 `?s=<run_id>`만 들어간다. 조건 코드는 주소에도 화면에도 나오지 않고, 배지 문구만 그려진다
- 화면: S1 기본 정보 → [다음] → S1b 자기소개 + 제안 카드 → [작성완료] → S2 저장 완료 (명세서 v2 4장). v1(완료 후 팝업) 화면은 코드 `b3b5123`

## 서버 실행

```powershell
python -I mockup/server.py --port 8765
```

## 직접 클릭 검사 (workplan P3 게이트 2)

1. 서버를 띄운 상태에서 배정 4개를 만든다 (조건 2 × 카드 위치 2)

   ```powershell
   .venv/Scripts/python.exe mockup/manual_check.py start
   ```

2. 출력된 주소 4개를 브라우저(크롬 등)에서 하나씩 열고, 출력된 안내 a~d대로 조작한다. 입력값은 아무거나 써도 된다
3. 기록을 출력해 내가 한 행동과 같은지 대조한다

   ```powershell
   .venv/Scripts/python.exe mockup/manual_check.py show
   ```

   확인할 것: 빈 칸 [다음]이 `next_invalid`로 남았는지, 자기소개 화면이 `card_shown`으로 남았는지, 제안 넣기는 `card_insert`, 직접 쓰기는 `intro_input`으로 남았는지, 저장 줄의 출처가 한 일과 맞는지(넣기 `card`, 직접 `typed`)

## 이벤트 종류

| type | 언제 | 주요 내용 |
|---|---|---|
| `page_load` | 배정을 받아 화면을 그린 뒤 | 화면 크기, 카드 위치 |
| `click` | 모든 클릭 | 대상 id, 좌표 |
| `key` | 문자가 아닌 키 | 키 이름 |
| `field_change` | 입력 칸 값이 바뀜 (칸을 떠날 때) | 칸 이름, 값 |
| `next_invalid` | 필수 칸이 빈 채 [다음] | 빈 칸 목록 |
| `next` | S1 통과 | 기본 정보 |
| `screen` | 화면 전환 | s1, s1b, s2와 전환 이유 |
| `card_shown` | S1b 표시 (카드가 같은 시점에 보임) | 카드 위치, 몇 번째 표시인지 |
| `card_rendered` | 다음 프레임에서 카드가 화면 안에 그려졌는지 확인 | 화면 안 여부, 위치와 크기 |
| `card_insert` | [이 문구 넣기] 클릭 | 이미 쓴 글을 바꿨는지 |
| `intro_input` | 자기소개 칸 키보드 입력 (입력 묶음마다 한 번) | 넣기 뒤 입력인지 |
| `submit` | [작성완료] 저장 | 저장된 이력서 전체, 자기소개 출처(`card`, `card_edited`, `typed`, `empty`) |
| `page_unload` | 페이지를 떠남 | 마지막 이력서 |

- 모든 이벤트에 `run_id`, `page_id`(페이지를 열 때마다 새 값), `seq`(페이지 안 순서), `client_ts`, `t_ms`, `server_ts`(KST)가 붙는다. 전송 순서가 바뀔 수 있으므로 순서는 `page_id`별 `seq`로 본다
- 한글 입력 중 생기는 `Process` 키는 기록하지 않는다
- [이 문구 넣기]로 값이 바뀔 때는 브라우저가 `input` 이벤트를 만들지 않으므로 `intro_input`이 생기지 않는다. `intro_input`은 키보드 입력만 뜻한다
- 새로고침하면 화면이 처음(S1)으로 돌아간다. 행동 판정은 실행 안의 첫 노출 기준이다 (codebook 1-7)
