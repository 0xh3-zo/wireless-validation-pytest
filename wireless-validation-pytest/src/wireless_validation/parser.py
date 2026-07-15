"""QXDM-style protocol log parser.

Extracted from the original single-file test suite and extended with:
  - RRC re-establishment cause extraction (TS 38.331 reestablishmentCause)
  - NAS 5GMM / 5GSM cause-code extraction (TS 24.501)
  - Serving-cell context on measurement reports (optional ``Cell=<id>`` token)
  - Measurement history helpers used by triage heuristics
    (e.g. "was the handover target ever measured before the HO command?")

Supported line grammar (superset of the original format — old logs still parse):

    2026-02-03 09:05:12.456  [RRC] RRC Reconfiguration (Handover Command) - Source Cell: 1001 -> Target Cell: 1002
    2026-02-03 09:05:12.521  [RRC] RRC Reconfiguration Complete - Target Cell: 1002
    2026-02-03 09:10:02.000  [RRC] RRC Connection Re-establishment Request - Cause: handoverFailure
    2026-02-03 09:11:00.000  [NAS] Registration Reject (5GS) - Cause: #22
    2026-02-03 09:12:00.000  [NAS] PDU Session Establishment Reject - Cause: #26
    2026-02-03 09:00:05.000  [5G_NR] Measurement Report: RSRP=-85dBm, RSRQ=-10dB, SINR=18dB, Cell=1001
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional

_LINE_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+\[(\w+)\]\s+(.+)"
)
_RSRP_RE = re.compile(r"RSRP=(-?\d+)dBm")
_RSRQ_RE = re.compile(r"RSRQ=(-?\d+)dB")
_SINR_RE = re.compile(r"SINR=(-?\d+)dB")
_CELL_RE = re.compile(r"Cell=(\d+)")
_SOURCE_CELL_RE = re.compile(r"Source Cell: (\d+)")
_TARGET_CELL_RE = re.compile(r"Target Cell: (\d+)")
_REEST_CAUSE_RE = re.compile(r"Cause:\s*(\w+)")
_NAS_CAUSE_RE = re.compile(r"Cause:\s*#(\d+)")

# How far ahead (in RRC events) we look for a handover outcome.
_HO_LOOKAHEAD_EVENTS = 10
# Ping-pong window: A->B then B->A within this many seconds.
PINGPONG_WINDOW_S = 10.0


class QXDMLogParser:
    """Parses QXDM-style protocol logs and extracts events / KPIs."""

    def __init__(self, log_content: str):
        self.log_content = log_content
        self.events = self._parse_events()

    # ------------------------------------------------------------------ #
    # Core parsing
    # ------------------------------------------------------------------ #
    def _parse_events(self) -> List[Dict]:
        events = []
        for line in self.log_content.strip().split("\n"):
            if not line.strip():
                continue
            match = _LINE_RE.match(line)
            if not match:
                continue  # skip malformed lines gracefully
            timestamp_str, layer, message = match.groups()
            events.append(
                {
                    "timestamp": datetime.strptime(
                        timestamp_str, "%Y-%m-%d %H:%M:%S.%f"
                    ),
                    "layer": layer,
                    "message": message,
                }
            )
        return events

    def get_events_by_layer(self, layer: str) -> List[Dict]:
        return [e for e in self.events if e["layer"] == layer]

    # ------------------------------------------------------------------ #
    # RF measurements
    # ------------------------------------------------------------------ #
    def extract_rf_measurements(self) -> List[Dict]:
        """Extract RSRP/RSRQ/SINR measurements, with serving cell if present."""
        measurements = []
        for event in self.events:
            if "5G_NR" not in event["layer"]:
                continue
            if "Measurement Report" not in event["message"]:
                continue
            rsrp = _RSRP_RE.search(event["message"])
            rsrq = _RSRQ_RE.search(event["message"])
            sinr = _SINR_RE.search(event["message"])
            if not (rsrp and rsrq and sinr):
                continue
            cell = _CELL_RE.search(event["message"])
            measurements.append(
                {
                    "timestamp": event["timestamp"],
                    "rsrp": int(rsrp.group(1)),
                    "rsrq": int(rsrq.group(1)),
                    "sinr": int(sinr.group(1)),
                    "cell": int(cell.group(1)) if cell else None,
                }
            )
        return measurements

    def measured_cells_before(self, when: datetime) -> set:
        """Set of cell IDs that appear in measurement reports strictly before `when`.

        Used by the MISSING-NEIGHBOR heuristic: a handover commanded toward a
        target the UE never reported measuring suggests a neighbor-relation /
        measurement-config gap rather than an RF problem.
        """
        return {
            m["cell"]
            for m in self.extract_rf_measurements()
            if m["cell"] is not None and m["timestamp"] < when
        }

    def rf_context_at(self, when: datetime) -> Optional[Dict]:
        """Most recent measurement at or before `when` (RF conditions context)."""
        best = None
        for m in self.extract_rf_measurements():
            if m["timestamp"] <= when and (
                best is None or m["timestamp"] > best["timestamp"]
            ):
                best = m
        if best is None:
            return None
        return {"rsrp": best["rsrp"], "rsrq": best["rsrq"], "sinr": best["sinr"]}

    # ------------------------------------------------------------------ #
    # Call setup
    # ------------------------------------------------------------------ #
    def calculate_call_setup_time(self) -> Optional[float]:
        """Time (ms) from RRC Connection Request to Setup Complete."""
        request_time = None
        complete_time = None
        for event in self.get_events_by_layer("RRC"):
            if "Connection Request" in event["message"]:
                request_time = event["timestamp"]
            elif "Setup Complete" in event["message"]:
                complete_time = event["timestamp"]
        if request_time and complete_time:
            return (complete_time - request_time).total_seconds() * 1000
        return None

    # ------------------------------------------------------------------ #
    # Handover analysis
    # ------------------------------------------------------------------ #
    def detect_handover_events(self) -> List[Dict]:
        """Detect handover attempts, outcome, duration, and failure cause.

        A handover is considered failed when it is followed by an RRC
        Re-establishment Request (cause captured when present) or when no
        Reconfiguration Complete appears within the lookahead window.
        """
        handovers = []
        rrc_events = self.get_events_by_layer("RRC")

        for i, event in enumerate(rrc_events):
            is_handover = (
                "Handover Command" in event["message"]
                or "Handover)" in event["message"]
                or (
                    "Reconfiguration" in event["message"]
                    and "Handover" in event["message"]
                )
            )
            if not is_handover:
                continue

            source_match = _SOURCE_CELL_RE.search(event["message"])
            # Commanded target may be present on the HO command line itself.
            commanded_target = _TARGET_CELL_RE.search(event["message"])

            ho = {
                "timestamp": event["timestamp"],
                "source_cell": int(source_match.group(1)) if source_match else None,
                "target_cell": (
                    int(commanded_target.group(1)) if commanded_target else None
                ),
                "success": False,
                "duration_ms": None,
                "failure_cause": None,
            }

            for j in range(i + 1, min(i + _HO_LOOKAHEAD_EVENTS, len(rrc_events))):
                nxt = rrc_events[j]
                if "Reconfiguration Complete" in nxt["message"]:
                    ho["success"] = True
                    ho["duration_ms"] = (
                        nxt["timestamp"] - event["timestamp"]
                    ).total_seconds() * 1000
                    tgt = _TARGET_CELL_RE.search(nxt["message"])
                    if tgt:
                        ho["target_cell"] = int(tgt.group(1))
                    break
                if "Re-establishment" in nxt["message"]:
                    ho["success"] = False
                    cause = _REEST_CAUSE_RE.search(nxt["message"])
                    ho["failure_cause"] = cause.group(1) if cause else None
                    break

            handovers.append(ho)
        return handovers

    def detect_pingpong_handovers(self) -> List[Dict]:
        """Detect A->B then B->A successful handover pairs within the window."""
        pingpongs = []
        hos = [h for h in self.detect_handover_events() if h["success"]]
        for a, b in zip(hos, hos[1:]):
            if (
                a["source_cell"] is not None
                and a["target_cell"] is not None
                and b["source_cell"] == a["target_cell"]
                and b["target_cell"] == a["source_cell"]
                and (b["timestamp"] - a["timestamp"])
                <= timedelta(seconds=PINGPONG_WINDOW_S)
            ):
                pingpongs.append(
                    {
                        "cell_a": a["source_cell"],
                        "cell_b": a["target_cell"],
                        "first_ho_ts": a["timestamp"],
                        "return_ho_ts": b["timestamp"],
                        "gap_s": (b["timestamp"] - a["timestamp"]).total_seconds(),
                    }
                )
        return pingpongs

    # ------------------------------------------------------------------ #
    # NAS failures
    # ------------------------------------------------------------------ #
    def extract_nas_failures(self) -> List[Dict]:
        """Extract NAS reject / failure events with 5GMM / 5GSM cause codes."""
        failures = []
        for event in self.get_events_by_layer("NAS"):
            msg = event["message"]
            if "Reject" not in msg and "Failure" not in msg:
                continue
            cause = _NAS_CAUSE_RE.search(msg)
            if "PDU Session" in msg:
                procedure, cause_family = "pdu_session", "5GSM"
            elif "Registration" in msg or "Service" in msg:
                procedure, cause_family = "registration", "5GMM"
            else:
                procedure, cause_family = "other", "unknown"
            failures.append(
                {
                    "timestamp": event["timestamp"],
                    "procedure": procedure,
                    "cause_family": cause_family,
                    "cause_code": int(cause.group(1)) if cause else None,
                    "message": msg,
                }
            )
        return failures
