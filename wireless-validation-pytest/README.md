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
git clone https://github.com/YOUR_USERNAME/wireless-validation-pytest.git
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

### 12 Test Cases Across 4 Categories:

#### 1️⃣ **Log Parsing Tests** (`TestLogParsing`)
- ✅ `test_parser_initialization` - Verifies log file loads correctly
- ✅ `test_filter_by_layer` - Validates protocol layer separation (RRC, NAS, 5G_NR)
- ✅ `test_extract_rf_measurements` - Confirms RSRP/RSRQ/SINR extraction

#### 2️⃣ **KPI Validation Tests** (`TestKPIValidation`)
- ✅ `test_rsrp_threshold` - Ensures ≤20% of samples below -110 dBm
- ✅ `test_call_setup_time` - Validates RRC setup within 2000ms SLA

#### 3️⃣ **Handover Analysis Tests** (`TestHandoverAnalysis`)
- ✅ `test_handover_scenarios` - Individual handover success/failure validation
- ✅ `test_handover_success_rate` - Verifies ≥95% success rate (3GPP target)

#### 4️⃣ **Edge Case Tests** (`TestEdgeCases`)
- ✅ `test_empty_log` - Handles empty/corrupt log files
- ✅ `test_malformed_log_line` - Skips unparseable lines gracefully
- ✅ `test_missing_handover_completion` - Detects incomplete handover attempts

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
test_log_parser.py::TestKPIValidation::test_rsrp_threshold PASSED        [ 33%]
  RSRP: 1/17 samples below -110 dBm (5.9%) — threshold ≤20%

test_log_parser.py::TestHandoverAnalysis::test_handover_success_rate FAILED [ 66%]
  HO success rate: 71.4% (KPI target: 80%)
  AssertionError: 2 handover failures detected at Cells 1003 and 1005

======================== 11 passed, 1 failed in 0.06s =======================
```

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

To modify thresholds, edit the fixture in `test_log_parser.py`:

```python
@pytest.fixture
def kpi_thresholds():
    return {
        "rsrp_min": -110,
        "handover_success_rate_min": 0.95,  # Change to 0.80 for 80%
        # ... other thresholds
    }
```

---

## 🧪 Example Test Output

```
============== test session starts ==============

test_log_parser.py::TestLogParsing::test_parser_initialization PASSED
test_log_parser.py::TestLogParsing::test_filter_by_layer PASSED
  Protocol breakdown → RRC:20  NAS:6  5G_NR:17

test_log_parser.py::TestKPIValidation::test_rsrp_threshold PASSED
  RSRP: 1/17 samples below -110 dBm (5.9%) — threshold ≤20%
  
test_log_parser.py::TestHandoverAnalysis::test_handover_success_rate PASSED
  HO success rate: 100% (KPI target: 95%)
  Handovers: 7 total | 7 success | 0 failed

============== 12 passed in 0.04s ===============
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

# 2. Point fixture at new log
# Edit test_log_parser.py: sample_qxdm_log fixture → open("drive_test.txt")

# 3. Run validation
pytest test_log_parser.py -v -s --html=report_$(date +%Y%m%d).html

# 4. Review failures and file Jira defects
# Open HTML report → identify failed tests → create defect tickets
```

### For CI/CD Pipelines:

```yaml
# .github/workflows/pytest.yml
- run: pytest test_log_parser.py -v
- if: failure()
  run: notify_slack "Network validation failed - check handover KPIs"
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
RAN Optimization & UE Device Testing Engineer | Wireless Validation Engineer  


- 📧 Email: [hh.arbizo@icloud.com]
- 💼 LinkedIn: [https://www.linkedin.com/in/herbert-arbizo/]
- 🌐 Portfolio: [https://github.com/0xh3-zo/wireless-validation-pytest]

---


<p align="center">
  <i>If you found this useful, please ⭐ star the repo!</i>
</p>
