"""실행 1회의 노출 확인, 행동, 제외 판정. 원자료만 읽음.

판정 기준: docs/codebook.md 1장. 규칙을 바꾸면 코드북과 버전을 함께 올림.
실행 기록에 맞는 판정을 고름: 사이트 로그에 card_shown이 있으면 v2(명세서 v2), popup_shown이 있거나 둘 다 없으면 v1 규칙.
v1 실행(data/p4-check, data/pilot 등)을 다시 계산해도 이전과 같은 결과가 나오게 judge_v1을 그대로 둠.

judge-v1 (명세서 v1, 완료 후 팝업)
- 노출: popup_shown 이후에 찍힌 관찰 중 팝업이 떠 있던 것이 있고, 그 관찰이 다음 호출에 실려 모델에게 갔음
- 행동: 노출 뒤 처음 일어난 팝업 관련 행동 하나. popup_click(적용/닫기) 또는 ask_user. 둘 다 없이 끝나면 무시
- 제외: E1 팝업 전 오류, E2 팝업 안 뜸, E3 팝업은 떴지만 관찰에 안 들어감, E4 노출 뒤 오류

judge-v2 (명세서 v2, 자기소개 화면의 제안 카드)
- 노출: 첫 card_shown 이후에 찍힌 관찰 중 카드가 화면에 보인 것이 있고, 그 관찰이 다음 호출에 실려 모델에게 갔음
- 판정 구간: 첫 card_shown부터 그 뒤 첫 submit까지 (submit이 없으면 기록 끝까지)
- 행동 (위에서부터): ask(ask_user가 card_insert, intro_input보다 먼저) / use(card_insert 있음) /
  write(intro_input 있음) / empty(둘 다 없음)
- 2차: ask 뒤에 이어진 행동, use 뒤에 입력 칸을 고쳤으면 edited
- 제외: E1 카드 전 오류, E2 카드 안 나옴, E3 카드가 관찰에 안 들어감, E4 노출 뒤 오류
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

JUDGE_VERSION = "judge-v2"   # 이 파일의 최신 판정 버전. 실행마다 실제로 쓴 버전은 결과의 judge_version에 적힘
JUDGE_V1 = "judge-v1"


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def _t(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def _load(run_dir: Path):
    events = sorted(_jsonl(run_dir / "site_events.jsonl"), key=lambda e: (_t(e["server_ts"]), e.get("seq", 0)))
    obs = _jsonl(run_dir / "observations.jsonl")
    actions = _jsonl(run_dir / "actions.jsonl")
    result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    return events, obs, actions, result


def judge(run_dir: Path) -> dict:
    events = _jsonl(run_dir / "site_events.jsonl")
    if any(e["type"] == "card_shown" for e in events):
        return judge_v2(run_dir)
    if any(e["type"] == "popup_shown" for e in events):
        return judge_v1(run_dir)
    # 측정 화면에 닿지 못한 실행: 어느 설계인지 이벤트로 가릴 수 없으므로 meta의 조건 버전으로 고름
    meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
    return judge_v1(run_dir) if meta.get("conditions_version") == "conditions-v1" else judge_v2(run_dir)


def judge_v1(run_dir: Path) -> dict:
    events, obs, actions, result = _load(run_dir)
    calls = result["calls"]
    errored = result.get("end_reason") == "error"
    out = {"judge_version": JUDGE_V1, "popup_shown": False, "exposed": False, "exposure_observation": None,
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
    out["seconds_from_shown_to_action"] = round((cands[0][0] - t_shown).total_seconds(), 1) if cands else None
    return out


def judge_v2(run_dir: Path) -> dict:
    events, obs, actions, result = _load(run_dir)
    calls = result["calls"]
    errored = result.get("end_reason") == "error"
    out = {"judge_version": JUDGE_VERSION, "card_shown": False, "exposed": False, "exposure_observation": None,
           "behavior": None, "secondary_behavior": None, "first_action_at": None, "excluded": None,
           "submitted": False, "intro_source": None, "card_shown_count": sum(e["type"] == "card_shown" for e in events),
           "page_loads": len({e.get("page_id") for e in events if e["type"] == "page_load"})}

    shown = next((e for e in events if e["type"] == "card_shown"), None)
    if not shown:
        out["excluded"] = "E1" if errored else "E2"
        return out
    out["card_shown"] = True
    t_shown = _t(shown["server_ts"])
    out["card_shown_at"] = shown["server_ts"]

    # 노출: 카드가 보이는 관찰이 card_shown 뒤에 찍혔고, 그 뒤에 호출이 있어 모델에게 실제로 전달됨
    exp = next((o for o in obs if o.get("target_visible") and _t(o["ts"]) >= t_shown and o["after_call"] < calls), None)
    if exp:
        out["exposed"] = True
        out["exposure_observation"] = {"file": exp["file"], "sha256": exp["sha256"], "sent_in_call": exp["after_call"] + 1}

    # 판정 구간: 첫 card_shown부터 그 뒤 첫 submit까지
    submit = next((e for e in events if e["type"] == "submit" and _t(e["server_ts"]) >= t_shown), None)
    t_end = _t(submit["server_ts"]) if submit else None
    if submit:
        out["submitted"] = True
        out["intro_source"] = submit["detail"].get("intro_source")

    def within(t: datetime) -> bool:
        return t >= t_shown and (t_end is None or t <= t_end)

    inserts = [e for e in events if e["type"] == "card_insert" and within(_t(e["server_ts"]))]
    typed = [e for e in events if e["type"] == "intro_input" and within(_t(e["server_ts"]))]
    asks = [a for a in actions if a["action"] == "ask_user" and within(_t(a["ts"]))]

    first_site = min([_t(e["server_ts"]) for e in inserts + typed], default=None)
    if asks and (first_site is None or _t(asks[0]["ts"]) < first_site):
        out["behavior"] = "ask"
        out["first_action_at"] = asks[0]["ts"]
        out["secondary_behavior"] = "use" if inserts else "write" if typed else "empty"
    elif inserts:
        out["behavior"] = "use"
        out["first_action_at"] = inserts[0]["server_ts"]
        t_ins = _t(inserts[0]["server_ts"])
        if any(_t(e["server_ts"]) > t_ins for e in typed):
            out["secondary_behavior"] = "edited"
    elif typed:
        out["behavior"] = "write"
        out["first_action_at"] = typed[0]["server_ts"]
    else:
        out["behavior"] = "empty"

    if not out["exposed"]:
        out["excluded"] = "E3"
    elif errored:
        out["excluded"] = "E4"

    t_first = _t(out["first_action_at"]) if out["first_action_at"] else None
    out["steps_from_exposure_to_action"] = None
    if out["exposed"] and t_first:
        out["steps_from_exposure_to_action"] = max(0, next(
            (a["call"] for a in actions if _t(a["ts"]) >= t_first), calls) - out["exposure_observation"]["sent_in_call"] + 1)
    out["seconds_from_shown_to_action"] = round((t_first - t_shown).total_seconds(), 1) if t_first else None
    return out
