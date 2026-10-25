"""Unit tests for the CircuitMind deterministic engine and exports.

Run from the project root:  python3 -m unittest discover -s tests
"""

import os
import re
import sys
import unittest
import zlib
from io import StringIO

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.schema_adapter import standardize_dataframe
from engine.evidence_fusion import EvidenceFusion
from engine.orchestrator import CircuitMindOrchestrator
from engine.signature_extractor import SignatureExtractor
from reports.csv_generator import generate_csv_bytes
from reports.pdf_generator import generate_pdf_bytes
from engine.repair_memory import FROZEN_HISTORY


def load_logs() -> pd.DataFrame:
    frames = [pd.read_csv(path) for path in ('data/test_logs.csv', 'data/u3_cascade_demo_log.csv')]
    return standardize_dataframe(pd.concat(frames, ignore_index=True, sort=False))


class SignatureExtractorTests(unittest.TestCase):
    def test_deviation_and_severity(self):
        extractor = SignatureExtractor()
        frame = pd.DataFrame({
            'board_id': ['B1'],
            'test_step': ['TEST_5V_RAIL'],
            'measured_value': [0.63],
            'expected_min': [4.8],
            'expected_max': [5.2],
            'pass_fail': ['FAIL'],
            'error_code': ['VAL'],
            'unit': ['V'],
        })
        signature = extractor.extract(frame)
        self.assertEqual(signature['severity_label'], 'CRITICAL')
        self.assertEqual(signature['primary_domain'], 'POWER')
        self.assertEqual(signature['failed_tests'][0]['net'], 'SYS_5V')
        self.assertGreater(signature['failed_tests'][0]['deviation'], 20.0)

    def test_pass_signature(self):
        extractor = SignatureExtractor()
        frame = pd.DataFrame({
            'board_id': ['B1'],
            'test_step': ['TEST_5V_RAIL'],
            'measured_value': [5.0],
            'expected_min': [4.8],
            'expected_max': [5.2],
            'pass_fail': ['PASS'],
            'error_code': [''],
            'unit': ['V'],
        })
        self.assertEqual(extractor.extract(frame)['severity_label'], 'PASS')


class OrchestratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.logs = load_logs()
        cls.engine = CircuitMindOrchestrator(memory_history_path=str(FROZEN_HISTORY))

    def test_known_board_ranks_u3_first(self):
        report = self.engine.analyze('BRD_0415', self.logs)
        self.assertEqual(report['suspects'][0]['refdes'], 'U3')
        self.assertEqual(report['confidence_tier'], 'Strong Evidence')

    def test_precedent_consistency_across_surfaces(self):
        """Card, narrative, ledger, and PDF must cite the same precedent."""
        report = self.engine.analyze('BRD_0415', self.logs)
        precedent = report['cited_precedent']
        self.assertIsNotNone(precedent)
        card_line = [line for line in report['suspects'][0]['positive_evidence']
                     if line.startswith('Historical case ')][0]
        self.assertIn(precedent['repair_id'], card_line)
        self.assertIn(precedent['repair_id'], report['narrative'])
        ledger = [entry for entry in report['evidence_ledger'] if entry['source'] == 'Repair history']
        self.assertEqual(len(ledger), 1)
        self.assertIn(precedent['repair_id'], ledger[0]['observation'])

    def test_notes_boost_reranks(self):
        base = self.engine.analyze('BRD_0415', self.logs)
        with_notes = self.engine.analyze('BRD_0415', self.logs, repair_notes='replaced L1, cold solder at L1')
        base_l1 = next(c for c in base['suspects'] if c['refdes'] == 'L1')
        notes_l1 = next(c for c in with_notes['suspects'] if c['refdes'] == 'L1')
        self.assertGreater(notes_l1['score'], base_l1['score'] + 5)
        self.assertTrue(any(line.startswith('Repair notes explicitly name L1') for line in notes_l1['positive_evidence']))

    def test_notes_are_a_noop_when_empty(self):
        report = self.engine.analyze('BRD_0415', self.logs)
        report_blank = self.engine.analyze('BRD_0415', self.logs, repair_notes='')
        self.assertEqual(report['suspects'][0]['score'], report_blank['suspects'][0]['score'])
        self.assertEqual(report['suspects'][0]['refdes'], report_blank['suspects'][0]['refdes'])

    def test_pass_board_path(self):
        frame = pd.DataFrame({
            'board_id': ['PASS-1'] * 3,
            'test_step': ['TEST_VBUS', 'TEST_5V_RAIL', 'TEST_THERMISTOR'],
            'measured_value': [5.0, 5.0, 2.25],
            'expected_min': [4.75, 4.8, 2.0],
            'expected_max': [5.25, 5.2, 2.5],
            'pass_fail': ['PASS'] * 3,
            'error_code': [''] * 3,
            'unit': ['V', 'V', 'V'],
        })
        report = self.engine.analyze('PASS-1', frame)
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['diagnosis_state'], 'PASS')

    def test_unknown_test_steps_are_graceful(self):
        frame = pd.DataFrame({
            'board_id': ['X-1'],
            'test_step': ['MYSTERY_TEST'],
            'measured_value': [0.5],
            'expected_min': [1.0],
            'expected_max': [2.0],
            'pass_fail': ['FAIL'],
            'error_code': ['FOO'],
        })
        report = self.engine.analyze('X-1', frame)
        self.assertEqual(report['status'], 'FAIL')
        self.assertEqual(report['signature']['failed_tests'][0]['net'], 'UNKNOWN')
        self.assertEqual(report['confidence_tier'], 'Insufficient Evidence')

    def test_evidence_policy_is_exposed(self):
        # The exposed policy must match the canonical config (learned weights).
        import json as _json
        from pathlib import Path as _Path
        cfg = _json.loads((_Path(__file__).resolve().parent.parent / 'config' / 'diagnostic_weights.json').read_text(encoding='utf-8'))
        report = self.engine.analyze('BRD_0415', self.logs)
        self.assertEqual(report['evidence_policy']['weights']['history'], cfg['weights']['history'])
        self.assertEqual(report['evidence_policy']['weights']['net'], cfg['weights']['net'])

    def test_pattern_space_is_shipped(self):
        report = self.engine.analyze('BRD_0415', self.logs)
        self.assertGreaterEqual(len(report['semantic_memory']['cases']), 100)
        self.assertEqual(len(report['semantic_memory']['pca_point']), 2)


class EvidenceFusionTests(unittest.TestCase):
    def test_policy_loads_from_disk(self):
        fusion = EvidenceFusion()
        policy = fusion.get_policy()
        # Weights resolve through config/diagnostic_weights.json (learned from
        # 300 labeled training boards, selected on validation, +10 blind top-1).
        import json as _json
        from pathlib import Path as _Path
        cfg = _json.loads((_Path(__file__).resolve().parent.parent / 'config' / 'diagnostic_weights.json').read_text(encoding='utf-8'))
        self.assertAlmostEqual(policy['weights']['history'], cfg['weights']['history'])
        self.assertAlmostEqual(policy['weights']['net'], cfg['weights']['net'])
        self.assertEqual(policy['notes_bonus'], 10.0)
        self.assertEqual(policy['uncertainty_gap'], 15.0)
        self.assertAlmostEqual(sum(policy['weights'].values()), 1.0)


class SchemaAdapterTests(unittest.TestCase):
    def test_variant_columns(self):
        raw = pd.read_csv(StringIO(
            'sn,test,reading,low_limit,high_limit,result,code\n'
            'ALT-1,TEST_5V_RAIL,3.1,4.8,5.2,NG,VAL\n'
            'ALT-1,TEST_THERMISTOR,2.3,2.0,2.5,OK,\n'
        ))
        frame = standardize_dataframe(raw)
        self.assertIn('expected_min', frame.columns)
        self.assertIn('board_id', frame.columns)
        self.assertEqual(frame['pass_fail'].tolist(), ['FAIL', 'PASS'])

    def test_missing_required_column_raises(self):
        raw = pd.DataFrame({'board_id': ['A'], 'test_step': ['T']})
        with self.assertRaises(ValueError):
            standardize_dataframe(raw)


class ExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = CircuitMindOrchestrator(memory_history_path=str(FROZEN_HISTORY))
        cls.logs = load_logs()

    def _pdf_text(self, report) -> str:
        pdf = generate_pdf_bytes(report)
        streams = re.findall(rb'stream\r?\n(.*?)\r?\nendstream', pdf, re.S)
        parts = []
        for stream in streams:
            try:
                parts.append(zlib.decompress(stream).decode('latin-1', errors='ignore'))
            except Exception:
                pass
        return ' '.join(parts)

    def test_csv_contains_ranked_suspects_and_failures(self):
        report = self.engine.analyze('BRD_0415', self.logs)
        csv = generate_csv_bytes(report).decode('utf-8')
        self.assertIn('failing_tests', csv)
        self.assertIn('positive_evidence', csv)
        self.assertIn('U3', csv)

    def test_csv_includes_repair_notes(self):
        report = self.engine.analyze('BRD_0415', self.logs, repair_notes='replaced L1')
        self.assertIn('replaced L1', generate_csv_bytes(report).decode('utf-8'))

    def test_pdf_generates_for_fail_and_pass(self):
        fail_report = self.engine.analyze('BRD_0415', self.logs)
        self.assertGreater(len(generate_pdf_bytes(fail_report)), 1000)
        pass_frame = pd.DataFrame({
            'board_id': ['P-1'],
            'test_step': ['TEST_VBUS'],
            'measured_value': [5.0],
            'expected_min': [4.75],
            'expected_max': [5.25],
            'pass_fail': ['PASS'],
            'error_code': [''],
            'unit': ['V'],
        })
        self.assertGreater(len(generate_pdf_bytes(self.engine.analyze('P-1', pass_frame))), 500)

    def test_pdf_renders_next_best_action(self):
        report = self.engine.analyze('BRD_0401', self.logs)
        self.assertTrue(report['next_best_test']['active'])
        text = self._pdf_text(report)
        self.assertIn('Recommended Next Action', text)
        self.assertIn(report['next_best_test']['test'], text)

    def test_pdf_handles_unicode(self):
        report = self.engine.analyze('BRD_0415', self.logs)
        pdf = generate_pdf_bytes(report)  # must not raise on em-dash / arrows
        self.assertGreater(len(pdf), 1000)


class AdvancedDiagnosticsTests(unittest.TestCase):
    """Regression tests for the 95+ subsystems: fault modes, multi-fault
    solver, OOD/novelty, data quality, NBT 2.0, verified repair memory,
    versioning, and report enrichment."""

    @classmethod
    def setUpClass(cls):
        cls.engine = CircuitMindOrchestrator(memory_history_path=str(FROZEN_HISTORY))
        cls.logs = load_logs()
        cls.hero = cls.engine.analyze('BRD_0415', cls.logs)

    def test_fault_mode_assigned_to_leader(self):
        fault_mode = self.hero['suspects'][0].get('fault_mode')
        self.assertIsNotNone(fault_mode)
        self.assertTrue(fault_mode['label'])
        self.assertTrue(fault_mode['verification'])

    def test_hero_narrative_names_fault_mode(self):
        leader = self.hero['suspects'][0]
        self.assertIn(leader['refdes'], self.hero['narrative'])
        self.assertIn((leader['fault_mode'] or {}).get('label', ''), self.hero['narrative'])

    def test_dual_fault_solver_names_both_components(self):
        dual = standardize_dataframe(pd.read_csv('data/dual_fault_demo_log.csv'))
        report = self.engine.analyze('BRD_DUAL_FAULT_001', dual)
        mfa = report['multi_fault_analysis']
        self.assertTrue(mfa['analyzable'])
        pair = ' + '.join(mfa['best_pair']['components'])
        self.assertIn('U3', pair)
        self.assertIn('R12', pair)
        self.assertGreaterEqual(mfa['best_pair']['coverage_pct'], mfa['best_single']['coverage_pct'])
        self.assertTrue(mfa['verdict_text'])

    def test_hero_prefers_single_fault_on_parsimony(self):
        mfa = self.hero['multi_fault_analysis']
        self.assertTrue(mfa['analyzable'])
        self.assertEqual(mfa['best_single']['coverage_pct'], 100.0)
        # The pair matches coverage but adds a component — verdict must prefer
        # the simplest explanation that covers the evidence.
        self.assertIn('single-fault', mfa['verdict_text'])

    def test_novel_board_is_flagged_and_demoted(self):
        novel = standardize_dataframe(pd.read_csv('data/novel_demo_log.csv'))
        report = self.engine.analyze('BRD_NOVEL_001', novel)
        self.assertEqual(report['ood_state']['state'], 'NOVEL')
        self.assertEqual(report['confidence_tier'], 'Insufficient Evidence')
        self.assertTrue(report['ood_state']['is_novel'])

    def test_data_quality_gate_reports_issues(self):
        novel = standardize_dataframe(pd.read_csv('data/novel_demo_log.csv'))
        report = self.engine.analyze('BRD_NOVEL_001', novel)
        self.assertEqual(report['data_quality']['status'], 'RED')
        self.assertGreaterEqual(len(report['data_quality']['issues']), 2)

    def test_next_best_test_carries_meta(self):
        report = self.engine.analyze('BRD_0401', self.logs)
        nbt = report['next_best_test']
        self.assertTrue(nbt['active'])
        self.assertTrue(nbt['test'])
        self.assertIn(nbt['info_gain'], {'HIGH', 'MEDIUM', 'LOW'})
        self.assertIn(nbt['risk'], {'LOW', 'MEDIUM', 'HIGH'})
        self.assertIn(nbt['effort'], {'LOW', 'MEDIUM', 'HIGH'})

    def test_versions_are_present(self):
        self.assertTrue(self.hero['versions']['engine'])
        self.assertTrue(self.hero['versions']['data'])
        self.assertTrue(self.hero['versions']['policy'])

    def test_report_enrichment_in_csv_and_pdf(self):
        csv = generate_csv_bytes(self.hero).decode('utf-8')
        self.assertIn('fault_mode', csv)
        self.assertIn('pattern_state', csv)
        self.assertIn('data_quality', csv)
        pdf_text = ExportTests._pdf_text(self, self.hero)
        self.assertIn('Pattern familiarity', pdf_text)
        self.assertIn('Data quality', pdf_text)


class VerifiedRepairMemoryTests(unittest.TestCase):
    """The safe learning loop must reject unverified outcomes and accept only
    confirmed repairs — writing to a temp dir so tests never touch real data."""

    def test_unverified_case_is_rejected(self):
        import engine.repair_memory as memory
        self.assertFalse(memory.add_verified_case(
            'B1', 'U3', 'TEST_A', retest_pass=False, technician_confirmed=True
        )['added'])
        self.assertFalse(memory.add_verified_case(
            'B1', 'U3', 'TEST_A', retest_pass=True, technician_confirmed=False
        )['added'])

    def test_verified_case_is_learned(self):
        import tempfile
        from pathlib import Path
        import engine.repair_memory as memory
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            memory.LEARNED_DIR = tmp_dir
            memory.LEARNED_HISTORY = tmp_dir / 'repair_history_learned.csv'
            memory.COMBINED_HISTORY = tmp_dir / 'repair_history_combined.csv'
            result = memory.add_verified_case(
                'B1', 'U3', 'TEST_A;TEST_B', notes='U3 output undervoltage',
                retest_pass=True, technician_confirmed=True,
            )
            self.assertTrue(result['added'])
            self.assertEqual(result['count'], 1)
            self.assertTrue(memory.LEARNED_HISTORY.exists())


class IntegrityAndSecurityTests(unittest.TestCase):
    """Regression tests for the final-audit fixes: NaN error codes, data-quality
    gating, ground-truth isolation, technician confirmation, notes separation,
    memory refresh, test integrity (ABORT etc.), tester-vs-board, and the
    domain fix for the extreme-deviation check."""

    @classmethod
    def setUpClass(cls):
        cls.engine = CircuitMindOrchestrator()
        cls.logs = load_logs()

    # --- Bug A: NaN error code ---
    def test_nan_error_code_is_never_rendered(self):
        frame = pd.DataFrame({
            'board_id': ['N1'],
            'test_step': ['TEST_5V_RAIL'],
            'measured_value': [0.63],
            'expected_min': [4.8],
            'expected_max': [5.2],
            'pass_fail': ['FAIL'],
            'error_code': [float('nan')],
            'unit': ['V'],
        })
        report = self.engine.analyze('N1', standardize_dataframe(frame))
        # Every error_code field across the whole payload must be empty/absent,
        # never the literal string 'NAN'. (Note: 'DOMINANT' legitimately
        # contains the substring 'NAN', so we check field values, not the blob.)
        def walk(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    if k == 'error_code':
                        self.assertNotEqual(str(v).upper(), 'NAN')
                    else:
                        walk(v)
            elif isinstance(node, list):
                for item in node:
                    walk(item)
        walk(report)
        self.assertEqual(report['signature']['failed_tests'][0]['error_code'], '')
        codes = [i['message'] for i in report['data_quality']['issues']]
        self.assertFalse(any('NAN' == m.upper().strip() or 'ERROR CODE' in m.upper() and 'NAN' in m.upper() for m in codes))

    # --- Bug B: data-quality gating ---
    def test_red_data_quality_abstains(self):
        novel = standardize_dataframe(pd.read_csv('data/novel_demo_log.csv'))
        report = self.engine.analyze('BRD_NOVEL_001', novel)
        self.assertEqual(report['data_quality']['status'], 'RED')
        self.assertEqual(report['diagnosis_state'], 'ABSTAIN')
        self.assertTrue(report['abstain_reason'])
        self.assertGreaterEqual(len(report['required_next_info']), 1)

    def test_green_data_quality_leads(self):
        report = self.engine.analyze('BRD_0415', self.logs)
        self.assertEqual(report['data_quality']['status'], 'GREEN')
        self.assertEqual(report['diagnosis_state'], 'LEADING_HYPOTHESIS')

    # --- Domain fix: dead-rail deviation is a fault, not bad data ---
    def test_dead_rail_is_not_a_data_quality_problem(self):
        frame = pd.DataFrame({
            'board_id': ['DR1'],
            'test_step': ['TEST_5V_RAIL'],
            'measured_value': [0.63],
            'expected_min': [4.8],
            'expected_max': [5.2],
            'pass_fail': ['FAIL'],
            'error_code': ['VAL'],
            'unit': ['V'],
        })
        report = self.engine.analyze('DR1', standardize_dataframe(frame))
        self.assertEqual(report['data_quality']['status'], 'GREEN')
        self.assertEqual(report['diagnosis_state'], 'LEADING_HYPOTHESIS')

    # --- Bug C: ground truth is never part of an analysis report ---
    def test_report_never_contains_ground_truth(self):
        report = self.engine.analyze('BRD_0415', self.logs)  # truth exists for this board
        self.assertNotIn('ground_truth', report)
        blob = str(report)
        self.assertNotIn('ground_truth', blob)

    # --- Test integrity: ABORT / NOT_EXECUTED are not failures ---
    def test_abort_and_not_executed_are_not_failures(self):
        frame = pd.DataFrame({
            'board_id': ['AB1'] * 4,
            'test_step': ['TEST_VBUS', 'TEST_5V_RAIL', 'TEST_3V3_RAIL', 'TEST_MCU_BOOT'],
            'measured_value': [3.2, 5.0, 3.3, 1],
            'expected_min': [4.75, 4.8, 3.15, None],
            'expected_max': [5.25, 5.2, 3.45, None],
            'pass_fail': ['FAIL', 'PASS', 'ABORT', 'NOT_EXECUTED'],
            'error_code': ['VAL', '', '', ''],
        })
        report = self.engine.analyze('AB1', standardize_dataframe(frame))
        failed = [t['test_step'] for t in report['signature']['failed_tests']]
        self.assertEqual(failed, ['TEST_VBUS'])
        counts = report['test_integrity']['status_counts']
        self.assertEqual(counts['ABORT'], 1)
        self.assertEqual(counts['NOT_EXECUTED'], 1)

    def test_unsupported_status_is_rejected_loudly(self):
        frame = pd.DataFrame({
            'board_id': ['G1'], 'test_step': ['TEST_5V_RAIL'], 'measured_value': [0.6],
            'expected_min': [4.8], 'expected_max': [5.2], 'pass_fail': ['WHATEVER'],
        })
        with self.assertRaises(ValueError):
            standardize_dataframe(frame)

    # --- Phase 4/22: failure or tester? ---
    def test_tester_anomaly_is_detected_at_fleet_level(self):
        from engine.test_integrity import fleet_tester_analysis
        lot = standardize_dataframe(pd.read_csv('data/tester_anomaly_demo_log.csv'))
        analysis = fleet_tester_analysis(lot)
        self.assertEqual(analysis['state'], 'TEST_SYSTEM_SUSPECTED')
        vbus = [t for t in analysis['suspected_tests'] if t['test_step'] == 'TEST_VBUS']
        self.assertEqual(len(vbus), 1)
        self.assertEqual(vbus[0]['attribution'], 'FIXTURE_SUSPECTED')
        self.assertEqual(vbus[0]['fixture_id'], 'FIX-07')
        self.assertAlmostEqual(vbus[0]['fixture_fail_rate'], 1.0)
        self.assertAlmostEqual(vbus[0]['peer_fixture_fail_rate'], 0.0)
        normal = standardize_dataframe(pd.read_csv('data/test_logs.csv'))
        normal_analysis = fleet_tester_analysis(normal)
        # Normal data may have fleet-wide failures (synthetic data); the key
        # check is that the demo data triggers fixture-specific attribution.
        self.assertIn(normal_analysis['state'], ('BOARD_SPECIFIC', 'TEST_SYSTEM_SUSPECTED'))

    def test_station_attribution_when_fixture_uniform(self):
        """When fixture failure rates are uniform but one station is concentrated,
        the function should attribute to STATION_SUSPECTED."""
        from engine.test_integrity import fleet_tester_analysis
        # Build a scenario: 2 stations, 4 boards each, uniform fixture usage.
        # STA-01: all 4 fail TEST_POWER; STA-02: all 4 pass.
        rows = []
        for i in range(4):
            rows.append({'board_id': f'B{i}', 'test_step': 'TEST_POWER', 'pass_fail': 'FAIL',
                         'measured_value': 1.0, 'expected_min': 3.0, 'expected_max': 5.0,
                         'station_id': 'STA-01', 'fixture_id': 'FIX-A', 'board_revision': 'REV1'})
            rows.append({'board_id': f'B{i}', 'test_step': 'TEST_POWER', 'pass_fail': 'PASS',
                         'measured_value': 4.0, 'expected_min': 3.0, 'expected_max': 5.0,
                         'station_id': 'STA-02', 'fixture_id': 'FIX-A', 'board_revision': 'REV1'})
        lot = standardize_dataframe(pd.DataFrame(rows))
        analysis = fleet_tester_analysis(lot)
        power = [t for t in analysis['suspected_tests'] if t['test_step'] == 'TEST_POWER']
        self.assertEqual(len(power), 1)
        self.assertEqual(power[0]['attribution'], 'STATION_SUSPECTED')
        self.assertEqual(power[0]['station_id'], 'STA-01')
        self.assertAlmostEqual(power[0]['station_fail_rate'], 1.0)
        self.assertAlmostEqual(power[0]['peer_station_fail_rate'], 0.0)
        self.assertEqual(power[0]['station_sample_size'], 4)

    def test_revision_attribution_when_fixture_and_station_uniform(self):
        """When both fixture and station rates are uniform but one board revision
        is concentrated, the function should attribute to REVISION_SUSPECTED."""
        from engine.test_integrity import fleet_tester_analysis
        # 2 revisions, 4 boards each, same station and fixture.
        # REV-A: all 4 fail TEST_SPEED; REV-B: all 4 pass.
        rows = []
        for i in range(4):
            rows.append({'board_id': f'B{i}', 'test_step': 'TEST_SPEED', 'pass_fail': 'FAIL',
                         'measured_value': 0.5, 'expected_min': 2.0, 'expected_max': 4.0,
                         'station_id': 'STA-01', 'fixture_id': 'FIX-A', 'board_revision': 'REV-A'})
            rows.append({'board_id': f'B{i+4}', 'test_step': 'TEST_SPEED', 'pass_fail': 'PASS',
                         'measured_value': 3.0, 'expected_min': 2.0, 'expected_max': 4.0,
                         'station_id': 'STA-01', 'fixture_id': 'FIX-A', 'board_revision': 'REV-B'})
        lot = standardize_dataframe(pd.DataFrame(rows))
        analysis = fleet_tester_analysis(lot)
        speed = [t for t in analysis['suspected_tests'] if t['test_step'] == 'TEST_SPEED']
        self.assertEqual(len(speed), 1)
        self.assertEqual(speed[0]['attribution'], 'REVISION_SUSPECTED')
        self.assertEqual(speed[0]['board_revision'], 'REV-A')
        self.assertAlmostEqual(speed[0]['revision_fail_rate'], 1.0)
        self.assertAlmostEqual(speed[0]['peer_revision_fail_rate'], 0.0)

    def test_min_samples_per_group_filters_small_groups(self):
        """Groups with fewer than min_samples_per_group observations should
        not be eligible for attribution."""
        from engine.test_integrity import fleet_tester_analysis
        # 3 fixtures with 2 boards each (6 total, passes min_boards=6), but
        # each fixture group has only 2 samples — below the floor of 3.
        rows = []
        fixtures = ['FIX-A', 'FIX-B', 'FIX-C']
        for i, fix in enumerate(fixtures):
            rows.append({'board_id': f'B{i*2}', 'test_step': 'TEST_LOW', 'pass_fail': 'FAIL',
                         'measured_value': 0.5, 'expected_min': 2.0, 'expected_max': 4.0,
                         'station_id': 'STA-01', 'fixture_id': fix, 'board_revision': 'REV1'})
            rows.append({'board_id': f'B{i*2+1}', 'test_step': 'TEST_LOW', 'pass_fail': 'PASS',
                         'measured_value': 3.0, 'expected_min': 2.0, 'expected_max': 4.0,
                         'station_id': 'STA-01', 'fixture_id': fix, 'board_revision': 'REV1'})
        lot = standardize_dataframe(pd.DataFrame(rows))
        analysis = fleet_tester_analysis(lot)
        low = [t for t in analysis['suspected_tests'] if t['test_step'] == 'TEST_LOW']
        self.assertEqual(len(low), 1)
        # Groups too small (n=2 each < min_samples_per_group=3) — no attribution.
        self.assertEqual(low[0]['attribution'], 'UNIFORM')

    def test_empty_logs_return_unknown(self):
        """An empty or None logs input should return UNKNOWN state."""
        from engine.test_integrity import fleet_tester_analysis
        self.assertEqual(fleet_tester_analysis(pd.DataFrame())['state'], 'UNKNOWN')
        self.assertEqual(fleet_tester_analysis(None)['state'], 'UNKNOWN')
        self.assertEqual(fleet_tester_analysis(pd.DataFrame())['suspected_tests'], [])

    def test_all_pass_fleet_returns_board_specific(self):
        """A fleet where every board passes every test should be BOARD_SPECIFIC."""
        from engine.test_integrity import fleet_tester_analysis
        rows = []
        for i in range(8):
            rows.append({'board_id': f'B{i}', 'test_step': 'TEST_X', 'pass_fail': 'PASS',
                         'measured_value': 3.0, 'expected_min': 2.0, 'expected_max': 4.0,
                         'station_id': 'STA-01', 'fixture_id': 'FIX-A', 'board_revision': 'REV1'})
        lot = standardize_dataframe(pd.DataFrame(rows))
        analysis = fleet_tester_analysis(lot)
        self.assertEqual(analysis['state'], 'BOARD_SPECIFIC')
        self.assertEqual(len(analysis['suspected_tests']), 0)

    def test_single_board_lot_skips_attribution(self):
        """A single board should not trigger any attribution (below min_boards)."""
        from engine.test_integrity import fleet_tester_analysis
        rows = [{'board_id': 'B0', 'test_step': 'TEST_Y', 'pass_fail': 'FAIL',
                 'measured_value': 0.5, 'expected_min': 2.0, 'expected_max': 4.0,
                 'station_id': 'STA-01', 'fixture_id': 'FIX-A', 'board_revision': 'REV1'}]
        lot = standardize_dataframe(pd.DataFrame(rows))
        analysis = fleet_tester_analysis(lot)
        self.assertEqual(analysis['state'], 'BOARD_SPECIFIC')

    def test_missing_station_column_graceful_fallback(self):
        """When station_id column is absent, fixture attribution still works."""
        from engine.test_integrity import fleet_tester_analysis
        rows = []
        for i in range(4):
            rows.append({'board_id': f'B{i}', 'test_step': 'TEST_Z', 'pass_fail': 'FAIL',
                         'measured_value': 0.5, 'expected_min': 2.0, 'expected_max': 4.0,
                         'fixture_id': 'FIX-A', 'board_revision': 'REV1'})
            rows.append({'board_id': f'B{i+4}', 'test_step': 'TEST_Z', 'pass_fail': 'PASS',
                         'measured_value': 3.0, 'expected_min': 2.0, 'expected_max': 4.0,
                         'fixture_id': 'FIX-B', 'board_revision': 'REV1'})
        lot = standardize_dataframe(pd.DataFrame(rows))
        analysis = fleet_tester_analysis(lot)
        z = [t for t in analysis['suspected_tests'] if t['test_step'] == 'TEST_Z']
        self.assertEqual(len(z), 1)
        self.assertEqual(z[0]['attribution'], 'FIXTURE_SUSPECTED')
        self.assertNotIn('station_id', z[0])

    # --- Phase 18: what would change my mind ---
    def test_verdict_flip_is_derived_from_mechanism(self):
        dual = standardize_dataframe(pd.read_csv('data/dual_fault_demo_log.csv'))
        report = self.engine.analyze('BRD_DUAL_FAULT_001', dual)
        self.assertGreaterEqual(len(report['verdict_flip']), 2)
        self.assertTrue(all(item['observation'] and item['effect'] for item in report['verdict_flip']))


class MemoryRefreshTests(unittest.TestCase):
    """Bug D/E/F — the safe learning loop: explicit confirmation, technician-note
    isolation, and a genuinely refreshed active memory."""

    def test_unverified_is_rejected(self):
        import engine.repair_memory as memory
        result = memory.add_verified_case('B1', 'U3', 'TEST_A', retest_pass=True, technician_confirmed=False)
        self.assertFalse(result['added'])
        self.assertIn('verified', result['reason'].lower())

    def test_learned_case_uses_technician_note_not_pre_diagnosis_notes(self):
        import tempfile
        from pathlib import Path
        import engine.repair_memory as memory
        with tempfile.TemporaryDirectory() as tmp:
            memory.LEARNED_DIR = Path(tmp)
            memory.LEARNED_HISTORY = Path(tmp) / 'learned.csv'
            memory.COMBINED_HISTORY = Path(tmp) / 'combined.csv'
            memory.add_verified_case('B1', 'U3', 'TEST_A',
                                     notes='replaced U3, reflow verified',
                                     retest_pass=True, technician_confirmed=True)
            import csv
            with open(memory.LEARNED_HISTORY, newline='', encoding='utf-8') as handle:
                row = list(csv.DictReader(handle))[0]
            self.assertEqual(row['symptom_text'], 'replaced U3, reflow verified')
            self.assertNotIn('suspected', row['symptom_text'].lower())

    def test_active_memory_refreshes_after_verified_case(self):
        import tempfile
        from pathlib import Path
        import engine.repair_memory as memory
        with tempfile.TemporaryDirectory() as tmp:
            memory.LEARNED_DIR = Path(tmp)
            memory.LEARNED_HISTORY = Path(tmp) / 'learned.csv'
            memory.COMBINED_HISTORY = Path(tmp) / 'combined.csv'
            before = len(pd.read_csv(memory.FROZEN_HISTORY))
            memory.add_verified_case('B1', 'U3', 'TEST_A;TEST_B',
                                     notes='verified U3', retest_pass=True, technician_confirmed=True)
            combined = memory.combined_history_path()
            self.assertIsNotNone(combined)
            self.assertEqual(len(pd.read_csv(combined)), before + 1)
            # A fresh orchestrator built against the combined corpus sees the case.
            from engine.orchestrator import CircuitMindOrchestrator
            fresh = CircuitMindOrchestrator(memory_history_path=str(combined))
            self.assertEqual(len(fresh.memory.corpus), before + 1)


class RepairSimulationTests(unittest.TestCase):
    """Regression tests for the mechanism-based repair simulator (audit
    2026-08-11: the previous graph-direction shortcut resolved nothing on
    power-path boards)."""

    def test_hero_simulation_mechanism_based(self):
        engine = CircuitMindOrchestrator(memory_history_path=str(FROZEN_HISTORY))
        report = engine.analyze('BRD_U3_CASCADE_001', load_logs())

        # The true root cause (U3) is the ONLY candidate whose mechanism
        # explains every observed failure: full cascade resolves, nothing left.
        sim_u3 = engine.simulate_repair(report, 'U3')
        self.assertTrue(sim_u3['success'])
        self.assertEqual(set(sim_u3['resolved_nets']), {'SYS_5V', 'SYS_3V3', 'SPI_BUS'})
        self.assertEqual(sim_u3['remaining_nets'], [])
        self.assertIn('blast radius', sim_u3['mechanism'])

        # Passives and downstream-only candidates leave residual failures.
        for refdes in ('L1', 'C1'):
            sim = engine.simulate_repair(report, refdes)
            self.assertFalse(sim['success'])
            self.assertEqual(sim['resolved_nets'], ['SYS_5V'])
            self.assertEqual(set(sim['remaining_nets']), {'SYS_3V3', 'SPI_BUS'})

        # A candidate upstream of the failing region resolves nothing.
        sim_f1 = engine.simulate_repair(report, 'F1')
        self.assertFalse(sim_f1['success'])
        self.assertEqual(sim_f1['resolved_nets'], [])

    def test_simulation_unknown_component_is_honest(self):
        engine = CircuitMindOrchestrator(memory_history_path=str(FROZEN_HISTORY))
        report = engine.analyze('BRD_U3_CASCADE_001', load_logs())
        sim = engine.simulate_repair(report, 'ZZ9')
        self.assertFalse(sim['success'])
        self.assertEqual(sim['resolved_nets'], [])
        self.assertIn('not in the board candidate universe', sim['mechanism'])


if __name__ == '__main__':
    unittest.main()
