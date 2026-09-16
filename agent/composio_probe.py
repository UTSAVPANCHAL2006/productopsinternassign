"""Optional Composio catalog probe — spirit of the role.

Primary research still comes from each app's public docs (fetch + LLM).
Composio toolkit catalog is a secondary cross-check: which of the 100 already
exist as toolkits, so ops can prioritize net-new vs overlap.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def _toolkit_names(listed: object) -> list[str]:
    names: list[str] = []
    items = getattr(listed, "items", None)
    if items is None and isinstance(listed, dict):
        items = listed.get("items") or listed.get("data") or []
    if items is None:
        # fallback: scrape name= from repr
        text = str(listed)
        names.extend(re.findall(r"name='([^']+)'", text))
        names.extend(re.findall(r'name="([^"]+)"', text))
        return sorted(set(names))
    for it in items or []:
        name = getattr(it, "name", None)
        if name is None and isinstance(it, dict):
            name = it.get("name")
        if name:
            names.append(str(name))
        slug = getattr(it, "slug", None)
        if slug is None and isinstance(it, dict):
            slug = it.get("slug")
        if slug:
            names.append(str(slug))
    return sorted(set(names))


def probe_composio(apps: list[dict] | None = None) -> dict:
    apps = apps or []
    api_key = os.getenv("COMPOSIO_API_KEY", "")
    out: dict = {
        "enabled": bool(api_key),
        "ok": False,
        "error": None,
        "toolkit_count": 0,
        "overlap": [],
        "missing_from_catalog_sample": [],
        "overlap_count": 0,
        "research_set_size": len(apps),
        "note": "",
        "why_docs_first": (
            "Docs fetch + LLM is the workhorse because the assignment asks for auth/access/API/MCP "
            "evidence per app. Composio catalog answers a different question: do we already ship a toolkit?"
        ),
    }
    if not api_key:
        out["note"] = "COMPOSIO_API_KEY not set — pipeline still runs with HTTP fetch + OpenAI."
        return out
    try:
        from composio import Composio

        client = Composio(api_key=api_key)
        # Paginate toolkit list when the SDK exposes pages
        all_names: list[str] = []
        page = 1
        while page <= 20:
            try:
                listed = client.toolkits.list(page=page)
            except TypeError:
                listed = client.toolkits.list()
                all_names.extend(_toolkit_names(listed))
                break
            batch = _toolkit_names(listed)
            if not batch:
                break
            all_names.extend(batch)
            # stop if no next page signal
            next_page = getattr(listed, "next_page", None) or getattr(listed, "nextPage", None)
            current = getattr(listed, "current_page", None) or getattr(listed, "currentPage", page)
            if next_page is None and page > 1 and not batch:
                break
            if next_page is None and page >= 3 and len(batch) < 5:
                # heuristic stop when pages dry up
                break
            if next_page is not None:
                page = int(next_page)
            else:
                page = int(current or page) + 1
                if page > 15:
                    break

        catalog = sorted(set(all_names))
        catalog_norm = {_norm(n): n for n in catalog}
        out["ok"] = True
        out["toolkit_count"] = len(catalog)
        out["raw_preview"] = ", ".join(catalog[:40])

        overlap = []
        missing = []
        for app in apps:
            name = app.get("name") or ""
            n = _norm(name)
            hit = catalog_norm.get(n)
            if not hit:
                # soft match: catalog name contained in app or vice versa
                for cn, original in catalog_norm.items():
                    if cn and (cn in n or n in cn) and min(len(cn), len(n)) >= 4:
                        hit = original
                        break
            if hit:
                overlap.append({"id": app.get("id"), "name": name, "composio_toolkit": hit})
            else:
                missing.append({"id": app.get("id"), "name": name})

        out["overlap"] = overlap
        out["overlap_count"] = len(overlap)
        out["missing_from_catalog_sample"] = missing[:25]
        out["missing_count"] = len(missing)
        out["note"] = (
            f"Composio catalog cross-check: {len(overlap)}/{len(apps)} research apps already have a "
            f"toolkit name match ({len(catalog)} toolkits listed). Catalog is secondary — "
            "auth/access/MCP verdicts still come from public docs."
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
    apps_path = ROOT / "data" / "apps.json"
    apps = json.loads(apps_path.read_text()) if apps_path.exists() else []
    report = probe_composio(apps)
    path = ROOT / "verification" / "composio_probe.json"
    path.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in report if k != "overlap" and k != "missing_from_catalog_sample"}, indent=2))
    print(f"overlap={report.get('overlap_count')} missing~={report.get('missing_count')}")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
