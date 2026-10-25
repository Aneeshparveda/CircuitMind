"""Generate the RESERVE test set — the final untouched evaluation split.

The reserve set uses the exact same scenarios/expected values as the main
generator (single source of truth in ``data/generate_synthetic.py``) but a
NEW seed and a NEW board-id range (BRD_0500–BRD_0599), so no board here has
ever been seen by training, validation, or the retrieval corpus.

The reserve boards are written to SEPARATE files:
  data/test_logs_reserve.csv
  validation/ground_truth_reserve.csv
They are never appended to ``data/test_logs.csv``, so the shipped pattern-signal
statistics and retrieval corpus contain zero reserve boards.

Deterministic: seed 20260731, fixed scenario mix.
Run: python3 validation/make_reserve_set.py
"""

import os
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data.generate_synthetic import SCENARIOS, EXPECTED  # noqa: E402

RESERVE_SEED = 20260731
N_BOARDS = 100
ID_START = 500  # BRD_0500 ... BRD_0599 — never used by the main splits


def make_reserve_set():
    random.seed(RESERVE_SEED)
    np.random.seed(RESERVE_SEED)

    test_logs = []
    ground_truth = []
    for i in range(N_BOARDS):
        board_id = f"BRD_{ID_START + i:04d}"
        scenario = random.choice(SCENARIOS)
        ground_truth.append({
            'board_id': board_id,
            'root_cause': scenario['root'],
            'scenario': scenario['name'],
            'split': 'reserve',
        })
        for step, (ex_min, ex_max, unit) in EXPECTED.items():
            if step in scenario['tests']:
                fail_min, fail_max, err_code = scenario['tests'][step]
                meas = random.uniform(fail_min, fail_max)
                status = 'FAIL'
            else:
                meas = random.uniform(ex_min, ex_max)
                status = 'PASS'
                err_code = ''
            test_logs.append({
                'board_id': board_id,
                'test_step': step,
                'measured_value': meas,
                'expected_min': ex_min,
                'expected_max': ex_max,
                'unit': unit,
                'pass_fail': status,
                'error_code': err_code,
            })

    df_logs = pd.DataFrame(test_logs)
    df_logs.to_csv(ROOT / 'data' / 'test_logs_reserve.csv', index=False)
    pd.DataFrame(ground_truth).to_csv(ROOT / 'validation' / 'ground_truth_reserve.csv', index=False)
    print(f"Reserve set written: {N_BOARDS} boards (seed {RESERVE_SEED}, BRD_{ID_START:04d}+).")
    print(f"  data/test_logs_reserve.csv + validation/ground_truth_reserve.csv")
    print("  (kept separate from data/test_logs.csv — never seen by the shipped system)")


if __name__ == '__main__':
    make_reserve_set()
