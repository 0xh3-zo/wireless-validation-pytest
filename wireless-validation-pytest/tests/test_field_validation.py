"""Field-log KPI validation — the triage demo entry point.

These tests are EXPECTED TO FAIL against the seeded fixture logs: each log
is engineered to exhibit one fault-domain signature (coverage hole, missing
neighbor, parameter/config, core reject). They are excluded from the default
test run (see pytest.ini) and selected explicitly by `make demo` /
`pytest -m field_demo`. A red result here is the input to the triage agent,
not a defect in the framework.
"""

from pathlib import Path

import pytest

from wireless_validation.kpis import current_log_file, kpi_check
from wireless_validation.parser import QXDMLogParser

FIXTURES = Path(__file__).parent.parent / "fixtures" / "failing_runs"


@pytest.mark.field_demo
@pytest.mark.parametrize(
    "log_name", sorted(p.name for p in FIXTURES.glob("*.txt"))
)
def test_field_log_kpis(log_name):
    token = current_log_file.set(log_name)
    try:
        kpi_check(QXDMLogParser((FIXTURES / log_name).read_text()))
    finally:
        current_log_file.reset(token)
