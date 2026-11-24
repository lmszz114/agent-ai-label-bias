"""Google 연결부: generate_content + computer_use 도구 (environment=browser).

- 모델: gemini-4-hydrogen (무료 등급 키). 가격 페이지 도구 요금표에는 화면 조작이 무료 등급 "사용 불가"로 적혀 있음.
  첫 호출에서 거부되면 그대로 기록하고 끝냄
- 좌표는 0~999 정규화 값 → 화면 픽셀로 변환
- safety_decision(require_confirmation): P2에서는 자동 확인하고 모두 기록함 (p2-candidates.md F2)
- 스크린샷 기록 정리(pruning)는 하지 않음 (다른 두 회사와 같은 조건)
"""

from __future__ import annotations

import os
import time

from google import genai
from google.genai import types

from common import (ASK_USER_DESCRIPTION, SYSTEM_PROMPT, TASK_PROMPT, USER_SIM_ANSWER, VIEWPORT, Browser, Ledger,
                    Run, cost_of, to_playwright_key)

MODEL = "gemini-4-hydrogen"
W, H = VIEWPORT["width"], VIEWPORT["height"]


def _x(v) -> int:
    return int(float(v) / 1000 * W)


def _y(v) -> int:
    return int(float(v) / 1000 * H)


def execute(browser: Browser, name: str, a: dict) -> None:
    page, m = browser.page, browser.page.mouse
    if name in ("click", "double_click", "triple_click", "right_click", "middle_click"):
        btn = {"right_click": "right", "middle_click": "middle"}.get(name, "left")
        m.click(_x(a["x"]), _y(a["y"]), button=btn, click_count={"double_click": 2, "triple_click": 3}.get(name, 1))
    elif name == "move":
        m.move(_x(a["x"]), _y(a["y"]))
    elif name == "mouse_down":
        m.move(_x(a["x"]), _y(a["y"])); m.down()
    elif name == "mouse_up":
        m.move(_x(a["x"]), _y(a["y"])); m.up()
    elif name == "type":
        page.keyboard.type(a["text"])
        if a.get("press_enter"):
            page.keyboard.press("Enter")
    elif name == "scroll":
        mag = float(a.get("magnitude", a.get("magnitude_in_pixels", 800)))
        m.move(_x(a["x"]), _y(a["y"]))
        d = a["direction"]
        dx = _x(mag) if d == "right" else -_x(mag) if d == "left" else 0
        dy = _y(mag) if d == "down" else -_y(mag) if d == "up" else 0
        m.wheel(dx, dy)
    elif name == "drag_and_drop":
        m.move(_x(a.get("x", a.get("start_x"))), _y(a.get("y", a.get("start_y")))); m.down()
        m.move(_x(a.get("destination_x", a.get("end_x"))), _y(a.get("destination_y", a.get("end_y")))); m.up()
    elif name == "press_key":
        page.keyboard.press(to_playwright_key(a["key"]))
    elif name == "key_down":
        page.keyboard.down(to_playwright_key(a["key"]))
    elif name == "key_up":
        page.keyboard.up(to_playwright_key(a["key"]))
    elif name == "hotkey":
        page.keyboard.press("+".join(to_playwright_key(k) for k in a["keys"]))
    elif name == "wait":
        time.sleep(min(float(a.get("seconds", 1)), 10))
    elif name == "take_screenshot":
        pass
    elif name in ("navigate", "go_back", "go_forward", "open_web_browser"):
        # 목업 밖으로 나가는 이동은 브라우저 경로 차단(route)이 막음. 이동 시도 자체를 기록함
        if name == "navigate":
            page.goto(a["url"])
        elif name == "go_back":
            page.go_back()
        elif name == "go_forward":
            page.go_forward()
    else:
        raise ValueError(f"알 수 없는 동작: {name}")
    page.wait_for_timeout(300)


def _usage(resp) -> dict:
    u = resp.usage_metadata
    g = lambda k: getattr(u, k, None) or 0
    return {k: g(k) for k in ["prompt_token_count", "candidates_token_count", "thoughts_token_count",
                              "tool_use_prompt_token_count", "cached_content_token_count", "total_token_count"]} | {
        "model_version": resp.model_version}


def _redacted_contents(contents, image_refs: dict) -> list:
    out = []
    for c in contents:
        d = c.model_dump(mode="json", exclude_none=True)
        for part in d.get("parts", []):
            fr = part.get("function_response")
            if fr:
                for p in fr.get("parts", []) or []:
                    blob = p.get("inline_data")
                    if blob and "data" in blob:
                        blob["data"] = image_refs.get(blob["data"], "sha256:unknown")
            if part.get("inline_data") and "data" in part["inline_data"]:
                part["inline_data"]["data"] = image_refs.get(part["inline_data"]["data"], "sha256:unknown")
        out.append(d)
    return out


def run_once(run: Run, ledger: Ledger, max_calls: int, max_seconds: float) -> dict:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    ask_decl = types.FunctionDeclaration(
        name="ask_user", description=ASK_USER_DESCRIPTION,
        parameters_json_schema={"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]})
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[types.Tool(computer_use=types.ComputerUse(environment=types.Environment.ENVIRONMENT_BROWSER)),
               types.Tool(function_declarations=[ask_decl])],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    browser = Browser(run)
    image_refs: dict[str, str] = {}
    contents = [types.Content(role="user", parts=[types.Part(text=TASK_PROMPT)])]
    outcome = {"end_reason": None, "final_text": None, "ask_user_calls": [], "safety_decisions": []}
    try:
        while True:
            if run.call_no >= max_calls:
                outcome["end_reason"] = "max_calls"; break
            if run.elapsed() >= max_seconds:
                outcome["end_reason"] = "max_time"; break
            ledger.check()
            sent = _redacted_contents(contents, image_refs)
            resp = client.models.generate_content(model=MODEL, contents=contents, config=config)
            call_no = run.log_call({"model": MODEL, "config": config.model_dump(mode="json", exclude_none=True), "contents": sent},
                                   resp.model_dump(mode="json", exclude_none=True), resp.response_id)
            usage = _usage(resp)
            out_tokens = usage["candidates_token_count"] + usage["thoughts_token_count"]
            in_tokens = usage["prompt_token_count"] + usage["tool_use_prompt_token_count"]
            ledger.add(run.run_id, call_no, MODEL, cost_of(MODEL, in_tokens, out_tokens)["cost_usd"], usage)

            if not resp.candidates or not resp.candidates[0].content or not resp.candidates[0].content.parts:
                outcome["end_reason"] = "empty_response"
                outcome["detail"] = resp.prompt_feedback.model_dump(mode="json") if resp.prompt_feedback else None
                break
            cand = resp.candidates[0]
            contents.append(cand.content)
            fcs = [p.function_call for p in cand.content.parts if p.function_call]
            if not fcs:
                outcome["end_reason"] = "completed"
                outcome["final_text"] = "\n".join(p.text for p in cand.content.parts if p.text and not p.thought)
                break

            responses = []
            for fc in fcs:
                args = dict(fc.args or {})
                extra = {}
                sd = args.pop("safety_decision", None)
                if sd:
                    outcome["safety_decisions"].append({"call": call_no, "action": fc.name, "decision": sd})
                    run.log_action("provider_safety_decision", {"action": fc.name, "decision": sd}, "auto_acknowledged")
                    extra["safety_acknowledgement"] = "true"
                if fc.name == "ask_user":
                    outcome["ask_user_calls"].append({"call": call_no, "question": args.get("question")})
                    run.log_action("ask_user", args, f"answered: {USER_SIM_ANSWER}")
                    responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"answer": USER_SIM_ANSWER}))
                    continue
                try:
                    execute(browser, fc.name, args)
                    run.log_action(fc.name, args, "ok")
                    result = {"url": browser.page.url, **extra}
                except Exception as err:
                    run.log_action(fc.name, args, f"error: {err}")
                    result = {"url": browser.page.url, "error": str(err), **extra}
                png = browser.screenshot()
                name, digest = run.save_screenshot(png)
                image_refs[__import__("base64").b64encode(png).decode("ascii")] = f"sha256:{digest} ({name})"
                responses.append(types.FunctionResponse(
                    id=fc.id, name=fc.name, response=result,
                    parts=[types.FunctionResponsePart(inline_data=types.FunctionResponseBlob(mime_type="image/png", data=png))]))
            contents.append(types.Content(role="user", parts=[types.Part(function_response=r) for r in responses]))
    except Exception as err:
        outcome["end_reason"] = "error"; outcome["error"] = f"{type(err).__name__}: {err}"
    finally:
        blocked = browser.blocked
        browser.close()
    run.finish(outcome, {"blocked_requests": blocked,
                         "provider_notes": "무료 등급 키. 날짜 고정 모델 ID 없음(model_version 기록). safety_decision은 자동 확인 후 기록. 프롬프트 주입 탐지는 기본값(꺼짐)."})
    return outcome
