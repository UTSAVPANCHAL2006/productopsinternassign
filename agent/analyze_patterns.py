"""Aggregate patterns from verified research results → patterns.json."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="inp", default=str(ROOT / "output" / "results_final.json"))
    parser.add_argument("--out", default=str(ROOT / "output" / "patterns.json"))
    args = parser.parse_args()

    payload = json.loads(Path(args.inp).read_text())
    rows = payload["results"]

    auth_c = Counter()
    access_c = Counter()
    build_c = Counter()
    api_c = Counter()
    mcp_n = 0
    human_n = 0
    by_cat = defaultdict(lambda: {"n": 0, "ready": 0, "outreach": 0, "self_serve": 0, "gated": 0})

    for r in rows:
        for a in r.get("auth_methods") or []:
            auth_c[a] += 1
        access_c[r.get("access_model", "unclear")] += 1
        build_c[r.get("buildability", "unknown")] += 1
        api_c[r.get("api_type", "unknown")] += 1
        if r.get("mcp_existing"):
            mcp_n += 1
        if r.get("human_needed"):
            human_n += 1
        cat = r["category"]
        by_cat[cat]["n"] += 1
        if r.get("buildability") in ("ready_today", "ready_with_caveats"):
            by_cat[cat]["ready"] += 1
        if r.get("buildability") == "needs_outreach":
            by_cat[cat]["outreach"] += 1
        if r.get("access_model") in ("self_serve_free", "self_serve_trial", "open_source_local"):
            by_cat[cat]["self_serve"] += 1
        if r.get("access_model") in ("paid_plan_required", "partner_or_sales_gated", "admin_approval"):
            by_cat[cat]["gated"] += 1

    easy_wins = [
        {"id": r["id"], "name": r["name"], "category": r["category"], "auth": r.get("auth_methods"), "access": r.get("access_model")}
        for r in rows
        if r.get("buildability") == "ready_today" and r.get("confidence", 0) >= 0.6
    ]
    outreach = [
        {"id": r["id"], "name": r["name"], "category": r["category"], "blocker": r.get("main_blocker"), "access": r.get("access_model")}
        for r in rows
        if r.get("buildability") == "needs_outreach" or r.get("access_model") == "partner_or_sales_gated"
    ]
    blockers = Counter(r.get("main_blocker") or "(none)" for r in rows if r.get("buildability") != "ready_today")

    # Headline insights — ops-oriented, not just counters
    top_auth = auth_c.most_common(3)
    ready_n = build_c.get("ready_today", 0) + build_c.get("ready_with_caveats", 0)
    gated_n = (
        access_c.get("partner_or_sales_gated", 0)
        + access_c.get("paid_plan_required", 0)
        + access_c.get("admin_approval", 0)
    )
    self_n = (
        access_c.get("self_serve_free", 0)
        + access_c.get("self_serve_trial", 0)
        + access_c.get("open_source_local", 0)
    )
    auth_phrase = ", ".join(f"{k} ({v})" for k, v in top_auth[:2]) if top_auth else "unknown"
    insights = [
        f"Auth is bifurcated — top signals: {auth_phrase}. Toolkit design should ship OAuth2 + API-key adapters as defaults, not one-size-fits-all.",
        f"Access is mostly self-serve ({self_n}/{len(rows)}), but {gated_n} apps still need paid plans, admin approval, or partner/sales — that is the real ops queue, not engineering.",
        f"{ready_n}/{len(rows)} look toolkit-buildable now (ready / ready-with-caveats). The scarce resource is outreach for the gated tail, not more scraping.",
        f"After MCP false-positive cleanup, only {mcp_n} apps have credible Model Context Protocol evidence — treat marketplace copy as noise.",
        f"{human_n} rows still need a human (403/JS docs, thin public surface). Automate the fat middle; staff the weird edges.",
        "Highest leverage for immediate toolkit work: Developer/Infra + Productivity (broad self-serve REST). Slowest: niche fintech + AI-native apps with thin public APIs.",
    ]

    out = {
        "n": len(rows),
        "insights": insights,
        "auth_counts": dict(auth_c.most_common()),
        "access_counts": dict(access_c.most_common()),
        "buildability_counts": dict(build_c.most_common()),
        "api_type_counts": dict(api_c.most_common()),
        "mcp_existing_count": mcp_n,
        "human_needed_count": human_n,
        "by_category": dict(by_cat),
        "easy_wins": easy_wins,
        "outreach_queue": outreach,
        "common_blockers": blockers.most_common(12),
    }
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"Wrote {args.out}")
    for line in insights:
        print("-", line)


if __name__ == "__main__":
    main()
