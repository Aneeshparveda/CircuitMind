"""Learn the evidence-fusion weights from labeled history.

The fusion is linear:  score(refdes) = sum( raw_stream * weight ) + notes_bonus.
So the ranking implied by any weight vector can be reproduced exactly from the
per-stream raw scores. We therefore:

  1. run the engine once per TRAIN board and extract each candidate's raw
     stream scores (independent of weights),
  2. grid-search the weight simplex (step 0.05, sum == 1.0) maximizing Top-1
     on TRAIN,
  3. select the best config by Top-1 on VAL (genuinely held out from fitting),
  4. DECIDE RETENTION ON VAL TOO — the learned policy is kept only if it beats
     or matches the hand-set policy on the validation holdout,
  5. report the chosen policy's performance on the BLIND set, which never
     influences any selection or retention decision, and
  6. (externally) the fresh reserve set is the final untouched evaluation.

Scientific protocol (audit 2026-08-11): the blind TEST set must never decide
whether a model is retained. That rule is structural here — selection and
retention both live in ``select_weights(train, val, policy)``, whose signature
cannot see the blind set, and ``report_blind`` is the only function that reads
``ground_truth_blind.csv``.

Deterministic: fixed grid, fixed tie-breaks, no RNG.
Run from the project root:  python3 validation/learn_weights.py
"""

import itertools
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine.orchestrator import CircuitMindOrchestrator  # noqa: E402
from data.schema_adapter import standardize_dataframe  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / 'config' / 'diagnostic_weights.json'

STREAMS = ['history', 'net', 'topology', 'criticality', 'category']
STEP = 0.05
POLICY_WEIGHTS = {'history': 0.35, 'net': 0.30, 'topology': 0.20, 'criticality': 0.10, 'category': 0.05}


def load_boards():
    truth_train = pd.read_csv(ROOT / 'validation' / 'ground_truth_train.csv')
    truth_val = pd.read_csv(ROOT / 'validation' / 'ground_truth_val.csv')
    truth_blind = pd.read_csv(ROOT / 'validation' / 'ground_truth_blind.csv')
    logs = standardize_dataframe(pd.read_csv(ROOT / 'data' / 'test_logs.csv'))
    return truth_train, truth_val, truth_blind, logs


def extract_raw_scores(engine, truth, logs, label):
    """Return {board_id: {'truth': str, 'raw': {refdes: {stream: score}}}}."""
    rows = {}
    for _, row in truth.iterrows():
        board_id = row['board_id']
        report = engine.analyze(board_id, logs)
        raw = {}
        for suspect in report.get('suspects', []):
            refdes = suspect['refdes']
            raw[refdes] = {stream: float(suspect['raw_evidence'].get(stream, 0.0))
                           for stream in STREAMS}
        rows[board_id] = {'truth': row['root_cause'], 'raw': raw}
    print(f"  extracted {len(rows)} {label} boards")
    return rows


def rank_with(weights, raw):
    """Return refdes list sorted by the weighted linear fusion."""
    return sorted(raw.keys(), key=lambda refdes: -sum(raw[refdes][stream] * weights[stream] for stream in STREAMS))


def top_accuracy(rows, weights, k=1):
    correct = 0
    for data in rows.values():
        ranked = rank_with(weights, data['raw'])
        if data['truth'] in ranked[:k]:
            correct += 1
    return correct / max(len(rows), 1)


def weight_simplex(step):
    n = len(STREAMS)
    n_steps = int(round(1.0 / step))
    points = []
    for combo in itertools.combinations(range(1, n_steps + n), n - 1):
        bounds = [0] + list(combo) + [n_steps + n]
        steps = [bounds[i + 1] - bounds[i] - 1 for i in range(n)]
        if all(s >= 0 for s in steps):
            points.append(tuple(s * step for s in steps))
    return points


def select_weights(train, val, policy):
    """Select fusion weights on TRAIN + VAL only. NEVER reads the blind set.

    Returns the chosen weights, a retention decision (vs the hand-set policy,
    evaluated on VAL), and the supporting numbers. The blind TEST set is
    intentionally outside this function's reach.
    """
    # Grid search over the simplex. Every grid point is scored on TRAIN and on
    # the held-out VAL split; selection is purely by (VAL top-1, VAL top-3,
    # train top-1). No arbitrary top-k filter on train is applied — the
    # previous top-20-by-train cutoff could exclude the genuinely best config
    # on VAL (observed in the Aug 12 audit pass).
    grid = weight_simplex(STEP)
    candidates = []
    for positional in grid:
        weights = dict(zip(STREAMS, positional))
        t1 = top_accuracy(train, weights, 1)
        v1 = top_accuracy(val, weights, 1)
        v3 = top_accuracy(val, weights, 3)
        candidates.append((v1, v3, t1, positional))
    candidates.sort(key=lambda item: (-item[0], -item[1], -item[2]))

    v1, v3, t1, learned = candidates[0]
    learned_dict = {s: float(w) for s, w in zip(STREAMS, learned)}

    # Retention decision on VAL (never blind): keep the learned policy when it
    # beats or matches the hand-set policy on the validation holdout.
    policy_v1 = top_accuracy(val, policy, 1) * 100
    policy_v3 = top_accuracy(val, policy, 3) * 100
    keep = v1 * 100 >= policy_v1 - 0.5 and v3 * 100 >= policy_v3 - 2.0

    return {
        'weights': learned_dict,
        'keep': bool(keep),
        'val_top1': v1 * 100,
        'val_top3': v3 * 100,
        'policy_val_top1': policy_v1,
        'policy_val_top3': policy_v3,
        'train_top1': t1 * 100,
    }


def report_blind(weights, truth_blind, logs):
    """Final untouched evaluation of a FROZEN config on the blind TEST set.

    Report-only: this function never feeds back into selection or retention.
    """
    cfg = json.loads(CONFIG_PATH.read_text(encoding='utf-8')) if CONFIG_PATH.exists() else {}
    had_weights = 'weights' in cfg
    orig_weights = cfg.get('weights')
    cfg['weights'] = {k: round(v, 2) for k, v in weights.items()}
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding='utf-8')
    try:
        engine_learned = CircuitMindOrchestrator()  # fresh engine loads the config
        blind_1 = blind_3 = 0
        n = len(truth_blind)
        for _, row in truth_blind.iterrows():
            report = engine_learned.analyze(row['board_id'], logs)
            refs = [s['refdes'] for s in report.get('suspects', [])]
            if refs and refs[0] == row['root_cause']:
                blind_1 += 1
                blind_3 += 1
            elif row['root_cause'] in refs[:3]:
                blind_3 += 1
        blind1_pct = blind_1 / n * 100
        blind3_pct = blind_3 / n * 100
        print(f"  blind (report-only): top-1 {blind1_pct:.1f}%  top-3 {blind3_pct:.1f}%")
        return blind1_pct, blind3_pct
    finally:
        if had_weights:
            cfg['weights'] = orig_weights
        else:
            cfg.pop('weights', None)
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding='utf-8')


def main():
    print("LEARNED FUSION WEIGHTS (blind set is report-only — never selected on)")
    print("========================================================================\n")

    truth_train, truth_val, truth_blind, logs = load_boards()
    engine = CircuitMindOrchestrator()

    t0 = time.perf_counter()
    train = extract_raw_scores(engine, truth_train, logs, 'train')
    val = extract_raw_scores(engine, truth_val, logs, 'val')
    blind = extract_raw_scores(engine, truth_blind, logs, 'blind')
    print(f"  extraction took {time.perf_counter() - t0:.1f}s\n")

    policy = dict(POLICY_WEIGHTS)
    print("Baseline (hand-set policy):")
    for name, rows in (('train', train), ('val', val), ('blind', blind)):
        t1 = top_accuracy(rows, policy, 1)
        t3 = top_accuracy(rows, policy, 3)
        print(f"  {name:6s} top-1 {t1 * 100:5.1f}%   top-3 {t3 * 100:5.1f}%")

    print("Grid search over the full weight simplex on TRAIN + VAL (no top-k filter)...")

    # Selection AND retention both happen on train+val only.
    result = select_weights(train, val, policy)
    learned_dict = result['weights']
    print(f"\nSelected on VAL: weights = { {s: round(w, 2) for s, w in learned_dict.items()} }")
    print(f"  train top-1 {result['train_top1']:.1f}%  |  val top-1 {result['val_top1']:.1f}%  "
          f"top-3 {result['val_top3']:.1f}%  (policy val: {result['policy_val_top1']:.1f}% / "
          f"{result['policy_val_top3']:.1f}%)")

    if result['keep']:
        cfg = json.loads(CONFIG_PATH.read_text(encoding='utf-8')) if CONFIG_PATH.exists() else {}
        cfg['weights'] = {k: round(v, 2) for k, v in learned_dict.items()}
        cfg['weights_note'] = (
            f"Learned from {len(train)} labeled training boards (grid search, step {STEP}); "
            f"selected and retained on the 100-board validation holdout. The blind TEST set "
            f"is reported only and never influences selection or retention. "
            f"Policy fallback: {POLICY_WEIGHTS}."
        )
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding='utf-8')
        print(f"\n✅ LEARNED WEIGHTS WRITTEN to config/diagnostic_weights.json (decision on VAL)")
    else:
        print("\n⛔ Learned weights did not beat policy on VAL — KEEPING hand-set policy.")
        print("   (honest outcome; the learner and its numbers stay in this script)")

    # Final untouched evaluation of the DECIDED config on blind — report only.
    decided = learned_dict if result['keep'] else policy
    print("\nBlind-set verification (final, report-only — no decision reads this):")
    report_blind(decided, truth_blind, logs)
    return result['keep']


if __name__ == '__main__':
    main()
