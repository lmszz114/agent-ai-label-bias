"""P3 조건 동등성 자동 검사와 로그 일치 검사 (workplan P3 게이트).

모든 내용 조합(15) × 버튼 순서(2)에 대해 두 조건(ai, auto)을 같은 순서로 조작하고 비교함.

검사 항목
  G1 화면 동등성: 상태마다 배지 영역을 가린(mask) 스크린샷의 해시가 두 조건에서 같음
     → 픽셀 차이가 배지 상자 안에만 있다는 뜻. 배지 상자의 위치와 크기도 같아야 함
  G2 DOM 동등성: 배지 글자만 비운 문서 HTML이 두 조건에서 같음
  G3 대조 확인: 배지를 가리지 않은 팝업 스크린샷은 두 조건에서 달라야 함 (검사가 헛돌지 않는지)
  G4 외부 요청 0: 127.0.0.1:포트 밖으로 나간 요청 수
  G5 로그 일치: 스크립트가 한 행동과 사이트 로그가 맞는지
     (빈 칸 제출 거부, 팝업 노출과 화면 안 표시, Esc와 바깥 클릭으로 안 닫힘, Tab 초점이 팝업 안에만 있음,
      누른 버튼, 적용 시에만 이력서 변경)
  G6 배치: 1280x800에서 S1이 스크롤 없이 다 보이고 팝업이 화면 안에 있음

실행: .venv/Scripts/python.exe mockup/check_equivalence.py   (목업 서버가 127.0.0.1:8765에서 떠 있어야 함)
결과: data/p3-equivalence/ (report.json, SUMMARY.md, 대표 스크린샷, manifest.sha256)
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import session as S  # noqa: E402

PORT = 8765
ORIGIN = f"http://127.0.0.1:{PORT}"
VIEWPORT = {"width": 1280, "height": 800}
OUT = S.REPO / "data" / "p3-equivalence"
KST = timezone(timedelta(hours=9))
CONDS = ["ai", "auto"]
TAG = datetime.now(KST).strftime("%Y%m%dT%H%M%S")  # 검사마다 run_id가 겹치지 않게 함
ORDERS = ["close_first", "apply_first"]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=S.REPO, capture_output=True, text=True).stdout.strip()


class Page:
    def __init__(self, browser, run_id: str):
        self.ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=1, locale="ko-KR")
        self.requests: list[str] = []
        self.external: list[str] = []
        self.ctx.route("**/*", self._guard)
        self.page = self.ctx.new_page()
        self.page.goto(f"{ORIGIN}/?s={run_id}", wait_until="networkidle")
        self.page.wait_for_function("document.getElementById('badge').textContent.length > 0")

    def _guard(self, route):
        url = route.request.url
        self.requests.append(url)
        if url.startswith(ORIGIN + "/"):
            route.continue_()
        else:
            self.external.append(url)
            route.abort()

    def state(self) -> dict:
        p = self.page
        p.wait_for_timeout(150)
        badge = p.locator("#badge")
        masked = p.screenshot(type="png", mask=[badge], mask_color="#FF00FF")
        raw = p.screenshot(type="png")
        dom = p.evaluate("""() => { const c = document.documentElement.cloneNode(true);
                             c.querySelector('#badge').textContent = ''; return c.outerHTML; }""")
        box = badge.bounding_box() if badge.is_visible() else None
        return {"masked": sha(masked), "raw": sha(raw), "dom": sha(dom.encode("utf-8")),
                "badge_box": box, "_raw_png": raw}

    def close(self):
        self.ctx.close()


def fill(page, prof: dict) -> None:
    vals = {"name": prof["name"], "job": prof["job"], "company": prof["career"]["company"],
            "period": prof["career"]["period"], "duty": prof["career"]["duty"],
            "school": prof["education"]["school"], "major": prof["education"]["major"], "skills": prof["skills"]}
    for k, v in vals.items():
        page.fill(f"#f-{k}", v)
    page.locator("#f-skills").blur()


def episode(browser, cond: str, content_id: str, order: str, choice: str) -> dict:
    """한 조건으로 정해진 조작을 하고 상태별 지문과 로그 검사용 정보를 돌려줌."""
    run_id = S.create(cond, content_id, order, run_id=f"p3chk-{TAG}-{cond}-{content_id}-{order}-{choice}")
    pg = Page(browser, run_id)
    p = pg.page
    st = {}
    st["s1_empty"] = pg.state()
    s1_scroll = p.evaluate("[document.documentElement.scrollHeight, innerHeight]")
    p.click("#btn-submit")                      # 빈 칸 제출 → 거부되어야 함
    st["s1_invalid"] = pg.state()
    fill(p, S.profile_for(content_id))
    st["s1_filled"] = pg.state()
    p.click("#btn-submit")
    p.wait_for_selector("#overlay:not([hidden])")
    st["s2_popup"] = pg.state()
    p.keyboard.press("Escape")                  # 닫히면 안 됨
    p.mouse.click(30, 400)                      # 팝업 바깥(어두운 배경). 닫히면 안 됨
    focus = []
    for _ in range(4):                          # Tab 초점이 팝업 버튼에만 가야 함 (뒤 화면은 inert)
        p.keyboard.press("Tab")
        focus.append(p.evaluate("document.activeElement ? document.activeElement.id : ''"))
    p.evaluate("document.activeElement && document.activeElement.blur()")
    still_open = p.is_visible("#overlay")
    st["s2_popup_after_esc"] = pg.state()
    btn = "#btn-apply" if choice == "apply" else "#btn-close"
    btn_box = p.locator(btn).bounding_box()
    p.click(btn)
    p.wait_for_selector("#overlay", state="hidden")
    st[f"s2_after_{choice}"] = pg.state()
    s2_text = p.inner_text("#summary")
    ext, nreq = list(pg.external), len(pg.requests)
    pg.close()
    return {"run_id": run_id, "states": st, "still_open_after_esc_click": still_open, "tab_focus": focus, "s1_scroll": s1_scroll,
            "button_box": btn_box, "s2_text": s2_text, "external": ext, "n_requests": nreq}


def read_events(run_id: str) -> list[dict]:
    ev = [json.loads(l) for l in S.EVENT_LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    return sorted((e for e in ev if e["run_id"] == run_id), key=lambda e: e["seq"])


def check_log(ep: dict, choice: str, order: str, popup_text: str) -> list[str]:
    """스크립트가 한 행동과 사이트 로그 대조. 불일치 목록을 돌려줌 (비면 일치)."""
    ev = read_events(ep["run_id"])
    types = [e["type"] for e in ev]
    errs = []
    def need(cond, msg):
        if not cond:
            errs.append(msg)
    need(types and types[0] == "page_load", "첫 이벤트가 page_load가 아님")
    inv = [e for e in ev if e["type"] == "submit_invalid"]
    need(len(inv) == 1 and len(inv[0]["detail"]["missing"]) == 8, "빈 칸 제출 거부 기록 이상")
    need(types.count("submit") == 1, "submit 기록 수가 1이 아님")
    need(types.count("popup_shown") == 1, "popup_shown 기록 수가 1이 아님")
    ren = [e for e in ev if e["type"] == "popup_rendered"]
    need(len(ren) == 1 and ren[0]["detail"]["in_viewport"], "팝업이 화면 안에 그려졌다는 기록 없음")
    keys = [e["detail"]["key"] for e in ev if e["type"] == "key"]
    need("Escape" in keys, "Esc 키 기록 없음")
    clicks = [e for e in ev if e["type"] == "popup_click"]
    pos = "left" if (order == "close_first") == (choice == "close") else "right"
    need(len(clicks) == 1 and clicks[0]["detail"] == {"button": choice, "position": pos},
         f"popup_click 기록이 실제({choice}, {pos})와 다름: {[c['detail'] for c in clicks]}")
    # popup_click 전에 팝업이 닫힌 기록이 없어야 함 (Esc, 바깥 클릭, Tab+Enter로 안 닫힘)
    i_click = types.index("popup_click") if "popup_click" in types else len(types)
    need("popup_closed" not in types[:i_click], "버튼을 누르기 전에 팝업이 닫힘")
    closed = [e for e in ev if e["type"] == "popup_closed"]
    need(len(closed) == 1 and closed[0]["detail"]["by"] == choice, "popup_closed 기록 이상")
    upd = [e for e in ev if e["type"] == "resume_updated"]
    if choice == "apply":
        need(len(upd) == 1 and upd[0]["detail"]["resume"]["intro"] == popup_text, "적용했는데 이력서 변경 기록이 없거나 다름")
        need(popup_text in ep["s2_text"], "적용했는데 S2 요약에 자기소개가 없음")
    else:
        need(not upd, "닫았는데 이력서 변경 기록이 있음")
        need("자기소개" not in ep["s2_text"], "닫았는데 S2 요약에 자기소개가 있음")
    need(ep["still_open_after_esc_click"], "Esc나 바깥 클릭 뒤 팝업이 사라짐")
    need(all(f in ("btn-close", "btn-apply", "") for f in ep["tab_focus"]), f"Tab 초점이 팝업 밖으로 감: {ep['tab_focus']}")
    sub = next(e for e in ev if e["type"] == "submit")
    need(sub["detail"]["resume"]["intro"] == "", "제출된 이력서의 자기소개가 비어 있지 않음")
    return errs


def main():
    from playwright.sync_api import sync_playwright
    # 코드 상태는 결과를 쓰기 전에 기록함 (결과 폴더 자신은 빼고 봄)
    commit = git("rev-parse", "HEAD")
    dirty = git("status", "--porcelain", "--", ".", ":(exclude)data/p3-equivalence")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "screenshots").mkdir(exist_ok=True)
    started = datetime.now(KST).isoformat(timespec="seconds")
    results, fails = [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=S.BROWSER_ARGS)
        for cid in S.content_ids():
            popup_text = S.resolve(S.create("ai", cid, "close_first", run_id="p3chk-probe"))["popup_text"]
            for order in ORDERS:
                for choice in ["close", "apply"]:
                    eps = {c: episode(browser, c, cid, order, choice) for c in CONDS}
                    time.sleep(0.3)   # 마지막 전송(pagehide)이 로그에 닿을 시간
                    a, b = eps["ai"], eps["auto"]
                    row = {"content_id": cid, "button_order": order, "choice": choice, "states": {}}
                    for name in a["states"]:
                        sa, sb = a["states"][name], b["states"][name]
                        row["states"][name] = {
                            "masked_equal": sa["masked"] == sb["masked"], "dom_equal": sa["dom"] == sb["dom"],
                            "badge_box_equal": sa["badge_box"] == sb["badge_box"],
                            "raw_differs": sa["raw"] != sb["raw"], "badge_visible": sa["badge_box"] is not None,
                            "masked_sha256": {"ai": sa["masked"], "auto": sb["masked"]}}
                        if cid == "p1-t1" and choice == "close" and (name == "s2_popup" or order == "close_first"):
                            for c, s in (("ai", sa), ("auto", sb)):
                                (OUT / "screenshots" / f"{cid}_{order}_{c}_{name}.png").write_bytes(s["_raw_png"])
                    row["button_box_equal"] = a["button_box"] == b["button_box"]
                    row["external_requests"] = a["external"] + b["external"]
                    row["n_requests"] = a["n_requests"] + b["n_requests"]
                    row["s1_fits"] = all(e["s1_scroll"][0] <= e["s1_scroll"][1] for e in (a, b))
                    row["log_errors"] = {c: check_log(eps[c], choice, order, popup_text) for c in CONDS}
                    # 판정
                    bad = []
                    for name, s in row["states"].items():
                        if not (s["masked_equal"] and s["dom_equal"] and s["badge_box_equal"]):
                            bad.append(f"G1/G2 {name}")
                        if s["badge_visible"] and not s["raw_differs"]:
                            bad.append(f"G3 {name}")
                        if not s["badge_visible"] and s["raw_differs"]:
                            bad.append(f"G1 {name} (배지가 안 보이는데 화면이 다름)")
                    if not row["button_box_equal"]:
                        bad.append("버튼 위치 다름")
                    if row["external_requests"]:
                        bad.append("G4 외부 요청")
                    if not row["s1_fits"]:
                        bad.append("G6 S1 스크롤 생김")
                    for c in CONDS:
                        bad += [f"G5 {c}: {m}" for m in row["log_errors"][c]]
                    row["pass"] = not bad
                    row["problems"] = bad
                    results.append(row)
                    print(f"{cid} {order} {choice}: {'통과' if not bad else bad}", flush=True)
                    if bad:
                        fails.append(row)
        browser.close()

    summary = {
        "checked_at": started, "finished_at": datetime.now(KST).isoformat(timespec="seconds"),
        "git_commit": commit, "git_dirty": bool(dirty), "git_dirty_files": dirty.splitlines(),
        "conditions_version": "conditions-v1", "content_version": "content-v1",
        "viewport": VIEWPORT, "browser_args": S.BROWSER_ARGS, "combinations": len(results), "episodes": len(results) * 2,
        "passed": sum(r["pass"] for r in results), "failed": len(fails),
        "external_requests_total": sum(len(r["external_requests"]) for r in results),
        "requests_total": sum(r["n_requests"] for r in results),
        "states_compared": sum(len(r["states"]) for r in results),
    }
    (OUT / "report.json").write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    write_summary_md(summary)
    lines = [f"{sha(p.read_bytes())}  {p.relative_to(OUT).as_posix()}"
             for p in sorted(OUT.rglob("*")) if p.is_file() and p.name != "manifest.sha256"]
    (OUT / "manifest.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    sys.exit(1 if fails else 0)


def write_summary_md(s: dict) -> None:
    ok = s["failed"] == 0
    md = f"""# P3 조건 동등성 검사 결과

| 항목 | 값 |
|---|---|
| 실행 날짜 (KST) | {s['checked_at']} ~ {s['finished_at']} |
| 구분 | 목업 검사 (API 실행 아님, 모델 없음) |
| 코드 | git `{s['git_commit'][:7]}`, 커밋 안 된 변경 {'있음' if s['git_dirty'] else '없음'} |
| 설정 | `{s['conditions_version']}`, `{s['content_version']}` |
| 조건 | ai (`AI 생성`), auto (`자동 생성`) |
| 조합 | 내용 15 × 버튼 순서 2 × 팝업 선택(닫기, 적용) 2 = {s['combinations']}개, 조건마다 1회씩 {s['episodes']}회 |
| 화면 크기 | {s['viewport']['width']}x{s['viewport']['height']}, 기기 배율 1 |
| 브라우저 | Chromium headless, 결정적 렌더링 옵션 `mockup/session.py` `BROWSER_ARGS` |

## 결과

| 검사 | 기준 | 결과 |
|---|---|---|
| 전체 | 모든 조합 통과 | {s['passed']}/{s['combinations']} 통과 ({'통과' if ok else '실패'}) |
| G1 화면 동등성 | 배지 상자를 가린 스크린샷 해시가 두 조건에서 같음 | 상태 {s['states_compared']}개 비교, report.json |
| G2 DOM 동등성 | 배지 글자만 비운 HTML이 같음 | report.json |
| G3 대조 확인 | 배지가 보이는 상태에서 가리지 않은 스크린샷은 다름 | report.json |
| G4 외부 요청 | 0건 | {s['external_requests_total']}건 (전체 요청 {s['requests_total']}건) |
| G5 로그 일치 | 스크립트 조작과 사이트 로그 불일치 0 | report.json `log_errors` |
| G6 배치 | S1 스크롤 없음, 팝업이 화면 안 | report.json |

- 상태: 빈 S1, 빈 칸 제출 후 S1, 입력한 S1, 팝업이 뜬 S2, Esc·바깥 클릭·Tab 이동 뒤 S2, 닫기 또는 적용 뒤 S2
- 대표 스크린샷: `screenshots/` (p1-t1 닫기 흐름의 모든 상태, 두 버튼 순서의 팝업 화면, 조건별)
- 재계산: `.venv/Scripts/python.exe mockup/check_equivalence.py` (목업 서버 실행 후). 파일 해시는 `manifest.sha256`
- 이 검사는 스크립트 조작이다. 사람이 직접 눌러 보는 검사(workplan P3 게이트 2)는 따로 한다
"""
    (OUT / "SUMMARY.md").write_text(md, encoding="utf-8")


if __name__ == "__main__":
    main()
