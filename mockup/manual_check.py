"""P3 게이트 2: 사람이 직접 눌러 보는 검사 도우미.

1) 배정 만들기:  .venv/Scripts/python.exe mockup/manual_check.py start
   → 조건 2 × 버튼 순서 2 = 4개 주소를 출력하고 mockup/runtime/manual_check.json에 저장
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
# 조건과 버튼 순서를 모두 한 번씩. 행동(닫기/적용)도 섞어서 두 경우를 모두 확인
CASES = [("ai", "close_first", "닫기"), ("ai", "apply_first", "이력서에 적용하기"),
         ("auto", "close_first", "이력서에 적용하기"), ("auto", "apply_first", "닫기")]


def start():
    tag = datetime.now(KST).strftime("%m%d%H%M")
    plan = []
    for i, (cond, order, press) in enumerate(CASES, 1):
        rid = S.create(cond, "p2-t1", order, run_id=f"manual-{tag}-{i}")
        plan.append({"no": i, "run_id": rid, "condition": cond, "order": order, "press": press,
                     "url": f"http://127.0.0.1:8765/?s={rid}"})
    PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print("각 주소를 브라우저에서 열고 아래 순서로 조작하세요.\n"
          "  a. 아무것도 입력하지 않고 [작성완료] → 빈 칸이 빨갛게 되는지\n"
          "  b. 필수 칸을 아무 값으로 채우고 [작성완료] → 저장 화면과 팝업이 함께 뜨는지\n"
          "  c. Esc 키, 팝업 바깥 어두운 곳 클릭 → 팝업이 안 닫히는지\n"
          "  d. 아래 '누를 버튼'을 클릭\n"
          "  e. 저장 화면의 요약을 확인 (적용했으면 자기소개가 보여야 함)\n")
    for p in plan:
        print(f"{p['no']}. {p['url']}   누를 버튼: [{p['press']}]")


def show():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    events = [json.loads(l) for l in S.EVENT_LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    for p in plan:
        ev = sorted((e for e in events if e["run_id"] == p["run_id"]), key=lambda e: e["seq"])
        print(f"\n=== {p['no']}. 조건 {p['condition']}, 버튼 순서 {p['order']}, 누를 버튼 [{p['press']}] ===")
        for e in ev:
            d = e["detail"]
            if e["type"] == "click":
                msg = f"클릭 {d['target']} ({d['x']},{d['y']}) 팝업{'열림' if d['popup_open'] else '닫힘'}"
            elif e["type"] == "field_change":
                msg = f"입력 {d['field']} = {d['value'][:20]}"
            elif e["type"] in ("submit", "resume_updated"):
                msg = f"{e['type']} 자기소개={'있음' if d['resume']['intro'] else '없음'}"
            elif e["type"] == "page_unload":
                continue
            else:
                msg = f"{e['type']} {json.dumps(d, ensure_ascii=False)}"
            print(f"  {e['seq']:>3} {e['server_ts'][11:23]} {msg}")
        if not ev:
            print("  (기록 없음: 아직 열지 않았거나 서버가 꺼져 있음)")


if __name__ == "__main__":
    {"start": start, "show": show}[sys.argv[1] if len(sys.argv) > 1 else "start"]()
