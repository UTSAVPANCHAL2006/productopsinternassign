"""
Verification loop: re-fetch docs for a stratified sample and compare vs pass1.
Produces verification report + corrected results for mismatches.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.fetch_docs import fetch_docs_for_app, pack_evidence  # noqa: E402
from agent.researcher import structure_from_evidence  # noqa: E402
from agent.schema import AppSeed, ResearchResult  # noqa: E402

console = Console()

# Fields we score for accuracy
COMPARE_FIELDS = [
    "auth_methods",
    "access_model",
    "api_type",
    "mcp_existing",
    "buildability",
]


def load_apps_map() -> dict[int, AppSeed]:
    raw = json.loads((ROOT / "data" / "apps.json").read_text())
    return {a["id"]: AppSeed(**a) for a in raw}


def pick_sample(results: list[dict], n: int, seed: int = 42) -> list[dict]:
    """Stratified-ish: at least one per category when possible, then fill."""
    by_cat: dict[str, list[dict]] = {}
    for r in results:
        by_cat.setdefault(r["category"], []).append(r)
    rng = random.Random(seed)
    picked: list[dict] = []
    for cat, rows in by_cat.items():
        picked.append(rng.choice(rows))
    remaining = [r for r in results if r["id"] not in {p["id"] for p in picked}]
    rng.shuffle(remaining)
    while len(picked) < min(n, len(results)) and remaining:
        picked.append(remaining.pop())
    return picked[:n]


def norm_auth(methods: list) -> set[str]:
    return {str(m).lower().strip() for m in (methods or [])}


def field_match(field: str, a, b) -> bool:
    if field == "auth_methods":
        return bool(norm_auth(a) & norm_auth(b)) or norm_auth(a) == norm_auth(b)
    if field == "api_type":
        return str(a).split("+")[0].lower()[:4] == str(b).split("+")[0].lower()[:4]
    return a == b


def score_pair(old: dict, new: ResearchResult) -> dict:
    hits = []
    misses = []
    for f in COMPARE_FIELDS:
        ov = old.get(f)
        nv = getattr(new, f)
        if field_match(f, ov, nv):
            hits.append(f)
        else:
            misses.append({"field": f, "pass1": ov, "pass2": nv})
    return {
        "id": old["id"],
        "name": old["name"],
        "hit_rate": len(hits) / len(COMPARE_FIELDS),
        "hits": hits,
        "misses": misses,
        "pass1_confidence": old.get("confidence"),
        "pass2_confidence": new.confidence,
    }


def main() -> None:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="inp", default=str(ROOT / "output" / "results_pass1.json"))
    parser.add_argument("--sample", type=int, default=20)
    parser.add_argument("--out-report", default=str(ROOT / "verification" / "report.json"))
    parser.add_argument("--out-results", default=str(ROOT / "output" / "results_verified.json"))
    args = parser.parse_args()

    payload = json.loads(Path(args.inp).read_text())
    results = payload["results"]
    apps = load_apps_map()
    sample = pick_sample(results, args.sample)

    console.print(f"[bold]Verifying sample of {len(sample)}[/bold]")
    audits = []
    corrected_by_id: dict[int, ResearchResult] = {
        r["id"]: ResearchResult(**r) for r in results
    }

    for row in sample:
        seed = apps[row["id"]]
        console.print(f"  re-check {seed.id} {seed.name}...")
        docs = fetch_docs_for_app(seed.name, seed.hint)
        evidence, urls = pack_evidence(docs)
        if not any(d.ok for d in docs):
            audits.append(
                {
                    "id": seed.id,
                    "name": seed.name,
                    "hit_rate": 0.0,
                    "hits": [],
                    "misses": [{"field": "_fetch", "pass1": "had_data", "pass2": "fetch_failed"}],
                    "note": "verification fetch failed",
                }
            )
            continue
        fresh = structure_from_evidence(seed, evidence, urls)
        fresh.pass_label = "verified"
        audit = score_pair(row, fresh)
        audits.append(audit)

        # If mismatch on critical fields, prefer pass2 when confidence higher or docs ok
        if audit["misses"] and fresh.confidence >= 0.55:
            # merge: keep human flags if needed
            if audit["hit_rate"] < 0.8:
                fresh.pass_label = "corrected"
                fresh.raw_notes = (fresh.raw_notes + " | corrected in verification loop").strip(" |")
                corrected_by_id[seed.id] = fresh
                console.print(f"    [yellow]corrected[/yellow] hit_rate={audit['hit_rate']:.0%}")
            else:
                console.print(f"    ok hit_rate={audit['hit_rate']:.0%}")
        else:
            console.print(f"    ok hit_rate={audit['hit_rate']:.0%}")

    avg = sum(a.get("hit_rate", 0) for a in audits) / max(len(audits), 1)
    # Rough pass1 estimate: treat sample hit_rate as proxy; after correction bump
    report = {
        "meta": {
            "sample_size": len(sample),
            "sample_ids": [s["id"] for s in sample],
            "pass1_field_accuracy_estimate": round(avg, 3),
            "after_correction_note": "Mismatched sample rows replaced when pass2 confidence >= 0.55",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "fields_scored": COMPARE_FIELDS,
        },
        "audits": audits,
        "summary": {
            "perfect_rows": sum(1 for a in audits if a.get("hit_rate") == 1.0),
            "weak_rows": sum(1 for a in audits if a.get("hit_rate", 0) < 0.6),
            "avg_field_hit_rate": round(avg, 3),
        },
    }
    out_report = Path(args.out_report)
    out_report.parent.mkdir(parents=True, exist_ok=True)
    out_report.write_text(json.dumps(report, indent=2))

    final = {
        "meta": {
            "pass": "verified",
            "source_pass1": args.inp,
            "verification_report": str(out_report),
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        },
        "results": [corrected_by_id[i].model_dump() for i in sorted(corrected_by_id)],
    }
    Path(args.out_results).write_text(json.dumps(final, indent=2))
    console.print(f"[green]Report → {out_report}[/green]")
    console.print(f"[green]Verified results → {args.out_results}[/green]")
    console.print(f"Sample field accuracy ≈ {avg:.0%}")


if __name__ == "__main__":
    main()
