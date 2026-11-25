"""P3 조건 동등성 자동 검사와 로그 일치 검사 (workplan P3 게이트, 명세서 v2).

모든 내용 조합(15) × 카드 위치(2) × 자기소개 행동(제안 넣기, 직접 쓰기)(2)에 대해
두 조건(ai, auto)을 같은 순서로 조작하고 비교함.

검사 항목
  G1 화면 동등성: 상태마다 배지 영역을 가린(mask) 스크린샷의 해시가 두 조건에서 같음
     → 픽셀 차이가 배지 상자 안에만 있다는 뜻. 배지 상자의 위치와 크기도 같아야 함
  G2 DOM 동등성: 배지 글자만 비운 문서 HTML이 두 조건에서 같음
  G3 대조 확인: 배지가 보이는 상태에서 가리지 않은 스크린샷은 두 조건에서 달라야 함 (검사가 헛돌지 않는지)
  G4 외부 요청 0: 127.0.0.1:포트 밖으로 나간 요청 수
  G5 로그 일치: 스크립트가 한 행동과 사이트 로그가 맞는지
     (빈 칸 [다음] 거부, 카드 노출과 화면 안 표시, 카드 위치, [이 문구 넣기]와 직접 입력 기록, 저장된 자기소개와 출처)
  G6 배치: 1280x800에서 S1, S1b가 스크롤 없이 다 보임

실행: .venv/Scripts/python.exe mockup/check_equivalence.py   (목업 서버가 127.0.0.1:8765에서 떠 있어야 함)
결과: data/p3-equivalence-v2/ (report.json, SUMMARY.md, 대표 스크린샷, manifest.sha256)
v1(완료 후 팝업) 검사 결과는 data/p3-equivalence/ (코드 c82392b)
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
OUT = S.REPO / "data" / "p3-equivalence-v2"
KST = timezone(timedelta(hours=9))
CONDS = ["ai", "auto"]
TAG = datetime.now(KST).strftime("%Y%m%dT%H%M%S")  # 검사마다 run_id가 겹치지 않게 함
LAYOUTS = ["card_above", "card_below"]
OWN_TEXT = "직접 쓴 자기소개 시험 문장입니다."


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


def scroll(p) -> list:
    return p.evaluate("[document.documentElement.scrollHeight, innerHeight]")


def episode(browser, cond: str, content_id: str, layout: str, choice: str) -> dict:
    """한 조건으로 정해진 조작을 하고 상태별 지문과 로그 검사용 정보를 돌려줌."""
    run_id = S.create(cond, content_id, layout, run_id=f"p3chk-{TAG}-{cond}-{content_id}-{layout}-{choice}")
    pg = Page(browser, run_id)
    p = pg.page
    st = {}
    st["s1_empty"] = pg.state()
    scrolls = {"s1": scroll(p)}
    p.click("#btn-next")                        # 빈 칸 [다음] → 거부되어야 함
    st["s1_invalid"] = pg.state()
    fill(p, S.profile_for(content_id))
    st["s1_filled"] = pg.state()
    p.click("#btn-next")
    p.wait_for_selector("#s1b:not([hidden])")
    st["s1b_shown"] = pg.state()
    scrolls["s1b"] = scroll(p)
    card_top = p.locator("#card").bounding_box()["y"]
    field_top = p.locator("#f-intro").bounding_box()["y"]
    btn_box = p.locator("#btn-insert").bounding_box()
    if choice == "use":
        p.click("#btn-insert")
    else:
        p.click("#f-intro")
        p.keyboard.type(OWN_TEXT)
    p.evaluate("document.activeElement && document.activeElement.blur()")
    st[f"s1b_after_{choice}"] = pg.state()
    p.click("#btn-submit")
    p.wait_for_selector("#s2:not([hidden])")
    st["s2_saved"] = pg.state()
    s2_text = p.inner_text("#summary")
    ext, nreq = list(pg.external), len(pg.requests)
    pg.close()
    return {"run_id": run_id, "states": st, "scrolls": scrolls, "card_above": card_top < field_top,
            "button_box": btn_box, "s2_text": s2_text, "external": ext, "n_requests": nreq}


def read_events(run_id: str) -> list[dict]:
    ev = [json.loads(l) for l in S.EVENT_LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    return sorted((e for e in ev if e["run_id"] == run_id), key=lambda e: e["seq"])


def check_log(ep: dict, choice: str, layout: str, card_text: str) -> list[str]:
    """스크립트가 한 행동과 사이트 로그 대조. 불일치 목록을 돌려줌 (비면 일치)."""
    ev = read_events(ep["run_id"])
    types = [e["type"] for e in ev]
    errs = []

    def need(cond, msg):
        if not cond:
            errs.append(msg)

    need(types and types[0] == "page_load", "첫 이벤트가 page_load가 아님")
    need(len({e.get("page_id") for e in ev}) == 1 and bool(ev[0].get("page_id")), "page_id가 없거나 한 실행에 여러 개")
    inv = [e for e in ev if e["type"] == "next_invalid"]
    need(len(inv) == 1 and len(inv[0]["detail"]["missing"]) == 8, "빈 칸 [다음] 거부 기록 이상")
    need(types.count("next") == 1, "next 기록 수가 1이 아님")
    shown = [e for e in ev if e["type"] == "card_shown"]
    need(len(shown) == 1 and shown[0]["detail"]["layout"] == layout, "card_shown 기록 수나 카드 위치 기록 이상")
    ren = [e for e in ev if e["type"] == "card_rendered"]
    need(len(ren) == 1 and ren[0]["detail"]["in_viewport"], "카드가 화면 안에 그려졌다는 기록 없음")
    need(ep["card_above"] == (layout == "card_above"), f"카드 실제 위치가 배정({layout})과 다름")
    ins = [e for e in ev if e["type"] == "card_insert"]
    typed = [e for e in ev if e["type"] == "intro_input"]
    subs = [e for e in ev if e["type"] == "submit"]
    need(len(subs) == 1, "submit 기록 수가 1이 아님")
    if choice == "use":
        need(len(ins) == 1 and not typed, f"제안 넣기 기록 이상: insert {len(ins)}, input {len(typed)}")
        want_intro, want_src = card_text, "card"
    else:
        need(not ins and len(typed) == 1, f"직접 입력 기록 이상: insert {len(ins)}, input {len(typed)}")
        want_intro, want_src = OWN_TEXT, "typed"
    if subs:
        d = subs[0]["detail"]
        need(d["resume"]["intro"] == want_intro, "저장된 자기소개가 실제 입력과 다름")
        need(d["intro_source"] == want_src, f"자기소개 출처 기록이 {want_src}가 아님: {d['intro_source']}")
    need(want_intro in ep["s2_text"], "S2 요약에 자기소개가 없음")
    return errs


def main():
    from playwright.sync_api import sync_playwright
    # 코드 상태는 결과를 쓰기 전에 기록함 (결과 폴더 자신은 빼고 봄)
    commit = git("rev-parse", "HEAD")
    dirty = git("status", "--porcelain", "--", ".", f":(exclude){OUT.relative_to(S.REPO).as_posix()}", ":(exclude)mockup/runtime")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "screenshots").mkdir(exist_ok=True)
    started = datetime.now(KST).isoformat(timespec="seconds")
    cond_version = json.loads(S.CONDITIONS.read_text(encoding="utf-8"))["version"]
    results, fails = [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=S.BROWSER_ARGS)
        for cid in S.content_ids():
            card_text = S.resolve(S.create("ai", cid, "card_above", run_id="p3chk-probe"))["card_text"]
            for layout in LAYOUTS:
                for choice in ["use", "write"]:
                    eps = {c: episode(browser, c, cid, layout, choice) for c in CONDS}
                    time.sleep(0.3)   # 마지막 전송(pagehide)이 로그에 닿을 시간
                    a, b = eps["ai"], eps["auto"]
                    row = {"content_id": cid, "layout": layout, "choice": choice, "states": {}}
                    for name in a["states"]:
                        sa, sb = a["states"][name], b["states"][name]
                        row["states"][name] = {
                            "masked_equal": sa["masked"] == sb["masked"], "dom_equal": sa["dom"] == sb["dom"],
                            "badge_box_equal": sa["badge_box"] == sb["badge_box"],
                            "raw_differs": sa["raw"] != sb["raw"], "badge_visible": sa["badge_box"] is not None,
                            "masked_sha256": {"ai": sa["masked"], "auto": sb["masked"]}}
                        if cid == "p1-t1" and (name == "s1b_shown" or (layout == "card_above" and choice == "use")):
                            for c, s in (("ai", sa), ("auto", sb)):
                                (OUT / "screenshots" / f"{cid}_{layout}_{c}_{name}.png").write_bytes(s["_raw_png"])
                    row["button_box_equal"] = a["button_box"] == b["button_box"]
                    row["external_requests"] = a["external"] + b["external"]
                    row["n_requests"] = a["n_requests"] + b["n_requests"]
                    row["fits"] = all(sc[0] <= sc[1] for e in (a, b) for sc in e["scrolls"].values())
                    row["log_errors"] = {c: check_log(eps[c], choice, layout, card_text) for c in CONDS}
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
                    if not row["fits"]:
                        bad.append("G6 스크롤 생김")
                    for c in CONDS:
                        bad += [f"G5 {c}: {m}" for m in row["log_errors"][c]]
                    row["pass"] = not bad
                    row["problems"] = bad
                    results.append(row)
                    print(f"{cid} {layout} {choice}: {'통과' if not bad else bad}", flush=True)
                    if bad:
                        fails.append(row)
        browser.close()

    summary = {
        "checked_at": started, "finished_at": datetime.now(KST).isoformat(timespec="seconds"),
        "git_commit": commit, "git_dirty": bool(dirty), "git_dirty_files": dirty.splitlines(),
        "conditions_version": cond_version, "content_version": "content-v1",
        "viewport": VIEWPORT, "browser_args": S.BROWSER_ARGS, "combinations": len(results), "episodes": len(results) * 2,
        "passed": sum(r["pass"] for r in results), "failed": len(fails),
        "external_requests_total": sum(len(r["external_requests"]) for r in results),
        "requests_total": sum(r["n_requests"] for r in results),
        "states_compared": sum(len(r["states"]) for r in results),
    }
    (OUT / "report.json").write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2),
                                     encoding="utf-8", newline="\n")
    write_summary_md(summary)
    lines = [f"{sha(p.read_bytes())}  {p.relative_to(OUT).as_posix()}"
             for p in sorted(OUT.rglob("*")) if p.is_file() and p.name != "manifest.sha256"]
    (OUT / "manifest.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    sys.exit(1 if fails else 0)


def write_summary_md(s: dict) -> None:
    ok = s["failed"] == 0
    md = f"""# P3 조건 동등성 검사 결과 (명세서 v2)

| 항목 | 값 |
|---|---|
| 실행 날짜 (KST) | {s['checked_at']} ~ {s['finished_at']} |
| 구분 | 목업 검사 (API 실행 아님, 모델 없음) |
| 코드 | git `{s['git_commit'][:7]}`, 커밋 안 된 변경 {'있음' if s['git_dirty'] else '없음'} |
| 설정 | `{s['conditions_version']}`, `{s['content_version']}` |
| 조건 | ai (`AI 생성`), auto (`자동 생성`) |
| 조합 | 내용 15 × 카드 위치 2 × 자기소개 행동(제안 넣기, 직접 쓰기) 2 = {s['combinations']}개, 조건마다 1회씩 {s['episodes']}회 |
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
| G6 배치 | S1, S1b 스크롤 없음, 카드가 화면 안 | report.json |

- 상태: 빈 S1, 빈 칸 [다음] 뒤 S1, 입력한 S1, 카드가 보이는 S1b, 제안 넣기 또는 직접 쓰기 뒤 S1b, 저장 뒤 S2
- 대표 스크린샷: `screenshots/` (p1-t1 카드 위 + 제안 넣기 흐름의 모든 상태, 두 카드 위치의 S1b 화면, 조건별)
- 재계산: `.venv/Scripts/python.exe mockup/check_equivalence.py` (목업 서버 실행 후). 파일 해시는 `manifest.sha256`
- 이 검사는 스크립트 조작이다. 사람이 직접 눌러 보는 검사(workplan P3 게이트 2)는 따로 한다
- v1(완료 후 팝업) 검사 결과는 `data/p3-equivalence/`
"""
    (OUT / "SUMMARY.md").write_text(md, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
