"""Unit tests for the CircuitMind structured Diagnostic Contract."""

import json
import unittest
import pandas as pd

from data.schema_adapter import standardize_dataframe
from engine.orchestrator import CircuitMindOrchestrator
from engine.repair_memory import FROZEN_HISTORY


class DiagnosticContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = CircuitMindOrchestrator(memory_history_path=str(FROZEN_HISTORY))
        frames = [pd.read_csv(p) for p in ('data/test_logs.csv', 'data/u3_cascade_demo_log.csv')]
        cls.logs = standardize_dataframe(pd.concat(frames, ignore_index=True, sort=False))

    def test_contract_structure_and_keys(self):
        report = self.engine.analyze('BRD_0415', self.logs)
        self.assertIn('diagnostic_contract', report)
        contract = report['diagnostic_contract']
        for key in ('case_number', 'board_id', 'timestamp', 'observed', 'inferred', 'rejected', 'recommended', 'verification'):
            self.assertIn(key, contract)

    def test_observed_fields(self):
        report = self.engine.analyze('BRD_0415', self.logs)
        observed = report['diagnostic_contract']['observed']
        self.assertGreaterEqual(observed['failed_test_count'], 1)
        self.assertEqual(observed['primary_domain'], 'POWER')
        self.assertIn(observed['severity'], {'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'})
        self.assertEqual(len(observed['deviation_range']), 2)
        self.assertGreaterEqual(len(observed['failed_tests']), 1)
        self.assertTrue(observed['fingerprint'])

    def test_inferred_fields(self):
        report = self.engine.analyze('BRD_0415', self.logs)
        inferred = report['diagnostic_contract']['inferred']
        self.assertEqual(inferred['leading_refdes'], 'U3')
        self.assertGreaterEqual(inferred['evidence_score'], 50.0)
        self.assertTrue(inferred['fault_mode'])
        self.assertGreaterEqual(inferred['mechanism_coverage_pct'], 50)
        self.assertEqual(inferred['confidence_tier'], 'Strong Evidence')
        self.assertEqual(inferred['diagnosis_state'], 'LEADING_HYPOTHESIS')

    def test_rejected_alternatives_and_evidence_gaps(self):
        report = self.engine.analyze('BRD_0415', self.logs)
        rejected = report['diagnostic_contract']['rejected']
        self.assertGreaterEqual(len(rejected), 1)
        for alt in rejected:
            self.assertTrue(alt['refdes'])
            self.assertTrue(alt['desc'])
            self.assertGreaterEqual(alt['score'], 0.0)
            self.assertIn('rejection_reason', alt)
            self.assertIn('evidence_gap', alt)
            self.assertTrue(alt['evidence_gap'])

    def test_recommended_action(self):
        report = self.engine.analyze('BRD_0415', self.logs)
        rec = report['diagnostic_contract']['recommended']
        self.assertIn(rec['action'], {'INSPECT', 'VERIFY_FIRST', 'ABSTAIN'})
        self.assertTrue(rec['target'])
        self.assertTrue(rec['rationale'])

    def test_verification_lifecycle_initial_state(self):
        report = self.engine.analyze('BRD_0415', self.logs)
        verif = report['diagnostic_contract']['verification']
        self.assertEqual(verif['state'], 'PENDING_VERIFICATION')
        self.assertFalse(verif['technician_confirmed'])
        self.assertFalse(verif['physical_repair_recorded'])
        self.assertFalse(verif['retest_passed'])
        self.assertFalse(verif['verified_repair'])
        self.assertFalse(verif['repair_memory_admitted'])
        self.assertEqual(verif['disclaimer'], 'Physical verification still required.')

    def test_contract_is_serializable(self):
        report = self.engine.analyze('BRD_0415', self.logs)
        contract = report['diagnostic_contract']
        serialized = json.dumps(contract)
        deserialized = json.loads(serialized)
        self.assertEqual(deserialized['board_id'], 'BRD_0415')
        self.assertEqual(deserialized['inferred']['leading_refdes'], 'U3')

    def test_pass_board_omits_contract(self):
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
        self.assertEqual(report['status'], 'PASS')
        self.assertNotIn('diagnostic_contract', report)

    def test_novel_board_contract_abstains(self):
        novel = standardize_dataframe(pd.read_csv('data/novel_demo_log.csv'))
        report = self.engine.analyze('BRD_NOVEL_001', novel)
        contract = report['diagnostic_contract']
        self.assertEqual(contract['inferred']['diagnosis_state'], 'ABSTAIN')
        self.assertEqual(contract['recommended']['action'], 'ABSTAIN')

    def test_source_timestamp_preservation(self):
        frame = pd.DataFrame({
            'board_id': ['TIME-1'],
            'test_step': ['TEST_5V_RAIL'],
            'measured_value': [0.5],
            'expected_min': [4.8],
            'expected_max': [5.2],
            'pass_fail': ['FAIL'],
            'timestamp': ['2026-08-20T10:15:30Z'],
        })
        report = self.engine.analyze('TIME-1', standardize_dataframe(frame))
        contract = report['diagnostic_contract']
        self.assertEqual(contract['timestamp'], '2026-08-20T10:15:30Z')

    def test_source_timestamp_fallback(self):
        report = self.engine.analyze('BRD_0415', self.logs)
        contract = report['diagnostic_contract']
        self.assertTrue(isinstance(contract['timestamp'], str))
        self.assertGreaterEqual(len(contract['timestamp']), 10)


    def test_narrative_contract_consistency(self):
        report = self.engine.analyze('BRD_0415', self.logs)
        contract = report['diagnostic_contract']
        narrative = report.get('narrative', '')

        # Contract leading suspect must be named in the narrative
        self.assertIn(contract['inferred']['leading_refdes'], narrative)
        # Description or component type must appear
        self.assertIn('TPS54331', narrative)
        # Score in contract matches score in narrative
        self.assertIn(f"{contract['inferred']['evidence_score']:.1f}", narrative)
        # Recommended action in contract matches recommendation in narrative
        self.assertIn(contract['recommended']['target'], narrative)

    def test_u3_hero_case_contract(self):
        # 1. BRD_0415
        report_0415 = self.engine.analyze('BRD_0415', self.logs)
        contract_0415 = report_0415['diagnostic_contract']
        self.assertEqual(contract_0415['inferred']['leading_refdes'], 'U3')
        self.assertEqual(contract_0415['inferred']['leading_desc'], 'TPS54331 Buck')
        self.assertEqual(contract_0415['inferred']['mechanism_coverage_pct'], 100)
        self.assertEqual(len(contract_0415['inferred']['mechanism_unexplained']), 0)
        self.assertEqual(contract_0415['inferred']['confidence_tier'], 'Strong Evidence')

        # 2. BRD_U3_CASCADE_001
        report_cascade = self.engine.analyze('BRD_U3_CASCADE_001', self.logs)
        contract_cascade = report_cascade['diagnostic_contract']
        self.assertEqual(contract_cascade['inferred']['leading_refdes'], 'U3')
        self.assertEqual(contract_cascade['inferred']['mechanism_coverage_pct'], 100)

    def test_dual_fault_case_contract(self):
        dual_logs = standardize_dataframe(pd.read_csv('data/dual_fault_demo_log.csv'))
        report = self.engine.analyze('BRD_DUAL_FAULT_001', dual_logs)
        contract = report['diagnostic_contract']
        self.assertEqual(contract['inferred']['leading_refdes'], 'U3')
        self.assertGreaterEqual(len(contract['rejected']), 1)
        # Multi-fault analysis is present
        multi = report.get('multi_fault_analysis', {})
        self.assertTrue(multi.get('analyzable', False))
        self.assertIsNotNone(multi.get('best_pair'))

    def test_tester_anomaly_case(self):
        from engine.test_integrity import fleet_tester_analysis
        tester_logs = standardize_dataframe(pd.read_csv('data/tester_anomaly_demo_log.csv'))
        analysis = fleet_tester_analysis(tester_logs)
        self.assertEqual(analysis['state'], 'TEST_SYSTEM_SUSPECTED')
        self.assertGreaterEqual(len(analysis['suspected_tests']), 1)
        # Ensure it flags fixture attribution rather than attributing to board defects
        attributions = [t.get('attribution') for t in analysis['suspected_tests']]
        self.assertIn('FIXTURE_SUSPECTED', attributions)


if __name__ == '__main__':
    unittest.main()
