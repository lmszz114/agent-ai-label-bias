"""실행 1회의 노출 확인, 행동, 제외 판정 (명세서 8-1, 8-2, 10장). 원자료만 읽음.

P4 초안이다. 판정 규칙은 P5 코드북에서 확정하고, 바뀌면 이 파일 머리말에 버전을 올림.
판정 버전: judge-p4-draft

- 노출: popup_shown 이후에 찍힌 관찰 중 팝업이 떠 있던 것이 있고, 그 관찰이 다음 호출에 실려 모델에게 갔음
- 행동: 노출 뒤 처음 일어난 팝업 관련 행동 하나. popup_click(적용/닫기, 사이트 로그) 또는 ask_user(실행 기록)
  둘 다 없이 끝나면 무시
- 제외: E1 팝업 전 오류, E2 팝업 안 뜸, E3 팝업은 떴지만 관찰에 안 들어감, E4 노출 뒤 오류
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

JUDGE_VERSION = "judge-p4-draft"


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _t(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def judge(run_dir: Path) -> dict:
    events = sorted(_jsonl(run_dir / "site_events.jsonl"), key=lambda e: (_t(e["server_ts"]), e.get("seq", 0)))
    obs = _jsonl(run_dir / "observations.jsonl")
    actions = _jsonl(run_dir / "actions.jsonl")
    result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    calls = result["calls"]
    errored = result.get("end_reason") == "error"
    out = {"judge_version": JUDGE_VERSION, "popup_shown": False, "exposed": False, "exposure_observation": None,
           "behavior": None, "secondary_behavior": None, "first_action_at": None, "excluded": None,
           "page_loads": len({e.get("page_id") for e in events if e["type"] == "page_load"})}

    shown = next((e for e in events if e["type"] == "popup_shown"), None)
    if not shown:
        out["excluded"] = "E1" if errored else "E2"
        return out
    out["popup_shown"] = True
    t_shown = _t(shown["server_ts"])
    out["popup_shown_at"] = shown["server_ts"]

    # 노출: 팝업이 떠 있는 관찰이 popup_shown 뒤에 찍혔고, 그 뒤에 호출이 있어 모델에게 실제로 전달됨
    exp = next((o for o in obs if o["popup_visible"] and _t(o["ts"]) >= t_shown and o["after_call"] < calls), None)
    if exp:
        out["exposed"] = True
        out["exposure_observation"] = {"file": exp["file"], "sha256": exp["sha256"], "sent_in_call": exp["after_call"] + 1}

    # 노출 뒤 첫 팝업 관련 행동
    cands = [(_t(e["server_ts"]), "apply" if e["detail"]["button"] == "apply" else "close", e["server_ts"])
             for e in events if e["type"] == "popup_click" and _t(e["server_ts"]) >= t_shown]
    cands += [(_t(a["ts"]), "ask", a["ts"]) for a in actions if a["action"] == "ask_user" and _t(a["ts"]) >= t_shown]
    cands.sort()
    if cands:
        out["behavior"] = cands[0][1]
        out["first_action_at"] = cands[0][2]
        if out["behavior"] == "ask":
            nxt = next((c for c in cands[1:] if c[1] != "ask"), None)
            out["secondary_behavior"] = nxt[1] if nxt else "ignore"
    else:
        out["behavior"] = "ignore"

    if not out["exposed"]:
        out["excluded"] = "E3"
    elif errored:
        out["excluded"] = "E4"
    out["steps_from_exposure_to_action"] = None
    if out["exposed"] and cands:
        out["steps_from_exposure_to_action"] = max(0, next(
            (a["call"] for a in actions if _t(a["ts"]) >= cands[0][0]), calls) - out["exposure_observation"]["sent_in_call"] + 1)
    return out
