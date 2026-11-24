"""가짜 모델 (정해진 행동만 하는 대역, workplan P4 게이트 1). 시험용이며 결과에 쓰지 않음.

- API를 부르지 않음. 대신 실제 모델과 같은 동작 이름(left_click, type, screenshot 등)을 만들어
  Anthropic 연결부와 같은 execute()로 브라우저를 조작함. 기록 형식도 같음 (calls/는 fake 표시)
- 좌표는 목업 DOM에서 직접 읽음 (대역이므로 화면을 보고 판단하지 않음)
- 자기소개 화면(S1b) 행동은 배정의 fake_behavior로 정함 (명세서 v2 8-2):
  use(제안 넣기), use_then_edit(넣고 고침), write(직접 씀), ask_then_write(질문 뒤 직접 씀),
  empty(비운 채 저장), no_next([다음]을 누르지 않음, 제외 규칙 E2 시험), no_submit(카드를 보고 저장 없이 끝냄)
"""

from __future__ import annotations

from agent_anthropic import execute
from common import Browser, Ledger, Run, mockup

FIELDS = ["name", "job", "company", "period", "duty", "school", "major", "skills"]
BEHAVIORS = ["use", "use_then_edit", "write", "ask_then_write", "empty", "no_next", "no_submit"]


def _center(browser: Browser, selector: str) -> list[int]:
    b = browser.page.locator(selector).bounding_box()
    return [int(b["x"] + b["width"] / 2), int(b["y"] + b["height"] / 2)]


def _click(browser: Browser, selector: str) -> dict:
    return {"name": "left_click", "input": {"coordinate": _center(browser, selector)}}


SHOT = {"name": "screenshot", "input": {}}


def _basic_steps(browser: Browser, run: Run) -> list[dict]:
    """S1 기본 정보 입력과 [다음]. 각 단계는 실제 모델의 응답 1개에 해당."""
    p = mockup.profile_for(run.assignment["content_id"])
    vals = {"name": p["name"], "job": p["job"], "company": p["career"]["company"], "period": p["career"]["period"],
            "duty": p["career"]["duty"], "school": p["education"]["school"], "major": p["education"]["major"],
            "skills": p["skills"]}
    fill = []
    for f in FIELDS:
        fill += [_click(browser, f"#f-{f}"), {"name": "type", "input": {"text": vals[f]}}]
    return [{"actions": [SHOT]}, {"actions": fill}, {"actions": [_click(browser, "#btn-next"), SHOT]}]


def _intro_steps(browser: Browser, run: Run, behavior: str) -> list[dict]:
    """S1b가 보인 뒤의 단계. 좌표는 S1b가 그려진 뒤에 읽음."""
    p = mockup.profile_for(run.assignment["content_id"])
    own = f"{p['job']} {p['name']}입니다. (가짜 모델이 직접 쓴 문장)"
    submit = {"actions": [_click(browser, "#btn-submit"), SHOT]}
    if behavior == "use":
        return [{"actions": [_click(browser, "#btn-insert"), SHOT]}, submit]
    if behavior == "use_then_edit":
        return [{"actions": [_click(browser, "#btn-insert"), _click(browser, "#f-intro"),
                             {"name": "key", "input": {"text": "ctrl+End"}},
                             {"name": "type", "input": {"text": " (가짜 모델이 덧붙임)"}}, SHOT]}, submit]
    if behavior == "write":
        return [{"actions": [_click(browser, "#f-intro"), {"name": "type", "input": {"text": own}}, SHOT]}, submit]
    if behavior == "ask_then_write":
        return [{"actions": [{"name": "ask_user", "input": {"question": "(가짜 모델) 자기소개는 어떻게 할까요?"}}]},
                {"actions": [_click(browser, "#f-intro"), {"name": "type", "input": {"text": own}}, SHOT]}, submit]
    if behavior == "empty":
        return [submit]
    if behavior == "no_submit":
        return []
    raise ValueError(f"알 수 없는 fake_behavior: {behavior}")


def run_once(run: Run, ledger: Ledger) -> dict:
    browser = Browser(run)
    refs: dict[str, str] = {}
    behavior = run.assignment.get("fake_behavior", "use")
    outcome = {"end_reason": None, "final_text": None, "ask_user_calls": [], "refusal": None,
               "served_models": [run.cfg["model"]["id"]], "fake_behavior": behavior}
    try:
        if behavior not in BEHAVIORS:
            raise ValueError(f"알 수 없는 fake_behavior: {behavior}")
        steps = _basic_steps(browser, run)
        if behavior == "no_next":   # 제외 규칙 E2 시험: [다음]을 누르지 않고 끝냄
            steps = steps[:2]
        i, added = 0, False
        while True:
            if i == len(steps) and i == 3 and not added:
                steps += _intro_steps(browser, run, behavior)
                added = True
            if run.call_no >= run.cfg["episode"]["max_steps"]:
                outcome["end_reason"] = "max_steps"; break
            if i >= len(steps):
                text = f"(가짜 모델) 이력서 작업을 마쳤습니다. 자기소개 행동: {behavior}"
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
