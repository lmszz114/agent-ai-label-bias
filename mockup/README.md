# 커리어노트 목업 (P3)

가상의 이력서 서비스 화면이다. 실존 서비스가 아니다. 설계는 [docs/design-stage1.md](../docs/design-stage1.md) 4~6장, 8장을 따른다.

## 구성

| 파일 | 역할 |
|---|---|
| `server.py` | 127.0.0.1 전용 서버. 화면 제공, 배정 풀기(`/api/session`), 이벤트 기록(`/event` → `runtime/events.jsonl`) |
| `session.py` | 실행 배정 파일 만들기(`create`), 화면 값 풀기(`resolve`), 공용 브라우저 옵션(`BROWSER_ARGS`) |
| `static/` | 화면 (HTML, CSS, JS). 외부 리소스 없음 |
| `check_equivalence.py` | 조건 동등성 자동 검사와 로그 일치 검사. 결과는 `data/p3-equivalence/` |
| `manual_check.py` | 사람이 직접 눌러 보는 검사 도우미 |
| `runtime/` | 배정 파일과 이벤트 로그 (git 제외. P4 실행 장치가 실행마다 run 폴더로 복사함) |

- 조건, 내용, 버튼 순서는 `configs/conditions/conditions-v1.json`, `configs/content/content-v1.json`과 배정 파일 값으로만 바뀐다. 화면 코드에 조건 분기는 없다
- 주소에는 `?s=<run_id>`만 들어간다. 조건 코드는 주소에도 화면에도 나오지 않고, 배지 문구만 그려진다

## 서버 실행

```powershell
python -I mockup/server.py --port 8765
```

## 직접 클릭 검사 (workplan P3 게이트 2)

1. 서버를 띄운 상태에서 배정 4개를 만든다 (조건 2 × 버튼 순서 2)

   ```powershell
   .venv/Scripts/python.exe mockup/manual_check.py start
   ```

2. 출력된 주소 4개를 브라우저(크롬 등)에서 하나씩 열고, 출력된 안내 a~e대로 조작한다. 입력값은 아무거나 써도 된다
3. 기록을 출력해 내가 한 행동과 같은지 대조한다

   ```powershell
   .venv/Scripts/python.exe mockup/manual_check.py show
   ```

   확인할 것: 빈 칸 제출이 `submit_invalid`로 남았는지, 팝업이 `popup_shown`으로 남았는지, Esc(`key Escape`)와 바깥 클릭 뒤에도 `popup_closed`가 없는지, 누른 버튼이 `popup_click`의 `button`과 `position`(왼쪽/오른쪽)에 맞게 남았는지, 적용했을 때만 `resume_updated`가 있는지

## 이벤트 종류

| type | 언제 | 주요 내용 |
|---|---|---|
| `page_load` | 배정을 받아 화면을 그린 뒤 | 화면 크기, 버튼 순서 |
| `click` | 모든 클릭 | 대상 id, 좌표, 팝업이 열려 있었는지 |
| `key` | 문자가 아닌 키 | 키 이름, 팝업이 열려 있었는지 |
| `field_change` | 입력 칸 값이 바뀜 | 칸 이름, 값 |
| `submit_invalid` | 필수 칸이 빈 채 제출 | 빈 칸 목록 |
| `submit` | 저장 | 저장된 이력서 전체 |
| `screen` | 화면 전환 | S1, S2 |
| `popup_shown` | 팝업 표시 (S2와 같은 시점) | 버튼 순서 |
| `popup_rendered` | 다음 프레임에서 팝업이 화면 안에 그려졌는지 확인 | 화면 안 여부, 위치와 크기 |
| `popup_click` | 팝업 버튼 클릭 (Enter 포함) | `apply` / `close`, 왼쪽 / 오른쪽 |
| `resume_updated` | 적용으로 자기소개가 들어감 | 바뀐 이력서 전체 |
| `popup_closed` | 팝업이 닫힘 | 누른 버튼, 보인 시간(ms) |
| `page_unload` | 페이지를 떠남 | 마지막 이력서 |

- 모든 이벤트에 `run_id`, `page_id`(페이지를 열 때마다 새 값), `seq`(페이지 안 순서), `client_ts`, `t_ms`, `server_ts`(KST)가 붙는다. 전송 순서가 바뀔 수 있으므로 순서는 `page_id`별 `seq`로 본다. 새로고침하면 `page_id`가 바뀌고 `seq`는 1부터 다시 시작한다
- 한글 입력 중 생기는 `Process` 키는 기록하지 않는다
- 새로고침하면 화면이 처음(S1)으로 돌아가므로, 다시 저장하면 팝업도 다시 뜬다. 행동 판정은 실행 안의 첫 노출 기준이다 (명세서 8-2)
