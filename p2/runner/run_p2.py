"""P2 기술 검증 실행기.

사용: .venv\\Scripts\\python.exe p2/runner/run_p2.py --provider anthropic --n 1
- 시험 페이지 서버(127.0.0.1:8765)가 떠 있어야 함
- API 키는 .env에서 환경변수로 읽음 (값을 출력하지 않음)
- 누적 비용이 --cap(기본 $15)에 닿으면 멈춤
- 버튼 순서는 회차마다 번갈아 배정 (close_first, apply_first, ...)
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv  # noqa: E402

from common import REPO, BudgetExceeded, Ledger, Run  # noqa: E402

PROVIDERS = {
    "anthropic": ("anthropic_agent", "claude-sonnet-5-5"),
    "openai": ("openai_agent", "gpt-6.2-sol"),
    "google": ("gemini_agent", "gemini-4-hydrogen"),
}


def server_up() -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8765/", timeout=3) as r:
            return r.status == 200
    except OSError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=PROVIDERS, required=True)
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--cap", type=float, default=15.0)
    ap.add_argument("--max-calls", type=int, default=25)
    ap.add_argument("--max-seconds", type=float, default=600)
    args = ap.parse_args()

    # P4부터는 커밋 안 된 변경이 있으면 거부하도록 바꿈 (docs/evidence.md 7장). P2는 기록만 함
    load_dotenv(REPO / ".env")
    if not server_up():
        print("시험 페이지 서버가 꺼져 있음: python -I p2/testpage/server.py 먼저 실행")
        return 2

    module_name, model = PROVIDERS[args.provider]
    module = __import__(module_name)
    ledger = Ledger(args.cap)
    for i in range(args.n):
        order = "close_first" if i % 2 == 0 else "apply_first"
        run = Run(provider=args.provider, model=model, button_order=order)
        try:
            ledger.check()
        except BudgetExceeded as e:
            print(e); return 3
        outcome = module.run_once(run, ledger, args.max_calls, args.max_seconds)
        result = json.loads((run.dir / "result.json").read_text(encoding="utf-8"))
        print(json.dumps({"run_id": run.run_id, "order": order, "end": outcome.get("end_reason"),
                          "calls": result["calls"], "sec": result["elapsed_sec"],
                          "ask_user": len(outcome.get("ask_user_calls", [])),
                          "error": outcome.get("error"),
                          "ledger_total_usd": round(ledger.total(), 4)}, ensure_ascii=False))
        if outcome.get("end_reason") == "error" and i == 0:
            print("첫 회차가 오류로 끝나 나머지 회차를 돌리지 않음")
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
