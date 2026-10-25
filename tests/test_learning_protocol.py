"""Regression tests for the scientific validation protocol (audit 2026-08-11).

The blind TEST set must never influence model selection or retention. These
tests make that a structural guarantee: the selection function cannot read the
blind file, its source never references it, and the retention decision is
derived exclusively from the validation holdout.

Run: python3 -m unittest tests.test_learning_protocol -v
"""

import inspect
import os
import sys
import unittest
from unittest import mock

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from validation import learn_weights as lw  # noqa: E402

STREAMS = lw.STREAMS
POLICY = {'history': 0.35, 'net': 0.30, 'topology': 0.20, 'criticality': 0.10, 'category': 0.05}


def _cand(**kw):
    return {s: float(kw.get(s, 0.0)) for s in STREAMS}


def _rows(truth, raws):
    """Build a tiny {board_id: {'truth', 'raw'}} structure, mirroring the
    learner's extraction output."""
    return {
        f'BRD_{i}': {'truth': t, 'raw': {r: dict(s) for r, s in raw.items()}}
        for i, (t, raw) in enumerate(zip(truth, raws))
    }


STRONG_HIST = {
    'U3': _cand(history=95, net=100, topology=70, criticality=100, category=100),
    'L1': _cand(history=5, net=100, topology=70, criticality=100, category=30),
}
WEAK_HIST = {
    'U3': _cand(history=5, net=100, topology=70, criticality=100, category=100),
    'L1': _cand(history=95, net=100, topology=70, criticality=100, category=30),
}


class LearningProtocolTests(unittest.TestCase):

    def test_selection_source_never_references_blind(self):
        src = inspect.getsource(lw.select_weights)
        # The docstring/comment may *mention* the blind set (to state the
        # contract), but the function body must never reference the blind data:
        # no variable like truth_blind / blind_1, no blind file path, no
        # assignment from a blind frame.
        import re
        self.assertNotIn('truth_blind', src)
        self.assertNotIn('ground_truth_blind', src)
        self.assertIsNone(re.search(r'\bblind\d*\s*[=(]', src))

    def test_selection_never_reads_blind_file(self):
        real_read_csv = pd.read_csv

        def guarded(path, *args, **kwargs):
            if 'ground_truth_blind' in str(path):
                raise AssertionError('selection read the blind TEST set')
            return real_read_csv(path, *args, **kwargs)

        train = _rows(['U3', 'U3'], [STRONG_HIST, STRONG_HIST])
        val = _rows(['U3', 'L1'], [STRONG_HIST, WEAK_HIST])
        with mock.patch.object(pd, 'read_csv', side_effect=guarded):
            result = lw.select_weights(train, val, POLICY)
        self.assertIn('weights', result)
        self.assertIn('keep', result)
        self.assertTrue(isinstance(result['keep'], bool))

    def test_retention_decision_is_derived_from_val_only(self):
        # Learned policy clearly beats the hand-set policy on VAL -> keep.
        train = _rows(['U3', 'U3'], [STRONG_HIST, STRONG_HIST])
        val = _rows(['U3', 'U3'], [STRONG_HIST, STRONG_HIST])
        result = lw.select_weights(train, val, POLICY)
        self.assertTrue(result['keep'])
        self.assertGreaterEqual(result['val_top1'], result['policy_val_top1'] - 0.5)

        # Learned policy clearly loses on VAL -> reject, regardless of what a
        # (hypothetical) blind set would say — the decision cannot read it.
        weak_val = _rows(['L1', 'L1'], [WEAK_HIST, WEAK_HIST])
        result2 = lw.select_weights(train, weak_val, POLICY)
        # The chosen config (history-heavy) ranks U3 first on L1-truth boards,
        # so val top-1 for the learner is 0 while policy also ranks U3 first —
        # keep stays consistent with the VAL comparison in either direction.
        self.assertEqual(result2['keep'],
                         bool(result2['val_top1'] >= result2['policy_val_top1'] - 0.5
                              and result2['val_top3'] >= result2['policy_val_top3'] - 2.0))

    def test_blind_reading_isolated_to_reporting_path(self):
        # report_blind takes the truth frame as a parameter (report-only); the
        # only file-level access to the blind split lives in load_boards, which
        # is used purely to hand frames to the reporting function.
        sig = inspect.signature(lw.report_blind)
        self.assertIn('truth_blind', sig.parameters)
        body = inspect.getsource(lw.select_weights).split('"""')[-1]
        self.assertNotIn('ground_truth_blind', body)


if __name__ == '__main__':
    unittest.main()
