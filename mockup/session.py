"""실행 배정 파일 만들기와 풀기.

배정 파일에는 코드값(조건 코드, 내용 id, 버튼 순서)만 적고, 화면 문구는 configs/에서 읽어 옴.
P4 실행 장치는 create()를 불러 실행마다 배정 파일을 만듦.

직접 확인용:
  python -I mockup/session.py --condition ai --content p1-t1 --order close_first
  → 브라우저 주소를 출력함
"""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STATIC_DIR = REPO / "mockup" / "static"
RUNTIME = REPO / "mockup" / "runtime"
ASSIGN_DIR = RUNTIME / "assignments"
EVENT_LOG = RUNTIME / "events.jsonl"
CONDITIONS = REPO / "configs" / "conditions" / "conditions-v1.json"
CONTENT = REPO / "configs" / "content" / "content-v1.json"

# 결정적 렌더링 옵션. 이 옵션 없이는 같은 화면을 두 번 찍어도 글자 가장자리 픽셀이 0~2단계씩 달라져
# 조건 동등성을 해시로 비교할 수 없었음 (P3 검사, 2026-11-24). P4 실행 장치도 같은 값으로 브라우저를 띄움
BROWSER_ARGS = [
    "--disable-gpu", "--force-color-profile=srgb", "--disable-lcd-text", "--font-render-hinting=none",
    "--disable-partial-raster", "--disable-skia-runtime-opts", "--disable-threaded-animation",
    "--disable-threaded-scrolling", "--num-raster-threads=1",
]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def content_ids() -> list[str]:
    return [t["id"] for p in _load(CONTENT)["profiles"] for t in p["texts"]]


def create(condition: str, content_id: str, order: str, run_id: str | None = None) -> str:
    cond = _load(CONDITIONS)
    if condition not in cond["conditions"]:
        raise ValueError(f"없는 조건: {condition}")
    if order not in cond["button_orders"]:
        raise ValueError(f"없는 버튼 순서: {order}")
    if content_id not in content_ids():
        raise ValueError(f"없는 내용 id: {content_id}")
    run_id = run_id or uuid.uuid4().hex[:12]
    ASSIGN_DIR.mkdir(parents=True, exist_ok=True)
    (ASSIGN_DIR / f"{run_id}.json").write_text(json.dumps({
        "run_id": run_id, "condition": condition, "content_id": content_id, "button_order": order,
        "conditions_version": cond["version"], "content_version": _load(CONTENT)["version"],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return run_id


def resolve(run_id: str) -> dict:
    """페이지에 넘길 값. 조건 코드는 넘기지 않고 화면에 그릴 문구만 넘김."""
    a = _load(ASSIGN_DIR / f"{run_id}.json")
    badge = _load(CONDITIONS)["conditions"][a["condition"]]["badge"]
    text = next(t["text"] for p in _load(CONTENT)["profiles"] for t in p["texts"] if t["id"] == a["content_id"])
    return {"run_id": run_id, "badge": badge, "popup_text": text, "button_order": a["button_order"]}


def profile_for(content_id: str) -> dict:
    return next(p for p in _load(CONTENT)["profiles"] if any(t["id"] == content_id for t in p["texts"]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", required=True)
    ap.add_argument("--content", required=True)
    ap.add_argument("--order", required=True)
    ap.add_argument("--run-id")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    rid = create(a.condition, a.content, a.order, a.run_id)
    print(f"http://127.0.0.1:{a.port}/?s={rid}")
