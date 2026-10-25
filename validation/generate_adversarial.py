"""Deterministic adversarial + OOD case generator.

Builds a small, seeded benchmark of deliberately hostile cases from the
existing blind board corpus:

  noise        — jittered measured values on failing tests
  unknown_test — failing steps renamed to names outside the test map
  novel_code   — error codes replaced with unrecognized codes
  missing_value— some failing measurements dropped (NaN)
  multi_fault  — two independent scenario signatures merged on one board
  ood          — entirely novel test steps + codes with no historical match

Every mutation uses ``SEED`` so the set is fully reproducible. Nothing in the
frozen corpus is modified; outputs land in ``validation/adversarial/``.
"""

import os
import random
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 2026
ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "validation" / "adversarial"

NOVEL_CODES = ['ERR_701', 'ERR_724', 'ERR_755', 'ERR_780']
OOD_STEPS = ['TEST_QUANTUM_DRIFT', 'TEST_NEURAL_ACCEL', 'TEST_OPTICAL_LINK', 'TEST_CRYO_BIAS']
DROP_FROM_BOM = ['Y1', 'U7', 'R2', 'R13', 'J2']  # none are root causes in the 15 scenarios


def _pick_blind_boards(ground_truth: pd.DataFrame, count: int, offset: int, step: int = 7) -> pd.DataFrame:
    """Deterministically pick ``count`` blind boards (stepped by ``step``)."""
    candidates = ground_truth[ground_truth['split'] == 'blind'].reset_index(drop=True)
    idxs = list(range(offset, len(candidates), step))[:count]
    return candidates.iloc[idxs]


def _board_logs(logs: pd.DataFrame, board_id: str) -> pd.DataFrame:
    return logs[logs['board_id'] == board_id].copy()


def generate() -> pd.DataFrame:
    rng = random.Random(SEED)
    np_rng = np.random.default_rng(SEED)
    os.makedirs(OUT_DIR, exist_ok=True)

    logs = pd.read_csv(ROOT / 'data' / 'test_logs.csv')
    truth = pd.read_csv(ROOT / 'validation' / 'ground_truth_blind.csv')
    truth_all = pd.read_csv(ROOT / 'validation' / 'ground_truth_train.csv')
    truth_all = pd.concat([
        truth_all,
        pd.read_csv(ROOT / 'validation' / 'ground_truth_val.csv'),
        truth,
    ], ignore_index=True)
    by_id = {str(row.board_id): row.root_cause for row in truth_all.itertuples(index=False)}

    rows = []
    meta = []
    base = _pick_blind_boards(truth, count=10, offset=0)

    def emit(board_id: str, mutation: str, truth_label: str, frame: pd.DataFrame):
        nonlocal rows, meta
        new_id = f"ADV_{mutation.upper()}_{len(meta) + 1:03d}"
        frame = frame.copy()
        frame['board_id'] = new_id
        rows.append(frame)
        meta.append({'board_id': new_id, 'perturbation': mutation, 'truth': truth_label, 'source': board_id})

    # 1. noise — jitter failing measurements by +/-15% of the window.
    for i, b in enumerate(base.iterrows()):
        bid = str(b[1].board_id)
        frame = _board_logs(logs, bid)
        failing = frame['pass_fail'].str.upper() == 'FAIL'
        frame.loc[failing, 'measured_value'] = frame.loc[failing, 'measured_value'].apply(
            lambda v: v if pd.isna(v) else float(v) * (1 + rng.uniform(-0.15, 0.15))
        )
        emit(bid, 'noise', by_id.get(bid, ''), frame)

    # 2. unknown_test — rename failing steps outside the test map.
    for i, b in enumerate(base.iterrows()):
        bid = str(b[1].board_id)
        frame = _board_logs(logs, bid)
        failing = frame['pass_fail'].str.upper() == 'FAIL'
        steps = frame.loc[failing, 'test_step'].unique()
        rename = {step: f"TEST_UNK_{i}_{j}" for j, step in enumerate(steps)}
        frame.loc[failing, 'test_step'] = frame.loc[failing, 'test_step'].map(rename)
        emit(bid, 'unknown_test', by_id.get(bid, ''), frame)

    # 3. novel_code — replace error codes with unrecognized codes.
    for i, b in enumerate(base.iterrows()):
        bid = str(b[1].board_id)
        frame = _board_logs(logs, bid)
        failing = frame['pass_fail'].str.upper() == 'FAIL'
        frame.loc[failing, 'error_code'] = rng.choice(NOVEL_CODES)
        emit(bid, 'novel_code', by_id.get(bid, ''), frame)

    # 4. missing_value — drop some failing measurements.
    for i, b in enumerate(base.iterrows()):
        bid = str(b[1].board_id)
        frame = _board_logs(logs, bid)
        failing = frame['pass_fail'].str.upper() == 'FAIL'
        drop = rng.sample(list(frame.loc[failing].index), k=min(2, int(failing.sum())))
        frame.loc[drop, 'measured_value'] = np.nan
        emit(bid, 'missing_value', by_id.get(bid, ''), frame)

    # 4b. missing_bom — boards evaluated with a reduced BOM (5 non-root-cause
    #     components removed from components.csv at benchmark time).
    for i, b in enumerate(base.iterrows()):
        bid = str(b[1].board_id)
        frame = _board_logs(logs, bid)
        emit(bid, 'missing_bom', by_id.get(bid, ''), frame)

    # 5. multi_fault — merge a U3-family board and an R12-family board. The
    # second board's FAIL row must override the first board's PASS row for the
    # same test step (keep='last' after concat).
    u3_boards = _pick_blind_boards(truth[truth['root_cause'] == 'U3'], count=6, offset=0, step=1)
    r12_boards = _pick_blind_boards(truth[truth['root_cause'] == 'R12'], count=6, offset=0, step=1)
    for i, (b1, b2) in enumerate(zip(u3_boards.iterrows(), r12_boards.iterrows())):
        f1 = _board_logs(logs, str(b1[1].board_id))
        f2 = _board_logs(logs, str(b2[1].board_id))
        merged = pd.concat([f1, f2[f2['pass_fail'].str.upper() == 'FAIL']], ignore_index=True)
        merged = merged.drop_duplicates(subset='test_step', keep='last')
        emit(str(b1[1].board_id), 'multi_fault', f"MULTI:{b1[1].root_cause}+{b2[1].root_cause}", merged)

    # 6. ood — entirely novel steps + novel codes, no historical match.
    expected = {
        'TEST_VBUS': (4.75, 5.25), 'TEST_FUSE': (4.70, 5.20), 'TEST_5V_RAIL': (4.8, 5.2),
        'TEST_3V3_RAIL': (3.2, 3.4), 'TEST_MCU_BOOT': (1, 1), 'TEST_SPI_FLASH': (1, 1),
        'TEST_WIFI_ENUM': (1, 1), 'TEST_RF_POWER': (15, 20), 'TEST_I2C_BUS': (1, 1),
        'TEST_THERMISTOR': (2.0, 2.5), 'TEST_MOTOR_PWM': (1, 1),
    }
    for i in range(10):
        rows_ood = []
        # Fail mostly on NOVEL test steps (unknown to the map/corpus), with a
        # couple of known steps — the signature should NOT match any family.
        novel_fail = rng.sample(OOD_STEPS, k=4)
        known_fail = rng.sample(list(expected.keys()), k=2)
        for step, (lo, hi) in expected.items():
            fail = step in known_fail
            code = rng.choice(NOVEL_CODES) if fail else ''
            rows_ood.append({
                'board_id': f"ADV_OOD_{i:03d}",
                'test_step': step,
                'measured_value': rng.uniform(0.1, 2.5) if fail else rng.uniform(lo, hi),
                'expected_min': lo, 'expected_max': hi, 'unit': 'V' if hi > 1 else 'bool',
                'pass_fail': 'FAIL' if fail else 'PASS', 'error_code': code,
            })
        for step in novel_fail:
            rows_ood.append({
                'board_id': f"ADV_OOD_{i:03d}",
                'test_step': step,
                'measured_value': 0.0, 'expected_min': 0.5, 'expected_max': 1.5,
                'unit': 'V', 'pass_fail': 'FAIL', 'error_code': rng.choice(NOVEL_CODES),
            })
        frame = pd.DataFrame(rows_ood)
        emit('OOD', 'ood', 'NONE', frame)

    logs_out = pd.concat(rows, ignore_index=True, sort=False)
    logs_out.to_csv(OUT_DIR / 'logs.csv', index=False)
    pd.DataFrame(meta).to_csv(OUT_DIR / 'ground_truth.csv', index=False)
    print(f"Adversarial set generated: {len(meta)} boards -> {OUT_DIR}")
    return pd.DataFrame(meta)


if __name__ == '__main__':
    generate()
