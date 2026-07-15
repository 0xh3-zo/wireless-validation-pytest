"""KPI thresholds, evidence collection, and evaluation helpers.

Design contract (agreed in triage-agent design review):

  * Tests route KPI assertions through the ``evaluate_*`` helpers below.
  * Each helper records **structured, event-level evidence** into the run
    collector *before* any assertion fires, so a failing test still leaves
    behind machine-triageable records (KPI values, cells, timestamps,
    cause codes) — not just an assertion string.
  * The pytest plugin in ``conftest.py`` serializes the collector into
    ``runs/<timestamp>/run_record.json`` at session end.

The collector is deliberately dumb: an append-only list with ID assignment
and a truncation cap. All judgment lives in ``triage/heuristics.py``.
"""

from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime
from typing import Dict, List, Optional

from .parser import QXDMLogParser

# --------------------------------------------------------------------------- #
# Thresholds (single source of truth — also embedded in run_record.json so the
# triage layer judges evidence against the same bars the tests used)
# --------------------------------------------------------------------------- #
KPI_THRESHOLDS: Dict = {
    "rsrp_min_dbm": -110,           # 3GPP TS 38.133 usable-coverage floor
    "rsrq_min_db": -15,             # 3GPP TS 38.133
    "sinr_min_db": 0,               # baseline decode threshold
    "rsrp_fail_fraction_max": 0.20, # <=20% of samples may breach rsrp_min
    "handover_success_rate_min": 0.95,   # 3GPP-aligned launch target
    "handover_duration_max_ms": 100,     # TS 38.331 interruption budget
    "call_setup_time_max_ms": 2000,      # internal SLA
}

# Sub-threshold used by triage to separate interference from coverage:
# RSRP adequate but SINR poor points at interference, not a coverage hole.
INTERFERENCE_RSRP_FLOOR_DBM = -95
INTERFERENCE_SINR_CEIL_DB = 3

_MAX_EVIDENCE_RECORDS = 200  # hard cap; truncation is flagged, never silent


class EvidenceCollector:
    """Append-only, capped store of evidence records for one pytest session."""

    def __init__(self) -> None:
        self.records: List[Dict] = []
        self.truncated: bool = False
        self._counter: int = 0

    def record(self, type: str, **fields) -> str:
        self._counter += 1
        evidence_id = f"EV-{self._counter:03d}"
        if len(self.records) >= _MAX_EVIDENCE_RECORDS:
            self.truncated = True
            return evidence_id  # ID still consumed so counts stay honest
        rec = {"evidence_id": evidence_id, "type": type}
        for key, value in fields.items():
            if isinstance(value, datetime):
                value = value.strftime("%H:%M:%S.%f")[:-3]
            rec[key] = value
        rec.setdefault("originating_test", current_test.get())
        rec.setdefault("log_file", current_log_file.get())
        self.records.append(rec)
        return evidence_id

    def reset(self) -> None:
        self.records = []
        self.truncated = False
        self._counter = 0


#: Session-wide collector. conftest.py resets it at session start and
#: serializes it at session end. Tests never touch it directly — the
#: evaluate_* helpers do.
collector = EvidenceCollector()

#: Set per-test by an autouse fixture so evidence self-attributes.
current_test: ContextVar[Optional[str]] = ContextVar("current_test", default=None)
current_log_file: ContextVar[Optional[str]] = ContextVar(
    "current_log_file", default=None
)


# --------------------------------------------------------------------------- #
# Evaluation helpers ("record evidence, then assert")
# --------------------------------------------------------------------------- #
def evaluate_rf(parser: QXDMLogParser, thresholds: Dict = KPI_THRESHOLDS) -> List[str]:
    """Record evidence for every RF sample breaching thresholds.

    Returns list of violation strings; caller asserts on emptiness.
    Distinguishes coverage-type breaches (RSRP collapsed) from
    interference-type breaches (RSRP adequate, SINR poor) at record level so
    the heuristics can route them to different fault domains.
    """
    violations = []
    measurements = parser.extract_rf_measurements()
    breaches = 0
    for m in measurements:
        rsrp_bad = m["rsrp"] < thresholds["rsrp_min_dbm"]
        sinr_bad = m["sinr"] < thresholds["sinr_min_db"]
        interference_like = (
            m["rsrp"] >= INTERFERENCE_RSRP_FLOOR_DBM
            and m["sinr"] < INTERFERENCE_SINR_CEIL_DB
        )
        if rsrp_bad or sinr_bad or interference_like:
            breaches += 1
            collector.record(
                "rf_degradation",
                timestamp=m["timestamp"],
                cell=m["cell"],
                rf_context={"rsrp": m["rsrp"], "rsrq": m["rsrq"], "sinr": m["sinr"]},
                rsrp_breach=rsrp_bad,
                sinr_breach=sinr_bad,
                interference_signature=interference_like and not rsrp_bad,
                thresholds={
                    "rsrp_min_dbm": thresholds["rsrp_min_dbm"],
                    "sinr_min_db": thresholds["sinr_min_db"],
                },
            )
    if measurements:
        frac = breaches / len(measurements)
        if frac > thresholds["rsrp_fail_fraction_max"]:
            violations.append(
                f"RF breach fraction {frac:.1%} exceeds "
                f"{thresholds['rsrp_fail_fraction_max']:.0%} "
                f"({breaches}/{len(measurements)} samples)"
            )
    return violations


def evaluate_handovers(
    parser: QXDMLogParser, thresholds: Dict = KPI_THRESHOLDS
) -> List[str]:
    """Record per-handover evidence (event level, per agreed granularity)."""
    violations = []
    handovers = parser.detect_handover_events()
    if not handovers:
        return violations

    for ho in handovers:
        if not ho["success"]:
            measured = parser.measured_cells_before(ho["timestamp"])
            collector.record(
                "handover_failure",
                timestamp=ho["timestamp"],
                source_cell=ho["source_cell"],
                target_cell=ho["target_cell"],
                reestablishment_cause=ho["failure_cause"],
                target_previously_measured=(
                    ho["target_cell"] in measured
                    if ho["target_cell"] is not None
                    else None
                ),
                rf_context=parser.rf_context_at(ho["timestamp"]),
            )
        elif (
            ho["duration_ms"] is not None
            and ho["duration_ms"] > thresholds["handover_duration_max_ms"]
        ):
            collector.record(
                "slow_handover",
                timestamp=ho["timestamp"],
                source_cell=ho["source_cell"],
                target_cell=ho["target_cell"],
                duration_ms=round(ho["duration_ms"], 1),
                threshold_ms=thresholds["handover_duration_max_ms"],
                rf_context=parser.rf_context_at(ho["timestamp"]),
            )
            violations.append(
                f"HO {ho['source_cell']}->{ho['target_cell']} took "
                f"{ho['duration_ms']:.0f}ms (max {thresholds['handover_duration_max_ms']}ms)"
            )

    for pp in parser.detect_pingpong_handovers():
        collector.record(
            "handover_pingpong",
            timestamp=pp["first_ho_ts"],
            cell_a=pp["cell_a"],
            cell_b=pp["cell_b"],
            return_gap_s=round(pp["gap_s"], 1),
        )
        violations.append(
            f"Ping-pong {pp['cell_a']}<->{pp['cell_b']} within {pp['gap_s']:.1f}s"
        )

    successes = sum(1 for h in handovers if h["success"])
    rate = successes / len(handovers)
    if rate < thresholds["handover_success_rate_min"]:
        violations.append(
            f"HO success rate {rate:.1%} below "
            f"{thresholds['handover_success_rate_min']:.0%} "
            f"({successes}/{len(handovers)})"
        )
    return violations


def evaluate_nas(parser: QXDMLogParser) -> List[str]:
    """Record evidence for NAS rejects/failures with cause codes."""
    violations = []
    for f in parser.extract_nas_failures():
        collector.record(
            "nas_failure",
            timestamp=f["timestamp"],
            procedure=f["procedure"],
            cause_family=f["cause_family"],
            cause_code=f["cause_code"],
            message=f["message"],
            rf_context=parser.rf_context_at(f["timestamp"]),
        )
        violations.append(
            f"NAS {f['procedure']} failure "
            f"({f['cause_family']} cause #{f['cause_code']})"
        )
    return violations


def evaluate_call_setup(
    parser: QXDMLogParser, thresholds: Dict = KPI_THRESHOLDS
) -> List[str]:
    """Record evidence when RRC setup exceeds the SLA."""
    violations = []
    setup_ms = parser.calculate_call_setup_time()
    if setup_ms is not None and setup_ms > thresholds["call_setup_time_max_ms"]:
        first_event_ts = parser.events[0]["timestamp"] if parser.events else None
        # RRC setup precedes the first measurement report, so a lookback
        # returns nothing; use the earliest measurement as session RF context
        # so heuristics can judge whether the radio was healthy.
        measurements = parser.extract_rf_measurements()
        rf_ctx = (
            {
                "rsrp": measurements[0]["rsrp"],
                "rsrq": measurements[0]["rsrq"],
                "sinr": measurements[0]["sinr"],
            }
            if measurements
            else None
        )
        collector.record(
            "slow_call_setup",
            timestamp=first_event_ts,
            setup_time_ms=round(setup_ms, 1),
            threshold_ms=thresholds["call_setup_time_max_ms"],
            rf_context=rf_ctx,
        )
        violations.append(
            f"RRC setup {setup_ms:.0f}ms exceeds "
            f"{thresholds['call_setup_time_max_ms']}ms SLA"
        )
    return violations


def kpi_check(parser: QXDMLogParser, thresholds: Dict = KPI_THRESHOLDS) -> None:
    """Run all evaluators against a parsed log, then assert.

    Evidence is recorded first, assertion second — a failing test therefore
    always leaves structured records behind for the triage agent.
    """
    violations = []
    violations += evaluate_rf(parser, thresholds)
    violations += evaluate_handovers(parser, thresholds)
    violations += evaluate_nas(parser)
    violations += evaluate_call_setup(parser, thresholds)
    assert not violations, "KPI violations:\n  - " + "\n  - ".join(violations)
