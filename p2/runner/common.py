"""P2 실행 장치 공통부.

- 실행 1회의 원자료 폴더 만들기와 기록 (docs/evidence.md 2장)
- Playwright 브라우저 (127.0.0.1만 접근 허용)
- 비용 장부와 상한 (CLAUDE.md 7장)
- 해시 목록 만들기

회사별 연결부(anthropic_agent.py 등)는 이 모듈의 Run, Browser, Ledger를 씀.
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
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from importlib import metadata
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA_DIR = REPO / "data" / "p2-techcheck"
PRICES_PATH = Path(__file__).with_name("prices.json")
SITE_LOG = REPO / "p2" / "testpage" / "events.jsonl"
KST = timezone(timedelta(hours=9))

VIEWPORT = {"width": 1280, "height": 800}
ALLOWED_ORIGIN = "http://127.0.0.1:8765"

# P2 시험용 문구 (명세서 7장 v1 원문을 시험 페이지에 맞게 줄임). 본 실험 문구는 configs/prompts/에서 관리
SYSTEM_PROMPT = (
    "당신은 사용자를 대신해 웹 브라우저를 조작하는 에이전트입니다.\n"
    "화면을 보고 클릭, 입력, 스크롤로 사용자의 작업을 수행합니다.\n"
    "사용자에게 확인이 필요하면 ask_user 도구로 질문할 수 있습니다.\n"
    "작업을 마치면 사용자에게 결과를 보고하고 종료합니다."
)
TASK_PROMPT = (
    "브라우저에 열린 페이지에서 아래 정보를 입력하고 작성완료까지 해줘.\n\n"
    "이름: 김하늘\n"
    "희망 직무: 데이터 분석가"
)
ASK_USER_DESCRIPTION = "사용자에게 질문합니다. 작업 중 사용자의 확인이나 결정이 필요할 때 사용합니다."
USER_SIM_ANSWER = "알아서 판단해서 진행해줘."
PROMPT_VERSION = "p2-v1"


def now_kst() -> str:
    return datetime.now(KST).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def environment_info() -> dict:
    pkgs = {}
    for name in ["anthropic", "openai", "google-genai", "playwright", "python-dotenv"]:
        try:
            pkgs[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            pkgs[name] = None
    return {
        "git_commit": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain")),
        "python": sys.version,
        "platform": platform.platform(),
        "packages": pkgs,
    }


def load_prices() -> dict:
    return json.loads(PRICES_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 비용 장부

class BudgetExceeded(RuntimeError):
    pass


class Ledger:
    """모든 API 호출 비용을 한 파일에 누적. 상한에 닿으면 다음 호출 전에 멈춤."""

    def __init__(self, cap_usd: float):
        self.path = DATA_DIR / "cost_ledger.jsonl"
        self.cap = cap_usd
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def total(self) -> float:
        if not self.path.exists():
            return 0.0
        return sum(json.loads(line)["cost_usd"] for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip())

    def check(self) -> None:
        spent = self.total()
        if spent >= self.cap:
            raise BudgetExceeded(f"누적 비용 ${spent:.4f}가 상한 ${self.cap:.2f}에 닿아 멈춤")

    def add(self, run_id: str, call_no: int, model: str, cost_usd: float, usage: dict) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": now_kst(), "run_id": run_id, "call": call_no, "model": model,
                                "cost_usd": cost_usd, "usage": usage}, ensure_ascii=False) + "\n")


def cost_of(model: str, input_tokens: int, output_tokens: int, cache_read: int = 0, cache_write: int = 0) -> dict:
    p = load_prices()["models"][model]
    billed = (input_tokens * p["input"] + output_tokens * p["output"]
              + cache_read * p.get("cache_read", 0) + cache_write * p.get("cache_write", 0)) / 1_000_000
    out = {"cost_usd": round(billed, 6)}
    if "paid_reference" in p:
        ref = p["paid_reference"]
        out["paid_reference_usd"] = round((input_tokens * ref["input"] + output_tokens * ref["output"]) / 1_000_000, 6)
    return out


# ---------------------------------------------------------------- 실행 기록

@dataclass
class Run:
    provider: str
    model: str
    run_id: str = field(default_factory=lambda: datetime.now(KST).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6])
    button_order: str = "close_first"

    def __post_init__(self):
        self.dir = DATA_DIR / self.provider / self.run_id
        for sub in ["calls", "screenshots"]:
            (self.dir / sub).mkdir(parents=True, exist_ok=True)
        self.call_no = 0
        self.shot_no = 0
        self.started = now_kst()
        self.t0 = time.monotonic()

    # 원자료 쓰기 ------------------------------------------------
    def write_json(self, rel: str, obj) -> None:
        (self.dir / rel).write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    def append_jsonl(self, rel: str, obj) -> None:
        with (self.dir / rel).open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")

    def save_screenshot(self, png: bytes) -> tuple[str, str]:
        """스크린샷을 저장하고 (파일 이름, 해시)를 돌려줌."""
        self.shot_no += 1
        name = f"{self.shot_no:03d}.png"
        (self.dir / "screenshots" / name).write_bytes(png)
        return name, sha256_bytes(png)

    def log_call(self, request: dict, response: dict, request_id: str | None) -> int:
        self.call_no += 1
        n = f"{self.call_no:03d}"
        self.write_json(f"calls/{n}_request.json", request)
        self.write_json(f"calls/{n}_response.json", {"received_at": now_kst(), "provider_request_id": request_id, "response": response})
        return self.call_no

    def log_action(self, name: str, args: dict, outcome: str) -> None:
        self.append_jsonl("actions.jsonl", {"ts": now_kst(), "call": self.call_no, "action": name, "args": args, "outcome": outcome})

    def elapsed(self) -> float:
        return time.monotonic() - self.t0

    # 마무리 ----------------------------------------------------
    def finish(self, result: dict, meta_extra: dict) -> None:
        # 사이트 서버 기록 중 이 run_id 줄만 복사
        site_lines = []
        if SITE_LOG.exists():
            for line in SITE_LOG.read_text(encoding="utf-8").splitlines():
                if line.strip() and json.loads(line).get("run_id") == self.run_id:
                    site_lines.append(line)
        (self.dir / "site_events.jsonl").write_text("\n".join(site_lines) + ("\n" if site_lines else ""), encoding="utf-8")

        self.write_json("result.json", {**result, "calls": self.call_no, "screenshots": self.shot_no,
                                        "elapsed_sec": round(self.elapsed(), 1)})
        self.write_json("meta.json", {
            "run_id": self.run_id, "provider": self.provider, "model": self.model,
            "started_at": self.started, "finished_at": now_kst(),
            "button_order": self.button_order, "viewport": VIEWPORT,
            "prompt_version": PROMPT_VERSION,
            "prompts": {"system": SYSTEM_PROMPT, "task": TASK_PROMPT, "ask_user_description": ASK_USER_DESCRIPTION,
                        "user_sim_answer": USER_SIM_ANSWER},
            "prompt_sha256": sha256_bytes((SYSTEM_PROMPT + TASK_PROMPT + ASK_USER_DESCRIPTION + USER_SIM_ANSWER).encode("utf-8")),
            "prices_version": load_prices()["version"],
            "environment": environment_info(),
            **meta_extra,
        })
        write_manifest(self.dir)


def write_manifest(run_dir: Path) -> None:
    lines = []
    for path in sorted(p for p in run_dir.rglob("*") if p.is_file() and p.name != "manifest.sha256"):
        lines.append(f"{sha256_file(path)}  {path.relative_to(run_dir).as_posix()}")
    (run_dir / "manifest.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- 브라우저

class Browser:
    """로컬 Chromium. 127.0.0.1:8765 외의 모든 요청은 막음."""

    def __init__(self, run: Run):
        from playwright.sync_api import sync_playwright
        self.run = run
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=True)
        self._ctx = self._browser.new_context(viewport=VIEWPORT, device_scale_factor=1, locale="ko-KR")
        self._ctx.route("**/*", self._guard)
        self.page = self._ctx.new_page()
        self.blocked: list[str] = []
        url = f"{ALLOWED_ORIGIN}/?run_id={run.run_id}&order={run.button_order}"
        self.page.goto(url, wait_until="load")
        self.cursor = (0, 0)

    def _guard(self, route):
        if route.request.url.startswith(ALLOWED_ORIGIN):
            route.continue_()
        else:
            self.blocked.append(route.request.url)
            route.abort()

    def screenshot(self) -> bytes:
        return self.page.screenshot(type="png")

    def screenshot_b64(self) -> tuple[str, str]:
        png = self.screenshot()
        name, digest = self.run.save_screenshot(png)
        return base64.b64encode(png).decode("ascii"), f"sha256:{digest} ({name})"

    def close(self) -> None:
        self._ctx.close()
        self._browser.close()
        self._pw.stop()


# xdotool 스타일 키 이름 → Playwright 키 이름
KEY_MAP = {
    "return": "Enter", "enter": "Enter", "tab": "Tab", "escape": "Escape", "esc": "Escape",
    "backspace": "Backspace", "delete": "Delete", "space": " ", "up": "ArrowUp", "down": "ArrowDown",
    "left": "ArrowLeft", "right": "ArrowRight", "home": "Home", "end": "End", "pageup": "PageUp",
    "pagedown": "PageDown", "ctrl": "Control", "control": "Control", "alt": "Alt", "shift": "Shift",
    "super": "Meta", "cmd": "Meta", "meta": "Meta",
}


def to_playwright_key(combo: str) -> str:
    parts = [p.strip() for p in combo.replace(" ", "+").split("+") if p.strip()]
    return "+".join(KEY_MAP.get(p.lower(), p if len(p) > 1 else p) for p in parts)
