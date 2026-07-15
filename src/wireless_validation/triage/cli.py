"""Triage CLI: python -m wireless_validation.triage <run_record.json>

Stage 2 of the two-stage design: this is the deliberate, engineer-invoked
step. Stage 1 (evidence capture during the pytest run) is automatic and
LLM-free; nothing calls a model until an engineer runs this command.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .heuristics import cluster_evidence
from .llm import DEFAULT_MODEL, resolve_provider
from .prompts import PROMPT_VERSION
from .report import (
    build_llm_payload,
    render_engineer_report,
    render_exec_summary,
    validate_citations,
)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="wireless_validation.triage",
        description="Cluster validation failures by fault domain and draft RCA.",
    )
    ap.add_argument("run_record", type=Path, help="Path to run_record.json")
    ap.add_argument(
        "--out", type=Path, default=None,
        help="Output directory (default: alongside the run record)",
    )
    ap.add_argument(
        "--provider", choices=["anthropic", "none"], default="anthropic",
        help="LLM provider for the reasoning pass ('none' = heuristics only)",
    )
    ap.add_argument("--model", default=DEFAULT_MODEL)
    args = ap.parse_args(argv)

    run_record = json.loads(args.run_record.read_text())
    out_dir = args.out or args.run_record.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    records = run_record["evidence_records"]
    if not records:
        print("No evidence records in run — nothing to triage. ✅")
        return 0

    # ---- Pass 1: deterministic heuristics (authoritative) ----
    clusters_obj, unclustered = cluster_evidence(records)
    clusters = [c.to_dict() for c in clusters_obj]
    print(f"Heuristic pass: {len(records)} evidence records -> "
          f"{len(clusters)} cluster(s), {len(unclustered)} unclustered")
    for c in clusters:
        print(f"  {c['cluster_id']} [{c['fault_domain']}] "
              f"{len(c['evidence_ids'])} records via {c['fired_rules']}")

    # ---- Pass 2: LLM reasoning (advisory, evidence-cited, validated) ----
    provider = resolve_provider(args.provider, model=args.model)
    analysis = None
    discarded = []
    if provider.name == "anthropic":
        print(f"LLM pass: {provider.name} ({args.model}), "
              f"prompt v{PROMPT_VERSION} ...")
        analysis = provider.analyze(
            build_llm_payload(run_record, clusters, unclustered)
        )
    if analysis is not None:
        valid_ids = {r["evidence_id"] for r in records}
        analysis, discarded = validate_citations(analysis, valid_ids)
        n_hyp = sum(len(c.get("hypotheses", []))
                    for c in analysis.get("cluster_analyses", []))
        print(f"LLM pass: {n_hyp} hypotheses passed citation validation, "
              f"{len(discarded)} discarded")
        mode_note = (f"heuristics + LLM ({args.model}, prompt v{PROMPT_VERSION}, "
                     f"temperature 0)")
    else:
        reason = provider.failure_note or "provider disabled"
        mode_note = f"heuristics-only ({reason})"
        print(f"LLM pass skipped -> {mode_note}")

    # ---- Artifacts ----
    triage_path = out_dir / "triage_report.md"
    exec_path = out_dir / "exec_summary.md"
    triage_path.write_text(
        render_engineer_report(
            run_record, clusters, unclustered, analysis, discarded, mode_note
        )
    )
    exec_path.write_text(
        render_exec_summary(run_record, clusters, analysis, mode_note)
    )
    print(f"\nWrote:\n  {triage_path}\n  {exec_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
