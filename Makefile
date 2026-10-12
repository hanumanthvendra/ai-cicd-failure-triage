.PHONY: help up demo demo-claude test patch check down
SHELL := /bin/bash
PY := python3

help:
	@echo "AI CI/CD Failure Triage — diagnose Jenkins failures with evidence"
	@echo ""
	@echo "  make up            sanity-check Python"
	@echo "  make test          unit tests (no Jenkins needed)"
	@echo "  make demo          fail the demo build, diagnose, patch copy, re-check"
	@echo "  make demo-claude   same diagnosis, Claude narrates (needs ANTHROPIC_API_KEY)"
	@echo "  make patch         write suggested files under out/patched"
	@echo "  make check         local stand-in for docker COPY + kubeconform"
	@echo "  make down          remove out/"

up:
	@$(PY) -c "import triage,sys; print('triage', triage.__version__, sys.version.split()[0])"

test:
	@$(PY) -m unittest -q tests.test_triage

demo:
	@chmod +x scripts/demo.sh
	@./scripts/demo.sh

demo-claude:
	@test -n "$$ANTHROPIC_API_KEY" || { echo "export ANTHROPIC_API_KEY first"; exit 1; }
	@$(PY) -m triage diagnose

patch:
	@$(PY) -m triage apply-suggested

check:
	@$(PY) -m triage check --workspace demo/failed; echo "(expected FAIL on the broken tree)"

down:
	rm -rf out && echo "out/ removed."
