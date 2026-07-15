"""pytest plugin: Stage 1 of the triage pipeline (automatic, LLM-free).

Captures structured failure evidence recorded by the ``evaluate_*`` helpers
in ``wireless_validation.kpis`` and serializes it to
``runs/<timestamp>/run_record.json`` (and ``runs/latest/`` for tooling) at
session end. No model is ever called from here — the LLM pass is the
engineer-invoked Stage 2 (``python -m wireless_validation.triage``).
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

# src-layout fallback so the repo works even without `pip install -e .`
_SRC = Path(__file__).parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import pytest  # noqa: E402

from wireless_validation import kpis  # noqa: E402

_RUNS_DIR = Path(__file__).parent / "runs"
_outcomes = {"passed": 0, "failed": 0}
_seen_log_files = set()


def pytest_sessionstart(session):
    kpis.collector.reset()
    _outcomes["passed"] = 0
    _outcomes["failed"] = 0
    _seen_log_files.clear()


@pytest.fixture(autouse=True)
def _attribute_evidence(request):
    """Every evidence record self-attributes to the test that produced it."""
    token = kpis.current_test.set(request.node.nodeid)
    yield
    kpis.current_test.reset(token)


def pytest_runtest_logreport(report):
    if report.when == "call":
        if report.passed:
            _outcomes["passed"] += 1
        elif report.failed:
            _outcomes["failed"] += 1
        if report.failed and hasattr(report, "nodeid"):
            pass  # evidence already captured by evaluate_* helpers


def pytest_sessionfinish(session, exitstatus):
    if not kpis.collector.records:
        return  # nothing triage-worthy; keep runs/ clean on green suites

    for rec in kpis.collector.records:
        if rec.get("log_file"):
            _seen_log_files.add(rec["log_file"])

    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    run_record = {
        "schema_version": "1.0",
        "run": {
            "timestamp": ts,
            "total_tests": _outcomes["passed"] + _outcomes["failed"],
            "failed": _outcomes["failed"],
            "log_files": sorted(_seen_log_files),
        },
        "kpi_thresholds": kpis.KPI_THRESHOLDS,
        "truncated": kpis.collector.truncated,
        "evidence_records": kpis.collector.records,
    }

    run_dir = _RUNS_DIR / ts.replace(":", "-")
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_record.json").write_text(
        json.dumps(run_record, indent=2, default=str)
    )
    latest = _RUNS_DIR / "latest"
    if latest.exists():
        shutil.rmtree(latest)
    latest.mkdir(parents=True)
    (latest / "run_record.json").write_text(
        json.dumps(run_record, indent=2, default=str)
    )

    tr = session.config.pluginmanager.get_plugin("terminalreporter")
    if tr:
        tr.write_line("")
        tr.write_line(
            f"[triage] {len(kpis.collector.records)} evidence records -> "
            f"{run_dir / 'run_record.json'}"
        )
        tr.write_line(
            "[triage] next: python -m wireless_validation.triage "
            "runs/latest/run_record.json"
        )
