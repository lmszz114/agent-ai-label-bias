"""P4 실행 장치 진입점.

사용:
  가짜 모델:  .venv/Scripts/python.exe runner/run.py --config configs/run/p4-fake-v1.json --fake-behaviors apply,close,ask_then_close,ignore --allow-dirty
  실제 모델:  .venv/Scripts/python.exe runner/run.py --config configs/run/p4-check-v1.json --n 3 --seed 20261124

- 목업 서버(python -I mockup/server.py)가 떠 있어야 함
- 조건 배정: 조건 2 × 내용 15 × 버튼 순서 2 = 60칸을 시드로 섞고 앞에서부터 씀 (schedule.json에 전부 남김)
- 커밋 안 된 코드로는 실제 모델을 돌리지 않음. --allow-dirty는 가짜 모델에만 허용
- API 키는 .env에서 환경변수로 읽음 (값을 출력하지 않음)
"""

from __future__ import annotations

import argparse
import itertools
import json
import random
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common import REPO, BudgetExceeded, Ledger, Run, code_state, load_config, load_prompts, mockup, now_kst  # noqa: E402


def schedule(seed: int) -> list[dict]:
    conds = list(json.loads(mockup.CONDITIONS.read_text(encoding="utf-8"))["conditions"])
    orders = json.loads(mockup.CONDITIONS.read_text(encoding="utf-8"))["button_orders"]
    cells = [{"condition": c, "content_id": k, "button_order": o}
             for c, k, o in itertools.product(conds, mockup.content_ids(), orders)]
    random.Random(seed).shuffle(cells)
    return [{**c, "seed": seed, "index": i} for i, c in enumerate(cells)]


def balanced(plan: list[dict], per_condition: int, seed: int) -> list[dict]:
    """조건마다 per_condition개, 그 안에서 버튼 순서를 절반씩 (명세서 6장). 섞인 배정표 앞에서부터 고르고 실행 순서를 다시 섞음."""
    picked, need, used = [], {}, set()
    for cell in plan:
        key = (cell["condition"], cell["button_order"])
        need.setdefault(key, per_condition // 2)
        # 같은 조건 안에서 내용이 겹치지 않게 함 (표본 독립성, 명세서 5장)
        if need[key] > 0 and (cell["condition"], cell["content_id"]) not in used:
            picked.append(cell); need[key] -= 1; used.add((cell["condition"], cell["content_id"]))
    random.Random(seed + 1).shuffle(picked)
    return [{**c, "run_order": i} for i, c in enumerate(picked)]


def server_up(origin: str) -> bool:
    try:
        with urllib.request.urlopen(origin + "/", timeout=3) as r:
            return r.status == 200
    except OSError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--seed", type=int, default=20261124)
    ap.add_argument("--start", type=int, default=0, help="배정표에서 시작할 위치")
    ap.add_argument("--per-condition", type=int, default=0, help="조건마다 이 횟수씩 균형 배정 (버튼 순서 절반씩). 0이면 배정표 순서대로 --n회")
    ap.add_argument("--fake-behaviors", default="", help="가짜 모델 전용: 실행마다 쓸 팝업 행동 (쉼표 구분)")
    ap.add_argument("--allow-dirty", action="store_true", help="가짜 모델 전용")
    args = ap.parse_args()

    cfg = load_config((REPO / args.config).resolve() if not args.config.is_absolute() else args.config)
    provider = cfg["model"]["provider"]
    data_dir = REPO / cfg["data_dir"]
    code = code_state(data_dir)
    if code["git_dirty"] and not (args.allow_dirty and provider == "fake"):
        print("커밋 안 된 변경이 있어 실행하지 않음 (docs/evidence.md 7장):")
        print("\n".join(code["git_dirty_files"]))
        return 2
    if not server_up(cfg["mockup_origin"]):
        print("목업 서버가 꺼져 있음: python -I mockup/server.py 먼저 실행")
        return 2

    if provider == "anthropic":
        from dotenv import load_dotenv
        load_dotenv(REPO / ".env")
        import agent_anthropic as agent
    elif provider == "fake":
        import agent_fake as agent
    else:
        print(f"지원하지 않는 provider: {provider}"); return 2

    behaviors = [b for b in args.fake_behaviors.split(",") if b]
    plan = schedule(args.seed)
    if args.per_condition:
        plan = balanced(plan, args.per_condition, args.seed)
        args.start = 0
    n = len(behaviors) if behaviors else (len(plan) if args.per_condition else args.n)
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "schedule.json").write_text(json.dumps({"seed": args.seed, "per_condition": args.per_condition,
                                                        "created_at": now_kst(), "cells": plan},
                                                       ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    prompts = load_prompts(cfg)
    ledger = Ledger(data_dir, cfg["budget_usd"])
    for i in range(n):
        a = dict(plan[args.start + i])
        if behaviors:
            a["fake_behavior"] = behaviors[i]
        try:
            ledger.check()
        except BudgetExceeded as e:
            print(e); return 3
        run = Run(cfg, prompts, a, code)
        outcome = agent.run_once(run, ledger)
        res = json.loads((run.dir / "result.json").read_text(encoding="utf-8"))
        print(json.dumps({"run_id": run.run_id, "assignment": a, "end": outcome.get("end_reason"),
                          "calls": res["calls"], "sec": res["elapsed_sec"], "error": outcome.get("error"),
                          "ledger_total_usd": round(ledger.total(), 4)}, ensure_ascii=False), flush=True)
        if outcome.get("end_reason") == "error" and i == 0 and provider != "fake":
            print("첫 회차가 오류로 끝나 나머지를 돌리지 않음")
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
