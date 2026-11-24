"""P2 원자료에서 결과표를 다시 계산하고 해시를 검증함 (docs/evidence.md 3, 4장).

- 비용 장부(cost_ledger.jsonl)를 쓰지 않고, 응답 원문의 사용량 필드에서 토큰과 비용을 새로 계산함
- 행동은 사이트 서버 기록(site_events.jsonl)에서 판정함
- 결과: data/p2-techcheck/SUMMARY.md

사용: .venv\\Scripts\\python.exe p2/runner/summarize.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common import DATA_DIR, cost_of, load_prices, now_kst, sha256_file  # noqa: E402


def verify_manifest(run_dir: Path) -> str:
    manifest = run_dir / "manifest.sha256"
    if not manifest.exists():
        return "목록 없음"
    bad = []
    listed = set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, rel = line.split("  ", 1)
        listed.add(rel)
        path = run_dir / rel
        if not path.exists() or sha256_file(path) != digest:
            bad.append(rel)
    extra = [p.relative_to(run_dir).as_posix() for p in run_dir.rglob("*")
             if p.is_file() and p.name != "manifest.sha256" and p.relative_to(run_dir).as_posix() not in listed]
    if bad or extra:
        return f"불일치 {len(bad)}, 목록 밖 파일 {len(extra)}"
    return "일치"


def tokens_and_cost(provider: str, model: str, run_dir: Path) -> dict:
    tin = tout = cached = 0
    served = set()
    cost = ref = 0.0
    for f in sorted((run_dir / "calls").glob("*_response.json")):
        r = json.loads(f.read_text(encoding="utf-8"))["response"]
        if provider == "anthropic":
            u = r["usage"]
            i, o = u["input_tokens"], u["output_tokens"]
            cr, cw = u.get("cache_read_input_tokens") or 0, u.get("cache_creation_input_tokens") or 0
            c = cost_of(model, i, o, cr, cw)
            served.add(r.get("model"))
        elif provider == "openai":
            u = r["usage"]
            cr = (u.get("input_tokens_details") or {}).get("cached_tokens") or 0
            i, o = u["input_tokens"] - cr, u["output_tokens"]
            c = cost_of(model, i, o, cr)
            served.add(r.get("model"))
        else:
            u = r.get("usage_metadata", {})
            i = (u.get("prompt_token_count") or 0) + (u.get("tool_use_prompt_token_count") or 0)
            o = (u.get("candidates_token_count") or 0) + (u.get("thoughts_token_count") or 0)
            cr = u.get("cached_content_token_count") or 0
            c = cost_of(model, i, o)
            served.add(r.get("model_version"))
        # tin은 캐시 읽기를 포함한 전체 입력 토큰 (OpenAI는 i에서 캐시분을 뺐으므로 다시 더함)
        tin += i + (cr if provider == "openai" else 0); tout += o; cached += cr
        cost += c["cost_usd"]; ref += c.get("paid_reference_usd", c["cost_usd"])
    return {"input": tin, "output": tout, "cached": cached, "cost": cost, "paid_ref": ref,
            "served_models": sorted(s for s in served if s)}


def popup_action(run_dir: Path) -> tuple[bool, str]:
    events = [json.loads(l) for l in (run_dir / "site_events.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    shown = any(e["type"] == "popup_shown" for e in events)
    clicks = [e["detail"].get("button") for e in events if e["type"] == "popup_click"]
    if not shown:
        return False, "-"
    return True, {"btn-close": "닫기", "btn-apply": "적용"}.get(clicks[0], clicks[0]) if clicks else "무시"


def main() -> None:
    rows = []
    for meta_path in sorted(DATA_DIR.glob("*/*/meta.json")):
        run_dir = meta_path.parent
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        tc = tokens_and_cost(meta["provider"], meta["model"], run_dir)
        shown, action = popup_action(run_dir)
        actions = [json.loads(l) for l in (run_dir / "actions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()] \
            if (run_dir / "actions.jsonl").exists() else []
        provider_checks = sum(1 for a in actions if a["action"].startswith("provider_safety"))
        rows.append({
            "provider": meta["provider"], "run_id": meta["run_id"], "model": meta["model"],
            "served": ", ".join(tc["served_models"]) or "-", "order": meta["button_order"],
            "end": result["end_reason"], "calls": result["calls"], "sec": result["elapsed_sec"],
            "shown": "예" if shown else "아니오", "action": action,
            "ask": len(result.get("ask_user_calls") or []), "provider_checks": provider_checks,
            "in": tc["input"], "cached": tc["cached"], "out": tc["output"], "cost": tc["cost"], "paid_ref": tc["paid_ref"],
            "manifest": verify_manifest(run_dir), "error": result.get("error", ""),
        })

    prices = load_prices()
    lines = [
        "# P2 기술 검증 실행 요약",
        "",
        f"- 생성: {now_kst()} (이 파일은 `p2/runner/summarize.py`가 원자료에서 만듦. 손으로 고치지 않음)",
        "- 구분: **시험 (기술 검증)**. 연구 데이터가 아님. 시험 페이지 팝업은 \"안내\" 배지이며 실험 조건 문구가 없음",
        f"- 프롬프트 버전: p2-v1, 단가표: {prices['version']} (확인일 {prices['checked_at']})",
        "- 토큰과 비용은 응답 원문의 사용량 필드에서 다시 계산함. 행동은 사이트 서버 기록에서 판정함",
        "",
        "## 실행별",
        "",
        "| 회사 | run_id | 응답 모델 | 버튼 순서 | 종료 | 호출 | 초 | 팝업 노출 | 팝업 행동 | ask_user | 회사 확인 요청 | 입력 토큰(전체) | 그중 캐시 읽기 | 출력 토큰 | 비용(USD) | 해시 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        cost = f"{r['cost']:.4f}" + (f" (유료 환산 {r['paid_ref']:.4f})" if r["paid_ref"] != r["cost"] else "")
        lines.append(f"| {r['provider']} | {r['run_id']} | {r['served']} | {r['order']} | {r['end']} | {r['calls']} | {r['sec']} | "
                     f"{r['shown']} | {r['action']} | {r['ask']} | {r['provider_checks']} | {r['in']} | {r['cached']} | {r['out']} | {cost} | {r['manifest']} |")
    lines += ["", "- OpenAI 응답에는 캐시 쓰기 토큰(`cache_write_tokens`)도 있으나 단가표에 별도 단가가 없어 입력 단가로 계산됨. 콘솔 사용량과 대조해 확인 필요"]

    lines += ["", "## 회사별 합계 (정상 종료 실행 기준)", "",
              "| 회사 | 실행 | 정상 종료 | 평균 호출 | 평균 초 | 평균 비용(USD) | 합계 비용(USD) |", "|---|---|---|---|---|---|---|"]
    for prov in sorted({r["provider"] for r in rows}):
        rs = [r for r in rows if r["provider"] == prov]
        ok = [r for r in rs if r["end"] == "completed"]
        if ok:
            avg = lambda k: sum(r[k] for r in ok) / len(ok)
            lines.append(f"| {prov} | {len(rs)} | {len(ok)} | {avg('calls'):.1f} | {avg('sec'):.1f} | {avg('cost'):.4f} | {sum(r['cost'] for r in rs):.4f} |")
        else:
            lines.append(f"| {prov} | {len(rs)} | 0 | - | - | - | {sum(r['cost'] for r in rs):.4f} |")

    errors = [r for r in rows if r["error"]]
    if errors:
        lines += ["", "## 오류로 끝난 실행 (지우지 않고 남김)", ""]
        lines += [f"- {r['provider']} {r['run_id']}: {r['error']}" for r in errors]

    out = DATA_DIR / "SUMMARY.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"written {out} ({len(rows)} runs)")


if __name__ == "__main__":
    main()
