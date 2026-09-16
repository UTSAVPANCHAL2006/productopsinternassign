"""LLM researcher: turns fetched docs into a structured ResearchResult."""
from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

from agent.fetch_docs import FetchedDoc, fetch_docs_for_app, pack_evidence
from agent.schema import AppSeed, ResearchResult

SYSTEM = """You are a Product Ops researcher for Composio.
Composio builds agent toolkits that call third-party APIs.
For each app, extract ONLY what is supported by the provided evidence text.
If evidence is thin/missing, set confidence low, human_needed=true, and say so.
Do not invent partner approvals. Prefer "unclear" over guessing.

Return STRICT JSON matching the schema keys given in the user message.
"""

SCHEMA_KEYS = """
{
  "one_liner": "string, one sentence what the product does",
  "auth_methods": ["OAuth2"|"API key"|"Basic"|"Bearer token"|"PAT / token"|"None / CLI local"|"Other"|"Unknown", ...],
  "access_model": "self_serve_free"|"self_serve_trial"|"paid_plan_required"|"admin_approval"|"partner_or_sales_gated"|"open_source_local"|"unclear",
  "access_notes": "string",
  "api_type": "REST|GraphQL|REST+GraphQL|SDK|MCP|CLI|RPC|none|unknown",
  "api_breadth": "narrow|moderate|broad|unknown",
  "mcp_existing": true/false,
  "mcp_notes": "string",
  "buildability": "ready_today"|"ready_with_caveats"|"needs_outreach"|"not_viable_yet",
  "main_blocker": "string — empty if ready_today",
  "evidence_urls": ["urls actually used"],
  "confidence": 0.0-1.0,
  "human_needed": true/false,
  "human_reason": "string",
  "raw_notes": "short notes on uncertainty"
}
"""


def _client() -> OpenAI:
    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def _model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def structure_from_evidence(seed: AppSeed, evidence: str, evidence_urls: list[str]) -> ResearchResult:
    client = _client()
    user = f"""App #{seed.id}: {seed.name}
Category: {seed.category}
Hint from assignment: {seed.hint}

Known candidate evidence URLs: {evidence_urls}

Evidence pack:
{evidence}

Fill this JSON schema:
{SCHEMA_KEYS}
"""
    resp = client.chat.completions.create(
        model=_model(),
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
    )
    content = resp.choices[0].message.content or "{}"
    data: dict[str, Any] = json.loads(content)

    # Prefer real fetched URLs if model invents others
    urls = data.get("evidence_urls") or evidence_urls
    urls = [u for u in urls if isinstance(u, str) and u.startswith("http")]
    if not urls:
        urls = evidence_urls

    return ResearchResult(
        id=seed.id,
        name=seed.name,
        category=seed.category,
        one_liner=str(data.get("one_liner") or ""),
        auth_methods=list(data.get("auth_methods") or ["Unknown"]),
        access_model=data.get("access_model") or "unclear",
        access_notes=str(data.get("access_notes") or ""),
        api_type=str(data.get("api_type") or "unknown"),
        api_breadth=str(data.get("api_breadth") or "unknown"),
        mcp_existing=bool(data.get("mcp_existing") or False),
        mcp_notes=str(data.get("mcp_notes") or ""),
        buildability=data.get("buildability") or "not_viable_yet",
        main_blocker=str(data.get("main_blocker") or ""),
        evidence_urls=urls,
        confidence=float(data.get("confidence") or 0.3),
        human_needed=bool(data.get("human_needed") or False),
        human_reason=str(data.get("human_reason") or ""),
        raw_notes=str(data.get("raw_notes") or ""),
        pass_label="pass1",
    )


def research_app(seed: AppSeed, docs: list[FetchedDoc] | None = None) -> ResearchResult:
    docs = docs or fetch_docs_for_app(seed.name, seed.hint)
    evidence, urls = pack_evidence(docs)
    if not any(d.ok for d in docs):
        # Still ask model with thin evidence so we record honest failure
        evidence = (
            f"No usable docs fetched for {seed.name}. Hint: {seed.hint}. "
            f"Attempted URLs: {[d.url for d in docs]}"
        )
    result = structure_from_evidence(seed, evidence, urls)
    if not any(d.ok for d in docs):
        result.human_needed = True
        result.human_reason = result.human_reason or "Docs fetch failed; needs manual URL hunt"
        result.confidence = min(result.confidence, 0.35)
        result.pass_label = "pass1"
    return result


def maybe_composio_context(seed: AppSeed) -> str:
    """Optional: list whether Composio already knows this app (spirit of the role)."""
    try:
        from composio import Composio  # type: ignore

        api_key = os.getenv("COMPOSIO_API_KEY")
        if not api_key:
            return ""
        # Best-effort; Composio SDK surfaces change — never fail the pipeline.
        c = Composio(api_key=api_key)
        # Try a few likely APIs without hard dependency on exact version
        for attr in ("tools", "apps", "toolkits"):
            obj = getattr(c, attr, None)
            if obj is None:
                continue
            for meth in ("get", "list", "get_toolkits"):
                fn = getattr(obj, meth, None)
                if callable(fn):
                    try:
                        data = fn()
                        text = str(data)[:2000]
                        if seed.name.lower().replace(" ", "") in text.lower().replace(" ", ""):
                            return f"Composio catalog mentions something like {seed.name}."
                    except Exception:  # noqa: BLE001
                        continue
        return "Composio SDK reachable; no definitive catalog hit for this app name."
    except Exception as exc:  # noqa: BLE001
        return f"Composio optional check skipped: {exc}"
