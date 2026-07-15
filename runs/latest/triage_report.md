# Failure Triage Report

**Run:** 2026-07-14T17:43:34  |  **Tests:** 5 total, 4 failed  |  **Evidence records:** 13
**Analysis mode:** heuristics-only (model returned unparseable JSON: Expecting value: line 105 column 375 (char 13899))

## CL-1 — Core / Transport
Fired rules: `NAS_CORE_CAUSE`

Evidence:
  - **EV-001** `nas_failure` @ 09:30:02.300 5GMM cause #22 RF: RSRP -78 dBm / RSRQ -9 dB / SINR 21 dB — _test_field_log_kpis[core_reject.txt]_
  - **EV-002** `nas_failure` @ 09:30:06.400 5GSM cause #26 RF: RSRP -80 dBm / RSRQ -9 dB / SINR 19 dB — _test_field_log_kpis[core_reject.txt]_

## CL-2 — RF / Coverage
Fired rules: `HO_FAIL_RF_COLLAPSE`, `RF_COVERAGE_HOLE`, `RF_INTERFERENCE`

Evidence:
  - **EV-003** `rf_degradation` @ 09:02:00.000 (cell 3001) RF: RSRP -112 dBm / RSRQ -16 dB / SINR -2 dB — _test_field_log_kpis[coverage_hole.txt]_
  - **EV-004** `rf_degradation` @ 09:03:00.000 (cell 3001) RF: RSRP -115 dBm / RSRQ -17 dB / SINR -4 dB — _test_field_log_kpis[coverage_hole.txt]_
  - **EV-005** `rf_degradation` @ 09:04:00.000 (cell 3002) RF: RSRP -90 dBm / RSRQ -13 dB / SINR 1 dB — _test_field_log_kpis[coverage_hole.txt]_
  - **EV-006** `rf_degradation` @ 09:04:30.000 (cell 3001) RF: RSRP -118 dBm / RSRQ -18 dB / SINR -6 dB — _test_field_log_kpis[coverage_hole.txt]_
  - **EV-007** `handover_failure` @ 09:03:30.000 (src 3001) cause=`otherFailure` RF: RSRP -115 dBm / RSRQ -17 dB / SINR -4 dB — _test_field_log_kpis[coverage_hole.txt]_

## CL-3 — Mobility / Neighbor
Fired rules: `HO_FAIL_TARGET_NEVER_MEASURED`, `HO_PINGPONG`

Evidence:
  - **EV-008** `handover_failure` @ 09:10:03.000 (src 2001, tgt 2099) cause=`handoverFailure` RF: RSRP -84 dBm / RSRQ -10 dB / SINR 16 dB — _test_field_log_kpis[missing_neighbor.txt]_
  - **EV-009** `handover_pingpong` @ 09:10:07.000 (2001<->2002) return in 7.0 s — _test_field_log_kpis[missing_neighbor.txt]_

## CL-4 — RAN Parameter / Config
Fired rules: `HO_FAIL_RECONFIG_CAUSE`, `SLOW_HO_HEALTHY_RF`, `SLOW_SETUP_HEALTHY_RF`

Evidence:
  - **EV-010** `slow_handover` @ 09:20:10.000 (src 4001, tgt 4002) RF: RSRP -79 dBm / RSRQ -9 dB / SINR 20 dB 185.0 ms (max 100 ms) — _test_field_log_kpis[param_config.txt]_
  - **EV-011** `slow_handover` @ 09:20:20.000 (src 4002, tgt 4003) RF: RSRP -81 dBm / RSRQ -10 dB / SINR 18 dB 230.0 ms (max 100 ms) — _test_field_log_kpis[param_config.txt]_
  - **EV-012** `handover_failure` @ 09:20:30.000 (src 4003) cause=`reconfigurationFailure` RF: RSRP -80 dBm / RSRQ -9 dB / SINR 19 dB — _test_field_log_kpis[param_config.txt]_
  - **EV-013** `slow_call_setup` @ 09:20:00.000 RF: RSRP -79 dBm / RSRQ -9 dB / SINR 20 dB 2650.0 ms (SLA 2000 ms) — _test_field_log_kpis[param_config.txt]_

---
_Heuristics: deterministic rule engine (see `triage/heuristics.py`). LLM pass: heuristics-only (model returned unparseable JSON: Expecting value: line 105 column 375 (char 13899)). Prompt version: 0.1._