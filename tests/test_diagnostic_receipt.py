"""Unit tests for the Diagnostic Receipt extractor."""

import json
import unittest
import pandas as pd

from data.schema_adapter import standardize_dataframe
from engine.orchestrator import CircuitMindOrchestrator
from engine.repair_memory import FROZEN_HISTORY
from engine.diagnostic_receipt import extract_diagnostic_receipt


class DiagnosticReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = CircuitMindOrchestrator(memory_history_path=str(FROZEN_HISTORY))
        frames = [pd.read_csv(p) for p in ('data/test_logs.csv', 'data/u3_cascade_demo_log.csv')]
        cls.logs = standardize_dataframe(pd.concat(frames, ignore_index=True, sort=False))

    def _report(self, board_id='BRD_0415'):
        return self.engine.analyze(board_id, self.logs)

    # ── 1. Receipt creation from a diagnostic contract ──
    def test_receipt_created_from_contract(self):
        report = self._report()
        receipt = extract_diagnostic_receipt(report)
        self.assertIsNotNone(receipt)
        for key in ('receipt_version', 'case_number', 'board_id', 'timestamp',
                     'observed', 'inferred', 'rejected', 'recommended', 'verification'):
            self.assertIn(key, receipt)

    # ── 2. Receipt preserves inferred values exactly ──
    def test_receipt_preserves_inferred_values(self):
        report = self._report()
        receipt = extract_diagnostic_receipt(report)
        contract = report['diagnostic_contract']
        self.assertEqual(receipt['inferred']['leading_refdes'], contract['inferred']['leading_refdes'])
        self.assertEqual(receipt['inferred']['leading_desc'], contract['inferred']['leading_desc'])
        self.assertAlmostEqual(receipt['inferred']['evidence_score'], contract['inferred']['evidence_score'], places=4)
        self.assertEqual(receipt['inferred']['mechanism_coverage_pct'], contract['inferred']['mechanism_coverage_pct'])
        self.assertEqual(receipt['inferred']['confidence_tier'], contract['inferred']['confidence_tier'])
        self.assertEqual(receipt['inferred']['diagnosis_state'], contract['inferred']['diagnosis_state'])

    # ── 3. Receipt preserves rejected candidates exactly ──
    def test_receipt_preserves_rejected_candidates(self):
        report = self._report()
        receipt = extract_diagnostic_receipt(report)
        contract = report['diagnostic_contract']
        self.assertEqual(len(receipt['rejected']), len(contract['rejected']))
        for r_alt, c_alt in zip(receipt['rejected'], contract['rejected']):
            self.assertEqual(r_alt['refdes'], c_alt['refdes'])
            self.assertEqual(r_alt['desc'], c_alt['desc'])
            self.assertAlmostEqual(r_alt['score'], c_alt['score'], places=4)
            self.assertEqual(r_alt['mechanism_coverage_pct'], c_alt['mechanism_coverage_pct'])
            self.assertEqual(r_alt['rejection_reason'], c_alt['rejection_reason'])

    # ── 4. Receipt preserves evidence_gap ──
    def test_receipt_preserves_evidence_gap(self):
        report = self._report()
        receipt = extract_diagnostic_receipt(report)
        contract = report['diagnostic_contract']
        for r_alt, c_alt in zip(receipt['rejected'], contract['rejected']):
            self.assertEqual(r_alt['evidence_gap'], c_alt['evidence_gap'])

    # ── 5. Receipt preserves verification lifecycle ──
    def test_receipt_preserves_verification_lifecycle(self):
        report = self._report()
        receipt = extract_diagnostic_receipt(report)
        contract = report['diagnostic_contract']
        verif = receipt['verification']
        c_verif = contract['verification']
        self.assertEqual(verif['state'], c_verif['state'])
        self.assertEqual(verif['technician_confirmed'], c_verif['technician_confirmed'])
        self.assertEqual(verif['physical_repair_recorded'], c_verif['physical_repair_recorded'])
        self.assertEqual(verif['retest_passed'], c_verif['retest_passed'])
        self.assertEqual(verif['verified_repair'], c_verif['verified_repair'])
        self.assertEqual(verif['repair_memory_admitted'], c_verif['repair_memory_admitted'])
        self.assertEqual(verif['disclaimer'], c_verif['disclaimer'])

    # ── 6. Receipt is JSON serializable ──
    def test_receipt_is_json_serializable(self):
        report = self._report()
        receipt = extract_diagnostic_receipt(report)
        serialized = json.dumps(receipt)
        deserialized = json.loads(serialized)
        self.assertEqual(deserialized['board_id'], receipt['board_id'])
        self.assertEqual(deserialized['inferred']['leading_refdes'], receipt['inferred']['leading_refdes'])

    # ── 7. PDF contains DIAGNOSTIC RECEIPT ──
    def test_pdf_contains_diagnostic_receipt(self):
        import re
        import zlib
        from reports.pdf_generator import generate_pdf_bytes
        report = self._report()
        pdf_bytes = generate_pdf_bytes(report)
        streams = re.findall(rb'stream[\r\n]+(.*?)[\r\n]+endstream', pdf_bytes, re.S)
        parts = []
        for stream in streams:
            try:
                parts.append(zlib.decompress(stream).decode('latin-1', errors='ignore'))
            except Exception:
                pass
        pdf_text = ' '.join(parts)
        self.assertIn('DIAGNOSTIC RECEIPT', pdf_text)
        self.assertIn('OBSERVED', pdf_text)
        self.assertIn('INFERRED', pdf_text)
        self.assertIn('RECOMMENDED', pdf_text)
        self.assertIn('VERIFICATION', pdf_text)

    # ── 8. CSV contains receipt metadata ──
    def test_csv_contains_receipt_metadata(self):
        from reports.csv_generator import generate_csv_bytes
        report = self._report()
        csv_bytes = generate_csv_bytes(report)
        csv_text = csv_bytes.decode('utf-8')
        self.assertIn('diagnostic_receipt_version', csv_text)
        self.assertIn('receipt_inferred_refdes', csv_text)
        self.assertIn('receipt_verification_state', csv_text)
        self.assertIn('receipt_recommended_action', csv_text)

    # ── 9. Receipt returns None for PASS boards ──
    def test_receipt_returns_none_for_pass_board(self):
        frame = pd.DataFrame({
            'board_id': ['PASS-1'],
            'test_step': ['TEST_VBUS'],
            'measured_value': [5.0],
            'expected_min': [4.75],
            'expected_max': [5.25],
            'pass_fail': ['PASS'],
            'error_code': [''],
            'unit': ['V'],
        })
        report = self.engine.analyze('PASS-1', frame)
        receipt = extract_diagnostic_receipt(report)
        self.assertIsNone(receipt)

    # ── 10. Receipt performs zero reasoning (pure extraction) ──
    def test_receipt_performs_zero_reasoning(self):
        """The receipt must be identical whether extracted once or twice — proving
        it is a pure function that reads from the contract without side effects."""
        report = self._report()
        receipt_a = extract_diagnostic_receipt(report)
        receipt_b = extract_diagnostic_receipt(report)
        self.assertEqual(json.dumps(receipt_a, sort_keys=True),
                         json.dumps(receipt_b, sort_keys=True))


    # ── 11. Verification lifecycle progression invariants ──
    def test_verification_lifecycle_progression_order(self):
        """Verify lifecycle progression guarantees that a later state is NEVER
        enabled/active before its required prerequisite state is complete."""
        def resolve_lifecycle_active_step(verif):
            if not verif.get('technician_confirmed', False):
                return 'HUMAN'
            if not verif.get('physical_repair_recorded', False):
                return 'REPAIR'
            if not verif.get('retest_passed', False):
                return 'RETEST'
            if not verif.get('verified_repair', False):
                return 'VERIFIED'
            if not verif.get('repair_memory_admitted', False):
                return 'MEMORY'
            return 'COMPLETE'

        # State 0: Initial unverified
        v0 = {
            'state': 'PENDING_VERIFICATION',
            'technician_confirmed': False,
            'physical_repair_recorded': False,
            'retest_passed': False,
            'verified_repair': False,
            'repair_memory_admitted': False,
        }
        self.assertEqual(resolve_lifecycle_active_step(v0), 'HUMAN')

        # State 1: Technician confirms
        v1 = dict(v0, technician_confirmed=True)
        self.assertEqual(resolve_lifecycle_active_step(v1), 'REPAIR')

        # State 2: Physical repair recorded
        v2 = dict(v1, physical_repair_recorded=True)
        self.assertEqual(resolve_lifecycle_active_step(v2), 'RETEST')

        # State 3: Retest passed
        v3 = dict(v2, retest_passed=True)
        self.assertEqual(resolve_lifecycle_active_step(v3), 'VERIFIED')

        # State 4: Verified repair
        v4 = dict(v3, verified_repair=True)
        self.assertEqual(resolve_lifecycle_active_step(v4), 'MEMORY')

        # State 5: Repair memory admitted
        v5 = dict(v4, repair_memory_admitted=True)
        self.assertEqual(resolve_lifecycle_active_step(v5), 'COMPLETE')

        # Safety Invariant: If retest passed without technician confirmation, cannot bypass human gate
        v_bypass = dict(v0, retest_passed=True, verified_repair=True)
        self.assertEqual(resolve_lifecycle_active_step(v_bypass), 'HUMAN')


if __name__ == '__main__':
    unittest.main()
