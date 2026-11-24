"""Anthropic 연결부: Messages API + computer_toolset_20260801 (명세서 11장).

- 모델 ID, effort, max_tokens는 실행 설정 파일에서 읽음
- 응답 content는 고치거나 빼지 않고 그대로 대화에 붙임 (preserved thinking, 스크린샷 정리 안 함)
- 거절이 와도 다른 모델로 넘기지 않음. 그대로 기록하고 끝냄
- 단계 = API 호출 1회 (명세서 9장, v1.1)
"""

from __future__ import annotations

import time

from common import Browser, Ledger, Run, cost_of, to_playwright_key


def tools(run: Run) -> list:
    return [
        {"type": "computer_toolset_20260801"},
        {"name": "ask_user", "description": run.prompts["ask_user_tool"]["text"], "strict": True,
         "input_schema": {"type": "object", "properties": {"question": {"type": "string"}},
                          "required": ["question"], "additionalProperties": False}},
    ]


def _dump(obj):
    return obj.model_dump(mode="json") if hasattr(obj, "model_dump") else obj


def _redact(value, refs: dict):
    """요청 기록용: base64 이미지를 스크린샷 파일 해시로 바꿈 (evidence.md 2장)."""
    if isinstance(value, dict):
        if value.get("type") == "base64" and "data" in value:
            return {**value, "data": refs.get(value["data"], "sha256:unknown")}
        return {k: _redact(v, refs) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v, refs) for v in value]
    return value


def _image(b64: str) -> list:
    return [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}}]


def execute(browser: Browser, name: str, inp: dict, refs: dict) -> list | str:
    page = browser.page
    if name == "screenshot":
        b64, ref = browser.observe("screenshot")
        refs[b64] = ref
        return _image(b64)
    if name == "zoom":
        x0, y0, x1, y1 = inp["region"]
        b64, ref = browser.observe("zoom", clip={"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0})
        refs[b64] = ref
        return _image(b64)
    coord = inp.get("coordinate")
    if coord:
        page.mouse.move(*coord)
        browser.cursor = tuple(coord)
    mods = [to_playwright_key(m) for m in (inp.get("text") or "").split("+") if m.strip()] \
        if (name.endswith("click") or name == "scroll") else []
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


def run_once(run: Run, ledger: Ledger) -> dict:
    import anthropic
    m = run.cfg["model"]
    max_steps, max_seconds = run.cfg["episode"]["max_steps"], run.cfg["episode"]["max_seconds"]
    client = anthropic.Anthropic()
    browser = Browser(run)
    refs: dict[str, str] = {}
    messages: list = [{"role": "user", "content": run.task}]
    outcome = {"end_reason": None, "final_text": None, "ask_user_calls": [], "refusal": None, "served_models": []}
    try:
        while True:
            if run.call_no >= max_steps:
                outcome["end_reason"] = "max_steps"; break
            if run.elapsed() >= max_seconds:
                outcome["end_reason"] = "max_time"; break
            ledger.check()
            request = {"model": m["id"], "max_tokens": m["max_tokens"], "system": run.prompts["system"]["text"],
                       "tools": tools(run), "output_config": {"effort": m["effort"]}, "messages": messages}
            resp = client.messages.create(**request)
            req_log = _redact({**request, "messages": [
                {**msg, "content": [_dump(c) for c in msg["content"]] if isinstance(msg["content"], list) else msg["content"]}
                for msg in messages]}, refs)
            call_no = run.log_call(req_log, resp.model_dump(mode="json"), resp._request_id)
            if resp.model not in outcome["served_models"]:
                outcome["served_models"].append(resp.model)
            u = resp.usage
            usage = {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                     "cache_read_input_tokens": u.cache_read_input_tokens or 0,
                     "cache_creation_input_tokens": u.cache_creation_input_tokens or 0}
            ledger.add(run.run_id, call_no, m["id"], cost_of(m["id"], usage["input_tokens"], usage["output_tokens"],
                                                           usage["cache_read_input_tokens"], usage["cache_creation_input_tokens"]), usage)
            messages.append({"role": "assistant", "content": resp.content})

            if resp.stop_reason == "refusal":
                outcome["end_reason"] = "refusal"; outcome["refusal"] = _dump(getattr(resp, "stop_details", None)); break

            results = []
            for block in resp.content:
                if block.type != "tool_use":
                    continue
                if getattr(block, "toolset_name", None) == "computer":
                    try:
                        content = execute(browser, block.name, dict(block.input), refs)
                        run.log_action(block.name, dict(block.input), "ok")
                        results.append({"type": "tool_result", "tool_use_id": block.id, "toolset_name": "computer", "content": content})
                    except Exception as err:  # 실패도 기록하고 모델에 알림
                        run.log_action(block.name, dict(block.input), f"error: {err}")
                        results.append({"type": "tool_result", "tool_use_id": block.id, "toolset_name": "computer",
                                        "content": f"Error: {err}", "is_error": True})
                elif block.name == "ask_user":
                    answer = run.prompts["user_sim"]["text"]
                    outcome["ask_user_calls"].append({"call": call_no, "question": block.input.get("question")})
                    run.log_action("ask_user", dict(block.input), f"answered: {answer}")
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": answer})

            if not results:
                outcome["end_reason"] = "completed" if resp.stop_reason == "end_turn" else f"stop_{resp.stop_reason}"
                outcome["final_text"] = "\n".join(b.text for b in resp.content if b.type == "text")
                break
            messages.append({"role": "user", "content": results})
    except Exception as err:
        outcome["end_reason"] = "error"; outcome["error"] = f"{type(err).__name__}: {err}"
    finally:
        blocked = list(browser.blocked)
        browser.close()
    run.finish(outcome, {"blocked_requests": blocked, "tools": tools(run),
                         "provider_notes": "API가 도구 사용 시스템 프롬프트를 붙임(끌 수 없음). 프롬프트 주입 분류기 켜짐(기본)."})
    return outcome
