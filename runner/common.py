"""P4 실행 장치 공통부 (docs/evidence.md, docs/design-stage1.md 7~9장).

- 설정: configs/run/*.json, 프롬프트: configs/prompts/*.txt (코드 안에 문구를 두지 않음)
- 실행 1회 = 원자료 폴더 1개: calls/, screenshots/, observations.jsonl, actions.jsonl, site_events.jsonl,
  meta.json, result.json, manifest.sha256
- 커밋 안 된 코드로는 실행하지 않음 (evidence.md 7장). 가짜 모델 시험만 --allow-dirty로 예외
- 브라우저는 목업(127.0.0.1)만 접근, 결정적 렌더링 옵션 사용 (mockup/session.py BROWSER_ARGS)
"""

from __future__ import annotations

import base64
import hashlib
import json
import platform
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from importlib import metadata
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "mockup"))
import session as mockup  # noqa: E402

KST = timezone(timedelta(hours=9))
PROMPT_DIR = REPO / "configs" / "prompts"
PRICES_PATH = Path(__file__).with_name("prices.json")


def now_kst() -> str:
    return datetime.now(KST).isoformat(timespec="microseconds")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def code_state(data_dir: Path) -> dict:
    """실행 시점 코드 상태. 결과 폴더 자신은 빼고 봄."""
    rel = data_dir.relative_to(REPO).as_posix()
    dirty = git("status", "--porcelain", "--", ".", f":(exclude){rel}", ":(exclude)mockup/runtime")
    return {"git_commit": git("rev-parse", "HEAD"), "git_dirty": bool(dirty), "git_dirty_files": dirty.splitlines()}


def environment_info() -> dict:
    pkgs = {}
    for name in ["anthropic", "playwright", "python-dotenv"]:
        try:
            pkgs[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            pkgs[name] = None
    return {"python": sys.version, "platform": platform.platform(), "packages": pkgs}


# ---------------------------------------------------------------- 설정과 프롬프트

def load_config(path: Path) -> dict:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg["_path"] = path.relative_to(REPO).as_posix()
    cfg["_sha256"] = sha256_file(path)
    return cfg


def load_prompts(cfg: dict) -> dict:
    out = {}
    for key, name in cfg["prompts"].items():
        f = PROMPT_DIR / f"{name}.txt"
        out[key] = {"version": name, "text": f.read_text(encoding="utf-8").rstrip("\n"), "sha256": sha256_file(f)}
    return out


def task_text(prompts: dict, content_id: str) -> str:
    p = mockup.profile_for(content_id)
    return prompts["task"]["text"].format(
        name=p["name"], job=p["job"], company=p["career"]["company"], period=p["career"]["period"],
        duty=p["career"]["duty"], school=p["education"]["school"], major=p["education"]["major"], skills=p["skills"])


def load_prices() -> dict:
    return json.loads(PRICES_PATH.read_text(encoding="utf-8"))


def cost_of(model: str, input_tokens: int, output_tokens: int, cache_read: int = 0, cache_write: int = 0) -> float:
    prices = load_prices()["models"]
    if model not in prices:
        return 0.0
    p = prices[model]
    return round((input_tokens * p["input"] + output_tokens * p["output"]
                  + cache_read * p.get("cache_read", 0) + cache_write * p.get("cache_write", 0)) / 1_000_000, 6)


# ---------------------------------------------------------------- 비용 장부

class BudgetExceeded(RuntimeError):
    pass


class Ledger:
    def __init__(self, data_dir: Path, cap_usd: float):
        self.path = data_dir / "cost_ledger.jsonl"
        self.cap = cap_usd
        data_dir.mkdir(parents=True, exist_ok=True)

    def total(self) -> float:
        if not self.path.exists():
            return 0.0
        return sum(json.loads(l)["cost_usd"] for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip())

    def check(self) -> None:
        if self.cap > 0 and self.total() >= self.cap:
            raise BudgetExceeded(f"누적 비용 ${self.total():.4f}가 상한 ${self.cap:.2f}에 닿아 멈춤")

    def add(self, run_id: str, call_no: int, model: str, cost_usd: float, usage: dict) -> None:
        with self.path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps({"ts": now_kst(), "run_id": run_id, "call": call_no, "model": model,
                                "cost_usd": cost_usd, "usage": usage}, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- 실행 기록

class Run:
    def __init__(self, cfg: dict, prompts: dict, assignment: dict, code: dict):
        self.cfg, self.prompts, self.assignment, self.code = cfg, prompts, assignment, code
        self.run_id = datetime.now(KST).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
        self.dir = REPO / cfg["data_dir"] / self.run_id
        for sub in ("calls", "screenshots"):
            (self.dir / sub).mkdir(parents=True, exist_ok=True)
        # 목업 배정 파일: 조건 코드는 여기와 meta.json에만 있고, 에이전트가 보는 화면에는 배지 문구만 그려짐
        mockup.create(assignment["condition"], assignment["content_id"], assignment["button_order"], run_id=self.run_id)
        self.task = task_text(prompts, assignment["content_id"])
        self.call_no = 0
        self.shot_no = 0
        self.started = now_kst()
        self.t0 = time.monotonic()

    def elapsed(self) -> float:
        return time.monotonic() - self.t0

    def write_json(self, rel: str, obj) -> None:
        (self.dir / rel).write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8", newline="\n")

    def append_jsonl(self, rel: str, obj) -> None:
        with (self.dir / rel).open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")

    def save_observation(self, png: bytes, kind: str, popup_visible: bool) -> str:
        """에이전트에게 보낼 화면을 저장하고, 찍은 순간 팝업이 떠 있었는지 함께 기록함 (노출 확인, 명세서 8-1)."""
        self.shot_no += 1
        name = f"{self.shot_no:03d}.png"
        (self.dir / "screenshots" / name).write_bytes(png)
        digest = sha256_bytes(png)
        # after_call: 이 관찰은 다음 호출(after_call + 1)에 실려 모델에게 감
        self.append_jsonl("observations.jsonl", {"ts": now_kst(), "file": name, "sha256": digest, "kind": kind,
                                                 "popup_visible": popup_visible, "after_call": self.call_no})
        return f"sha256:{digest} ({name})"

    def log_call(self, request: dict, response: dict, request_id: str | None) -> int:
        self.call_no += 1
        n = f"{self.call_no:03d}"
        self.write_json(f"calls/{n}_request.json", request)
        self.write_json(f"calls/{n}_response.json", {"received_at": now_kst(), "provider_request_id": request_id,
                                                      "response": response})
        return self.call_no

    def log_action(self, name: str, args: dict, outcome: str) -> None:
        self.append_jsonl("actions.jsonl", {"ts": now_kst(), "call": self.call_no, "action": name, "args": args,
                                            "outcome": outcome})

    def finish(self, outcome: dict, extra: dict) -> None:
        lines = []
        if mockup.EVENT_LOG.exists():
            for line in mockup.EVENT_LOG.read_text(encoding="utf-8").splitlines():
                if line.strip() and json.loads(line).get("run_id") == self.run_id:
                    lines.append(line)
        (self.dir / "site_events.jsonl").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8", newline="\n")
        self.write_json("result.json", {**outcome, "calls": self.call_no, "observations": self.shot_no,
                                        "elapsed_sec": round(self.elapsed(), 1)})
        m = self.cfg["model"]
        self.write_json("meta.json", {
            "run_id": self.run_id, "started_at": self.started, "finished_at": now_kst(),
            "official": False, "purpose": self.cfg["purpose"],
            "model": {"provider": m["provider"], "id": m["id"], **{k: v for k, v in m.items() if k not in ("provider", "id")}},
            "assignment": self.assignment,
            "run_config": {"path": self.cfg["_path"], "version": self.cfg["version"], "sha256": self.cfg["_sha256"]},
            "conditions_version": self.cfg["conditions"], "content_version": self.cfg["content"],
            "prompts": self.prompts, "task_text": self.task,
            "episode_limits": self.cfg["episode"], "viewport": self.cfg["viewport"],
            "browser_args": mockup.BROWSER_ARGS, "prices_version": load_prices()["version"],
            "code": self.code, "environment": environment_info(), **extra,
        })
        write_manifest(self.dir)


def write_manifest(run_dir: Path) -> None:
    lines = [f"{sha256_file(p)}  {p.relative_to(run_dir).as_posix()}"
             for p in sorted(run_dir.rglob("*")) if p.is_file() and p.name != "manifest.sha256"]
    (run_dir / "manifest.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


# ---------------------------------------------------------------- 브라우저

class Browser:
    """목업만 접근하는 Chromium. 관찰(스크린샷)마다 팝업이 떠 있었는지 DOM에서 확인해 함께 남김."""

    def __init__(self, run: Run):
        from playwright.sync_api import sync_playwright
        self.run = run
        self.origin = run.cfg["mockup_origin"]
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=True, args=mockup.BROWSER_ARGS)
        self._ctx = self._browser.new_context(viewport=run.cfg["viewport"], device_scale_factor=1, locale="ko-KR")
        self.blocked: list[str] = []
        self._ctx.route("**/*", self._guard)
        self.page = self._ctx.new_page()
        self.page.goto(f"{self.origin}/?s={run.run_id}", wait_until="networkidle")
        self.page.wait_for_function("document.getElementById('badge') && document.getElementById('badge').textContent.length > 0")
        self.cursor = (0, 0)

    def _guard(self, route):
        if route.request.url.startswith(self.origin + "/"):
            route.continue_()
        else:
            self.blocked.append(route.request.url)
            route.abort()

    def popup_visible(self) -> bool:
        try:
            return bool(self.page.evaluate("(() => { const o = document.getElementById('overlay'); return !!o && !o.hidden; })()"))
        except Exception:
            return False

    def observe(self, kind: str = "screenshot", clip: dict | None = None) -> tuple[str, str]:
        """(base64, 기록용 참조)를 돌려줌."""
        png = self.page.screenshot(type="png", clip=clip) if clip else self.page.screenshot(type="png")
        ref = self.run.save_observation(png, kind, self.popup_visible())
        return base64.b64encode(png).decode("ascii"), ref

    def close(self) -> None:
        self._ctx.close()
        self._browser.close()
        self._pw.stop()


KEY_MAP = {
    "return": "Enter", "enter": "Enter", "tab": "Tab", "escape": "Escape", "esc": "Escape",
    "backspace": "Backspace", "delete": "Delete", "space": " ", "up": "ArrowUp", "down": "ArrowDown",
    "left": "ArrowLeft", "right": "ArrowRight", "home": "Home", "end": "End", "pageup": "PageUp",
    "pagedown": "PageDown", "ctrl": "Control", "control": "Control", "alt": "Alt", "shift": "Shift",
    "super": "Meta", "cmd": "Meta", "meta": "Meta",
}


def to_playwright_key(combo: str) -> str:
    parts = [p.strip() for p in combo.replace(" ", "+").split("+") if p.strip()]
    return "+".join(KEY_MAP.get(p.lower(), p) for p in parts)
