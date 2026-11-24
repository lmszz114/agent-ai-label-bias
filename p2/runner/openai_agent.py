"""OpenAI 연결부: Responses API + computer 도구.

- 모델: gpt-6.2-sol (날짜 고정 ID 없음. 응답의 model 필드를 매번 기록)
- 대화는 previous_response_id로 이어감 (store 기본값 true). instructions는 매 호출 다시 보냄
- pending_safety_checks: P2에서는 자동 확인(acknowledge)하고 모두 기록함 (p2-candidates.md F2)
"""

from __future__ import annotations

import json

from openai import OpenAI

from common import (ASK_USER_DESCRIPTION, SYSTEM_PROMPT, TASK_PROMPT, USER_SIM_ANSWER, Browser, Ledger, Run,
                    cost_of)

MODEL = "gpt-6.2-sol"

TOOLS = [
    {"type": "computer"},
    {"type": "function", "name": "ask_user", "description": ASK_USER_DESCRIPTION, "strict": True,
     "parameters": {"type": "object", "properties": {"question": {"type": "string"}},
                    "required": ["question"], "additionalProperties": False}},
]

KEYMAP = {"ENTER": "Enter", "RETURN": "Enter", "CTRL": "Control", "CONTROL": "Control", "ALT": "Alt",
          "SHIFT": "Shift", "ESC": "Escape", "ESCAPE": "Escape", "TAB": "Tab", "BACKSPACE": "Backspace",
          "DELETE": "Delete", "SPACE": " ", "CMD": "Meta", "META": "Meta", "SUPER": "Meta",
          "UP": "ArrowUp", "DOWN": "ArrowDown", "LEFT": "ArrowLeft", "RIGHT": "ArrowRight",
          "ARROWUP": "ArrowUp", "ARROWDOWN": "ArrowDown", "ARROWLEFT": "ArrowLeft", "ARROWRIGHT": "ArrowRight"}
BUTTONS = {"left": "left", "right": "right", "wheel": "middle"}


def _k(name: str) -> str:
    return KEYMAP.get(name.upper(), name)


def execute(browser: Browser, a) -> None:
    page = browser.page
    t = a.type
    mods = [_k(x) for x in (getattr(a, "keys", None) or [])] if t != "keypress" else []
    for m in mods:
        page.keyboard.down(m)
    try:
        if t == "click":
            if a.button not in BUTTONS:
                raise ValueError(f"지원하지 않는 버튼: {a.button}")
            page.mouse.click(a.x, a.y, button=BUTTONS[a.button])
        elif t == "double_click":
            page.mouse.dblclick(a.x, a.y)
        elif t == "move":
            page.mouse.move(a.x, a.y)
        elif t == "scroll":
            page.mouse.move(a.x, a.y); page.mouse.wheel(a.scroll_x, a.scroll_y)
        elif t == "drag":
            pts = [(p.x, p.y) if hasattr(p, "x") else tuple(p) for p in a.path]
            page.mouse.move(*pts[0]); page.mouse.down()
            for p in pts[1:]:
                page.mouse.move(*p)
            page.mouse.up()
        elif t == "keypress":
            page.keyboard.press("+".join(_k(x) for x in a.keys))
        elif t == "type":
            page.keyboard.type(a.text)
        elif t == "wait":
            page.wait_for_timeout(1000)
        elif t == "screenshot":
            pass
        else:
            raise ValueError(f"알 수 없는 동작: {t}")
    finally:
        for m in reversed(mods):
            page.keyboard.up(m)
    page.wait_for_timeout(300)


def _redact(inputs, image_refs: dict):
    out = json.loads(json.dumps(inputs, default=str))
    for item in out if isinstance(out, list) else []:
        o = item.get("output") if isinstance(item, dict) else None
        if isinstance(o, dict) and str(o.get("image_url", "")).startswith("data:image"):
            o["image_url"] = image_refs.get(o["image_url"], "sha256:unknown")
    return out


def run_once(run: Run, ledger: Ledger, max_calls: int, max_seconds: float) -> dict:
    client = OpenAI()
    browser = Browser(run)
    image_refs: dict[str, str] = {}
    outcome = {"end_reason": None, "final_text": None, "ask_user_calls": [], "safety_checks": []}
    next_input = TASK_PROMPT
    prev_id = None
    try:
        while True:
            if run.call_no >= max_calls:
                outcome["end_reason"] = "max_calls"; break
            if run.elapsed() >= max_seconds:
                outcome["end_reason"] = "max_time"; break
            ledger.check()
            request = {"model": MODEL, "instructions": SYSTEM_PROMPT, "tools": TOOLS, "input": next_input}
            if prev_id:
                request["previous_response_id"] = prev_id
            resp = client.responses.create(**request)
            call_no = run.log_call({**request, "input": _redact(next_input, image_refs)},
                                   resp.model_dump(mode="json"), resp._request_id)
            u = resp.usage
            cached = (u.input_tokens_details.cached_tokens or 0) if u.input_tokens_details else 0
            usage = {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens, "cached_tokens": cached,
                     "reasoning_tokens": (u.output_tokens_details.reasoning_tokens or 0) if u.output_tokens_details else 0,
                     "served_model": resp.model}
            # 캐시된 입력은 cache_read 단가, 나머지는 input 단가
            ledger.add(run.run_id, call_no, MODEL, cost_of(MODEL, u.input_tokens - cached, u.output_tokens, cached)["cost_usd"], usage)
            prev_id = resp.id

            if resp.status != "completed":
                outcome["end_reason"] = f"status_{resp.status}"
                outcome["detail"] = resp.incomplete_details.model_dump() if resp.incomplete_details else None
                break

            outs = []
            for item in resp.output:
                if item.type == "computer_call":
                    checks = [c.model_dump() for c in (item.pending_safety_checks or [])]
                    if checks:
                        outcome["safety_checks"].append({"call": call_no, "checks": checks})
                        run.log_action("provider_safety_check", {"checks": checks}, "auto_acknowledged")
                    for a in (item.actions or ([item.action] if getattr(item, "action", None) else [])):
                        try:
                            execute(browser, a)
                            run.log_action(a.type, a.model_dump(), "ok")
                        except Exception as err:
                            run.log_action(a.type, a.model_dump(), f"error: {err}")
                    b64, ref = browser.screenshot_b64()
                    url = f"data:image/png;base64,{b64}"
                    image_refs[url] = ref
                    out = {"type": "computer_call_output", "call_id": item.call_id,
                           "output": {"type": "computer_screenshot", "image_url": url, "detail": "original"}}
                    if checks:
                        out["acknowledged_safety_checks"] = checks
                    outs.append(out)
                elif item.type == "function_call" and item.name == "ask_user":
                    args = json.loads(item.arguments)
                    outcome["ask_user_calls"].append({"call": call_no, "question": args.get("question")})
                    run.log_action("ask_user", args, f"answered: {USER_SIM_ANSWER}")
                    outs.append({"type": "function_call_output", "call_id": item.call_id, "output": USER_SIM_ANSWER})

            if not outs:
                outcome["end_reason"] = "completed"; outcome["final_text"] = resp.output_text
                break
            next_input = outs
    except Exception as err:
        outcome["end_reason"] = "error"; outcome["error"] = f"{type(err).__name__}: {err}"
    finally:
        blocked = browser.blocked
        browser.close()
    run.finish(outcome, {"tools": TOOLS, "blocked_requests": blocked,
                         "provider_notes": "날짜 고정 모델 ID 없음(응답 model 필드 기록). safety check는 자동 확인 후 기록."})
    return outcome
