"""실행 결과 폴더의 원자료에서 결과표를 다시 계산함 (docs/evidence.md 3, 4장).

- 토큰과 비용은 비용 장부가 아니라 응답 원문의 usage에서 새로 계산
- 행동과 노출은 judge.py로 사이트 로그와 관찰 기록에서 판정
- 해시 목록 검증, 필수 기록 항목(workplan P4 할 일 4) 채움 여부 확인
- 결과: <data_dir>/SUMMARY.md, <data_dir>/summary.json

사용: .venv/Scripts/python.exe runner/summarize.py data/p4-fake
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common import REPO, cost_of, now_kst, sha256_file  # noqa: E402
from judge import JUDGE_VERSION, judge  # noqa: E402

REQUIRED = ["run_id", "started_at", "model_id", "served_models", "git_commit", "condition", "content_id",
            "button_order", "seed", "observations", "actions", "final_text", "site_events", "tokens", "cost_usd",
            "elapsed_sec", "end_reason"]


def verify_manifest(run_dir: Path) -> str:
    m = run_dir / "manifest.sha256"
    if not m.exists():
        return "목록 없음"
    listed, bad = set(), 0
    for line in m.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        listed.add(rel)
        if not (run_dir / rel).exists() or sha256_file(run_dir / rel) != digest:
            bad += 1
    extra = [p for p in run_dir.rglob("*") if p.is_file() and p.name != "manifest.sha256"
             and p.relative_to(run_dir).as_posix() not in listed]
    return "일치" if not bad and not extra else f"불일치 {bad}, 목록 밖 {len(extra)}"


def usage(run_dir: Path, model: str) -> dict:
    t = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
    cost = 0.0
    for f in sorted((run_dir / "calls").glob("*_response.json")):
        r = json.loads(f.read_text(encoding="utf-8"))["response"]
        u = r.get("usage") if isinstance(r, dict) else None
        if not u:
            continue
        i, o = u["input_tokens"], u["output_tokens"]
        cr, cw = u.get("cache_read_input_tokens") or 0, u.get("cache_creation_input_tokens") or 0
        t["input"] += i; t["output"] += o; t["cache_read"] += cr; t["cache_write"] += cw
        cost += cost_of(model, i, o, cr, cw)
    return {"tokens": t, "cost_usd": round(cost, 6)}


def row(run_dir: Path) -> dict:
    meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
    res = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    a = meta["assignment"]
    u = usage(run_dir, meta["model"]["id"])
    n_obs = sum(1 for l in (run_dir / "observations.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()) \
        if (run_dir / "observations.jsonl").exists() else 0
    n_act = sum(1 for l in (run_dir / "actions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()) \
        if (run_dir / "actions.jsonl").exists() else 0
    n_site = sum(1 for l in (run_dir / "site_events.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())
    r = {"run_id": meta["run_id"], "started_at": meta["started_at"], "model_id": meta["model"]["id"],
         "served_models": res.get("served_models"), "git_commit": meta["code"]["git_commit"],
         "git_dirty": meta["code"]["git_dirty"], "condition": a["condition"], "content_id": a["content_id"],
         "button_order": a["button_order"], "seed": a.get("seed"), "fake_behavior": a.get("fake_behavior"),
         "observations": n_obs, "actions": n_act, "final_text": res.get("final_text"), "site_events": n_site,
         "tokens": u["tokens"], "cost_usd": u["cost_usd"], "elapsed_sec": res["elapsed_sec"], "calls": res["calls"],
         "end_reason": res.get("end_reason"), "error": res.get("error"), "ask_user_calls": len(res.get("ask_user_calls", [])),
         "blocked_requests": len(meta.get("blocked_requests", [])), "manifest": verify_manifest(run_dir),
         "judge": judge(run_dir)}
    r["missing_fields"] = [k for k in REQUIRED if r.get(k) in (None, "", [])
                           and not (k == "final_text" and r["end_reason"] in ("max_steps", "max_time", "error"))]
    return r


def main() -> int:
    data_dir = (REPO / sys.argv[1]).resolve()
    runs = sorted(p for p in data_dir.iterdir() if p.is_dir() and (p / "meta.json").exists())
    rows = [row(p) for p in runs]
    (data_dir / "summary.json").write_text(json.dumps({"generated_at": now_kst(), "judge_version": JUDGE_VERSION,
                                                       "runs": rows}, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    metas = [json.loads((p / "meta.json").read_text(encoding="utf-8")) for p in runs]
    first = metas[0] if metas else {}
    lines = [
        f"# 실행 결과 요약: `{data_dir.relative_to(REPO).as_posix()}`", "",
        "| 항목 | 값 |", "|---|---|",
        f"| 실행 날짜 (KST) | {rows[0]['started_at'][:19] if rows else '-'} ~ {rows[-1]['started_at'][:19] if rows else '-'} |",
        f"| 구분 | {first.get('purpose', '-')} |",
        f"| 모델 ID | {', '.join(sorted({r['model_id'] for r in rows}))} (응답에 기록된 모델: {', '.join(sorted({m for r in rows for m in (r['served_models'] or [])}))}) |",
        f"| 프롬프트 버전 | {', '.join(f'{k}={v['version']}' for k, v in first.get('prompts', {}).items())} |",
        f"| 설정 | {first.get('run_config', {}).get('version', '-')}, {first.get('conditions_version', '-')}, {first.get('content_version', '-')} |",
        f"| 코드 | {', '.join(sorted({r['git_commit'][:7] + (' (커밋 안 된 변경 있음)' if r['git_dirty'] else '') for r in rows}))} |",
        f"| 실행 수 | {len(rows)} |",
        f"| 판정 | `{JUDGE_VERSION}` (docs/codebook.md 1장) |",
        f"| 요약 생성 | {now_kst()[:19]} |", "",
        "## 실행별", "",
        "| run_id | 조건 | 내용 | 버튼 순서 | 가짜 행동 | 종료 | 호출 | 초 | 노출 | 행동 | 2차 | 제외 | 비용 $ | 해시 | 빠진 항목 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        j = r["judge"]
        lines.append(f"| {r['run_id']} | {r['condition']} | {r['content_id']} | {r['button_order']} | {r['fake_behavior'] or '-'} "
                     f"| {r['end_reason']} | {r['calls']} | {r['elapsed_sec']} | {'예' if j['exposed'] else '아니오'} "
                     f"| {j['behavior'] or '-'} | {j['secondary_behavior'] or '-'} | {j['excluded'] or '-'} | {r['cost_usd']:.4f} "
                     f"| {r['manifest']} | {', '.join(r['missing_fields']) or '없음'} |")
    total = sum(r["cost_usd"] for r in rows)
    lines += ["", f"- 총비용 (응답 usage에서 재계산): ${total:.4f}",
              f"- 외부 요청 차단 기록: {sum(r['blocked_requests'] for r in rows)}건",
              "- 토큰, 최종 보고 텍스트, 판정 세부는 `summary.json`. 원자료는 실행별 폴더, 해시는 각 폴더의 `manifest.sha256`",
              "- 재계산: `.venv/Scripts/python.exe runner/summarize.py " + data_dir.relative_to(REPO).as_posix() + "`"]
    (data_dir / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
