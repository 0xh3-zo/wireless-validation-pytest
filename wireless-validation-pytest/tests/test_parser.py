"""Parser tests: original 12-test coverage migrated to the package layout,
plus coverage for the new cause-code / cell-context / ping-pong extraction."""

import pytest

from wireless_validation.parser import QXDMLogParser


@pytest.fixture
def sample_qxdm_log():
    return """
2026-02-03 10:15:23.456  [RRC] RRC Connection Request
2026-02-03 10:15:23.489  [RRC] RRC Connection Setup
2026-02-03 10:15:23.502  [RRC] RRC Connection Setup Complete
2026-02-03 10:15:24.123  [NAS] PDU Session Establishment Request
2026-02-03 10:15:24.234  [NAS] PDU Session Establishment Accept
2026-02-03 10:15:25.000  [5G_NR] Measurement Report: RSRP=-85dBm, RSRQ=-10dB, SINR=18dB
2026-02-03 10:15:30.456  [RRC] RRC Reconfiguration (Handover)
2026-02-03 10:15:30.489  [RRC] RRC Reconfiguration Complete
2026-02-03 10:15:35.000  [5G_NR] Measurement Report: RSRP=-92dBm, RSRQ=-12dB, SINR=15dB
2026-02-03 10:15:40.000  [RRC] RRC Connection Release
"""


class TestLogParsing:
    def test_parser_initialization(self, sample_qxdm_log):
        parser = QXDMLogParser(sample_qxdm_log)
        assert len(parser.events) > 0
        assert all("timestamp" in e for e in parser.events)
        assert all("layer" in e for e in parser.events)

    def test_filter_by_layer(self, sample_qxdm_log):
        parser = QXDMLogParser(sample_qxdm_log)
        assert len(parser.get_events_by_layer("RRC")) == 6
        assert len(parser.get_events_by_layer("NAS")) == 2

    def test_extract_rf_measurements(self, sample_qxdm_log):
        parser = QXDMLogParser(sample_qxdm_log)
        measurements = parser.extract_rf_measurements()
        assert len(measurements) == 2
        assert measurements[0]["rsrp"] == -85
        assert measurements[0]["rsrq"] == -10
        assert measurements[0]["sinr"] == 18
        assert measurements[0]["cell"] is None  # legacy format has no Cell=

    def test_call_setup_time(self, sample_qxdm_log):
        parser = QXDMLogParser(sample_qxdm_log)
        setup = parser.calculate_call_setup_time()
        assert setup is not None and setup <= 2000


class TestHandoverAnalysis:
    def test_successful_handover_with_cells(self):
        log = """
2026-02-03 10:00:00.000  [RRC] RRC Reconfiguration (Handover Command) - Source Cell: 123
2026-02-03 10:00:00.050  [RRC] RRC Reconfiguration Complete - Target Cell: 456
"""
        ho = QXDMLogParser(log).detect_handover_events()[0]
        assert ho["success"] is True
        assert ho["duration_ms"] == 50
        assert ho["source_cell"] == 123 and ho["target_cell"] == 456
        assert ho["failure_cause"] is None

    def test_failed_handover_extracts_cause(self):
        log = """
2026-02-03 10:10:00.000  [RRC] RRC Reconfiguration (Handover Command) - Source Cell: 111 -> Target Cell: 222
2026-02-03 10:10:02.000  [RRC] RRC Connection Re-establishment Request - Cause: handoverFailure
"""
        ho = QXDMLogParser(log).detect_handover_events()[0]
        assert ho["success"] is False
        assert ho["failure_cause"] == "handoverFailure"
        assert ho["target_cell"] == 222  # commanded target from the HO line

    def test_missing_handover_completion_is_failure(self):
        log = """
2026-02-03 10:00:00.000  [RRC] RRC Reconfiguration (Handover Command) - Source Cell: 999
2026-02-03 10:00:05.000  [RRC] Some other event
"""
        ho = QXDMLogParser(log).detect_handover_events()[0]
        assert ho["success"] is False and ho["failure_cause"] is None

    def test_pingpong_detection(self):
        log = """
2026-02-03 10:00:00.000  [RRC] RRC Reconfiguration (Handover Command) - Source Cell: 1
2026-02-03 10:00:00.050  [RRC] RRC Reconfiguration Complete - Target Cell: 2
2026-02-03 10:00:07.000  [RRC] RRC Reconfiguration (Handover Command) - Source Cell: 2
2026-02-03 10:00:07.060  [RRC] RRC Reconfiguration Complete - Target Cell: 1
"""
        pp = QXDMLogParser(log).detect_pingpong_handovers()
        assert len(pp) == 1
        assert pp[0]["cell_a"] == 1 and pp[0]["cell_b"] == 2
        assert pp[0]["gap_s"] == 7.0

    def test_pingpong_outside_window_ignored(self):
        log = """
2026-02-03 10:00:00.000  [RRC] RRC Reconfiguration (Handover Command) - Source Cell: 1
2026-02-03 10:00:00.050  [RRC] RRC Reconfiguration Complete - Target Cell: 2
2026-02-03 10:00:20.000  [RRC] RRC Reconfiguration (Handover Command) - Source Cell: 2
2026-02-03 10:00:20.060  [RRC] RRC Reconfiguration Complete - Target Cell: 1
"""
        assert QXDMLogParser(log).detect_pingpong_handovers() == []


class TestCauseCodesAndContext:
    def test_nas_failure_extraction(self):
        log = """
2026-02-03 10:00:01.000  [5G_NR] Measurement Report: RSRP=-80dBm, RSRQ=-9dB, SINR=18dB, Cell=7
2026-02-03 10:00:02.000  [NAS] Registration Reject (5GS) - Cause: #22
2026-02-03 10:00:03.000  [NAS] PDU Session Establishment Reject - Cause: #26
"""
        failures = QXDMLogParser(log).extract_nas_failures()
        assert len(failures) == 2
        assert failures[0]["cause_family"] == "5GMM" and failures[0]["cause_code"] == 22
        assert failures[1]["cause_family"] == "5GSM" and failures[1]["cause_code"] == 26

    def test_measured_cells_before(self):
        log = """
2026-02-03 10:00:01.000  [5G_NR] Measurement Report: RSRP=-80dBm, RSRQ=-9dB, SINR=18dB, Cell=10
2026-02-03 10:00:05.000  [5G_NR] Measurement Report: RSRP=-81dBm, RSRQ=-9dB, SINR=18dB, Cell=11
"""
        parser = QXDMLogParser(log)
        assert parser.measured_cells_before(parser.events[1]["timestamp"]) == {10}

    def test_rf_context_at(self):
        log = """
2026-02-03 10:00:01.000  [5G_NR] Measurement Report: RSRP=-80dBm, RSRQ=-9dB, SINR=18dB
2026-02-03 10:00:05.000  [5G_NR] Measurement Report: RSRP=-95dBm, RSRQ=-12dB, SINR=8dB
2026-02-03 10:00:06.000  [RRC] RRC Connection Release
"""
        parser = QXDMLogParser(log)
        ctx = parser.rf_context_at(parser.events[-1]["timestamp"])
        assert ctx == {"rsrp": -95, "rsrq": -12, "sinr": 8}


class TestEdgeCases:
    def test_empty_log(self):
        assert QXDMLogParser("").events == []

    def test_malformed_log_line(self):
        log = """
2026-02-03 10:15:23.456  [RRC] Valid line
This is a malformed line without proper format
2026-02-03 10:15:24.456  [NAS] Another valid line
"""
        assert len(QXDMLogParser(log).events) == 2
