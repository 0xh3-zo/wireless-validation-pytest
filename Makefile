.PHONY: test demo demo-ai clean

# Green suite: parser, KPI helpers, heuristics, citation validation.
test:
	python -m pytest

# 3-minute demo, no API key required (heuristics-only triage):
#   1. run the seeded field logs (fails BY DESIGN — that's the triage input)
#   2. cluster failures and render both artifacts
demo:
	-python -m pytest tests/test_field_validation.py -m field_demo -q
	PYTHONPATH=src python -m wireless_validation.triage runs/latest/run_record.json --provider none
	@echo ""
	@echo "Artifacts: runs/latest/triage_report.md, runs/latest/exec_summary.md"

# Same demo with the LLM reasoning pass (requires ANTHROPIC_API_KEY).
demo-ai:
	-python -m pytest tests/test_field_validation.py -m field_demo -q
	PYTHONPATH=src python -m wireless_validation.triage runs/latest/run_record.json --provider anthropic
	@echo ""
	@echo "Artifacts: runs/latest/triage_report.md, runs/latest/exec_summary.md"

clean:
	rm -rf runs/ .pytest_cache report.html assets/
