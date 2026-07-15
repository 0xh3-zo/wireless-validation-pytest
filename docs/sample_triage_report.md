# Failure Triage Report

**Run:** 2026-07-14T22:10:18  |  **Tests:** 5 total, 4 failed  |  **Evidence records:** 13
**Analysis mode:** heuristics + LLM (claude-sonnet-4-6, prompt v0.2, temperature 0)

## CL-1 — Core / Transport
Fired rules: `NAS_CORE_CAUSE`

Evidence:
  - **EV-001** `nas_failure` @ 09:30:02.300 5GMM cause #22 RF: RSRP -78 dBm / RSRQ -9 dB / SINR 21 dB — _test_field_log_kpis[core_reject.txt]_
  - **EV-002** `nas_failure` @ 09:30:06.400 5GSM cause #26 RF: RSRP -80 dBm / RSRQ -9 dB / SINR 19 dB — _test_field_log_kpis[core_reject.txt]_

LLM concurrence with heuristic assignment: ✅ concurs

### Hypothesis #1 — confidence **HIGH**
**Mechanism:** AMF congestion (5GMM #22, EV-001) followed by SMF/UPF resource exhaustion (5GSM #26, EV-002) with pristine RF (RSRP -78/-80 dBm, SINR 21/19 dB) unambiguously exonerates the RAN layer; both cause codes are core-side by TS 24.501 definition and the RF context clears all KPI thresholds.
**Evidence cited:** EV-001, EV-002 _(all citations verified against run record)_
**Recommended next step:** Pull AMF subscriber-context logs at 09:30:02–09:30:06 UTC and check AMF load counters / SMF N11 interface error rates to confirm congestion scope and whether it is time-clustered across other UEs.
**What would change this assessment:** Evidence of RF degradation co-located with these NAS failures, or a cause code mapping to a RAN-side reject (e.g., #15 no suitable cells), would reopen RAN involvement.

## CL-2 — RF / Coverage
Fired rules: `HO_FAIL_RF_COLLAPSE`, `RF_COVERAGE_HOLE`, `RF_INTERFERENCE`

Evidence:
  - **EV-003** `rf_degradation` @ 09:02:00.000 (cell 3001) RF: RSRP -112 dBm / RSRQ -16 dB / SINR -2 dB — _test_field_log_kpis[coverage_hole.txt]_
  - **EV-004** `rf_degradation` @ 09:03:00.000 (cell 3001) RF: RSRP -115 dBm / RSRQ -17 dB / SINR -4 dB — _test_field_log_kpis[coverage_hole.txt]_
  - **EV-005** `rf_degradation` @ 09:04:00.000 (cell 3002) RF: RSRP -90 dBm / RSRQ -13 dB / SINR 1 dB — _test_field_log_kpis[coverage_hole.txt]_
  - **EV-006** `rf_degradation` @ 09:04:30.000 (cell 3001) RF: RSRP -118 dBm / RSRQ -18 dB / SINR -6 dB — _test_field_log_kpis[coverage_hole.txt]_
  - **EV-007** `handover_failure` @ 09:03:30.000 (src 3001) cause=`otherFailure` RF: RSRP -115 dBm / RSRQ -17 dB / SINR -4 dB — _test_field_log_kpis[coverage_hole.txt]_

LLM concurrence with heuristic assignment: ✅ concurs

### Hypothesis #1 — confidence **HIGH**
**Mechanism:** Cell 3001 exhibits a sustained coverage hole: RSRP degrades from -112 to -118 dBm and SINR from -2 to -6 dB across three consecutive samples (EV-003, EV-004, EV-006) with interference_signature=false, consistent with path-loss-driven RLF; the otherFailure reestablishment cause at RSRP -115/SINR -4 (EV-007) confirms T310 expiry driven by this RF collapse, not a neighbor-config issue.
**Evidence cited:** EV-003, EV-004, EV-006, EV-007 _(all citations verified against run record)_
**Recommended next step:** Run a drive/walk test on cell 3001 sector with a calibrated scanner to map the -110 dBm RSRP boundary and identify whether a physical obstruction, antenna tilt change, or hardware fault (e.g., AISG alarm) is the root cause.
**What would change this assessment:** Discovery that RSRP is adequate at the cell edge but SINR is poor would shift the diagnosis to uplink interference or pilot pollution rather than a coverage hole.

### Hypothesis #2 — confidence **MEDIUM**
**Mechanism:** Cell 3002 shows adequate RSRP (-90 dBm, no breach) but SINR near floor (1 dB) with interference_signature=true (EV-005), indicating a distinct interference problem on this cell that is separate from the 3001 coverage hole and requires a different remediation owner.
**Evidence cited:** EV-005 _(all citations verified against run record)_
**Recommended next step:** Run a spectrum scan on the n-band used by cell 3002 to identify the interfering source (co-channel neighbor, external emitter, or PIM) and cross-check with neighboring cell EIRP/tilt audit.
**What would change this assessment:** A spectrum scan showing no external interference and RSRP collapse at the same location would reclassify EV-005 as a secondary coverage symptom rather than an independent interference event.

## CL-3 — Mobility / Neighbor
Fired rules: `HO_FAIL_TARGET_NEVER_MEASURED`, `HO_PINGPONG`

Evidence:
  - **EV-008** `handover_failure` @ 09:10:03.000 (src 2001, tgt 2099) cause=`handoverFailure` RF: RSRP -84 dBm / RSRQ -10 dB / SINR 16 dB — _test_field_log_kpis[missing_neighbor.txt]_
  - **EV-009** `handover_pingpong` @ 09:10:07.000 (2001<->2002) return in 7.0 s — _test_field_log_kpis[missing_neighbor.txt]_

LLM concurrence with heuristic assignment: ✅ concurs

### Hypothesis #1 — confidence **HIGH**
**Mechanism:** HO to cell 2099 fails with handoverFailure cause and target_previously_measured=false (EV-008) at healthy RF (RSRP -84, SINR 16), indicating the X2/Xn neighbor relation to 2099 is absent from the source cell 2001 ANR table, causing the UE to attempt a blind HO that T304 cannot complete; the 7-second ping-pong between 2001 and 2002 (EV-009) further indicates A3 offset/TTT is too aggressive on this cell pair.
**Evidence cited:** EV-008, EV-009 _(all citations verified against run record)_
**Recommended next step:** Audit the ANR/neighbor list on cell 2001 for a missing entry to PCI/cell-ID 2099, add the X2 neighbor relation, and simultaneously increase A3 TTT on the 2001-2002 pair to suppress ping-pong (compare against golden config baseline).
**What would change this assessment:** If cell 2099 is present in the neighbor list but the HO preparation message is rejected by the target (X2AP HO Preparation Failure), the fault moves to target-cell admission control or misconfigured target RRC config.

## CL-4 — RAN Parameter / Config
Fired rules: `HO_FAIL_RECONFIG_CAUSE`, `SLOW_HO_HEALTHY_RF`, `SLOW_SETUP_HEALTHY_RF`

Evidence:
  - **EV-010** `slow_handover` @ 09:20:10.000 (src 4001, tgt 4002) RF: RSRP -79 dBm / RSRQ -9 dB / SINR 20 dB 185.0 ms (max 100 ms) — _test_field_log_kpis[param_config.txt]_
  - **EV-011** `slow_handover` @ 09:20:20.000 (src 4002, tgt 4003) RF: RSRP -81 dBm / RSRQ -10 dB / SINR 18 dB 230.0 ms (max 100 ms) — _test_field_log_kpis[param_config.txt]_
  - **EV-012** `handover_failure` @ 09:20:30.000 (src 4003) cause=`reconfigurationFailure` RF: RSRP -80 dBm / RSRQ -9 dB / SINR 19 dB — _test_field_log_kpis[param_config.txt]_
  - **EV-013** `slow_call_setup` @ 09:20:00.000 RF: RSRP -79 dBm / RSRQ -9 dB / SINR 20 dB 2650.0 ms (SLA 2000 ms) — _test_field_log_kpis[param_config.txt]_

LLM concurrence with heuristic assignment: ✅ concurs

### Hypothesis #1 — confidence **HIGH**
**Mechanism:** reconfigurationFailure on cell 4003 (EV-012) at RSRP -80/SINR 19 dB rules out RF as a cause; preceded by two slow HOs at 185 ms and 230 ms (EV-010, EV-011) and a 2650 ms call setup (EV-013) all with healthy RF, pointing to an RRC reconfiguration message the UE cannot apply — likely a capability mismatch or invalid parameter pushed in a recent config change on the 4001-4003 cell chain.
**Evidence cited:** EV-010, EV-011, EV-012, EV-013 _(all citations verified against run record)_
**Recommended next step:** Pull QXDM log filtered on 0xB0C0/0xB821 RRC OTA for the 4001→4002→4003 HO sequence, inspect the RRCReconfiguration IEs for unsupported feature flags, and diff the 4001-4003 cell RRC parameter set against the validated golden config to identify the offending parameter.
**What would change this assessment:** If QXDM shows T304 expiry (not a UE-side reconfiguration rejection) and the target cell RRC config is valid, the slow HOs would implicate transport latency on the F1/X2 interface rather than a parameter misconfiguration.

## Cross-cluster patterns
- All four failure clusters originate from distinct log files and distinct cell sets (3001/3002, 2001/2002/2099, 4001/4002/4003) with no shared UE context or timestamp overlap, ruling out a single device defect or a network-wide event as a common cause. (evidence: EV-003, EV-008, EV-010, EV-001) → Each cluster requires an independent remediation track; there is no single systemic fix, and prioritization should follow service impact: core congestion (CL-1) and coverage hole (CL-2) affect basic connectivity, while neighbor config (CL-3) and parameter misconfiguration (CL-4) affect mobility quality.
- CL-2 (EV-007, otherFailure/RLF) and CL-3 (EV-008, handoverFailure/missing neighbor) both produce handover failures but via entirely different mechanisms — RF collapse vs. absent neighbor relation — confirming the heuristic engine correctly separated them rather than merging into a single mobility cluster. (evidence: EV-007, EV-008) → Merging these into one mobility cluster would prescribe the wrong fix; the separation must be preserved in the remediation plan.

## Insufficient-evidence notes
- EV-005 (cell 3002 interference) is a single snapshot; without a time series or spectrum scan result it is not possible to determine whether the interference is persistent, intermittent, or caused by a specific neighbor — a spectrum scan is required before a remediation action can be scoped.
- EV-009 (ping-pong between 2001 and 2002) provides return_gap_s=7.0 but no A3 offset or TTT values are present in the payload; it is not possible to confirm whether the ping-pong is caused by an overly aggressive A3 threshold or by genuine RF instability on the cell boundary without auditing the actual mobility parameter configuration.

---
_Heuristics: deterministic rule engine (see `triage/heuristics.py`). LLM pass: heuristics + LLM (claude-sonnet-4-6, prompt v0.2, temperature 0). Prompt version: 0.2._