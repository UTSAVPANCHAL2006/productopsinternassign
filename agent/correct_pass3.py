"""
Pass-3 deterministic corrections after LLM structuring.

Why: pass1 often confuses Marketplace / Multi-Channel Platform with
Model Context Protocol (MCP). This loop only keeps mcp_existing=true when
notes clearly refer to Model Context Protocol, and applies curated
corrections for high-signal apps whose docs were 403/JS-walled.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MCP_OK = re.compile(r"model\s+context\s+protocol|\bmcp\s+server\b", re.I)
MCP_BAD = re.compile(
    r"marketplace|multi-?channel\s+platform|managed\s+control\s+plane|"
    r"marketing\s+connect|marketplace\s+connector",
    re.I,
)

# Curated human corrections when fetch failed but public docs are well-known.
# Each entry merges over the agent row; evidence_urls must be real.
CURATED: dict[int, dict] = {
    1: {  # Salesforce
        "one_liner": "Enterprise CRM platform with a broad REST and SOAP API surface for CRM objects and automation.",
        "auth_methods": ["OAuth2"],
        "access_model": "self_serve_free",
        "access_notes": "Connected Apps / Dev Edition orgs are self-serve; production customer installs often need admin approval.",
        "api_type": "REST",
        "api_breadth": "broad",
        "mcp_existing": False,
        "mcp_notes": "",
        "buildability": "ready_with_caveats",
        "main_blocker": "OAuth Connected App + sandbox setup friction; many customers require admin install approval.",
        "evidence_urls": [
            "https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/intro_oauth_and_connected_apps.htm",
            "https://developer.salesforce.com/docs",
        ],
        "confidence": 0.85,
        "human_needed": True,
        "human_reason": "Primary doc URL returned 403 to the fetcher; corrected from known Salesforce REST OAuth docs.",
        "pass_label": "corrected",
    },
    34: {  # GoHighLevel
        "one_liner": "GoHighLevel is an all-in-one CRM / marketing automation platform for agencies with public REST integrations APIs.",
        "auth_methods": ["OAuth2", "API key"],
        "access_model": "self_serve_trial",
        "access_notes": "Developer app + OAuth documented on Stoplight; agency/sub-account credentials via GHL account.",
        "api_type": "REST",
        "api_breadth": "broad",
        "mcp_existing": False,
        "mcp_notes": "",
        "buildability": "ready_with_caveats",
        "main_blocker": "Fetcher could not reliably scrape Stoplight JS docs; human opened highlevel.stoplight.io.",
        "evidence_urls": [
            "https://highlevel.stoplight.io/docs/integrations/",
            "https://marketplace.gohighlevel.com/",
        ],
        "confidence": 0.75,
        "human_needed": True,
        "human_reason": "Pass1/2 fetch failed; browser/WebFetch confirmed Stoplight integration docs exist.",
        "pass_label": "corrected",
    },
    44: {  # Salesforce Commerce Cloud
        "one_liner": "Salesforce B2C Commerce (Commerce Cloud) exposes SCAPI / commerce APIs for storefront and admin commerce operations.",
        "auth_methods": ["OAuth2"],
        "access_model": "paid_plan_required",
        "access_notes": "Requires a B2C Commerce instance / Account Manager credentials; not a free hobby sandbox.",
        "api_type": "REST",
        "api_breadth": "broad",
        "mcp_existing": False,
        "buildability": "ready_with_caveats",
        "main_blocker": "Needs a Commerce Cloud tenant; docs are public but credentials are customer/partner gated.",
        "evidence_urls": [
            "https://developer.salesforce.com/docs/commerce/commerce-api/guide",
            "https://developer.salesforce.com/docs/commerce",
        ],
        "confidence": 0.8,
        "human_needed": True,
        "human_reason": "Pass1 fetch failed on generic commerce URL; human verified SCAPI guide.",
        "pass_label": "corrected",
    },
    62: {  # Vercel
        "auth_methods": ["Bearer token", "OAuth2"],
        "access_model": "self_serve_free",
        "access_notes": "Personal access tokens from Vercel dashboard; team tokens for team scope.",
        "api_type": "REST",
        "api_breadth": "moderate",
        "buildability": "ready_today",
        "main_blocker": "",
        "evidence_urls": ["https://vercel.com/docs/rest-api"],
        "confidence": 0.9,
        "human_needed": False,
        "human_reason": "",
        "pass_label": "corrected",
    },
    83: {  # Binance
        "one_liner": "Binance spot/crypto exchange with extensive REST and WebSocket market + trading APIs.",
        "auth_methods": ["API key"],
        "access_model": "self_serve_free",
        "access_notes": "API keys created in Binance account API Management; some endpoints need KYC / permissions.",
        "api_type": "REST",
        "api_breadth": "broad",
        "mcp_existing": False,
        "buildability": "ready_with_caveats",
        "main_blocker": "Account KYC + IP restrictions / trading permissions; docs moved to developers.binance.com (JS-walled for crawlers).",
        "evidence_urls": [
            "https://developers.binance.com/docs/binance-spot-api-docs",
            "https://binance-docs.github.io/apidocs/spot/en/",
        ],
        "confidence": 0.8,
        "human_needed": True,
        "human_reason": "Old github.io docs redirect; crawler hit JS robot check; human confirmed public spot API docs.",
        "pass_label": "corrected",
    },
    86: {  # QuickBooks
        "one_liner": "Intuit QuickBooks Online accounting platform with OAuth2 REST APIs for books, invoices, and payments.",
        "auth_methods": ["OAuth2"],
        "access_model": "self_serve_free",
        "access_notes": "Intuit Developer account is self-serve; production apps go through Intuit app review.",
        "api_type": "REST",
        "api_breadth": "broad",
        "mcp_existing": False,
        "buildability": "ready_with_caveats",
        "main_blocker": "App review / production keys after sandbox development.",
        "evidence_urls": ["https://developer.intuit.com/app/developer/qbo/docs/get-started"],
        "confidence": 0.85,
        "human_needed": True,
        "human_reason": "Docs fetch failed in pass1; corrected from Intuit developer get-started.",
        "pass_label": "corrected",
    },
    89: {  # Ramp
        "one_liner": "Ramp corporate card and spend platform with developer APIs for transactions, bills, and users.",
        "auth_methods": ["OAuth2", "API key"],
        "access_model": "partner_or_sales_gated",
        "access_notes": "Developer access typically requires a Ramp business account; some surfaces are partner-gated.",
        "api_type": "REST",
        "api_breadth": "moderate",
        "buildability": "needs_outreach",
        "main_blocker": "Needs Ramp customer/partner relationship for meaningful sandbox credentials.",
        "evidence_urls": ["https://docs.ramp.com/"],
        "confidence": 0.7,
        "human_needed": True,
        "human_reason": "Docs page is a JS shell for the crawler; human opened docs.ramp.com.",
        "pass_label": "corrected",
    },
    90: {  # PitchBook
        "one_liner": "PitchBook private-market data platform with a paid REST API for companies, deals, people, and funds.",
        "auth_methods": ["API key"],
        "access_model": "partner_or_sales_gated",
        "access_notes": "API is a separate paid contract from the PitchBook platform; keys/credits issued by PitchBook Direct Data / account manager — not self-serve free.",
        "api_type": "REST",
        "api_breadth": "broad",
        "mcp_existing": False,
        "buildability": "needs_outreach",
        "main_blocker": "Standalone API contract + credits required; contact sales / account manager.",
        "evidence_urls": [
            "https://pitchbook.com/help/PitchBook-api",
            "https://documenter.getpostman.com/view/5190535/TzCV1iRc",
            "https://pitchbook.com/products/direct-access-data/api",
        ],
        "confidence": 0.9,
        "human_needed": True,
        "human_reason": "Agent fetch failed; human verified PitchBook help + Postman docs (PB-Token auth, contract-gated).",
        "pass_label": "corrected",
    },
    28: {  # WhatsApp Business — often over-marked self-serve
        "one_liner": "Meta WhatsApp Cloud API for business messaging, templates, and webhooks.",
        "auth_methods": ["OAuth2", "Bearer token"],
        "access_model": "admin_approval",
        "access_notes": "Meta developer app is self-serve to start, but WhatsApp Business / Business Manager verification and phone-number onboarding add approval gates.",
        "api_type": "REST",
        "api_breadth": "broad",
        "mcp_existing": False,
        "buildability": "ready_with_caveats",
        "main_blocker": "Business verification + WABA setup; not a one-click API key.",
        "evidence_urls": [
            "https://developers.facebook.com/docs/whatsapp/cloud-api/get-started",
        ],
        "confidence": 0.85,
        "human_needed": True,
        "human_reason": "Hand check: pass1 called it self_serve_free; corrected to admin_approval / caveats.",
        "pass_label": "corrected",
    },
    4: {  # Attio
        "one_liner": "Attio is a flexible, data-driven CRM with a modern REST API, App SDK, SQL, and MCP for AI tools.",
        "auth_methods": ["OAuth2", "API key"],
        "access_model": "self_serve_free",
        "access_notes": "Developer workspace + OAuth apps are self-serve from Attio developer docs.",
        "api_type": "REST",
        "api_breadth": "broad",
        "mcp_existing": True,
        "mcp_notes": "Attio documents an MCP surface to manage the workspace from Claude/ChatGPT/other AI tools.",
        "buildability": "ready_today",
        "main_blocker": "",
        "evidence_urls": ["https://developers.attio.com/docs/overview", "https://docs.attio.com/"],
        "confidence": 0.95,
        "human_needed": False,
        "human_reason": "",
        "pass_label": "corrected",
    },
    17: {  # Plain
        "one_liner": "Plain is an API-first B2B support platform with a GraphQL API for threads, customers, and AI agents.",
        "auth_methods": ["API key", "Bearer token"],
        "access_model": "self_serve_trial",
        "access_notes": "API keys with permissions; workspace signup is self-serve for builders.",
        "api_type": "GraphQL",
        "api_breadth": "broad",
        "mcp_existing": True,
        "mcp_notes": "Plain docs recommend an MCP server path for agent access to the GraphQL API.",
        "buildability": "ready_today",
        "main_blocker": "",
        "evidence_urls": ["https://www.plain.com/docs", "https://www.plain.com/docs/graphql"],
        "confidence": 0.9,
        "human_needed": False,
        "pass_label": "corrected",
    },
    19: {  # Gorgias
        "one_liner": "Gorgias is an ecommerce helpdesk with REST APIs; private apps use API keys, public apps require OAuth2.",
        "auth_methods": ["API key", "OAuth2", "Basic"],
        "access_model": "self_serve_trial",
        "access_notes": "API keys from Settings → REST API for private apps; public marketplace apps must use OAuth2.",
        "api_type": "REST",
        "api_breadth": "broad",
        "mcp_existing": False,
        "buildability": "ready_today",
        "main_blocker": "",
        "evidence_urls": [
            "https://developers.gorgias.com/reference/authentication",
            "https://developers.gorgias.com/docs/access-tokens-api-keys",
        ],
        "confidence": 0.9,
        "human_needed": False,
        "pass_label": "corrected",
    },
    24: {  # Lark
        "one_liner": "Larksuite (Lark) is a collaboration suite with an open platform REST APIs for messaging, docs, and SSO.",
        "auth_methods": ["OAuth2"],
        "access_model": "self_serve_free",
        "access_notes": "Create apps in Lark Open Platform; OAuth authorization code + access tokens.",
        "api_type": "REST",
        "api_breadth": "broad",
        "mcp_existing": False,
        "buildability": "ready_with_caveats",
        "main_blocker": "Docs are region/app-console oriented; crawler often blocked — human verified open.larksuite.com OAuth docs.",
        "evidence_urls": [
            "https://open.larksuite.com/document/common-capabilities/sso/api/obtain-oauth-code",
            "https://open.larksuite.com/document/",
        ],
        "confidence": 0.85,
        "human_needed": True,
        "pass_label": "corrected",
    },
    47: {  # Ecwid
        "one_liner": "Ecwid is an ecommerce platform with REST APIs; custom apps use Bearer secret tokens, public apps use OAuth2.",
        "auth_methods": ["Bearer token", "OAuth2"],
        "access_model": "self_serve_free",
        "access_notes": "Store custom app secret/public tokens self-serve; public apps use OAuth install flow.",
        "api_type": "REST",
        "api_breadth": "broad",
        "mcp_existing": False,
        "buildability": "ready_today",
        "main_blocker": "",
        "evidence_urls": [
            "https://docs.ecwid.com/get-started/make-your-first-api-request",
            "https://api-docs.ecwid.com/",
        ],
        "confidence": 0.9,
        "human_needed": False,
        "pass_label": "corrected",
    },
    48: {  # Gumroad
        "one_liner": "Gumroad is a creator commerce platform with a REST OAuth API for products, sales, and licenses.",
        "auth_methods": ["OAuth2", "Bearer token"],
        "access_model": "self_serve_free",
        "access_notes": "Register an OAuth application in Gumroad settings; personal access tokens can be generated for own-account use.",
        "api_type": "REST",
        "api_breadth": "moderate",
        "mcp_existing": False,
        "buildability": "ready_today",
        "main_blocker": "",
        "evidence_urls": [
            "https://gumroad.com/api",
            "https://gumroad.com/help/article/280-create-application-api",
        ],
        "confidence": 0.9,
        "human_needed": False,
        "human_reason": "Pass1 fetch failed; human verified gumroad.com/api OAuth docs.",
        "pass_label": "corrected",
    },
    51: {  # DataForSEO
        "one_liner": "DataForSEO provides SEO/SERP data APIs (keyword, backlinks, on-page) over REST.",
        "auth_methods": ["Basic"],
        "access_model": "self_serve_trial",
        "access_notes": "Free account signup; API login + generated API password via Basic Auth header.",
        "api_type": "REST",
        "api_breadth": "broad",
        "mcp_existing": False,
        "buildability": "ready_today",
        "main_blocker": "",
        "evidence_urls": ["https://docs.dataforseo.com/v3/auth/", "https://docs.dataforseo.com/v3/"],
        "confidence": 0.95,
        "human_needed": False,
        "pass_label": "corrected",
    },
    66: {  # Neo4j
        "one_liner": "Neo4j is a graph database with HTTP/Bolt APIs for Cypher queries and Aura cloud management APIs.",
        "auth_methods": ["Basic", "Bearer token"],
        "access_model": "self_serve_free",
        "access_notes": "Aura free tier / local Neo4j; HTTP auth typically basic or token depending on deployment.",
        "api_type": "REST",
        "api_breadth": "moderate",
        "mcp_existing": False,
        "buildability": "ready_with_caveats",
        "main_blocker": "HTTP API is legacy vs drivers/Query API — prefer official drivers for production toolkits.",
        "evidence_urls": ["https://neo4j.com/docs/http-api/current/", "https://neo4j.com/docs/"],
        "confidence": 0.85,
        "human_needed": False,
        "pass_label": "corrected",
    },
    67: {  # Snowflake
        "one_liner": "Snowflake is a cloud data platform with a SQL REST API and drivers for warehouses and data apps.",
        "auth_methods": ["OAuth2", "Key pair", "PAT / token"],
        "access_model": "paid_plan_required",
        "access_notes": "Trial accounts exist but ongoing warehouse use is paid; auth via OAuth/keypair/programmatic access tokens.",
        "api_type": "REST",
        "api_breadth": "broad",
        "mcp_existing": False,
        "buildability": "ready_with_caveats",
        "main_blocker": "Needs a Snowflake account/warehouse (paid after trial) and careful auth setup.",
        "evidence_urls": ["https://docs.snowflake.com/en/developer-guide/sql-api/index"],
        "confidence": 0.9,
        "human_needed": False,
        "pass_label": "corrected",
    },
    79: {  # Smartsheet
        "one_liner": "Smartsheet is a work management platform with REST APIs and SDKs for sheets, rows, and automations.",
        "auth_methods": ["OAuth2", "API key", "Bearer token"],
        "access_model": "self_serve_trial",
        "api_type": "REST",
        "api_breadth": "broad",
        "mcp_existing": False,
        "buildability": "ready_today",
        "main_blocker": "",
        "evidence_urls": ["https://smartsheet.redoc.ly/", "https://developers.smartsheet.com/"],
        "confidence": 0.85,
        "human_needed": False,
        "human_reason": "MCP marketplace wording stripped; auth clarified from developer portal.",
        "pass_label": "corrected",
    },
    84: {  # Paygent / NMI
        "one_liner": "Paygent Connect is an NMI-powered payment gateway with REST/emulation APIs for card processing.",
        "auth_methods": ["API key", "Security key"],
        "access_model": "partner_or_sales_gated",
        "access_notes": "Merchant/processor onboarding required; not a free public sandbox for arbitrary developers.",
        "api_type": "REST",
        "api_breadth": "moderate",
        "mcp_existing": False,
        "buildability": "needs_outreach",
        "main_blocker": "Needs merchant account / NMI partner relationship for credentials.",
        "evidence_urls": ["https://secure.nmi.com/merchants/resources/integration/integration_portal.php"],
        "confidence": 0.75,
        "human_needed": True,
        "pass_label": "corrected",
    },
    92: {  # Otter
        "one_liner": "Otter AI provides AI meeting transcription and notes; public REST docs are thin; MCP is marketed.",
        "auth_methods": ["Unknown"],
        "access_model": "unclear",
        "api_type": "MCP",
        "api_breadth": "unknown",
        "mcp_existing": True,
        "mcp_notes": "Assignment hint and Otter help reference an MCP server, but public auth/API docs remain thin.",
        "buildability": "needs_outreach",
        "main_blocker": "No clear self-serve developer API credentials page — outreach / partner path needed.",
        "evidence_urls": ["https://help.otter.ai/hc/en-us", "https://otter.ai/"],
        "confidence": 0.45,
        "human_needed": True,
        "pass_label": "corrected",
    },
    15: {  # Pylon
        "one_liner": "Pylon is a B2B support platform with AI agents and product/account context integrations.",
        "auth_methods": ["API key", "OAuth2"],
        "access_model": "self_serve_trial",
        "api_type": "REST",
        "api_breadth": "moderate",
        "mcp_existing": True,
        "mcp_notes": "Product docs reference Model Context Protocol for agent context.",
        "buildability": "ready_with_caveats",
        "main_blocker": "Docs surface still thin vs Zendesk/Intercom — confirm auth scopes before shipping toolkit.",
        "evidence_urls": ["https://docs.usepylon.com/", "https://usepylon.com"],
        "confidence": 0.7,
        "human_needed": True,
        "pass_label": "corrected",
    },
    20: {  # Gladly
        "one_liner": "Gladly is a customer service / conversational commerce platform with a developer API.",
        "auth_methods": ["API key", "OAuth2"],
        "access_model": "partner_or_sales_gated",
        "api_type": "REST",
        "api_breadth": "moderate",
        "mcp_existing": False,
        "buildability": "needs_outreach",
        "main_blocker": "Developer access typically tied to Gladly customer/partner onboarding.",
        "evidence_urls": ["https://developer.gladly.com/"],
        "confidence": 0.65,
        "human_needed": True,
        "pass_label": "corrected",
    },
    49: {  # Amazon SP-API
        "buildability": "ready_with_caveats",
        "main_blocker": "Requires Amazon Selling Partner / developer registration and approval — public docs exist, credentials are gated.",
        "access_model": "partner_or_sales_gated",
        "auth_methods": ["OAuth2"],
        "api_type": "REST",
        "api_breadth": "broad",
        "confidence": 0.85,
        "human_needed": True,
        "human_reason": "Partner-gated access cannot be 'ready_today' without caveats.",
        "pass_label": "corrected",
        "evidence_urls": ["https://developer-docs.amazon.com/sp-api/docs"],
    },
    50: {  # fanbasis
        "one_liner": "Fanbasis is a creator ecommerce / monetization platform (funnels, community, payments).",
        "auth_methods": ["API key"],
        "access_model": "paid_plan_required",
        "api_type": "REST",
        "api_breadth": "moderate",
        "buildability": "ready_with_caveats",
        "main_blocker": "Public docs thin; product naming/docs surface needs human confirmation for full toolkit scope.",
        "evidence_urls": ["https://fanbasis.com/"],
        "confidence": 0.55,
        "human_needed": True,
        "human_reason": "Agent hallucinated product name 'Commas'; corrected one-liner + confidence down.",
        "pass_label": "corrected",
    },
    73: {  # Linear
        "one_liner": "Linear is an issue tracking / project management tool with a GraphQL API for teams and agents.",
        "auth_methods": ["OAuth2", "API key"],
        "access_model": "self_serve_free",
        "access_notes": "Personal API keys and OAuth apps available from Linear developer docs.",
        "api_type": "GraphQL",
        "api_breadth": "broad",
        "buildability": "ready_today",
        "main_blocker": "",
        "evidence_urls": ["https://developers.linear.app/docs"],
        "confidence": 0.95,
        "human_needed": False,
        "pass_label": "corrected",
    },
    78: {  # Coda
        "one_liner": "Coda is a docs-as-apps productivity platform with a REST API for docs, tables, and rows.",
        "auth_methods": ["Bearer token", "API key"],
        "access_model": "self_serve_free",
        "api_type": "REST",
        "api_breadth": "broad",
        "mcp_existing": False,
        "buildability": "ready_today",
        "main_blocker": "",
        "evidence_urls": ["https://coda.io/developers/apis/v1"],
        "confidence": 0.9,
        "human_needed": False,
        "human_reason": "Agent mislabeled product as Superhuman Docs; corrected.",
        "pass_label": "corrected",
    },
    88: {  # Brex
        "one_liner": "Brex is a spend platform (cards, expenses, bill pay) with REST APIs for financial workflows.",
        "auth_methods": ["OAuth2", "API key"],
        "access_model": "partner_or_sales_gated",
        "access_notes": "Developer docs are public; production access typically requires a Brex customer/partner relationship.",
        "api_type": "REST",
        "api_breadth": "moderate",
        "buildability": "needs_outreach",
        "main_blocker": "Needs Brex business relationship for meaningful sandbox/production credentials.",
        "evidence_urls": ["https://developer.brex.com/"],
        "confidence": 0.75,
        "human_needed": True,
        "pass_label": "corrected",
    },
    100: {  # Grain
        "one_liner": "Grain is an AI meeting notetaker that records, transcribes, and shares meeting insights.",
        "auth_methods": ["OAuth2", "API key"],
        "access_model": "self_serve_trial",
        "api_type": "REST",
        "api_breadth": "moderate",
        "mcp_existing": True,
        "mcp_notes": "Grain documents MCP / AI assistant integrations on product help surfaces.",
        "buildability": "ready_with_caveats",
        "main_blocker": "Public API docs thinner than CRM/dev platforms; confirm scopes before toolkit build.",
        "evidence_urls": ["https://grain.com/", "https://support.grain.com/"],
        "confidence": 0.65,
        "human_needed": True,
        "pass_label": "corrected",
    },
}


def sanitize_mcp(row: dict) -> tuple[dict, bool]:
    notes = (row.get("mcp_notes") or "") + " " + (row.get("raw_notes") or "")
    notes_l = notes.lower()
    changed = False
    if row.get("mcp_existing"):
        ok = bool(MCP_OK.search(notes))
        # Marketplace / multi-channel wording without real MCP
        if MCP_BAD.search(notes) and not MCP_OK.search(notes):
            ok = False
        # Speculative announce / hint-only claims
        if any(x in notes_l for x in ("announced", "coming soon", "hint references", "preview starting")):
            ok = False
        if not ok:
            row = dict(row)
            row["mcp_existing"] = False
            row["mcp_notes"] = (
                (row.get("mcp_notes") or "")
                + " | stripped: pass3 rejected weak/non-MCP wording"
            ).strip(" |")
            row["pass_label"] = "corrected"
            row["raw_notes"] = (
                (row.get("raw_notes") or "") + " | mcp false-positive cleaned in pass3"
            ).strip(" |")
            changed = True
    return row, changed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="inp", default=str(ROOT / "output" / "results_verified.json"))
    parser.add_argument("--out", default=str(ROOT / "output" / "results_final.json"))
    parser.add_argument(
        "--report", default=str(ROOT / "verification" / "pass3_corrections.json")
    )
    args = parser.parse_args()

    payload = json.loads(Path(args.inp).read_text())
    rows = payload["results"]
    mcp_stripped = []
    curated_applied = []

    out_rows = []
    for r in rows:
        r2, changed = sanitize_mcp(r)
        if changed:
            mcp_stripped.append({"id": r["id"], "name": r["name"], "old_notes": r.get("mcp_notes")})
        if r2["id"] in CURATED:
            before = {k: r2.get(k) for k in CURATED[r2["id"]]}
            r2 = {**r2, **CURATED[r2["id"]]}
            curated_applied.append({"id": r2["id"], "name": r2["name"], "before": before})
        out_rows.append(r2)

    for r2 in out_rows:
        # Consistency: never leave ready_today with Unknown auth or unclear access
        auth = r2.get("auth_methods") or []
        access = r2.get("access_model") or "unclear"
        build = r2.get("buildability")
        conf = float(r2.get("confidence") or 0)
        breadth = (r2.get("api_breadth") or "").lower()
        reasons: list[str] = []

        if build == "ready_today" and (auth == ["Unknown"] or access == "unclear"):
            reasons.append("auth/access unclear")
        if build == "ready_today" and access == "partner_or_sales_gated":
            r2["buildability"] = "needs_outreach"
            r2["main_blocker"] = r2.get("main_blocker") or (
                "Partner / sales gate — eng cannot self-serve credentials without outreach."
            )
            r2["pass_label"] = "corrected"
            r2["raw_notes"] = (
                (r2.get("raw_notes") or "")
                + " | consistency: partner gate cannot be ready_today"
            ).strip(" |")
            continue
        if build == "ready_today" and access in ("paid_plan_required", "admin_approval"):
            reasons.append(f"access={access}")
        if build == "ready_today" and r2.get("human_needed"):
            reasons.append("human_needed still flagged")
        if build == "ready_today" and conf < 0.85:
            reasons.append(f"confidence {conf:.2f} < 0.85")
        if build == "ready_today" and breadth in ("narrow", "unknown", ""):
            reasons.append(f"api_breadth={breadth or 'missing'}")

        if reasons:
            r2["buildability"] = "ready_with_caveats"
            if not (r2.get("main_blocker") or "").strip():
                r2["main_blocker"] = (
                    "Not pure ready_today: " + "; ".join(reasons) + "."
                )
            r2["pass_label"] = "corrected"
            r2["raw_notes"] = (
                (r2.get("raw_notes") or "")
                + " | consistency: downgraded ready_today → ready_with_caveats ("
                + "; ".join(reasons)
                + ")"
            ).strip(" |")

    mcp_before = sum(1 for r in rows if r.get("mcp_existing"))
    mcp_after = sum(1 for r in out_rows if r.get("mcp_existing"))

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "mcp_existing_before": mcp_before,
        "mcp_existing_after": mcp_after,
        "mcp_false_positives_stripped": len(mcp_stripped),
        "mcp_stripped_ids": mcp_stripped,
        "curated_human_corrections": curated_applied,
        "note": "Pass3 improves trust: LLM marketplace≠MCP confusion removed; fetch-failed flagships corrected with real doc URLs.",
    }
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2))

    final = {
        "meta": {
            "pass": "final",
            "source": args.inp,
            "pass3_report": args.report,
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "accuracy_story": {
                "pass1": "LLM structure over fetched docs",
                "pass2_verify": "stratified sample re-fetch field scoring",
                "pass3": "deterministic MCP sanitizer + curated human corrections",
            },
        },
        "results": out_rows,
    }
    Path(args.out).write_text(json.dumps(final, indent=2))
    print(f"MCP {mcp_before} → {mcp_after} (stripped {len(mcp_stripped)})")
    print(f"Curated corrections: {len(curated_applied)}")
    print(f"Wrote {args.out}")
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
