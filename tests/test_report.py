"""Tests for the governance layer: citation validation and rendering."""

from wireless_validation.triage.report import (
    render_exec_summary,
    validate_citations,
)

VALID_IDS = {"EV-001", "EV-002"}


def _analysis(cited):
    return {
        "cluster_analyses": [
            {
                "cluster_id": "CL-1",
                "concur_with_heuristic": True,
                "hypotheses": [
                    {
                        "rank": 1,
                        "mechanism": "test mechanism",
                        "confidence": "HIGH",
                        "cited_evidence": cited,
                        "recommended_next_step": "pull QXDM log",
                        "what_would_change_my_mind": "counter-evidence",
                    }
                ],
            }
        ],
        "cross_cluster_patterns": [],
    }


def test_valid_citations_pass():
    analysis, discarded = validate_citations(_analysis(["EV-001"]), VALID_IDS)
    assert discarded == []
    assert len(analysis["cluster_analyses"][0]["hypotheses"]) == 1


def test_fabricated_citation_is_discarded():
    analysis, discarded = validate_citations(
        _analysis(["EV-001", "EV-999"]), VALID_IDS
    )
    assert analysis["cluster_analyses"][0]["hypotheses"] == []
    assert len(discarded) == 1
    assert "EV-999" in discarded[0]["_discard_reason"]


def test_uncited_hypothesis_is_discarded():
    analysis, discarded = validate_citations(_analysis([]), VALID_IDS)
    assert analysis["cluster_analyses"][0]["hypotheses"] == []
    assert discarded[0]["_discard_reason"] == "no evidence cited"


def test_cross_cluster_patterns_held_to_same_standard():
    a = _analysis(["EV-001"])
    a["cross_cluster_patterns"] = [
        {"observation": "x", "cited_evidence": ["EV-404"], "implication": "y"}
    ]
    analysis, discarded = validate_citations(a, VALID_IDS)
    assert analysis["cross_cluster_patterns"] == []
    assert any(d["cluster_id"] == "cross-cluster" for d in discarded)


def _run_record():
    return {
        "run": {"timestamp": "2026-07-14T10:00:00", "total_tests": 5, "failed": 4},
        "evidence_records": [{"evidence_id": "EV-001", "type": "nas_failure"}],
        "kpi_thresholds": {},
    }


def test_exec_summary_fallback_is_exactly_five_sentences():
    clusters = [
        {"cluster_id": "CL-1", "fault_domain": "core_transport",
         "fired_rules": ["NAS_CORE_CAUSE"], "evidence_ids": ["EV-001"]}
    ]
    text = render_exec_summary(_run_record(), clusters, None, "heuristics-only")
    body = [
        line for line in text.splitlines()
        if line and not line.startswith(("#", "-", "_"))
    ]
    assert len(body) == 5


def test_exec_summary_rejects_wrong_length_llm_draft():
    clusters = []
    analysis = {"exec_summary_draft": {"sentences": ["only", "three", "sentences"]}}
    text = render_exec_summary(_run_record(), clusters, analysis, "llm")
    assert "rejected for violating the five-sentence contract" in text
