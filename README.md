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
# Basic test run (output to terminal)
pytest test_log_parser.py -v

# With detailed output (shows KPI values)
pytest test_log_parser.py -v -s

# Generate HTML report
pytest test_log_parser.py -v --html=report.html --self-contained-html
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
├── test_log_parser.py       # Main test suite (12 test cases)
├── requirements.txt         # Python dependencies
├── pytest.ini               # pytest configuration
├── README.md                # This file
├── .gitignore              # Git ignore rules
└── sample_log.txt          # Example QXDM log (optional)
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

### For Device Manufacturers (Apple, Samsung, Google)
- Pre-certification validation against carrier networks
- Modem firmware regression testing
- Multi-vendor chipset comparison (Qualcomm vs MediaTek)
- IOT testing with different RAN vendors

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
