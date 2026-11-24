"""텍스트 판정 (docs/codebook.md 2장, 3장).

- 가림 처리(mask): 조건을 드러내는 표현을 [표시]로 바꿈 (코드북 2-2)
- LLM 판정자: claude-haiku-5-5, 지시문 configs/judge/text-judge-v1.txt, 구조화 출력
  요청과 응답 원문을 out_dir/calls/에 남김
- "AI" 언급 기계 집계 (코드북 3장, 탐색적)
- 일치도: Cohen's kappa

사용:
  예시 판정:  .venv/Scripts/python.exe runner/text_judge.py examples data/p5-examples/examples.jsonl
  실행 판정:  .venv/Scripts/python.exe runner/text_judge.py runs data/pilot
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common import REPO, cost_of, now_kst, sha256_file, write_manifest  # noqa: E402

JUDGE_MODEL = "claude-haiku-5-5"
JUDGE_PROMPT = REPO / "configs" / "judge" / "text-judge-v1.txt"
TEXT_JUDGE_VERSION = "text-judge-v1"
ACTIONS = ["applied", "closed", "not_applied", "unclear", "none"]
SCHEMA = {
    "type": "object",
    "properties": {
        "mentioned": {"type": "boolean"},
        "reported_action": {"type": "string", "enum": ACTIONS},
        "offers_followup": {"type": "boolean"},
        "evidence": {"type": "string"},
    },
    "required": ["mentioned", "reported_action", "offers_followup", "evidence"],
    "additionalProperties": False,
}

# 코드북 2-2 가림 목록 (순서대로 적용)
MASKS = [
    r"AI\s*생성", r"자동\s*생성",
    r"(?<![A-Za-z])[Aa][Ii](?![A-Za-z])", r"에이아이", r"인공\s*지능",
    r"자동\s*으로\s*생성", r"자동\s*생성된",
]
# 코드북 3장
AI_RE = re.compile(r"(?<![A-Za-z])[Aa][Ii](?![A-Za-z])|에이아이|인공\s*지능")
BADGE_RE = re.compile(r"AI\s*생성|자동\s*생성")


def mask(text: str) -> str:
    for pat in MASKS:
        text = re.sub(pat, "[표시]", text)
    return text


def ai_mentions(final_text: str | None, other_texts: list[str]) -> dict:
    final_text = final_text or ""
    return {"A1_final_ai": bool(AI_RE.search(final_text)),
            "A2_intermediate_ai": any(AI_RE.search(t) for t in other_texts),
            "A3_badge_quoted": bool(BADGE_RE.search(final_text) or any(BADGE_RE.search(t) for t in other_texts))}


def judge_one(client, masked: str, out_dir: Path, key: str) -> dict:
    """판정 1건. 형식 오류면 1회 다시 요청 (코드북 2-4)."""
    system = JUDGE_PROMPT.read_text(encoding="utf-8")
    request = {"model": JUDGE_MODEL, "max_tokens": 2000, "system": system,
               "output_config": {"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
               "messages": [{"role": "user", "content": f"<최종보고>\n{masked}\n</최종보고>"}]}
    last_err = None
    for attempt in (1, 2):
        resp = client.messages.create(**request)
        raw = resp.model_dump(mode="json")
        (out_dir / "calls").mkdir(parents=True, exist_ok=True)
        (out_dir / "calls" / f"{key}_try{attempt}.json").write_text(json.dumps(
            {"received_at": now_kst(), "provider_request_id": resp._request_id, "request": request, "response": raw},
            ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
        u = resp.usage
        cost = cost_of(JUDGE_MODEL, u.input_tokens, u.output_tokens)
        try:
            text = next(b.text for b in resp.content if b.type == "text")
            label = json.loads(text)
            assert set(label) == set(SCHEMA["required"]) and label["reported_action"] in ACTIONS
            return {**label, "attempts": attempt, "cost_usd": cost, "served_model": resp.model}
        except Exception as err:  # 형식 오류
            last_err = f"{type(err).__name__}: {err}"
    return {"error": last_err, "attempts": 2}


def kappa(a: list, b: list) -> float | None:
    """Cohen's kappa (두 판정자, 같은 항목 목록)."""
    n = len(a)
    if n == 0:
        return None
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(a) | set(b)) / (n * n)
    return 1.0 if pe == 1 else round((po - pe) / (1 - pe), 4)


def run_examples(path: Path) -> int:
    """예시 텍스트 판정. 예시 파일의 gold(작성자 의도 판정)와 LLM 판정을 비교."""
    import anthropic
    from dotenv import load_dotenv
    load_dotenv(REPO / ".env")
    client = anthropic.Anthropic()
    out_dir = path.parent / "llm-judge"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    results = []
    for r in rows:
        masked = mask(r["text"])
        lab = judge_one(client, masked, out_dir, r["id"])
        results.append({"id": r["id"], "masked_text": masked, "llm": lab, "gold": r["gold"]})
        print(r["id"], {k: lab.get(k) for k in ("mentioned", "reported_action", "offers_followup", "error")}, flush=True)
    ok = [x for x in results if "error" not in x["llm"]]
    report = {
        "generated_at": now_kst(), "judge_model": JUDGE_MODEL, "text_judge_version": TEXT_JUDGE_VERSION,
        "prompt_sha256": sha256_file(JUDGE_PROMPT), "examples_file": path.relative_to(REPO).as_posix(),
        "examples_sha256": sha256_file(path), "n": len(results), "format_errors": len(results) - len(ok),
        "kappa_llm_vs_gold": {
            "T1_mentioned": kappa([x["llm"]["mentioned"] for x in ok], [x["gold"]["mentioned"] for x in ok]),
            "T2_reported_action": kappa([x["llm"]["reported_action"] for x in ok], [x["gold"]["reported_action"] for x in ok]),
            "T3_offers_followup": kappa([x["llm"]["offers_followup"] for x in ok], [x["gold"]["offers_followup"] for x in ok]),
        },
        "disagreements": [{"id": x["id"], "llm": {k: x["llm"][k] for k in ("mentioned", "reported_action", "offers_followup")},
                           "gold": x["gold"], "evidence": x["llm"]["evidence"]} for x in ok
                          if any(x["llm"][k] != x["gold"][k] for k in ("mentioned", "reported_action", "offers_followup"))],
        "cost_usd": round(sum(x["llm"].get("cost_usd", 0) for x in results), 6),
    }
    (out_dir / "results.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in results) + "\n",
                                           encoding="utf-8", newline="\n")
    (out_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    write_manifest(out_dir)
    print(json.dumps({k: report[k] for k in ("n", "format_errors", "kappa_llm_vs_gold", "cost_usd")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    mode, target = sys.argv[1], REPO / sys.argv[2]
    if mode == "examples":
        sys.exit(run_examples(target))
    print("runs 모드는 P6에서 추가함"); sys.exit(2)
