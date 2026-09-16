# Composio Product Ops Intern — Toolkit Research Agent

Take-home for **AI Product Ops Intern**: research **100 apps** for toolkit readiness (auth, self-serve vs gated, API surface, MCP, buildability) with an **agent pipeline**, then present **patterns + verification** on one HTML case study.

## Live deliverable

- Case study: see `SUBMIT.md` / deployed Vercel URL  
- This repo: how to run the research agent (below)

## Assignment → how we covered it

| Ask | Where |
|-----|--------|
| Per-app research fields | `output/results_final.json` + Findings matrix |
| Patterns / clusters | Case study §01 + `output/patterns.json` |
| Agent, not by hand | `agent/run_research.py` (+ `agent/demo.py` proof trigger) |
| Composio spirit | `agent/composio_probe.py` (honest success/fail) |
| Verify accuracy | Pass2 sample (`verification/report.json`), Pass3 MCP cleanup, human/browser handcheck (`verification/handcheck.json`) |
| Single HTML case study | `case_study/index.html` |

## Pipeline

```
apps.json → fetch docs → OpenAI structure → results_pass1.json
         → verify sample → results_verified.json
         → MCP sanitize + curated human fixes → results_final.json
         → patterns + HTML case study
```

**Human in the loop when:** 403/JS docs, no public API, sales/partner gate, conflicting auth. Flagged `human_needed`.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

```
OPENAI_API_KEY=...
COMPOSIO_API_KEY=...   # optional; probe records failure honestly if invalid
OPENAI_MODEL=gpt-4.1-mini
```

## Run

```bash
# Live proof (4 apps → printed table)
python -m agent.demo --ids 2,61,71,81

# Full 100
python -m agent.run_research --concurrency 5
python -m agent.verify --sample 20
python -m agent.correct_pass3
python -m agent.handcheck
python -m agent.composio_probe
python -m agent.analyze_patterns
python -m agent.build_case_study
open case_study/index.html
```

Or: `bash scripts/run_all.sh`

## Accuracy story (summary)

1. **Pass 1** — LLM over fetched docs (noisy MCP / marketplace confusion)  
2. **Pass 2** — stratified sample re-fetch ≈ **89%** field hit rate  
3. **Pass 3** — MCP false positives **44 → 25**; curated fixes for fetch failures  
4. **Hand/browser check** — 10 mixed apps; misses (WhatsApp access, PitchBook gate, GoHighLevel docs, Salesforce 403) corrected and shown on the page  

## Submit

1. Live HTML link  
2. This public repo URL  

Never commit `.env`.
