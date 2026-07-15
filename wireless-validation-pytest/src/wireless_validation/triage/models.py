"""Data model for the failure-triage layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

FAULT_DOMAINS = (
    "rf_coverage",
    "mobility_neighbor",
    "ran_parameter_config",
    "core_transport",
    "device_side",
)


@dataclass
class FaultCluster:
    cluster_id: str
    fault_domain: str
    fired_rules: List[str] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "cluster_id": self.cluster_id,
            "fault_domain": self.fault_domain,
            "fired_rules": sorted(set(self.fired_rules)),
            "evidence_ids": self.evidence_ids,
        }


@dataclass
class RCAHypothesis:
    """LLM-produced hypothesis after citation validation."""

    rank: int
    mechanism: str
    confidence: str
    cited_evidence: List[str]
    recommended_next_step: str
    what_would_change_my_mind: str
    citation_valid: bool = True
    discard_reason: Optional[str] = None
