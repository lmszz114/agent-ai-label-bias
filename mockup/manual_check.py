"""P3 게이트 2: 사람이 직접 눌러 보는 검사 도우미 (명세서 v2).

1) 배정 만들기:  .venv/Scripts/python.exe mockup/manual_check.py start
   → 조건 2 × 카드 위치 2 = 4개 주소를 출력하고 mockup/runtime/manual_check.json에 저장
2) 브라우저에서 각 주소를 열고 안내대로 조작
3) 기록 보기:    .venv/Scripts/python.exe mockup/manual_check.py show
   → 주소별로 사이트 로그를 사람이 읽기 쉬운 줄로 출력. 내가 한 행동과 같은지 대조
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import session as S  # noqa: E402

PLAN = S.RUNTIME / "manual_check.json"
KST = timezone(timedelta(hours=9))
# 조건과 카드 위치를 모두 한 번씩. 자기소개 행동(제안 넣기 / 직접 쓰기)도 섞어서 두 경우를 모두 확인
CASES = [("ai", "card_above", "제안 넣기"), ("ai", "card_below", "직접 쓰기"),
         ("auto", "card_above", "직접 쓰기"), ("auto", "card_below", "제안 넣기")]


def start():
    tag = datetime.now(KST).strftime("%m%d%H%M")
    plan = []
    for i, (cond, layout, todo) in enumerate(CASES, 1):
        rid = S.create(cond, "p2-t1", layout, run_id=f"manual-{tag}-{i}")
        plan.append({"no": i, "run_id": rid, "condition": cond, "layout": layout, "todo": todo,
                     "url": f"http://127.0.0.1:8765/?s={rid}"})
    PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print("각 주소를 브라우저에서 열고 아래 순서로 조작하세요.\n"
          "  a. 아무것도 입력하지 않고 [다음] → 빈 칸이 빨갛게 되고 넘어가지 않는지\n"
          "  b. 필수 칸을 아무 값으로 채우고 [다음] → 자기소개 화면과 제안 카드가 함께 보이는지\n"
          "  c. '할 일'대로: 제안 넣기 = [이 문구 넣기] 클릭 / 직접 쓰기 = 자기소개 칸에 아무 글이나 입력\n"
          "  d. [작성완료] → 저장 화면 요약에 c에서 넣은 자기소개가 보이는지\n")
    for p in plan:
        print(f"{p['no']}. {p['url']}   할 일: {p['todo']}")


def show():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    events = [json.loads(l) for l in S.EVENT_LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    for p in plan:
        ev = [e for e in events if e["run_id"] == p["run_id"]]
        print(f"\n=== {p['no']}. 조건 {p['condition']}, 카드 위치 {p['layout']}, 할 일 {p['todo']} ===")
        # 페이지를 연 순서대로, 각 페이지 안에서는 seq 순서로
        pages = sorted({e.get("page_id", "?") for e in ev},
                       key=lambda pid: min(x["server_ts"] for x in ev if x.get("page_id", "?") == pid))
        for n, pid in enumerate(pages, 1):
            print(f"  -- 페이지 {n}번째 열기 (page_id {pid}) --")
            for e in sorted((x for x in ev if x.get("page_id", "?") == pid), key=lambda x: x["seq"]):
                show_one(e)
        if not ev:
            print("  (기록 없음: 아직 열지 않았거나 서버가 꺼져 있음)")


def show_one(e: dict) -> None:
    d = e["detail"]
    if e["type"] in ("page_unload", "key"):
        return
    if e["type"] == "click":
        msg = f"클릭 {d['target']} ({d['x']},{d['y']})"
    elif e["type"] == "field_change":
        msg = f"입력 {d['field']} = {d['value'][:20]}"
    elif e["type"] == "submit":
        msg = f"저장 자기소개={'있음' if d['resume']['intro'] else '없음'}, 출처={d['intro_source']}"
    elif e["type"] == "next":
        msg = "다음 (기본 정보 통과)"
    else:
        msg = f"{e['type']} {json.dumps(d, ensure_ascii=False)}"
    print(f"    {e['seq']:>3} {e['server_ts'][11:23]} {msg}")


if __name__ == "__main__":
    {"start": start, "show": show}[sys.argv[1] if len(sys.argv) > 1 else "start"]()
