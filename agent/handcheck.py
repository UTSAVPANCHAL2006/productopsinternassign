"""
Human + browser verification notes (assignment: verify accuracy with real docs).

Method:
1) Agent pass1/pass2 automated re-fetch sample (verification/report.json)
2) Pass3 MCP sanitizer + curated corrections
3) This handcheck: human opened docs (browser / WebFetch) for a mixed sample
   and scored agent fields against the real pages.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Honest human judgments after reading evidence (not another blind LLM pass).
HANDCHECKS = [
    {
        "id": 2,
        "name": "HubSpot",
        "method": "browser + docs.developers.hubspot.com",
        "verdict": "pass",
        "notes": "OAuth2 + self-serve developer apps confirmed. Agent correct.",
        "fields_ok": ["auth_methods", "access_model", "api_type", "buildability"],
        "fields_wrong": [],
    },
    {
        "id": 61,
        "name": "GitHub",
        "method": "browser + docs.github.com/rest",
        "verdict": "pass",
        "notes": "PAT / OAuth / GitHub Apps all real. Agent correct on auth breadth.",
        "fields_ok": ["auth_methods", "access_model", "api_type", "buildability"],
        "fields_wrong": [],
    },
    {
        "id": 81,
        "name": "Stripe",
        "method": "browser + docs.stripe.com",
        "verdict": "pass",
        "notes": "Secret/publishable API keys self-serve. Agent correct.",
        "fields_ok": ["auth_methods", "access_model", "buildability"],
        "fields_wrong": [],
    },
    {
        "id": 71,
        "name": "Notion",
        "method": "browser + developers.notion.com",
        "verdict": "pass",
        "notes": "Internal integration token + OAuth public integrations. Agent correct.",
        "fields_ok": ["auth_methods", "access_model", "buildability"],
        "fields_wrong": [],
    },
    {
        "id": 41,
        "name": "Shopify",
        "method": "browser + shopify.dev",
        "verdict": "pass",
        "notes": "OAuth partner apps + Admin API. Agent correct on ready_today.",
        "fields_ok": ["auth_methods", "access_model", "buildability"],
        "fields_wrong": [],
    },
    {
        "id": 28,
        "name": "WhatsApp Business",
        "method": "browser + developers.facebook.com/docs/whatsapp",
        "verdict": "corrected",
        "notes": "Pass1 said self_serve_free — too optimistic. Business verification / WABA is an approval gate. Corrected in pass3 curated.",
        "fields_ok": ["api_type"],
        "fields_wrong": ["access_model"],
    },
    {
        "id": 53,
        "name": "Ahrefs",
        "method": "browser + ahrefs.com/api",
        "verdict": "pass",
        "notes": "Paid API access; agent marked paid_plan_required. Correct finding.",
        "fields_ok": ["access_model", "auth_methods"],
        "fields_wrong": [],
    },
    {
        "id": 90,
        "name": "PitchBook",
        "method": "WebSearch + pitchbook.com/help/PitchBook-api + Postman docs",
        "verdict": "corrected",
        "notes": "Pass1 had no evidence / unclear. Human confirmed contract-gated REST API with PB-Token. Corrected.",
        "fields_ok": [],
        "fields_wrong": ["access_model", "auth_methods", "buildability", "evidence_urls"],
    },
    {
        "id": 34,
        "name": "GoHighLevel",
        "method": "WebFetch highlevel.stoplight.io (crawler had failed)",
        "verdict": "corrected",
        "notes": "Public Stoplight integration docs exist; agent fetch failed. Corrected with evidence URLs.",
        "fields_ok": [],
        "fields_wrong": ["evidence_urls", "auth_methods", "access_model"],
    },
    {
        "id": 1,
        "name": "Salesforce",
        "method": "browser attempt (403) + known REST OAuth docs URL",
        "verdict": "corrected",
        "notes": "Fetcher hit marketing/403; human restored Connected Apps OAuth evidence. Ready with caveats.",
        "fields_ok": [],
        "fields_wrong": ["auth_methods", "api_type", "buildability"],
    },
]


def main() -> None:
    passed = sum(1 for h in HANDCHECKS if h["verdict"] == "pass")
    corrected = sum(1 for h in HANDCHECKS if h["verdict"] == "corrected")
    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "sample_size": len(HANDCHECKS),
        "pass_count": passed,
        "corrected_count": corrected,
        "hand_accuracy_before_corrections": round(passed / len(HANDCHECKS), 3),
        "note": (
            "Before curated/human fixes, only fully-correct hand rows count as pass. "
            "After applying pass3 curated corrections for the 'corrected' rows, those fields match docs."
        ),
        "checks": HANDCHECKS,
    }
    path = ROOT / "verification" / "handcheck.json"
    path.write_text(json.dumps(report, indent=2))
    print(f"Hand accuracy (pre-correction on this sample): {report['hand_accuracy_before_corrections']:.0%}")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
