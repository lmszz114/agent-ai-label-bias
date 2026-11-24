"""Anthropic 연결부: Messages API + computer_toolset_20260801.

- 모델: claude-sonnet-5-5, 사고(thinking)는 모델 기본(adaptive), effort는 high로 명시
- 응답 content는 그대로 대화에 붙임 (preserved thinking: 이전 내용을 고치거나 빼지 않음)
- 거절(refusal)이 와도 다른 모델로 넘기지 않음. 실험 중 모델이 바뀌면 안 되므로 그대로 기록하고 끝냄
- 회사 쪽 프롬프트 주입 분류기는 끌 수 없음. 응답에 드러나는 신호(stop_reason 등)는 원문에 그대로 남음
"""

from __future__ import annotations

import time

import anthropic

from common import (ASK_USER_DESCRIPTION, SYSTEM_PROMPT, TASK_PROMPT, USER_SIM_ANSWER, Browser, Ledger, Run,
                    cost_of, to_playwright_key)

MODEL = "claude-sonnet-5-5"
EFFORT = "high"
MAX_TOKENS = 16000

TOOLS = [
    {"type": "computer_toolset_20260801"},
    {
        "name": "ask_user",
        "description": ASK_USER_DESCRIPTION,
        "strict": True,
        "input_schema": {"type": "object", "properties": {"question": {"type": "string"}},
                         "required": ["question"], "additionalProperties": False},
    },
]


def _dump(obj):
    return obj.model_dump(mode="json") if hasattr(obj, "model_dump") else obj


def _redact_images(value, image_refs: dict):
    """요청 기록용: base64 이미지를 스크린샷 파일 해시로 바꿈."""
    if isinstance(value, dict):
        if value.get("type") == "base64" and "data" in value:
            return {**value, "data": image_refs.get(value["data"], "sha256:unknown")}
        return {k: _redact_images(v, image_refs) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_images(v, image_refs) for v in value]
    return value


def _mods(text: str | None) -> list[str]:
    return [to_playwright_key(m) for m in (text or "").split("+") if m.strip()]


def execute(browser: Browser, name: str, inp: dict) -> list | str:
    page = browser.page
    coord = inp.get("coordinate")
    if name == "screenshot":
        b64, ref = browser.screenshot_b64()
        browser.last_ref = (b64, ref)
        return [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}}]
    if name == "zoom":
        x0, y0, x1, y1 = inp["region"]
        png = page.screenshot(type="png", clip={"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0})
        fname, digest = browser.run.save_screenshot(png)
        import base64
        b64 = base64.b64encode(png).decode("ascii")
        browser.last_ref = (b64, f"sha256:{digest} ({fname})")
        return [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}}]
    if coord:
        page.mouse.move(*coord)
        browser.cursor = tuple(coord)
    mods = _mods(inp.get("text")) if name.endswith("click") or name == "scroll" else []
    for m in mods:
        page.keyboard.down(m)
    try:
        if name in ("left_click", "right_click", "middle_click"):
            page.mouse.click(*browser.cursor, button={"left_click": "left", "right_click": "right", "middle_click": "middle"}[name])
        elif name == "double_click":
            page.mouse.dblclick(*browser.cursor)
        elif name == "triple_click":
            page.mouse.click(*browser.cursor, click_count=3)
        elif name == "left_click_drag":
            page.mouse.move(*inp["start_coordinate"]); page.mouse.down()
            page.mouse.move(*inp["coordinate"]); page.mouse.up()
            browser.cursor = tuple(inp["coordinate"])
        elif name == "mouse_move":
            pass
        elif name == "left_mouse_down":
            page.mouse.down()
        elif name == "left_mouse_up":
            page.mouse.up()
        elif name == "cursor_position":
            return f"X={browser.cursor[0]},Y={browser.cursor[1]}"
        elif name == "scroll":
            amount = int(inp.get("scroll_amount", 3)) * 100
            dx, dy = {"up": (0, -amount), "down": (0, amount), "left": (-amount, 0), "right": (amount, 0)}[inp["scroll_direction"]]
            page.mouse.wheel(dx, dy)
        elif name == "type":
            page.keyboard.type(inp["text"])
        elif name == "key":
            for _ in range(int(inp.get("repeat", 1))):
                page.keyboard.press(to_playwright_key(inp["text"]))
        elif name == "hold_key":
            key = to_playwright_key(inp["text"])
            page.keyboard.down(key); time.sleep(float(inp["duration"])); page.keyboard.up(key)
        elif name == "wait":
            time.sleep(min(float(inp.get("duration", 1)), 10))
        else:
            raise ValueError(f"알 수 없는 동작: {name}")
    finally:
        for m in reversed(mods):
            page.keyboard.up(m)
    page.wait_for_timeout(300)
    return "OK"


def run_once(run: Run, ledger: Ledger, max_calls: int, max_seconds: float) -> dict:
    client = anthropic.Anthropic()
    browser = Browser(run)
    browser.last_ref = None
    image_refs: dict[str, str] = {}
    messages: list = [{"role": "user", "content": TASK_PROMPT}]
    outcome = {"end_reason": None, "final_text": None, "ask_user_calls": [], "refusal": None}
    try:
        while True:
            if run.call_no >= max_calls:
                outcome["end_reason"] = "max_calls"; break
            if run.elapsed() >= max_seconds:
                outcome["end_reason"] = "max_time"; break
            ledger.check()
            request = {"model": MODEL, "max_tokens": MAX_TOKENS, "system": SYSTEM_PROMPT, "tools": TOOLS,
                       "output_config": {"effort": EFFORT}, "messages": messages}
            resp = client.messages.create(**request)
            req_log = _redact_images({**request, "messages": [_dump(m) if not isinstance(m, dict) else
                                                                {**m, "content": [_dump(c) for c in m["content"]] if isinstance(m["content"], list) else m["content"]}
                                                                for m in messages]}, image_refs)
            call_no = run.log_call(req_log, resp.model_dump(mode="json"), resp._request_id)
            u = resp.usage
            usage = {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                     "cache_read_input_tokens": u.cache_read_input_tokens or 0,
                     "cache_creation_input_tokens": u.cache_creation_input_tokens or 0}
            ledger.add(run.run_id, call_no, MODEL, cost_of(MODEL, u.input_tokens, u.output_tokens,
                                                         usage["cache_read_input_tokens"], usage["cache_creation_input_tokens"])["cost_usd"], usage)
            messages.append({"role": "assistant", "content": resp.content})

            if resp.stop_reason == "refusal":
                outcome["end_reason"] = "refusal"; outcome["refusal"] = _dump(resp.stop_details); break

            results = []
            for block in resp.content:
                if block.type != "tool_use":
                    continue
                if getattr(block, "toolset_name", None) == "computer":
                    try:
                        content = execute(browser, block.name, dict(block.input))
                        if browser.last_ref and isinstance(content, list):
                            image_refs[browser.last_ref[0]] = browser.last_ref[1]; browser.last_ref = None
                        run.log_action(block.name, dict(block.input), "ok")
                        results.append({"type": "tool_result", "tool_use_id": block.id, "toolset_name": "computer", "content": content})
                    except Exception as err:  # 실패도 기록하고 모델에 알림
                        run.log_action(block.name, dict(block.input), f"error: {err}")
                        results.append({"type": "tool_result", "tool_use_id": block.id, "toolset_name": "computer",
                                        "content": f"Error: {err}", "is_error": True})
                elif block.name == "ask_user":
                    outcome["ask_user_calls"].append({"call": call_no, "question": block.input.get("question")})
                    run.log_action("ask_user", dict(block.input), f"answered: {USER_SIM_ANSWER}")
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": USER_SIM_ANSWER})

            if not results:
                outcome["end_reason"] = "completed" if resp.stop_reason == "end_turn" else f"stop_{resp.stop_reason}"
                outcome["final_text"] = "\n".join(b.text for b in resp.content if b.type == "text")
                break
            messages.append({"role": "user", "content": results})
    except Exception as err:
        outcome["end_reason"] = "error"; outcome["error"] = f"{type(err).__name__}: {err}"
    finally:
        blocked = browser.blocked
        browser.close()
    run.finish(outcome, {"effort": EFFORT, "max_tokens": MAX_TOKENS, "tools": TOOLS, "blocked_requests": blocked,
                         "provider_notes": "API가 도구 사용 시스템 프롬프트를 붙임(끌 수 없음). 프롬프트 주입 분류기 켜짐(기본)."})
    return outcome
