"""Unit tests for the deterministic fault-domain rules.

These tests are the executable spec for the reviewed triage judgment —
especially causal precedence (RF collapse outranks neighbor blame).
"""

from wireless_validation.triage.heuristics import cluster_evidence


def _domains(clusters):
    return {c.fault_domain: c for c in clusters}


def test_coverage_hole_rule():
    records = [
        {
            "evidence_id": "EV-001",
            "type": "rf_degradation",
            "rsrp_breach": True,
            "rf_context": {"rsrp": -115, "rsrq": -17, "sinr": -4},
        }
    ]
    clusters, unclustered = cluster_evidence(records)
    d = _domains(clusters)
    assert "rf_coverage" in d and not unclustered
    assert "RF_COVERAGE_HOLE" in d["rf_coverage"].fired_rules


def test_interference_distinguished_from_coverage():
    records = [
        {
            "evidence_id": "EV-001",
            "type": "rf_degradation",
            "rsrp_breach": False,
            "interference_signature": True,
            "rf_context": {"rsrp": -90, "rsrq": -13, "sinr": 1},
        }
    ]
    clusters, _ = cluster_evidence(records)
    assert "RF_INTERFERENCE" in _domains(clusters)["rf_coverage"].fired_rules


def test_precedence_ho_failure_during_rf_collapse_goes_to_rf():
    """Causal precedence: HO failure amid RSRP collapse is an RF problem,
    even when target was never measured (which would otherwise fire the
    missing-neighbor rule)."""
    records = [
        {
            "evidence_id": "EV-001",
            "type": "handover_failure",
            "source_cell": 3001,
            "target_cell": 3099,
            "target_previously_measured": False,
            "reestablishment_cause": "otherFailure",
            "rf_context": {"rsrp": -115, "rsrq": -17, "sinr": -4},
        }
    ]
    clusters, _ = cluster_evidence(records)
    d = _domains(clusters)
    assert list(d) == ["rf_coverage"]
    assert "HO_FAIL_RF_COLLAPSE" in d["rf_coverage"].fired_rules


def test_missing_neighbor_rule_with_healthy_rf():
    records = [
        {
            "evidence_id": "EV-001",
            "type": "handover_failure",
            "source_cell": 2001,
            "target_cell": 2099,
            "target_previously_measured": False,
            "reestablishment_cause": "handoverFailure",
            "rf_context": {"rsrp": -84, "rsrq": -10, "sinr": 16},
        }
    ]
    clusters, _ = cluster_evidence(records)
    d = _domains(clusters)
    assert "HO_FAIL_TARGET_NEVER_MEASURED" in d["mobility_neighbor"].fired_rules


def test_reconfiguration_failure_cause_routes_to_config():
    records = [
        {
            "evidence_id": "EV-001",
            "type": "handover_failure",
            "source_cell": 4003,
            "target_cell": None,
            "target_previously_measured": None,
            "reestablishment_cause": "reconfigurationFailure",
            "rf_context": {"rsrp": -80, "rsrq": -9, "sinr": 19},
        }
    ]
    clusters, _ = cluster_evidence(records)
    assert "ran_parameter_config" in _domains(clusters)


def test_pingpong_and_slow_ho():
    records = [
        {"evidence_id": "EV-001", "type": "handover_pingpong",
         "cell_a": 1, "cell_b": 2, "return_gap_s": 7.0},
        {"evidence_id": "EV-002", "type": "slow_handover",
         "source_cell": 4001, "target_cell": 4002, "duration_ms": 185,
         "rf_context": {"rsrp": -79, "rsrq": -9, "sinr": 20}},
    ]
    clusters, _ = cluster_evidence(records)
    d = _domains(clusters)
    assert "HO_PINGPONG" in d["mobility_neighbor"].fired_rules
    assert "SLOW_HO_HEALTHY_RF" in d["ran_parameter_config"].fired_rules


def test_nas_core_cause_with_healthy_rf():
    records = [
        {"evidence_id": "EV-001", "type": "nas_failure",
         "cause_family": "5GSM", "cause_code": 26,
         "rf_context": {"rsrp": -78, "rsrq": -9, "sinr": 21}},
    ]
    clusters, _ = cluster_evidence(records)
    assert "NAS_CORE_CAUSE" in _domains(clusters)["core_transport"].fired_rules


def test_nas_failure_with_bad_rf_is_not_blindly_core():
    """A NAS failure while the radio is collapsing shouldn't exonerate RAN —
    with no rule matching, it lands in unclustered for manual review."""
    records = [
        {"evidence_id": "EV-001", "type": "nas_failure",
         "cause_family": "5GSM", "cause_code": 26,
         "rf_context": {"rsrp": -117, "rsrq": -18, "sinr": -5}},
    ]
    clusters, unclustered = cluster_evidence(records)
    assert unclustered == ["EV-001"]


def test_device_override_same_failure_across_three_cells():
    base = {
        "type": "handover_failure",
        "target_previously_measured": True,
        "reestablishment_cause": "handoverFailure",
        "rf_context": {"rsrp": -80, "rsrq": -9, "sinr": 18},
    }
    records = [
        {**base, "evidence_id": f"EV-00{i}", "source_cell": 100 + i}
        for i in range(1, 4)
    ]
    clusters, _ = cluster_evidence(records)
    d = _domains(clusters)
    assert list(d) == ["device_side"]
    assert set(d["device_side"].fired_rules) == {"DEVICE_CROSS_CELL"}
    assert d["device_side"].to_dict()["fired_rules"] == ["DEVICE_CROSS_CELL"]


def test_unknown_rf_context_never_exonerates_radio():
    records = [
        {"evidence_id": "EV-001", "type": "nas_failure",
         "cause_family": "5GMM", "cause_code": 22, "rf_context": None},
    ]
    clusters, unclustered = cluster_evidence(records)
    assert unclustered == ["EV-001"]
