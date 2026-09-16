"""Shared models for toolkit research rows."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


AuthMethod = Literal[
    "OAuth2",
    "API key",
    "Basic",
    "Bearer token",
    "PAT / token",
    "None / CLI local",
    "Other",
    "Unknown",
]

AccessModel = Literal[
    "self_serve_free",
    "self_serve_trial",
    "paid_plan_required",
    "admin_approval",
    "partner_or_sales_gated",
    "open_source_local",
    "unclear",
]

Buildability = Literal[
    "ready_today",
    "ready_with_caveats",
    "needs_outreach",
    "not_viable_yet",
]


class ResearchResult(BaseModel):
    id: int
    name: str
    category: str
    one_liner: str = ""
    auth_methods: list[str] = Field(default_factory=list)
    access_model: AccessModel = "unclear"
    access_notes: str = ""
    api_type: str = ""  # REST / GraphQL / SDK / MCP / CLI / none
    api_breadth: str = ""  # narrow / moderate / broad / unknown
    mcp_existing: bool = False
    mcp_notes: str = ""
    buildability: Buildability = "not_viable_yet"
    main_blocker: str = ""
    evidence_urls: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    human_needed: bool = False
    human_reason: str = ""
    raw_notes: str = ""
    pass_label: str = "pass1"  # pass1 | verified | corrected


class AppSeed(BaseModel):
    id: int
    name: str
    category: str
    hint: str
