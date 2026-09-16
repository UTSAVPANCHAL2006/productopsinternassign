"""Build a clear, 2-minute case study HTML for the Composio take-home."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def esc(s: object) -> str:
    return (
        str(s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def access_label(m: str) -> str:
    return {
        "self_serve_free": "Self-serve free",
        "self_serve_trial": "Self-serve trial",
        "paid_plan_required": "Paid plan",
        "admin_approval": "Admin approval",
        "partner_or_sales_gated": "Partner / sales",
        "open_source_local": "Open source",
        "unclear": "Unclear",
    }.get(m, m or "—")


def build_label(m: str) -> str:
    return {
        "ready_today": "Ready today",
        "ready_with_caveats": "Ready w/ caveats",
        "needs_outreach": "Needs outreach",
        "not_viable_yet": "Not viable yet",
    }.get(m, m or "—")


def short(s: object, n: int = 88) -> str:
    t = " ".join(str(s or "").split())
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def pct(n: float | int, d: int) -> str:
    return f"{round(100 * n / max(d, 1))}%"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default=str(ROOT / "output" / "results_final.json"))
    parser.add_argument("--patterns", default=str(ROOT / "output" / "patterns.json"))
    parser.add_argument("--verification", default=str(ROOT / "verification" / "report.json"))
    parser.add_argument("--pass3", default=str(ROOT / "verification" / "pass3_corrections.json"))
    parser.add_argument("--handcheck", default=str(ROOT / "verification" / "handcheck.json"))
    parser.add_argument("--composio", default=str(ROOT / "verification" / "composio_probe.json"))
    parser.add_argument("--backlog", default=str(ROOT / "output" / "priority_backlog.json"))
    parser.add_argument("--out", default=str(ROOT / "case_study" / "index.html"))
    args = parser.parse_args()

    results = json.loads(Path(args.results).read_text())["results"]
    patterns = json.loads(Path(args.patterns).read_text())
    verification = json.loads(Path(args.verification).read_text()) if Path(args.verification).exists() else {}
    pass3 = json.loads(Path(args.pass3).read_text()) if Path(args.pass3).exists() else {}
    handcheck = json.loads(Path(args.handcheck).read_text()) if Path(args.handcheck).exists() else {}
    composio = json.loads(Path(args.composio).read_text()) if Path(args.composio).exists() else {}
    backlog = json.loads(Path(args.backlog).read_text()) if Path(args.backlog).exists() else {}

    n = len(results)
    build_c = patterns.get("buildability_counts") or {}
    access_c = patterns.get("access_counts") or {}
    auth_c = patterns.get("auth_counts") or {}
    easy = patterns.get("easy_wins") or []
    outreach = patterns.get("outreach_queue") or []
    blockers = patterns.get("common_blockers") or []
    by_cat = patterns.get("by_category") or {}
    summary = verification.get("summary") or {}
    vmeta = verification.get("meta") or {}
    audits = verification.get("audits") or []

    auto_acc = summary.get("avg_field_hit_rate", 0)
    auto_acc_s = f"{auto_acc:.0%}" if isinstance(auto_acc, float) else str(auto_acc)
    hand_acc = handcheck.get("hand_accuracy_before_corrections", 0)
    hand_acc_s = f"{hand_acc:.0%}" if isinstance(hand_acc, (int, float)) else str(hand_acc)

    top_auth = list(auth_c.items())[:3]
    top_auth_txt = ", ".join(f"{k} ({v})" for k, v in top_auth)
    self_serve = (
        access_c.get("self_serve_free", 0)
        + access_c.get("self_serve_trial", 0)
        + access_c.get("open_source_local", 0)
    )
    gated = (
        access_c.get("paid_plan_required", 0)
        + access_c.get("partner_or_sales_gated", 0)
        + access_c.get("admin_approval", 0)
    )
    ready_strict = build_c.get("ready_today", 0)
    ready = ready_strict + build_c.get("ready_with_caveats", 0)
    human_n = sum(1 for r in results if r.get("human_needed"))
    mcp_n = patterns.get("mcp_existing_count", 0)
    composio_overlap = composio.get("overlap_count")
    composio_tk = composio.get("toolkit_count")

    # Plain reviewer headlines (short)
    headlines = [
        f"<strong>Auth:</strong> {top_auth_txt}. Ship OAuth2 + API-key adapters as the default toolkit stack.",
        f"<strong>Access:</strong> {self_serve}/{n} self-serve · {gated}/{n} paid/admin/partner-gated. Ops capacity should sit on the gated tail, not re-scraping docs.",
        f"<strong>Buildability (strict):</strong> <strong>{ready_strict}</strong> ready_today (self-serve · conf≥0.85 · no human flag). "
        f"{build_c.get('ready_with_caveats', 0)} more are ready_with_caveats (paid/admin/partial docs). "
        f"{build_c.get('needs_outreach', 0)} need outreach. Paid plan ≠ silent ready_today.",
        f"<strong>MCP:</strong> pass1 over-counted marketplaces as MCP ({pass3.get('mcp_existing_before', '?')}) → after cleanup <strong>{mcp_n}</strong> credible MCP signals.",
        f"<strong>Categories:</strong> Dev/Infra + Productivity are the densest self-serve REST wins; niche fintech + thin AI-native apps burn ops time.",
        f"<strong>Common blocker:</strong> {esc(((blockers[0][0] if blockers else 'thin or missing public docs').rstrip('.'))[:110])}.",
    ]

    week1 = backlog.get("week1_build") or []
    thin = backlog.get("thin_or_blocked") or []
    week1_li = "".join(
        f"<li><b>{esc(x['name'])}</b><span>{esc(x.get('category'))} · {esc(', '.join(x.get('auth') or []))}</span></li>"
        for x in week1[:12]
    )
    thin_li = "".join(
        f"<li><b>{esc(x['name'])}</b><span>conf {x.get('confidence')} · {esc(short(x.get('blocker'), 80))}</span></li>"
        for x in thin[:8]
    ) or "<li>None — every app had at least a partial signal.</li>"

    easy_li = "".join(
        f"<li><b>{esc(x['name'])}</b><span>{esc(x['category'])}</span></li>" for x in easy[:10]
    )
    outreach_li = "".join(
        f"<li><b>{esc(x['name'])}</b><span>{esc(short(x.get('blocker') or x.get('access') or '', 90))}</span></li>"
        for x in outreach[:10]
    )

    cats = sorted({r["category"] for r in results})
    cat_opts = "".join(f"<option value=\"{esc(c)}\">{esc(c)}</option>" for c in cats)

    cat_rows = ""
    for cat, s in by_cat.items():
        cat_rows += (
            f"<tr><td>{esc(cat)}</td><td>{s['n']}</td><td>{s['ready']}</td>"
            f"<td>{s['self_serve']}</td><td>{s['gated']}</td><td>{s['outreach']}</td>"
            f"<td>{pct(s['ready'], s['n'])}</td></tr>"
        )

    # Matrix rows
    matrix = []
    for r in sorted(results, key=lambda x: x["id"]):
        ev = r.get("evidence_urls") or []
        ev_html = " ".join(
            f'<a href="{esc(u)}" target="_blank" rel="noopener">docs</a>' for u in ev[:2]
        ) or "—"
        human = '<span class="flag">human</span>' if r.get("human_needed") else ""
        matrix.append(
            "<tr "
            f"data-build='{esc(r.get('buildability'))}' "
            f"data-access='{esc(r.get('access_model'))}' "
            f"data-cat='{esc(r['category'])}' "
            f"data-human='{1 if r.get('human_needed') else 0}' "
            f"data-mcp='{1 if r.get('mcp_existing') else 0}'>"
            f"<td>{r['id']}</td>"
            f"<td><div class='app'>{esc(r['name'])} {human}</div>"
            f"<div class='sub'>{esc(short(r.get('one_liner'), 110))}</div></td>"
            f"<td data-catcell='1'>{esc(r['category'])}</td>"
            f"<td>{esc(', '.join(r.get('auth_methods') or []))}</td>"
            f"<td>{esc(access_label(r.get('access_model','')))}</td>"
            f"<td>{esc(r.get('api_type'))} · {esc(r.get('api_breadth'))}</td>"
            f"<td>{'Yes' if r.get('mcp_existing') else 'No'}</td>"
            f"<td><span class='pill {esc(r.get('buildability'))}'>{esc(build_label(r.get('buildability','')))}</span>"
            f"<div class='sub'>{esc(r.get('main_blocker'))}</div></td>"
            f"<td>{float(r.get('confidence') or 0):.2f}</td>"
            f"<td>{ev_html}</td></tr>"
        )

    hand_rows = "".join(
        f"<tr><td>{h.get('id')}</td><td>{esc(h.get('name'))}</td>"
        f"<td>{esc(h.get('method'))}</td>"
        f"<td class='{'ok' if h.get('verdict')=='pass' else 'fix'}'>{esc(h.get('verdict'))}</td>"
        f"<td>{esc(h.get('notes'))}</td></tr>"
        for h in (handcheck.get("checks") or [])
    )

    audit_parts = []
    for a in audits:
        miss = a.get("misses") or []
        miss_txt = "; ".join(
            f"{m.get('field')}: {m.get('pass1')} → {m.get('pass2')}" for m in miss
        ) or "—"
        audit_parts.append(
            f"<tr><td>{a.get('id')}</td><td>{esc(a.get('name'))}</td>"
            f"<td>{a.get('hit_rate', 0):.0%}</td>"
            f"<td>{esc(', '.join(a.get('hits') or []))}</td>"
            f"<td class='miss'>{esc(miss_txt)}</td></tr>"
        )
    audit_rows = "".join(audit_parts)

    composio_line = (
        f"Docs fetch + LLM = primary research. Composio SDK catalog = secondary cross-check: "
        f"{composio_overlap}/{n} research apps match an existing toolkit "
        f"({composio_tk} toolkits listed). Catalog answers “already shipped?” — not auth/access evidence."
        if composio.get("ok") and composio_overlap is not None
        else (
            "Composio probe failed — research still ran via docs fetch + OpenAI; failure recorded honestly. "
            "Docs-first is intentional: catalog ≠ per-app auth/access/MCP evidence."
            if composio.get("enabled")
            else "Composio key unset — research ran docs-first (fetch + OpenAI). Catalog cross-check optional."
        )
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Composio Take-home · 100-App Toolkit Research</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Literata:opsz,wght@7..72,600;7..72,700&display=swap" rel="stylesheet" />
<style>
:root {{
  --bg:#f6f7f4; --card:#fff; --ink:#18212b; --muted:#5b6b79; --line:#e3e8ec;
  --teal:#0f766e; --teal2:#e7f6f3; --amber:#9a6700; --amber2:#fff6e5; --red:#b42318; --red2:#feeceb;
}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:"DM Sans",system-ui,sans-serif;color:var(--ink);background:
  radial-gradient(700px 320px at 0% 0%,#e4f4f0,transparent 60%),
  radial-gradient(600px 280px at 100% 0%,#e8eef6,transparent 55%), var(--bg);line-height:1.55}}
.wrap{{max-width:1080px;margin:0 auto;padding:28px 18px 64px}}
h1,h2,h3{{font-family:Literata,Georgia,serif;letter-spacing:-.02em;line-height:1.15;margin:0 0 8px}}
h1{{font-size:clamp(1.9rem,3.8vw,2.7rem);max-width:14ch}}
h2{{font-size:1.45rem}}
p,li{{color:var(--ink)}}
.muted{{color:var(--muted)}}
a{{color:#1d6fbf}}
.eyebrow{{font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--teal);margin:0 0 10px}}
.lede{{color:var(--muted);max-width:62ch;margin:0 0 18px;font-size:1.05rem}}
.nav{{display:flex;flex-wrap:wrap;gap:8px;margin:16px 0 0}}
.nav a{{text-decoration:none;color:var(--ink);font-size:13px;font-weight:600;padding:8px 12px;border:1px solid var(--line);border-radius:999px;background:#fff}}
.nav a:hover,.nav a.on{{border-color:#b7ddd7;background:var(--teal2);color:var(--teal)}}
.stickybar{{position:sticky;top:0;z-index:20;backdrop-filter:blur(10px);background:rgba(246,247,244,.9);border-bottom:1px solid var(--line);margin:0 -18px 8px;padding:10px 18px}}
.plan{{display:grid;grid-template-columns:1.1fr .9fr .9fr;gap:12px;margin-top:14px}}
@media(max-width:900px){{.plan{{grid-template-columns:1fr}}}}
.plan .box ul{{max-height:280px;overflow:auto}}
.plan .box h3{{font-size:.95rem}}
.links{{display:flex;flex-wrap:wrap;gap:10px;margin-top:12px}}
.links a{{font-size:13px;font-weight:600;text-decoration:none;color:var(--teal);border-bottom:1px solid #9fd3cb}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:22px 22px 24px;margin:16px 0;box-shadow:0 10px 30px rgba(24,33,43,.04)}}
.tldr{{background:linear-gradient(180deg,#fff,#f7fcfa);border-color:#cfe8e2}}
.tldr ol{{margin:12px 0 0;padding-left:1.2rem}}
.tldr li{{margin:0 0 10px}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:14px}}
@media(max-width:800px){{.stats{{grid-template-columns:1fr 1fr}}}}
.stat{{border:1px solid var(--line);border-radius:12px;padding:12px 14px;background:#fff}}
.stat b{{display:block;font-family:Literata,Georgia,serif;font-size:1.55rem;color:var(--teal)}}
.stat span{{font-size:12px;color:var(--muted)}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
@media(max-width:760px){{.grid2{{grid-template-columns:1fr}}}}
.box{{border:1px solid var(--line);border-radius:12px;padding:14px 16px;background:#fcfdfc}}
.box h3{{font-size:1rem;margin-bottom:8px}}
.box.wins h3{{color:var(--teal)}}
.box.queue h3{{color:var(--amber)}}
.box ul{{list-style:none;margin:0;padding:0}}
.box li{{padding:8px 0;border-bottom:1px solid var(--line);display:flex;flex-direction:column;gap:2px;font-size:14px}}
.box li:last-child{{border-bottom:0}}
.box li span{{color:var(--muted);font-size:12px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th,td{{text-align:left;padding:10px 8px;border-bottom:1px solid var(--line);vertical-align:top}}
th{{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);background:#f3f6f7;position:sticky;top:0}}
.scroll{{overflow:auto;max-height:560px;border:1px solid var(--line);border-radius:12px}}
.app{{font-weight:700}}
.sub{{color:var(--muted);font-size:12px;margin-top:3px;max-width:280px}}
.flag{{font-size:10px;font-weight:700;text-transform:uppercase;color:var(--amber);background:var(--amber2);padding:1px 5px;border-radius:4px;margin-left:4px}}
.pill{{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:700;border:1px solid var(--line)}}
.ready_today{{background:var(--teal2);color:#0b5f58;border-color:#b7e4dc}}
.ready_with_caveats{{background:var(--amber2);color:#7a5200;border-color:#f0d7a0}}
.needs_outreach{{background:#fff3e8;color:#9a3412;border-color:#ffd7b5}}
.not_viable_yet{{background:var(--red2);color:var(--red);border-color:#f5c2c0}}
.chips{{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 10px}}
.chip,.btn{{appearance:none;border:1px solid var(--line);background:#fff;border-radius:999px;padding:8px 12px;font:inherit;font-size:13px;font-weight:600;cursor:pointer}}
.chip.on,.btn.primary{{background:var(--teal2);border-color:#9fd3cb;color:#0b5f58}}
.btn.primary{{background:var(--teal);border-color:var(--teal);color:#fff}}
.filters{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:10px}}
.filters input,.filters select{{border:1px solid var(--line);border-radius:10px;padding:8px 10px;font:inherit}}
#count{{margin-left:auto;font-size:12px;color:var(--muted)}}
.steps{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px}}
@media(max-width:900px){{.steps{{grid-template-columns:1fr 1fr}}}}
.step{{border:1px solid var(--line);border-radius:12px;padding:12px;background:#fff;font-size:13px}}
.step b{{display:block;color:var(--teal);font-size:11px;letter-spacing:.06em;text-transform:uppercase;margin-bottom:4px}}
.note{{border-left:3px solid var(--amber);background:var(--amber2);padding:12px 14px;border-radius:0 10px 10px 0;margin-top:12px;font-size:14px}}
.note.ok{{border-left-color:var(--teal);background:var(--teal2)}}
.journey{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:12px 0}}
@media(max-width:800px){{.journey{{grid-template-columns:1fr 1fr}}}}
.j{{border:1px solid var(--line);border-radius:12px;padding:12px;background:#fff}}
.j em{{display:block;font-style:normal;font-size:11px;font-weight:700;color:var(--teal);letter-spacing:.06em;margin-bottom:4px}}
.ok{{color:var(--teal);font-weight:700}}
.fix{{color:var(--amber);font-weight:700}}
.miss{{color:var(--amber);font-size:12px}}
pre{{margin:0;background:#18212b;color:#dce6ee;border-radius:12px;padding:14px 16px;overflow:auto;font-size:12px;line-height:1.55}}
.proof-top{{display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:10px}}
.toast{{position:fixed;right:18px;bottom:18px;background:#18212b;color:#fff;padding:10px 14px;border-radius:10px;font-size:13px;opacity:0;transform:translateY(6px);transition:.2s}}
.toast.show{{opacity:1;transform:none}}
footer{{margin-top:18px;color:var(--muted);font-size:12px}}
</style>
</head>
<body>
<div class="wrap">
  <p class="eyebrow">Composio · AI Product Ops Intern · Take-home</p>
  <h1>100-app toolkit readiness map</h1>
  <p class="lede">
    Before Composio builds a toolkit, ops researches auth, access gates, API surface, and MCP readiness.
    This case study does that for the 100-app set — with an agent pipeline, clear patterns, and verified accuracy.
  </p>
  <div class="links">
    <a href="https://github.com/UTSAVPANCHAL2006/productopsinternassign" target="_blank" rel="noopener">Public repo</a>
    <a href="#plan">Easy wins vs outreach</a>
    <a href="#matrix">Filterable findings + CSV</a>
    <a href="#verification">Accuracy journey</a>
  </div>
  <div class="stats">
    <div class="stat"><b>{n}</b><span>apps researched</span></div>
    <div class="stat"><b>{build_c.get('ready_today',0)}</b><span>strict ready today</span></div>
    <div class="stat"><b>{len(outreach)}</b><span>outreach / gated</span></div>
    <div class="stat"><b>{auto_acc_s} sample</b><span>auto verify · not 100%</span></div>
  </div>
  <div class="stickybar">
  <nav class="nav" style="margin:0">
    <a href="#patterns" data-nav>1 Patterns</a>
    <a href="#plan" data-nav>2 Queues</a>
    <a href="#matrix" data-nav>3 Findings</a>
    <a href="#agent" data-nav>4 Agent</a>
    <a href="#proof" data-nav>5 Proof</a>
    <a href="#verification" data-nav>6 Verification</a>
  </nav>
  </div>

  <section class="card tldr" id="patterns">
    <p class="eyebrow">01 · Patterns (read this first)</p>
    <h2>What the 100 apps say</h2>
    <p class="muted">Assignment ask: don’t dump rows — cluster and say where easy wins are vs outreach.</p>
    <ol>
      {''.join(f'<li>{item}</li>' for item in headlines)}
    </ol>
    <div class="grid2" style="margin-top:16px">
      <div class="box wins">
        <h3>Easy wins — build toolkit now</h3>
        <ul>{easy_li}</ul>
      </div>
      <div class="box queue">
        <h3>Needs outreach / partner gate</h3>
        <ul>{outreach_li}</ul>
      </div>
    </div>
    <div class="scroll" style="max-height:320px;margin-top:14px">
      <table>
        <thead><tr><th>Category</th><th>N</th><th>Buildable</th><th>Self-serve</th><th>Gated</th><th>Outreach</th><th>Ready %</th></tr></thead>
        <tbody>{cat_rows}</tbody>
      </table>
    </div>
  </section>

  <section class="card" id="plan">
    <p class="eyebrow">02 · Queues (from patterns)</p>
    <h2>Easy wins vs outreach vs thin docs</h2>
    <p class="muted">Assignment ask — cluster where eng can build now vs where outreach / thin evidence blocks. Not a day-1 strategy deck.</p>
    <div class="plan">
      <div class="box wins">
        <h3>Easy wins ({len(week1)})</h3>
        <p class="muted" style="margin:0 0 8px;font-size:12px">ready_today · conf ≥ 0.85 · self-serve · showing top {min(12, len(week1))}</p>
        <ul>{week1_li}</ul>
      </div>
      <div class="box queue">
        <h3>Outreach queue ({len(outreach)})</h3>
        <p class="muted" style="margin:0 0 8px;font-size:12px">partner / sales / needs_outreach</p>
        <ul>{outreach_li}</ul>
      </div>
      <div class="box">
        <h3>Thin / defeated ({len(thin)})</h3>
        <p class="muted" style="margin:0 0 8px;font-size:12px">correct finding with evidence — not a failure</p>
        <ul>{thin_li}</ul>
      </div>
    </div>
  </section>

  <section class="card" id="matrix">
    <p class="eyebrow">03 · Findings matrix</p>
    <h2>All 100 apps — skimmable evidence table</h2>
    <p class="muted">Fields required by the brief: category, one-liner, auth, access, API, MCP, verdict, blocker, confidence, evidence.</p>
    <div class="chips" id="chips">
      <button type="button" class="chip on" data-q="all">All</button>
      <button type="button" class="chip" data-q="ready">Ready today</button>
      <button type="button" class="chip" data-q="caveats">Caveats</button>
      <button type="button" class="chip" data-q="outreach">Needs outreach</button>
      <button type="button" class="chip" data-q="human">Human needed</button>
      <button type="button" class="chip" data-q="mcp">Has MCP</button>
      <button type="button" class="chip" data-q="gated">Partner / sales</button>
    </div>
    <div class="filters">
      <input id="q" type="search" placeholder="Search app…" />
      <select id="build">
        <option value="">All verdicts</option>
        <option value="ready_today">Ready today</option>
        <option value="ready_with_caveats">Ready w/ caveats</option>
        <option value="needs_outreach">Needs outreach</option>
        <option value="not_viable_yet">Not viable yet</option>
      </select>
      <select id="access">
        <option value="">All access</option>
        <option value="self_serve_free">Self-serve free</option>
        <option value="self_serve_trial">Self-serve trial</option>
        <option value="paid_plan_required">Paid plan</option>
        <option value="partner_or_sales_gated">Partner / sales</option>
        <option value="admin_approval">Admin approval</option>
        <option value="open_source_local">Open source</option>
        <option value="unclear">Unclear</option>
      </select>
      <select id="cat"><option value="">All categories</option>{cat_opts}</select>
      <button type="button" class="btn" id="reset">Reset</button>
      <button type="button" class="btn primary" id="csv">Download CSV</button>
      <span id="count"></span>
    </div>
    <div class="scroll">
      <table id="matrix-table">
        <thead>
          <tr>
            <th>#</th><th>App</th><th>Category</th><th>Auth</th><th>Access</th>
            <th>API</th><th>MCP</th><th>Verdict</th><th>Conf</th><th>Evidence</th>
          </tr>
        </thead>
        <tbody>
          {''.join(matrix)}
        </tbody>
      </table>
    </div>
  </section>

  <section class="card" id="agent">
    <p class="eyebrow">04 · The agent (not by hand)</p>
    <h2>Pipeline that researched the 100</h2>
    <p class="muted">Workhorse = docs fetch + OpenAI structuring. Composio toolkit catalog is a secondary overlap check (spirit of the role), not the source of auth/access verdicts.</p>
    <div class="steps">
      <div class="step"><b>1 Seed</b>Load 100 apps from <code>data/apps.json</code></div>
      <div class="step"><b>2 Fetch</b>HTTP pull developer docs into evidence packs</div>
      <div class="step"><b>3 Structure</b>LLM fills auth / access / API / MCP / verdict JSON</div>
      <div class="step"><b>4 Verify</b>Sample re-fetch + human/browser handcheck</div>
      <div class="step"><b>5 Correct</b>MCP sanitizer + consistency + curated fixes</div>
    </div>
    <div class="note">
      <strong>Where a human was needed:</strong> 403 / JS-walled docs, missing public API pages,
      “contact sales” gates, and MCP false positives (marketplace ≠ Model Context Protocol).
      {human_n} rows still flagged <em>human</em> in the matrix.
    </div>
    <div class="note ok"><strong>Composio:</strong> {esc(composio_line)}</div>
  </section>

  <section class="card" id="proof">
    <p class="eyebrow">05 · Proof</p>
    <div class="proof-top">
      <div>
        <h2>Live page + runnable agent</h2>
        <p class="muted" style="margin:0">This deployed case study is the deliverable. Repo README runs the agent.</p>
      </div>
      <button type="button" class="btn primary" id="copy">Copy run commands</button>
    </div>
    <pre id="cmds"># quick proof (4 apps)
python -m agent.demo --ids 2,61,71,81

# full research
python -m agent.run_research --concurrency 5
python -m agent.verify --sample 20
python -m agent.correct_pass3
python -m agent.handcheck
python -m agent.composio_probe
python -m agent.analyze_patterns
python -m agent.build_case_study</pre>
  </section>

  <section class="card" id="verification">
    <p class="eyebrow">06 · Verification (accuracy first)</p>
    <h2>How trust improved across loops</h2>
    <p class="muted">Scope honesty: we do <strong>not</strong> claim 100/100 hand-verified fields. Trust comes from stratified auto sample + expanded hand/browser sample + targeted corrections.</p>
    <div class="note">
      <strong>What “verified” means here:</strong>
      Auto pass2 = {vmeta.get('sample_size', 20)}/{n} apps · Hand/browser = {handcheck.get('sample_size', 15)}/{n} apps ·
      Pass3 consistency + MCP cleanup runs on all {n}. Remaining rows inherit agent confidence + human_needed flags.
    </div>
    <div class="journey">
      <div class="j"><em>Pass 1</em>Agent research on all 100. Fast but noisy (MCP/marketplace confusion; some 403/JS docs).</div>
      <div class="j"><em>Pass 2</em>Auto re-fetch sample of {vmeta.get('sample_size',20)}. Field hit rate <strong>{auto_acc_s}</strong> ({summary.get('perfect_rows','—')} perfect / {summary.get('weak_rows','—')} weak).</div>
      <div class="j"><em>Pass 3</em>MCP false positives cleaned: {pass3.get('mcp_existing_before','?')} → <strong>{pass3.get('mcp_existing_after','?')}</strong>. Consistency: paid/admin cannot stay silent ready_today.</div>
      <div class="j"><em>Human + browser</em>Hand-opened {handcheck.get('sample_size',15)} apps. Pre-fix hand accuracy <strong>{hand_acc_s}</strong>; {handcheck.get('corrected_count',0)} corrected (WhatsApp, PitchBook, GoHighLevel, Salesforce…).</div>
    </div>

    <h3 style="margin-top:8px">Human / browser handcheck</h3>
    <div class="scroll" style="max-height:260px;margin:8px 0 14px">
      <table>
        <thead><tr><th>ID</th><th>App</th><th>Method</th><th>Verdict</th><th>Notes</th></tr></thead>
        <tbody>{hand_rows}</tbody>
      </table>
    </div>

    <h3>Auto sample hits / misses</h3>
    <p class="muted">Sample ids: {esc(', '.join(str(i) for i in (vmeta.get('sample_ids') or [])))}</p>
    <div class="scroll" style="max-height:340px">
      <table>
        <thead><tr><th>ID</th><th>App</th><th>Hit rate</th><th>Hits</th><th>Misses</th></tr></thead>
        <tbody>{audit_rows}</tbody>
      </table>
    </div>
  </section>

  <footer>
    Built for the Composio AI Product Ops Intern take-home.
    Gated / thin-docs apps with evidence are correct findings — not failures.
  </footer>
</div>
<div class="toast" id="toast"></div>
<script>
(function(){{
  const q=document.getElementById('q');
  const build=document.getElementById('build');
  const access=document.getElementById('access');
  const cat=document.getElementById('cat');
  const count=document.getElementById('count');
  const chips=[...document.querySelectorAll('#chips .chip')];
  const rows=[...document.querySelectorAll('#matrix-table tbody tr')];
  let quick='all';
  const toast=document.getElementById('toast');
  function tip(m){{toast.textContent=m;toast.classList.add('show');clearTimeout(tip.t);tip.t=setTimeout(()=>toast.classList.remove('show'),1600)}}
  function matchQuick(tr){{
    if(quick==='all') return true;
    if(quick==='ready') return tr.dataset.build==='ready_today';
    if(quick==='caveats') return tr.dataset.build==='ready_with_caveats';
    if(quick==='outreach') return tr.dataset.build==='needs_outreach'||tr.dataset.access==='partner_or_sales_gated';
    if(quick==='human') return tr.dataset.human==='1';
    if(quick==='mcp') return tr.dataset.mcp==='1';
    if(quick==='gated') return tr.dataset.access==='partner_or_sales_gated';
    return true;
  }}
  function apply(){{
    const qq=(q.value||'').toLowerCase().trim();
    let shown=0;
    rows.forEach(tr=>{{
      const okQ=!qq||tr.innerText.toLowerCase().includes(qq);
      const okB=!build.value||tr.dataset.build===build.value;
      const okA=!access.value||tr.dataset.access===access.value;
      const okC=!cat.value||tr.dataset.cat===cat.value;
      const show=okQ&&okB&&okA&&okC&&matchQuick(tr);
      tr.style.display=show?'':'none';
      if(show) shown++;
    }});
    count.textContent=shown+' / '+rows.length+' shown';
  }}
  function csvEscape(v){{
    const s=String(v??'');
    return /[",\\n]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s;
  }}
  function downloadCsv(){{
    const headers=['id','app','category','auth','access','api','mcp','verdict','confidence','blocker'];
    const lines=[headers.join(',')];
    rows.forEach(tr=>{{
      if(tr.style.display==='none') return;
      const tds=[...tr.children];
      const app=(tds[1].querySelector('.app')?.textContent||'').replace(/\\s+human\\s*$/i,'').trim();
      const blocker=tds[7].querySelector('.sub')?.textContent||'';
      const verdict=tds[7].querySelector('.pill')?.textContent||'';
      lines.push([
        tds[0].textContent.trim(),
        app,
        tds[2].textContent.trim(),
        tds[3].textContent.trim(),
        tds[4].textContent.trim(),
        tds[5].textContent.trim(),
        tds[6].textContent.trim(),
        verdict,
        tds[8].textContent.trim(),
        blocker
      ].map(csvEscape).join(','));
    }});
    const blob=new Blob([lines.join('\\n')],{{type:'text/csv;charset=utf-8'}});
    const a=document.createElement('a');
    a.href=URL.createObjectURL(blob);
    a.download='composio_100_apps_filtered.csv';
    a.click();
    URL.revokeObjectURL(a.href);
    tip('CSV downloaded');
  }}
  chips.forEach(c=>c.addEventListener('click',()=>{{
    quick=c.dataset.q; chips.forEach(x=>x.classList.toggle('on',x===c));
    build.value=''; access.value=''; cat.value=''; apply();
    document.getElementById('matrix').scrollIntoView({{behavior:'smooth'}});
  }}));
  q.addEventListener('input',apply);
  function resetQuick(){{quick='all';chips.forEach(x=>x.classList.toggle('on',x.dataset.q==='all'));apply()}}
  build.addEventListener('change',resetQuick);
  access.addEventListener('change',resetQuick);
  cat.addEventListener('change',resetQuick);
  document.getElementById('reset').addEventListener('click',()=>{{
    q.value='';build.value='';access.value='';cat.value='';quick='all';
    chips.forEach(x=>x.classList.toggle('on',x.dataset.q==='all')); apply(); tip('Filters reset');
  }});
  document.getElementById('csv').addEventListener('click',downloadCsv);
  document.querySelectorAll('[data-nav]').forEach(a=>a.addEventListener('click',e=>{{
    e.preventDefault();
    const id=a.getAttribute('href').slice(1);
    document.getElementById(id)?.scrollIntoView({{behavior:'smooth'}});
    document.querySelectorAll('[data-nav]').forEach(n=>n.classList.toggle('on',n===a));
  }}));
  const sections=['patterns','plan','matrix','agent','proof','verification'];
  const navs=[...document.querySelectorAll('[data-nav]')];
  const spy=()=>{{
    let cur='patterns';
    for(const id of sections){{
      const el=document.getElementById(id);
      if(el && el.getBoundingClientRect().top<=120) cur=id;
    }}
    navs.forEach(n=>n.classList.toggle('on',n.getAttribute('href')==='#'+cur));
  }};
  window.addEventListener('scroll',spy,{{passive:true}});
  spy();
  document.getElementById('copy').addEventListener('click',async()=>{{
    const t=document.getElementById('cmds').innerText;
    try{{await navigator.clipboard.writeText(t)}}catch{{const ta=document.createElement('textarea');ta.value=t;document.body.appendChild(ta);ta.select();document.execCommand('copy');ta.remove()}}
    tip('Commands copied');
  }});
  apply();
}})();
</script>
</body>
</html>
"""
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(html)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
