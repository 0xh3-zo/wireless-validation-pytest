"""Render triage artifacts: engineer-facing markdown + executive summary.

Governance mechanics implemented here (not in the model):
  * CITATION VALIDATION — every evidence_id cited by an LLM hypothesis is
    checked against the actual run record. Hypotheses with missing or
    fabricated citations are stamped DISCARDED in the report, never
    silently rendered. The validator, not the model, decides what ships.
  * MODE TRANSPARENCY — the report header states whether an LLM pass ran,
    which model/prompt version produced it, or why it degraded to
    heuristics-only.
  * HUMAN SIGN-OFF — the executive summary carries an explicit
    "AI-drafted, engineer-approved: [ ]" checkbox; the artifact itself
    records that a human is the release authority.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Tuple

from .prompts import PROMPT_VERSION

_DOMAIN_LABELS = {
    "rf_coverage": "RF / Coverage",
    "mobility_neighbor": "Mobility / Neighbor",
    "ran_parameter_config": "RAN Parameter / Config",
    "core_transport": "Core / Transport",
    "device_side": "Device-side",
}

_DOMAIN_BUSINESS_RISK = {
    "rf_coverage": "coverage/interference gaps that customers experience as dead zones or slow data",
    "mobility_neighbor": "dropped or degraded sessions while customers are moving",
    "ran_parameter_config": "systematic performance loss from misconfiguration, fixable without new hardware",
    "core_transport": "service failures originating outside the radio network",
    "device_side": "a device-specific defect that would ship to every customer using this model",
}


def validate_citations(
    analysis: Dict, valid_ids: set
) -> Tuple[Dict, List[Dict]]:
    """Enforce hard constraint 1: discard hypotheses with invalid citations.

    Returns (validated_analysis, discarded) where discarded entries carry
    the offending hypothesis and reason for the audit trail.
    """
    discarded: List[Dict] = []
    for cluster in analysis.get("cluster_analyses", []):
        kept = []
        for hyp in cluster.get("hypotheses", []):
            cited = hyp.get("cited_evidence") or []
            bad = [c for c in cited if c not in valid_ids]
            if not cited:
                hyp["_discard_reason"] = "no evidence cited"
                discarded.append({"cluster_id": cluster.get("cluster_id"), **hyp})
            elif bad:
                hyp["_discard_reason"] = f"cited nonexistent evidence: {bad}"
                discarded.append({"cluster_id": cluster.get("cluster_id"), **hyp})
            else:
                kept.append(hyp)
        cluster["hypotheses"] = kept

    # Cross-cluster patterns are held to the same standard.
    kept_patterns = []
    for pat in analysis.get("cross_cluster_patterns", []):
        cited = pat.get("cited_evidence") or []
        if cited and all(c in valid_ids for c in cited):
            kept_patterns.append(pat)
        else:
            pat["_discard_reason"] = "missing or invalid citations"
            discarded.append({"cluster_id": "cross-cluster", **pat})
    analysis["cross_cluster_patterns"] = kept_patterns

    return analysis, discarded


def _evidence_line(rec: Dict) -> str:
    parts = [f"**{rec['evidence_id']}** `{rec['type']}`"]
    if rec.get("timestamp"):
        parts.append(f"@ {rec['timestamp']}")
    cells = []
    if rec.get("source_cell") is not None:
        cells.append(f"src {rec['source_cell']}")
    if rec.get("target_cell") is not None:
        cells.append(f"tgt {rec['target_cell']}")
    if rec.get("cell") is not None:
        cells.append(f"cell {rec['cell']}")
    if rec.get("cell_a") is not None:
        cells.append(f"{rec['cell_a']}<->{rec['cell_b']}")
    if cells:
        parts.append("(" + ", ".join(cells) + ")")
    if rec.get("reestablishment_cause"):
        parts.append(f"cause=`{rec['reestablishment_cause']}`")
    if rec.get("cause_code") is not None:
        parts.append(f"{rec.get('cause_family')} cause #{rec['cause_code']}")
    rf = rec.get("rf_context")
    if rf:
        parts.append(
            f"RF: RSRP {rf['rsrp']} dBm / RSRQ {rf['rsrq']} dB / SINR {rf['sinr']} dB"
        )
    if rec.get("duration_ms") is not None:
        parts.append(f"{rec['duration_ms']} ms (max {rec.get('threshold_ms')} ms)")
    if rec.get("setup_time_ms") is not None:
        parts.append(f"{rec['setup_time_ms']} ms (SLA {rec.get('threshold_ms')} ms)")
    if rec.get("return_gap_s") is not None:
        parts.append(f"return in {rec['return_gap_s']} s")
    if rec.get("originating_test"):
        parts.append(f"— _{rec['originating_test'].split('::')[-1]}_")
    return "  - " + " ".join(parts)


def render_engineer_report(
    run_record: Dict,
    clusters: List[Dict],
    unclustered: List[str],
    analysis: Optional[Dict],
    discarded: List[Dict],
    mode_note: str,
) -> str:
    records = {r["evidence_id"]: r for r in run_record["evidence_records"]}
    run = run_record["run"]
    lines = [
        "# Failure Triage Report",
        "",
        f"**Run:** {run['timestamp']}  |  "
        f"**Tests:** {run['total_tests']} total, {run['failed']} failed  |  "
        f"**Evidence records:** {len(records)}"
        + ("  |  ⚠ **TRUNCATED at cap — evidence beyond cap not analyzed**"
           if run_record.get("truncated") else ""),
        f"**Analysis mode:** {mode_note}",
        "",
    ]

    for cluster in clusters:
        label = _DOMAIN_LABELS.get(cluster["fault_domain"], cluster["fault_domain"])
        lines.append(f"## {cluster['cluster_id']} — {label}")
        lines.append(
            f"Fired rules: " + ", ".join(f"`{r}`" for r in cluster["fired_rules"])
        )
        lines.append("")
        lines.append("Evidence:")
        for eid in cluster["evidence_ids"]:
            lines.append(_evidence_line(records[eid]))
        lines.append("")

        if analysis:
            cl_analysis = next(
                (
                    c
                    for c in analysis.get("cluster_analyses", [])
                    if c.get("cluster_id") == cluster["cluster_id"]
                ),
                None,
            )
            if cl_analysis:
                concur = cl_analysis.get("concur_with_heuristic")
                lines.append(
                    f"LLM concurrence with heuristic assignment: "
                    f"{'✅ concurs' if concur else '⚠ challenges (see reassignment proposals)'}"
                )
                lines.append("")
                for hyp in cl_analysis.get("hypotheses", []):
                    lines.append(
                        f"### Hypothesis #{hyp.get('rank')} — "
                        f"confidence **{hyp.get('confidence')}**"
                    )
                    lines.append(f"**Mechanism:** {hyp.get('mechanism')}")
                    lines.append(
                        "**Evidence cited:** "
                        + ", ".join(hyp.get("cited_evidence", []))
                        + " _(all citations verified against run record)_"
                    )
                    lines.append(
                        f"**Recommended next step:** {hyp.get('recommended_next_step')}"
                    )
                    lines.append(
                        f"**What would change this assessment:** "
                        f"{hyp.get('what_would_change_my_mind')}"
                    )
                    lines.append("")

    if unclustered:
        lines.append("## Unclustered evidence (no rule matched — review manually)")
        for eid in unclustered:
            lines.append(_evidence_line(records[eid]))
        lines.append("")

    if analysis and analysis.get("reassignment_proposals"):
        lines.append("## LLM reassignment proposals (advisory — engineer decides)")
        for prop in analysis["reassignment_proposals"]:
            lines.append(
                f"- Move **{prop.get('evidence_id')}** from "
                f"{prop.get('from_cluster')} to `{prop.get('proposed_domain')}`: "
                f"{prop.get('reasoning')}"
            )
        lines.append("")

    if analysis and analysis.get("cross_cluster_patterns"):
        lines.append("## Cross-cluster patterns")
        for pat in analysis["cross_cluster_patterns"]:
            lines.append(
                f"- {pat.get('observation')} "
                f"(evidence: {', '.join(pat.get('cited_evidence', []))}) "
                f"→ {pat.get('implication')}"
            )
        lines.append("")

    if analysis and analysis.get("insufficient_evidence_notes"):
        lines.append("## Insufficient-evidence notes")
        for note in analysis["insufficient_evidence_notes"]:
            lines.append(f"- {note}")
        lines.append("")

    if discarded:
        lines.append("## ⚠ Discarded LLM output (failed citation validation)")
        lines.append(
            "_The following model output cited evidence that does not exist in "
            "the run record and was rejected by the validator:_"
        )
        for d in discarded:
            lines.append(
                f"- ⚠ **CITATION FAILED — DISCARDED** "
                f"({d.get('cluster_id')}): {d.get('mechanism', d.get('observation', '?'))} "
                f"— {d.get('_discard_reason')}"
            )
        lines.append("")

    lines.append("---")
    lines.append(
        f"_Heuristics: deterministic rule engine (see `triage/heuristics.py`). "
        f"LLM pass: {mode_note}. Prompt version: {PROMPT_VERSION}._"
    )
    return "\n".join(lines)


def _fallback_exec_summary(run: Dict, clusters: List[Dict]) -> List[str]:
    """Deterministic five-sentence exec summary for heuristics-only mode."""
    n_ev = sum(len(c["evidence_ids"]) for c in clusters)
    domains = [_DOMAIN_LABELS[c["fault_domain"]] for c in clusters]
    biggest = max(clusters, key=lambda c: len(c["evidence_ids"])) if clusters else None
    sentences = [
        f"Validation run on {run['timestamp']} completed with "
        f"{run['failed']} of {run['total_tests']} test cases failing, "
        f"producing {n_ev} distinct failure evidence records.",
        f"Automated rule-based triage grouped the failures into "
        f"{len(clusters)} fault domain(s): {', '.join(domains) or 'none'}.",
    ]
    if biggest:
        sentences.append(
            f"The largest cluster is {_DOMAIN_LABELS[biggest['fault_domain']]} "
            f"({len(biggest['evidence_ids'])} records), which if unresolved "
            f"represents {_DOMAIN_BUSINESS_RISK[biggest['fault_domain']]}."
        )
    else:
        sentences.append("No evidence records required clustering.")
    sentences.append(
        "These results are from deterministic rules only; no AI reasoning "
        "pass was applied to this run."
    )
    sentences.append(
        "Engineering review of the per-cluster evidence is required before "
        "any launch-readiness call is made."
    )
    return sentences


def render_exec_summary(
    run_record: Dict,
    clusters: List[Dict],
    analysis: Optional[Dict],
    mode_note: str,
) -> str:
    run = run_record["run"]
    sentences = None
    ai_drafted = False
    if analysis:
        draft = (analysis.get("exec_summary_draft") or {}).get("sentences")
        if draft and len(draft) == 5:
            sentences, ai_drafted = draft, True
        elif draft:
            # Model violated the 5-sentence contract: fall back, and say so.
            sentences = _fallback_exec_summary(run, clusters)
            sentences[3] = (
                "The AI-drafted summary was rejected for violating the "
                "five-sentence contract; this deterministic summary replaced it."
            )
    if sentences is None:
        sentences = _fallback_exec_summary(run, clusters)

    lines = [
        "# Executive Summary — Validation Run "
        + run["timestamp"],
        "",
    ]
    lines += [s if s.endswith(".") else s + "." for s in sentences]
    lines += [
        "",
        "---",
        f"_{'AI-drafted (' + mode_note + '), engineer-approved: [ ]' if ai_drafted else 'Deterministically generated (' + mode_note + '), engineer-approved: [ ]'}_",
    ]
    return "\n".join(lines)


def build_llm_payload(
    run_record: Dict, clusters: List[Dict], unclustered: List[str]
) -> Dict:
    return {
        "schema_version": "1.0",
        "run": run_record["run"],
        "kpi_thresholds": run_record["kpi_thresholds"],
        "evidence_records": run_record["evidence_records"],
        "heuristic_clusters": clusters,
        "unclustered_evidence_ids": unclustered,
    }


def dumps(obj) -> str:
    return json.dumps(obj, indent=2, default=str)
