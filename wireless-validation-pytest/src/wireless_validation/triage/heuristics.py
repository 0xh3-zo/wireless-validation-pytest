"""Deterministic fault-domain clustering rules.

This module encodes the RAN triage judgment reviewed and approved in the
design phase. It runs with zero LLM involvement and is the authoritative
first pass: the LLM layer may *propose* reassignments but cannot move
evidence between clusters (see prompts.py, hard constraint 4).

Rules are evaluated in PRECEDENCE order — first match claims the record.
Precedence encodes causality: e.g. a handover that failed while RSRP was
collapsing is an RF problem manifesting as a mobility symptom, so the RF
rule must outrank the neighbor rule.

Each rule returns a fault domain or None. Rule names surface verbatim in
the engineer report so the reader can audit exactly why a record landed
where it did.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .models import FaultCluster

# RF context bars used by cross-domain rules ("was the radio healthy?")
_RF_COLLAPSE_RSRP = -105   # at/below: RF claims the failure
_HEALTHY_RSRP = -100       # above: radio considered exonerated
_HEALTHY_SINR = 5
_INTERFERENCE_RSRP_FLOOR = -95
_INTERFERENCE_SINR_CEIL = 3

# NAS causes that exonerate the RAN outright (TS 24.501 semantics per the
# reviewed grounding table).
_CORE_5GMM_CAUSES = {7, 11, 22}
_CORE_5GSM_CAUSES = {26, 31}

# Device rule: same failure type across >= this many distinct cells w/ healthy RF.
_DEVICE_MIN_DISTINCT_CELLS = 3


def _rf(rec: Dict) -> Optional[Dict]:
    return rec.get("rf_context") or None


def _rf_healthy(rec: Dict) -> bool:
    rf = _rf(rec)
    if not rf:
        return False  # unknown RF never exonerates the radio
    return rf["rsrp"] > _HEALTHY_RSRP and rf["sinr"] >= _HEALTHY_SINR


def _rf_collapsed(rec: Dict) -> bool:
    rf = _rf(rec)
    return bool(rf) and rf["rsrp"] <= _RF_COLLAPSE_RSRP


# --------------------------------------------------------------------------- #
# Individual rules — (name, predicate, fault_domain), evaluated in order.
# --------------------------------------------------------------------------- #
def _rule_rf_coverage_hole(rec: Dict) -> bool:
    if rec["type"] != "rf_degradation":
        return False
    rf = _rf(rec)
    return bool(rf) and rec.get("rsrp_breach") and rf["sinr"] < 0


def _rule_rf_interference(rec: Dict) -> bool:
    # RSRP adequate, SINR poor: interference signature, not coverage.
    return rec["type"] == "rf_degradation" and bool(
        rec.get("interference_signature")
    )


def _rule_rf_degradation_other(rec: Dict) -> bool:
    return rec["type"] == "rf_degradation"


def _rule_ho_fail_rf_collapse(rec: Dict) -> bool:
    # Causal precedence: HO failure amid RSRP collapse belongs to RF.
    return rec["type"] == "handover_failure" and _rf_collapsed(rec)


def _rule_ho_fail_target_never_measured(rec: Dict) -> bool:
    return (
        rec["type"] == "handover_failure"
        and rec.get("target_previously_measured") is False
    )


def _rule_ho_fail_reconfig_cause(rec: Dict) -> bool:
    # reestablishmentCause=reconfigurationFailure: UE could not comply with
    # the RRC config — parameter/config domain, not neighbor planning.
    return (
        rec["type"] == "handover_failure"
        and rec.get("reestablishment_cause") == "reconfigurationFailure"
    )


def _rule_ho_fail_handover_cause(rec: Dict) -> bool:
    # T304 expiry with target previously measured and RF not collapsed:
    # mobility-domain (target-side access / neighbor tuning).
    return (
        rec["type"] == "handover_failure"
        and rec.get("reestablishment_cause") == "handoverFailure"
    )


def _rule_pingpong(rec: Dict) -> bool:
    return rec["type"] == "handover_pingpong"


def _rule_slow_ho_healthy_rf(rec: Dict) -> bool:
    return rec["type"] == "slow_handover" and _rf_healthy(rec)


def _rule_slow_setup_healthy_rf(rec: Dict) -> bool:
    return rec["type"] == "slow_call_setup" and _rf_healthy(rec)


def _rule_nas_core_cause(rec: Dict) -> bool:
    if rec["type"] != "nas_failure" or not _rf_healthy(rec):
        return False
    code = rec.get("cause_code")
    fam = rec.get("cause_family")
    return (fam == "5GMM" and code in _CORE_5GMM_CAUSES) or (
        fam == "5GSM" and code in _CORE_5GSM_CAUSES
    )


def _rule_nas_any_healthy_rf(rec: Dict) -> bool:
    # NAS failure with healthy radio: not a radio problem even if the
    # cause code is outside the curated core set.
    return rec["type"] == "nas_failure" and _rf_healthy(rec)


#: (rule_name, predicate, fault_domain) in PRECEDENCE order.
RULES: List[Tuple[str, callable, str]] = [
    ("RF_COVERAGE_HOLE",            _rule_rf_coverage_hole,            "rf_coverage"),
    ("RF_INTERFERENCE",             _rule_rf_interference,             "rf_coverage"),
    ("HO_FAIL_RF_COLLAPSE",         _rule_ho_fail_rf_collapse,         "rf_coverage"),
    ("HO_FAIL_TARGET_NEVER_MEASURED", _rule_ho_fail_target_never_measured, "mobility_neighbor"),
    ("HO_FAIL_RECONFIG_CAUSE",      _rule_ho_fail_reconfig_cause,      "ran_parameter_config"),
    ("HO_FAIL_HANDOVER_CAUSE",      _rule_ho_fail_handover_cause,      "mobility_neighbor"),
    ("HO_PINGPONG",                 _rule_pingpong,                    "mobility_neighbor"),
    ("SLOW_HO_HEALTHY_RF",          _rule_slow_ho_healthy_rf,          "ran_parameter_config"),
    ("SLOW_SETUP_HEALTHY_RF",       _rule_slow_setup_healthy_rf,       "ran_parameter_config"),
    ("NAS_CORE_CAUSE",              _rule_nas_core_cause,              "core_transport"),
    ("NAS_ANY_HEALTHY_RF",          _rule_nas_any_healthy_rf,          "core_transport"),
    ("RF_DEGRADATION_OTHER",        _rule_rf_degradation_other,        "rf_coverage"),
]


def _apply_device_override(
    records: List[Dict], assignments: Dict[str, Tuple[str, str]]
) -> None:
    """DEVICE_CROSS_CELL: same failure type on >= N distinct cells, all with
    healthy per-cell RF, reassigns those records to device_side.

    Runs after per-record rules because it is a pattern over the whole run,
    not a property of a single record.
    """
    by_type: Dict[str, List[Dict]] = {}
    for rec in records:
        if rec["type"] in ("handover_failure", "nas_failure", "slow_call_setup"):
            by_type.setdefault(rec["type"], []).append(rec)

    for ftype, recs in by_type.items():
        healthy = [r for r in recs if _rf_healthy(r)]
        cells = {
            r.get("source_cell") or r.get("cell")
            for r in healthy
            if (r.get("source_cell") or r.get("cell")) is not None
        }
        if len(cells) >= _DEVICE_MIN_DISTINCT_CELLS:
            for r in healthy:
                assignments[r["evidence_id"]] = ("DEVICE_CROSS_CELL", "device_side")


def cluster_evidence(records: List[Dict]) -> Tuple[List[FaultCluster], List[str]]:
    """Assign every evidence record to a fault-domain cluster.

    Returns (clusters, unclustered_evidence_ids). One cluster per fault
    domain per run; fired_rules records every rule that contributed.
    """
    assignments: Dict[str, Tuple[str, str]] = {}  # evidence_id -> (rule, domain)

    for rec in records:
        for name, predicate, domain in RULES:
            if predicate(rec):
                assignments[rec["evidence_id"]] = (name, domain)
                break  # precedence: first match claims the record

    _apply_device_override(records, assignments)

    clusters: Dict[str, FaultCluster] = {}
    unclustered: List[str] = []
    n = 0
    for rec in records:
        eid = rec["evidence_id"]
        if eid not in assignments:
            unclustered.append(eid)
            continue
        rule, domain = assignments[eid]
        if domain not in clusters:
            n += 1
            clusters[domain] = FaultCluster(cluster_id=f"CL-{n}", fault_domain=domain)
        clusters[domain].fired_rules.append(rule)
        clusters[domain].evidence_ids.append(eid)

    return list(clusters.values()), unclustered
