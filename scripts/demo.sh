#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -f api-key.txt ]; then
  export ANTHROPIC_API_KEY="$(tr -d '[:space:]' < api-key.txt)"
fi
PY=python3

hr(){ printf '\033[1;36m────────────────────────────────────────────────────────────\033[0m\n'; }
title(){ hr; printf '\033[1m  %s\033[0m\n' "$*"; hr; }

title "PROOF 1 — Jenkins PR-47 is red (bad Dockerfile + invalid replicas)"
$PY -m triage check --workspace demo/failed || true

title "PROOF 2 — Assistant reads console + JUnit + git diff (does not rebuild)"
$PY -m triage diagnose --out out

title "PROOF 3 — Human applies the suggested patch to a copy, then re-checks"
$PY -m triage apply-suggested --out out/patched
$PY -m triage check --workspace out/patched

hr
echo "→ Causes cite log lines, JUnit names, and the PR diff."
echo "→ The assistant never retriggers Jenkins. A human reruns CI after applying the patch."
