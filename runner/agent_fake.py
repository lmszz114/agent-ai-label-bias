"""가짜 모델 (정해진 행동만 하는 대역, workplan P4 게이트 1). 시험용이며 결과에 쓰지 않음.

- API를 부르지 않음. 대신 실제 모델과 같은 동작 이름(left_click, type, screenshot 등)을 만들어
  Anthropic 연결부와 같은 execute()로 브라우저를 조작함. 기록 형식도 같음 (calls/는 fake 표시)
- 좌표는 목업 DOM에서 직접 읽음 (대역이므로 화면을 보고 판단하지 않음)
- 팝업 행동은 배정의 fake_behavior로 정함: apply, close, ask_then_close, ignore, no_submit(제외 규칙 E2 시험)
"""

from __future__ import annotations

from agent_anthropic import execute
from common import Browser, Ledger, Run, mockup

FIELDS = ["name", "job", "company", "period", "duty", "school", "major", "skills"]


def _center(browser: Browser, selector: str) -> list[int]:
    b = browser.page.locator(selector).bounding_box()
    return [int(b["x"] + b["width"] / 2), int(b["y"] + b["height"] / 2)]


def _plan(browser: Browser, run: Run) -> list[dict]:
    """호출(단계)별 행동 목록. 각 단계는 실제 모델의 응답 1개에 해당."""
    p = mockup.profile_for(run.assignment["content_id"])
    vals = {"name": p["name"], "job": p["job"], "company": p["career"]["company"], "period": p["career"]["period"],
            "duty": p["career"]["duty"], "school": p["education"]["school"], "major": p["education"]["major"],
            "skills": p["skills"]}
    fill = []
    for f in FIELDS:
        fill += [{"name": "left_click", "input": {"coordinate": _center(browser, f"#f-{f}")}},
                 {"name": "type", "input": {"text": vals[f]}}]
    return [
        {"actions": [{"name": "screenshot", "input": {}}]},
        {"actions": fill},
        {"actions": [{"name": "left_click", "input": {"coordinate": _center(browser, "#btn-submit")}},
                     {"name": "screenshot", "input": {}}]},
    ]


def _popup_step(browser: Browser, behavior: str) -> list[dict]:
    if behavior == "apply":
        return [{"actions": [{"name": "left_click", "input": {"coordinate": _center(browser, "#btn-apply")}},
                             {"name": "screenshot", "input": {}}]}]
    if behavior == "close":
        return [{"actions": [{"name": "left_click", "input": {"coordinate": _center(browser, "#btn-close")}},
                             {"name": "screenshot", "input": {}}]}]
    if behavior == "ask_then_close":
        return [{"actions": [{"name": "ask_user", "input": {"question": "(가짜 모델) 팝업 문구를 적용할까요?"}}]},
                {"actions": [{"name": "left_click", "input": {"coordinate": _center(browser, "#btn-close")}},
                             {"name": "screenshot", "input": {}}]}]
    if behavior == "ignore":
        return []
    raise ValueError(f"알 수 없는 fake_behavior: {behavior}")


def run_once(run: Run, ledger: Ledger) -> dict:
    browser = Browser(run)
    refs: dict[str, str] = {}
    behavior = run.assignment.get("fake_behavior", "close")
    outcome = {"end_reason": None, "final_text": None, "ask_user_calls": [], "refusal": None,
               "served_models": [run.cfg["model"]["id"]], "fake_behavior": behavior}
    try:
        steps = _plan(browser, run)
        if behavior == "no_submit":   # 제외 규칙 E2 시험: 작성완료를 누르지 않고 끝냄
            steps = steps[:2]
        i = 0
        while True:
            if i == len(steps) and i == 3:
                steps += _popup_step(browser, behavior)   # 팝업 좌표는 팝업이 뜬 뒤에 읽음
            if run.call_no >= run.cfg["episode"]["max_steps"]:
                outcome["end_reason"] = "max_steps"; break
            if i >= len(steps):
                text = f"(가짜 모델) 이력서를 작성완료했습니다. 팝업 행동: {behavior}"
                run.log_call({"fake": True, "step": i + 1}, {"fake": True, "text": text, "actions": []}, None)
                outcome["end_reason"] = "completed"; outcome["final_text"] = text
                break
            step = steps[i]
            call_no = run.log_call({"fake": True, "step": i + 1}, {"fake": True, "actions": step["actions"]}, None)
            ledger.add(run.run_id, call_no, run.cfg["model"]["id"], 0.0, {})
            for a in step["actions"]:
                if a["name"] == "ask_user":
                    answer = run.prompts["user_sim"]["text"]
                    outcome["ask_user_calls"].append({"call": call_no, "question": a["input"]["question"]})
                    run.log_action("ask_user", a["input"], f"answered: {answer}")
                    continue
                execute(browser, a["name"], a["input"], refs)
                run.log_action(a["name"], a["input"], "ok")
            i += 1
    except Exception as err:
        outcome["end_reason"] = "error"; outcome["error"] = f"{type(err).__name__}: {err}"
    finally:
        blocked = list(browser.blocked)
        browser.close()
    run.finish(outcome, {"blocked_requests": blocked, "provider_notes": "가짜 모델. API 호출 없음. 시험용"})
    return outcome
