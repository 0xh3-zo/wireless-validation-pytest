# 📡 QXDM Protocol Log Analysis Framework

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![pytest](https://img.shields.io/badge/pytest-7.4+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

Automated pytest framework for validating 5G NR device performance from QXDM protocol logs. Built for wireless validation engineers working on device certification and network optimization.

---

## ✨ Features

- **✅ RF KPI Validation** - Automated threshold checks for RSRP, RSRQ, SINR per 3GPP TS 38.133
- **✅ Handover Analysis** - Success rate calculation, duration measurement, RCA for failures
- **✅ Call Setup Metrics** - RRC connection time from Request → Setup Complete
- **✅ Coverage Analysis** - Automatic detection of dead zones and coverage holes
- **✅ Session Continuity** - PDU session stability validation across drive tests
- **✅ HTML Reports** - Professional test reports with detailed KPI breakdowns
- **🆕 AI Failure Triage** - Post-run agent that clusters failures by fault domain and drafts evidence-cited RCA hypotheses — with the LLM held to engineering standards (see below)

---

## 🧭 AI Failure Triage — clustering failures the way a RAN engineer actually does

A failed drive-test run doesn't hand you a root cause. It hands you a pile of
red test cases, and the expensive part of validation was never running the
tests — it's the hours an engineer spends afterward deciding *which team owns
which failure*. Send an RF problem to the core team and you've burned a day of
two teams' time. On a launch-critical program, mis-routed triage is schedule
risk wearing a lab coat.

This framework now does the first pass of that routing automatically, and it
does it the way an experienced engineer would: **rules first, reasoning
second, evidence always.**

### How it works

**Stage 1 — evidence capture (automatic, free, no AI).** During the pytest
run, every KPI check records structured, event-level evidence *before* it
asserts: the failing handover's source/target cells, the RRC
`reestablishmentCause`, the NAS 5GMM/5GSM cause code, and the RF conditions
(RSRP/RSRQ/SINR) at the moment of failure. A failing run leaves behind
`runs/<timestamp>/run_record.json` — machine-triageable facts, not just
assertion strings.

**Stage 2 — triage (engineer-invoked).** `python -m wireless_validation.triage`
runs two passes:

1. **A deterministic rule engine** (`triage/heuristics.py`) assigns every
   evidence record to a fault domain — RF/coverage, mobility/neighbor,
   RAN parameter/config, core/transport, device-side — using 3GPP-grounded
   rules applied in *causal precedence order*. Precedence is the domain
   knowledge: a handover that failed while RSRP was collapsing is an RF
   problem manifesting as a mobility symptom, so the RF rule outranks the
   neighbor rule. A NAS reject with a healthy radio is not a radio problem.
   Failures reproducing across three healthy cells implicate the device, not
   the network. Every assignment names the exact rule that fired, so the
   routing is auditable line by line.
2. **An optional LLM reasoning pass** (Anthropic API by default, swappable
   provider interface) reviews the clusters and drafts ranked RCA hypotheses —
   each with a confidence level, a concrete next diagnostic step ("pull the
   QXDM log and check `reestablishmentCause` on cell 2001's neighbor
   relations"), and a stated falsifier: *what evidence would change this
   assessment.*

Two artifacts come out of every triage run: an engineer-facing markdown
report, and a five-sentence executive summary that frames the failures as
launch risk in business terms.

### The AI is a junior analyst here, not the decision-maker

The interesting engineering in this feature is the governance, and it lives
in code, not in a prompt's good intentions:

- **Mandatory, validated citations.** Every hypothesis must cite evidence IDs
  from the actual run record. A validator checks each citation against the
  data; hypotheses citing evidence that doesn't exist are stamped
  **`CITATION FAILED — DISCARDED`** in the report — rejected model output is
  shown, never silently rendered and never silently dropped.
- **Heuristics hold authority.** The model may *propose* moving evidence
  between clusters, but proposals land in an advisory section for engineer
  review. The deterministic rules — reviewed, versioned, unit-tested — decide
  the routing.
- **Agreement-based confidence.** A hypothesis only earns HIGH confidence when
  the rule engine and the model independently point at the same mechanism with
  multiple supporting records. Divergence is capped at LOW and must state what
  evidence would raise it.
- **Human sign-off is in the artifact.** The executive summary ships with an
  explicit `AI-drafted, engineer-approved: [ ]` checkbox. The release call
  belongs to a person.
- **Graceful degradation.** No `ANTHROPIC_API_KEY`? The pipeline runs
  heuristics-only, says so in the report header, and still produces both
  artifacts. A triage tool that crashes on a red run would be worse than no
  tool.
- **Versioned reasoning.** The prompt (`triage/prompts.py`) carries a version
  number embedded in every report. The 3GPP cause-code semantics and reasoning
  priorities in it were authored and reviewed by a human — changing them is a
  reviewed change, not a hot edit.

### Try it in three minutes

```bash
make demo       # no API key needed — heuristics-only triage
make demo-ai    # with ANTHROPIC_API_KEY set — adds the LLM reasoning pass
```

The demo runs the seeded field logs in `fixtures/failing_runs/` — synthetic
drive-test logs, each engineered to exhibit one real-world failure signature
(a coverage hole, a handover toward a never-measured neighbor, slow handovers
with a `reconfigurationFailure`, NAS rejects with congestion/resource cause
codes) — then clusters the failures and writes both reports to `runs/latest/`.
All fixture data is synthetic and contains no carrier or OEM confidential
information.

> **Transparency note:** this feature was built solo with AI-assisted
> implementation — AI coding tools accelerated the typing; the architecture,
> the 3GPP fault-domain rules, the prompt's reasoning priorities, and every
> merged line were authored, reviewed, or corrected by the maintainer. For a
> triage tool whose whole value is trustworthy judgment, that division of
> labor is the point.

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/0xh3-zo/wireless-validation-pytest.git
cd wireless-validation-pytest

# Install dependencies
pip install -r requirements.txt
```

### Run Tests

```bash
# Green suite (parser, KPI helpers, heuristics, citation validator)
pytest

# HTML report
pytest --html=report.html --self-contained-html

# Full failure-triage demo (seeded failing field logs -> clustered RCA reports)
make demo
```

---

## 📊 Test Coverage

### Green suite — 30 tests, always passing (`pytest`)

- **Parser** (`tests/test_parser.py`) — event parsing, layer filtering, RF extraction (with and without `Cell=` context), call-setup timing, handover detection, `reestablishmentCause` capture, NAS 5GMM/5GSM cause codes, ping-pong detection, malformed/empty-log edge cases
- **Heuristics** (`tests/test_heuristics.py`) — every fault-domain rule, precedence order (RF collapse outranks neighbor blame), the cross-cell device override, and unclustered fall-through
- **Governance** (`tests/test_report.py`) — citation validation (valid kept, fabricated discarded, uncited discarded), exec-summary five-sentence contract enforcement

### Demo suite — 5 seeded field logs (`make demo`, marker `field_demo`)

Deliberately failing inputs for the triage agent, excluded from the default run. Four logs each exhibit one fault-domain signature; one healthy baseline proves the checks pass clean logs.

---

## 🔧 How It Works

### Input: QXDM Protocol Log (Plain Text)

```
2026-02-03 09:00:01.456  [RRC] RRC Connection Request
2026-02-03 09:00:01.502  [RRC] RRC Connection Setup Complete
2026-02-03 09:00:05.000  [5G_NR] Measurement Report: RSRP=-85dBm, RSRQ=-10dB, SINR=18dB
2026-02-03 09:05:12.456  [RRC] RRC Reconfiguration (Handover Command) - Source Cell: 1001
2026-02-03 09:05:12.521  [RRC] RRC Reconfiguration Complete - Target Cell: 1002
```

### Process: Automated Validation

The framework:
1. Parses protocol events using regex patterns
2. Extracts RF measurements and handover attempts
3. Validates against 3GPP thresholds and internal KPIs
4. Calculates success rates, durations, and identifies failures
5. Generates pass/fail results with detailed error messages

### Output: Test Results + HTML Report

```
tests/test_field_validation.py::test_field_log_kpis[missing_neighbor.txt] FAILED
E   AssertionError: KPI violations:
E     - HO success rate 66.7% below 95% (2/3)
E     - Ping-pong 2001<->2002 within 7.0s

[triage] 13 evidence records -> runs/2026-07-14T16-04-00/run_record.json
[triage] next: python -m wireless_validation.triage runs/latest/run_record.json
```

Every failure also leaves structured evidence behind — that JSON record is
the input to the triage agent described above.

---

## 📐 KPI Thresholds (Configurable)

All thresholds are defined in the `kpi_thresholds` fixture:

| Metric | Threshold | Standard |
|--------|-----------|----------|
| RSRP minimum | -110 dBm | 3GPP TS 38.133 |
| RSRQ minimum | -15 dB | 3GPP TS 38.133 |
| SINR minimum | 0 dB | 3GPP baseline |
| Call setup time | ≤ 2000 ms | Internal SLA |
| Handover success rate | ≥ 95% | 3GPP TS 38.331 |
| Handover duration | ≤ 100 ms | 3GPP TS 38.331 |

Thresholds live in one place — `src/wireless_validation/kpis.py` — and are
embedded into every `run_record.json`, so the triage layer always judges
evidence against the same bars the tests used:

```python
KPI_THRESHOLDS = {
    "rsrp_min_dbm": -110,
    "handover_success_rate_min": 0.95,  # change to 0.80 for 80%
    # ...
}
```

---

## 🧪 Example Triage Output

```
$ make demo
Heuristic pass: 13 evidence records -> 4 cluster(s), 0 unclustered
  CL-1 [core_transport] 2 records via ['NAS_CORE_CAUSE']
  CL-2 [rf_coverage] 5 records via ['HO_FAIL_RF_COLLAPSE', 'RF_COVERAGE_HOLE', 'RF_INTERFERENCE']
  CL-3 [mobility_neighbor] 2 records via ['HO_FAIL_TARGET_NEVER_MEASURED', 'HO_PINGPONG']
  CL-4 [ran_parameter_config] 4 records via ['HO_FAIL_RECONFIG_CAUSE', 'SLOW_HO_HEALTHY_RF', 'SLOW_SETUP_HEALTHY_RF']

Wrote:
  runs/latest/triage_report.md
  runs/latest/exec_summary.md
```

---

## 🛠️ Technologies Used

- **Python 3.8+** - Core programming language
- **pytest 7.4+** - Test framework with fixtures and parametrization
- **Regex** - Protocol log parsing and event extraction
- **pytest-html** - HTML report generation

---

## 📂 Repository Structure

```
wireless-validation-pytest/
├── src/wireless_validation/
│   ├── parser.py            # QXDM log parser (events, KPIs, cause codes)
│   ├── kpis.py              # Thresholds + evidence-recording KPI checks
│   └── triage/
│       ├── heuristics.py    # 3GPP-grounded fault-domain rules (deterministic)
│       ├── prompts.py       # Versioned, human-reviewed LLM prompt
│       ├── llm.py           # Swappable provider (Anthropic default, stdlib-only)
│       ├── report.py        # Renderers + citation validator
│       ├── models.py        # Evidence / cluster / hypothesis data model
│       └── cli.py           # python -m wireless_validation.triage
├── tests/                   # Green suite: parser, heuristics, governance (30 tests)
│   └── test_field_validation.py  # Seeded failing demo logs (marker: field_demo)
├── fixtures/failing_runs/   # Synthetic per-fault-domain drive-test logs
├── conftest.py              # pytest plugin: writes runs/<ts>/run_record.json
├── Makefile                 # make test | make demo | make demo-ai
└── pyproject.toml
```

---

## 🎯 Use Cases

### For Wireless Validation Engineers
- Automate daily drive test log analysis
- Catch network issues (poor RF, handover failures) immediately
- Generate compliance reports for 3GPP certification
- Track KPI trends across multiple test sessions

### For Network Optimization Teams
- Identify coverage holes from field test data
- Analyze handover performance across cell sites
- Validate parameter changes (A3 offsets, timers)
- Root cause analysis for call drops


---

## 🔄 Workflow Integration

### Typical Daily Use:

```bash
# 1. Export QXDM log from field test
# QXDM Professional → File → Export → Text File → save as drive_test.txt

# 2. Drop it into fixtures/failing_runs/ (or point a test at it)
cp drive_test.txt fixtures/failing_runs/

# 3. Run validation — structured evidence is captured automatically
pytest tests/test_field_validation.py -m field_demo --html=report_$(date +%Y%m%d).html

# 4. Triage the failures before filing Jira defects
python -m wireless_validation.triage runs/latest/run_record.json
# Open runs/latest/triage_report.md → each cluster maps to an owning team
```

### For CI/CD Pipelines:

```yaml
# .github/workflows/pytest.yml
- run: pytest                     # green suite gates the merge
- run: pytest -m field_demo || true   # field logs may fail — that's triage input
- run: python -m wireless_validation.triage runs/latest/run_record.json --provider none
- uses: actions/upload-artifact@v4
  with: {name: triage-report, path: runs/latest/}
```

---

## 📖 Related Standards

- **3GPP TS 38.133** - NR Requirements for support of radio resource management
- **3GPP TS 38.331** - NR Radio Resource Control (RRC) protocol specification
- **3GPP TS 24.501** - Non-Access-Stratum (NAS) protocol for 5G System

---

## 🤝 Contributing

This is a portfolio project demonstrating wireless validation testing skills. Contributions, issues, and feature requests are welcome!

To contribute:
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -m 'Add YourFeature'`)
4. Push to the branch (`git push origin feature/YourFeature`)
5. Open a Pull Request

---

## 📝 License

MIT License - See LICENSE file for details

---

## 👤 Author

**Herbert Arbizo**  
Senior RAN Engineer · Engineering Program Manager | 5G NR · Open RAN · AI-Assisted Program Operations  


- 📧 Email: [hh.arbizo@icloud.com]
- 💼 LinkedIn: [https://www.linkedin.com/in/herbert-arbizo/]
- 🌐 Related project: [GateKeeper — AI Program Operations Command Center](https://github.com/0xh3-zo/GateKeeper) · [live demo](https://gatekeeper-h-arbizo.streamlit.app/)

---


<p align="center">
  <i>If you found this useful, please ⭐ star the repo!</i>
</p>
