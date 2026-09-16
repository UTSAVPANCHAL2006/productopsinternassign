#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
python -m agent.run_research --concurrency 5 --resume
python -m agent.verify --sample 20
python -m agent.correct_pass3
python -m agent.handcheck
python -m agent.composio_probe
python -m agent.analyze_patterns
python -m agent.build_case_study
echo "Open case_study/index.html"
