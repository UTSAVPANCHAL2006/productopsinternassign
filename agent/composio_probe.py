"""Optional Composio catalog probe — spirit of the role.

Records success/failure honestly. Invalid keys must not fake toolkit hits.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def probe_composio(sample_names: list[str] | None = None) -> dict:
    sample_names = sample_names or [
        "GitHub",
        "Slack",
        "Notion",
        "Gmail",
        "HubSpot",
        "Stripe",
    ]
    api_key = os.getenv("COMPOSIO_API_KEY", "")
    out: dict = {
        "enabled": bool(api_key),
        "ok": False,
        "error": None,
        "sample_hits": [],
        "note": "",
    }
    if not api_key:
        out["note"] = "COMPOSIO_API_KEY not set — pipeline still runs with HTTP fetch + OpenAI."
        return out
    try:
        from composio import Composio

        client = Composio(api_key=api_key)
        # List toolkits (may 401 if key invalid — capture honestly)
        listed = client.toolkits.list()
        text = str(listed)
        out["ok"] = True
        out["raw_preview"] = text[:1500]
        for name in sample_names:
            hit = name.lower().replace(" ", "") in text.lower().replace(" ", "")
            out["sample_hits"].append({"name": name, "mentioned": hit})
        out["note"] = (
            "Composio SDK reachable. Catalog used as a cross-check signal only — "
            "assignment research still comes from each app's public docs."
        )
    except Exception as exc:  # noqa: BLE001
        out["ok"] = False
        out["error"] = str(exc)
        out["note"] = (
            "Composio SDK call failed (often invalid/expired API key). "
            "Research agent continues without catalog enrichment — documented as a human/ops follow-up."
        )
    return out


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    report = probe_composio()
    path = ROOT / "verification" / "composio_probe.json"
    path.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
