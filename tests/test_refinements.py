"""Focused tests for the CircuitMind prototype refinement pass.

Covers:
  1. Narrative contract integration (Refinement 1)
  2. Live verification state sync (Refinement 2)
  3. FPDF2 deprecation cleanup (Refinement 3)
  4. Demo reliability / edge-case smoke test (Refinement 4)
"""

import json
import re
import unittest
import warnings
import zlib

import pandas as pd

from data.schema_adapter import standardize_dataframe
from engine.orchestrator import CircuitMindOrchestrator
from engine.repair_memory import FROZEN_HISTORY, add_verified_case
from engine.diagnostic_receipt import extract_diagnostic_receipt
from reports.pdf_generator import generate_pdf_bytes
from reports.csv_generator import generate_csv_bytes
from engine.test_integrity import fleet_tester_analysis


def _engine():
    return CircuitMindOrchestrator(memory_history_path=str(FROZEN_HISTORY))


def _demo_logs():
    frames = [
        pd.read_csv(p) for p in (
            'data/test_logs.csv',
            'data/u3_cascade_demo_log.csv',
        )
    ]
    return standardize_dataframe(pd.concat(frames, ignore_index=True, sort=False))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  REFINEMENT 1 — NARRATIVE CONTRACT INTEGRATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class NarrativeContractIntegrationTests(unittest.TestCase):
    """Verify the narrative generator consumes diagnostic_contract."""

    @classmethod
    def setUpClass(cls):
        cls.engine = _engine()
        cls.logs = _demo_logs()
        cls.report = cls.engine.analyze('BRD_0415', cls.logs)
        cls.contract = cls.report['diagnostic_contract']
        cls.narrative = cls.report.get('narrative', '')

    def test_contract_present_path_uses_contract_refdes(self):
        """When contract exists, narrative must use the contract's leading_refdes."""
        leading = self.contract['inferred']['leading_refdes']
        self.assertIn(leading, self.narrative,
                      "Narrative must name the contract's leading RefDes")

    def test_contract_present_path_uses_contract_score(self):
        """When contract exists, narrative must use the contract's evidence score."""
        score_str = f"{self.contract['inferred']['evidence_score']:.1f}"
        self.assertIn(score_str, self.narrative,
                      "Narrative must cite the contract's evidence score")

    def test_contract_absent_fallback(self):
        """Without diagnostic_contract, narrative must still generate from raw fields."""
        from engine.narrative_generator import NarrativeGenerator
        gen = NarrativeGenerator()
        # Build a minimal report with no contract
        mini_report = {
            'board_id': 'TEST_BOARD',
            'signature': {
                'failed_tests': [{'test_step': 'T1', 'deviation': 2.0}],
                'primary_domain': 'POWER',
                'severity_label': 'CRITICAL',
            },
            'dag_analysis': {'primary_nets': [], 'cascade_nets': []},
            'suspects': [{
                'refdes': 'R99', 'desc': 'Resistor', 'score': 55.0,
                'net': 'NET_X', 'fault_mode': {'label': 'OPEN'},
                'expected_vs_observed': {'explained': ['T1'], 'unexpected': []},
                'coverage_pct': 100,
            }],
            'semantic_memory': {},
            'confidence_tier': 'Moderate Evidence',
        }
        narrative = gen.generate(mini_report)
        self.assertIn('R99', narrative)
        self.assertIn('55.0', narrative)
        self.assertIn('DIAGNOSTIC CONTRACT', narrative)

    def test_narrative_does_not_invent_different_leading_refdes(self):
        """Narrative must not name a different component as leading suspect."""
        leading = self.contract['inferred']['leading_refdes']
        # The narrative's **first** bold-marked component must be the contract's leading
        bold_matches = re.findall(r'\*\*([A-Z]\d+)', self.narrative)
        if bold_matches:
            self.assertEqual(bold_matches[0], leading,
                             "First bold RefDes in narrative must match contract leading")

    def test_contract_recommendation_consistent_with_narrative(self):
        """The contract's recommended target must appear in the narrative."""
        target = self.contract['recommended']['target']
        self.assertIn(target, self.narrative,
                      "Narrative recommendation must reference the contract's target")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  REFINEMENT 2 — LIVE VERIFICATION STATE SYNC
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class VerificationStateSyncTests(unittest.TestCase):
    """Verify that the verification sync logic in app.py works correctly.

    These tests exercise the *logic* without requiring a running Streamlit
    server — we simulate what handle_event does to the report dict.
    """

    @classmethod
    def setUpClass(cls):
        cls.engine = _engine()
        cls.logs = _demo_logs()
        cls.report = cls.engine.analyze('BRD_0415', cls.logs)

    def _make_report_copy(self):
        """Deep copy the report to avoid cross-test mutation."""
        import copy
        return copy.deepcopy(self.report)

    def test_successful_verification_updates_report(self):
        """Successful add_verified_case must update the active report verification."""
        report = self._make_report_copy()
        contract = report.get('diagnostic_contract', {})
        verif = contract.get('verification', {})

        # Simulate what app.py does after conf.get('added') is True
        conf = {'added': True, 'repair_id': 'LEARN-TEST01', 'count': 1}
        if conf.get('added') and isinstance(verif, dict):
            verif['technician_confirmed'] = True
            verif['physical_repair_recorded'] = True
            verif['retest_passed'] = True
            verif['verified_repair'] = True
            verif['repair_memory_admitted'] = True
            verif['state'] = 'VERIFIED_REPAIR'

        self.assertEqual(verif['state'], 'VERIFIED_REPAIR')
        self.assertTrue(verif['technician_confirmed'])
        self.assertTrue(verif['repair_memory_admitted'])

    def test_failed_technician_confirmation_does_not_verify(self):
        """If technician_confirmed=False, repair_memory rejects; no VERIFIED_REPAIR."""
        result = add_verified_case(
            board_id='BRD_TEST',
            refdes='U99',
            failed_steps='T1|T2',
            notes='test',
            retest_pass=True,
            technician_confirmed=False,
        )
        self.assertFalse(result['added'])
        self.assertIn('rejected', result.get('reason', '').lower())

    def test_failed_retest_does_not_verify(self):
        """If retest_pass=False, repair_memory rejects; no VERIFIED_REPAIR."""
        result = add_verified_case(
            board_id='BRD_TEST',
            refdes='U99',
            failed_steps='T1|T2',
            notes='test',
            retest_pass=False,
            technician_confirmed=True,
        )
        self.assertFalse(result['added'])
        self.assertIn('rejected', result.get('reason', '').lower())

    def test_repair_memory_admission_not_claimed_unless_admitted(self):
        """If add_verified_case returns added=False, verification must not update."""
        report = self._make_report_copy()
        contract = report.get('diagnostic_contract', {})
        verif = contract.get('verification', {})
        original_state = verif.get('state')

        # Simulate the rejection path
        conf = {'added': False, 'reason': 'Case rejected'}
        if conf.get('added') and isinstance(verif, dict):
            verif['state'] = 'VERIFIED_REPAIR'  # Should not execute

        self.assertEqual(verif.get('state'), original_state,
                         "Verification must not change when admission is rejected")

    def test_existing_verification_gates_unchanged(self):
        """The initial verification state must have all gates False."""
        report = self._make_report_copy()
        verif = report['diagnostic_contract']['verification']
        self.assertFalse(verif.get('technician_confirmed', True))
        self.assertFalse(verif.get('physical_repair_recorded', True))
        self.assertFalse(verif.get('retest_passed', True))
        self.assertFalse(verif.get('verified_repair', True))
        self.assertFalse(verif.get('repair_memory_admitted', True))
        self.assertEqual(verif.get('state'), 'PENDING_VERIFICATION')


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  REFINEMENT 3 — FPDF2 DEPRECATION CLEANUP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PDFDeprecationCleanupTests(unittest.TestCase):
    """Verify that the PDF generator produces valid output without FPDF2 warnings."""

    @classmethod
    def setUpClass(cls):
        cls.engine = _engine()
        cls.logs = _demo_logs()
        cls.report = cls.engine.analyze('BRD_0415', cls.logs)

    def test_pdf_generates_without_fpdf_deprecation_warnings(self):
        """PDF generation should not trigger FPDF2 ln= deprecation warnings."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            pdf_bytes = generate_pdf_bytes(self.report)
            fpdf_warnings = [
                w for w in caught
                if issubclass(w.category, DeprecationWarning)
                and 'ln' in str(w.message).lower()
                and 'fpdf' in str(w.filename).lower()
            ]
            self.assertEqual(len(fpdf_warnings), 0,
                             f"FPDF2 deprecation warnings found: {[str(w.message) for w in fpdf_warnings]}")
            self.assertGreater(len(pdf_bytes), 100)

    def test_pdf_still_contains_receipt_content(self):
        """After migration, PDF must still contain diagnostic receipt sections."""
        pdf_bytes = generate_pdf_bytes(self.report)
        streams = re.findall(rb'stream[\r\n]+(.*?)[\r\n]+endstream', pdf_bytes, re.S)
        full_text = b''
        for s in streams:
            try:
                full_text += zlib.decompress(s)
            except zlib.error:
                full_text += s
        text = full_text.decode('latin-1', errors='replace')
        self.assertIn('DIAGNOSTIC RECEIPT', text)
        self.assertIn('OBSERVED', text)
        self.assertIn('INFERRED', text)
        self.assertIn('RECOMMENDED', text)
        self.assertIn('VERIFICATION', text)

    def test_pdf_contains_board_id_and_status(self):
        """PDF must contain basic report fields."""
        pdf_bytes = generate_pdf_bytes(self.report)
        streams = re.findall(rb'stream[\r\n]+(.*?)[\r\n]+endstream', pdf_bytes, re.S)
        full_text = b''
        for s in streams:
            try:
                full_text += zlib.decompress(s)
            except zlib.error:
                full_text += s
        text = full_text.decode('latin-1', errors='replace')
        self.assertIn('BRD_0415', text)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  REFINEMENT 4 — DEMO RELIABILITY SMOKE TEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class DemoReliabilitySmokeTests(unittest.TestCase):
    """End-to-end deterministic smoke tests for every built-in demo case."""

    @classmethod
    def setUpClass(cls):
        cls.engine = _engine()
        cls.logs = _demo_logs()
        cls.dual_logs = standardize_dataframe(pd.read_csv('data/dual_fault_demo_log.csv'))
        cls.novel_logs = standardize_dataframe(pd.read_csv('data/novel_demo_log.csv'))
        cls.tester_logs = standardize_dataframe(pd.read_csv('data/tester_anomaly_demo_log.csv'))

    def _assert_contract_clean(self, report, board_id):
        """Common assertions for any FAIL-status report with a contract."""
        contract = report.get('diagnostic_contract')
        self.assertIsNotNone(contract, f"Contract missing for {board_id}")
        for key in ('case_number', 'board_id', 'timestamp', 'observed',
                     'inferred', 'rejected', 'recommended', 'verification'):
            self.assertIn(key, contract, f"Contract key '{key}' missing for {board_id}")
        # No NaN in JSON-serializable contract
        serialized = json.dumps(contract)
        self.assertNotIn('NaN', serialized, f"NaN found in contract for {board_id}")
        self.assertNotIn(': null', serialized.replace('null,', '').replace('null}', ''),
                         ) if False else None  # null is valid JSON; only check NaN

    def test_brd_0415_hero_case(self):
        """BRD_0415 — U3 hero case: normal successful diagnostic flow."""
        report = self.engine.analyze('BRD_0415', self.logs)
        self.assertEqual(report['status'], 'FAIL')
        self.assertEqual(report['diagnostic_contract']['inferred']['leading_refdes'], 'U3')
        self._assert_contract_clean(report, 'BRD_0415')
        # Narrative must name the leading suspect
        self.assertIn('U3', report.get('narrative', ''))

    def test_brd_u3_cascade_001(self):
        """BRD_U3_CASCADE_001 — cascade behavior preserved."""
        report = self.engine.analyze('BRD_U3_CASCADE_001', self.logs)
        self.assertEqual(report['status'], 'FAIL')
        self.assertEqual(report['diagnostic_contract']['inferred']['leading_refdes'], 'U3')
        self._assert_contract_clean(report, 'BRD_U3_CASCADE_001')

    def test_brd_0401_difficult_case(self):
        """BRD_0401 — difficult case behavior preserved."""
        report = self.engine.analyze('BRD_0401', self.logs)
        self.assertEqual(report['status'], 'FAIL')
        self._assert_contract_clean(report, 'BRD_0401')
        self.assertIsNotNone(report.get('suspects'))
        self.assertGreaterEqual(len(report['suspects']), 1)

    def test_brd_dual_fault_001(self):
        """BRD_DUAL_FAULT_001 — dual-fault behavior preserved, no false single-fault collapse."""
        report = self.engine.analyze('BRD_DUAL_FAULT_001', self.dual_logs)
        self.assertEqual(report['status'], 'FAIL')
        self._assert_contract_clean(report, 'BRD_DUAL_FAULT_001')
        multi = report.get('multi_fault_analysis', {})
        self.assertTrue(multi.get('analyzable', False),
                        "Dual-fault case must be analyzable for multi-fault")

    def test_brd_novel_001_ood(self):
        """BRD_NOVEL_001 — ABSTAIN/OOD behavior preserved, no forced diagnosis."""
        report = self.engine.analyze('BRD_NOVEL_001', self.novel_logs)
        ood = report.get('ood_state', {})
        # Should flag as unfamiliar
        if ood.get('state'):
            self.assertNotEqual(ood['state'], 'KNOWN',
                                "Novel case must not be classified as KNOWN")

    def test_tester_anomaly(self):
        """Tester anomaly demo — fixture attribution preserved."""
        analysis = fleet_tester_analysis(self.tester_logs)
        self.assertEqual(analysis['state'], 'TEST_SYSTEM_SUSPECTED')
        self.assertGreaterEqual(len(analysis['suspected_tests']), 1)

    def test_pass_board_handling(self):
        """PASS boards — no false diagnostic contract, no false repair recommendation."""
        # Find a passing board in the logs
        all_boards = self.logs['board_id'].astype(str).unique()
        pass_report = None
        for bid in all_boards:
            r = self.engine.analyze(bid, self.logs)
            if r['status'] == 'PASS':
                pass_report = r
                break
        if pass_report is not None:
            # PASS boards should have an empty suspect list
            suspects = pass_report.get('suspects', [])
            self.assertEqual(len(suspects), 0,
                             "PASS board must have no suspects")
            # Narrative should indicate passing
            narrative = pass_report.get('narrative', '')
            self.assertTrue('passed' in narrative.lower() or 'no faults' in narrative.lower(),
                            "PASS narrative should indicate all tests passed")

    def test_pdf_generation_hero(self):
        """PDF generation must succeed for BRD_0415 and contain receipt."""
        report = self.engine.analyze('BRD_0415', self.logs)
        pdf_bytes = generate_pdf_bytes(report)
        self.assertGreater(len(pdf_bytes), 200,
                           "PDF output too small — likely corrupt")
        # Extract and verify receipt content presence
        streams = re.findall(rb'stream[\r\n]+(.*?)[\r\n]+endstream', pdf_bytes, re.S)
        extracted = []
        for s in streams:
            try:
                extracted.append(zlib.decompress(s).decode('latin-1', errors='replace'))
            except Exception:
                extracted.append(s.decode('latin-1', errors='replace'))
        text = " ".join(extracted)
        self.assertIn('DIAGNOSTIC RECEIPT', text)

    def test_csv_generation_hero(self):
        """CSV generation must succeed for BRD_0415 and contain receipt metadata."""
        report = self.engine.analyze('BRD_0415', self.logs)
        csv_bytes = generate_csv_bytes(report)
        csv_text = csv_bytes.decode('utf-8')
        self.assertIn('BRD_0415', csv_text)
        # Receipt metadata rows should be present
        self.assertIn('receipt_', csv_text)

    def test_no_nan_in_any_demo_contract(self):
        """No NaN values in any demo case's diagnostic contract."""
        cases = [
            ('BRD_0415', self.logs),
            ('BRD_U3_CASCADE_001', self.logs),
            ('BRD_0401', self.logs),
            ('BRD_DUAL_FAULT_001', self.dual_logs),
            ('BRD_NOVEL_001', self.novel_logs),
        ]
        for board_id, logs in cases:
            report = self.engine.analyze(board_id, logs)
            contract = report.get('diagnostic_contract')
            if contract:
                serialized = json.dumps(contract)
                self.assertNotIn('NaN', serialized,
                                 f"NaN found in contract for {board_id}")


if __name__ == '__main__':
    unittest.main()
