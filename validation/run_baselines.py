"""Baselines suite — the honest table the audit demanded.

On the SAME frozen blind split (ground_truth_blind.csv), compare:

  majority       — always predict the most common fault family in training
  exact-pattern  — family whose canonical failed-step set matches exactly
  jaccard        — nearest fault family by failed-step Jaccard similarity
  tfidf-only     — CircuitMind fusion with ONLY the retrieval stream (history=1)
  current fusion — the shipped learned-policy engine

Why this exists: an external audit reproduced 88% top-1 with a trivial Jaccard
classifier on the instance holdout. That is true — and honest — because the
generated families are separable by failed-step pattern alone. This table shows
that fact explicitly, so the team never over-claims. The discriminating
benchmark (benchmark_discriminating.py) is where the fusion must actually
separate same-pattern cases.

Run: python3 validation/run_baselines.py
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from data.generate_synthetic import SCENARIOS  # noqa: E402
from engine.orchestrator import CircuitMindOrchestrator  # noqa: E402
from data.schema_adapter import standardize_dataframe  # noqa: E402
from validation._bench_common import score_report  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

FAMILY_PATTERNS = {s['root']: frozenset(s['tests'].keys()) for s in SCENARIOS}


def failed_steps_for(board_logs):
    return frozenset(
        str(r['test_step']).strip()
        for _, r in board_logs.iterrows() if str(r['pass_fail']).strip().upper() == 'FAIL'
    )


def jaccard(a, b):
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def main():
    logs = standardize_dataframe(pd.read_csv(ROOT / 'data' / 'test_logs.csv'))
    truth = pd.read_csv(ROOT / 'validation' / 'ground_truth_blind.csv')
    train_truth = pd.read_csv(ROOT / 'validation' / 'ground_truth_train.csv')
    n = len(truth)

    majority_family = train_truth['root_cause'].value_counts().idxmax()

    exact_top1 = 0
    jac_top1 = jac_top3 = 0
    abstains = 0

    for row in truth.itertuples(index=False):
        board_id = str(row.board_id)
        root = str(row.root_cause)
        steps = failed_steps_for(logs[logs['board_id'] == board_id])

        exact = next((f for f, p in FAMILY_PATTERNS.items() if steps == p), None)
        if exact is None:
            abstains += 1
        else:
            exact_top1 += int(exact == root)
        ranking = sorted(FAMILY_PATTERNS, key=lambda f: -jaccard(steps, FAMILY_PATTERNS[f]))
        jac_top1 += int(ranking[0] == root)
        jac_top3 += int(root in ranking[:3])

    # CircuitMind: retrieval-only (history=1) and the shipped learned policy.
    engine = CircuitMindOrchestrator()
    tfidf_top1 = tfidf_top3 = 0
    fusion_top1 = fusion_top3 = 0
    for row in truth.itertuples(index=False):
        board_id = str(row.board_id)
        root = str(row.root_cause)
        engine.fusion.weights = {'history': 1.0, 'net': 0.0, 'topology': 0.0, 'criticality': 0.0, 'category': 0.0}
        report = engine.analyze(board_id, logs)
        h1, h3, _ = score_report(report, root)
        tfidf_top1 += int(h1)
        tfidf_top3 += int(h3)

    # Shipped policy: fresh engine (reads config/diagnostic_weights.json).
    engine2 = CircuitMindOrchestrator()
    for row in truth.itertuples(index=False):
        report = engine2.analyze(str(row.board_id), logs)
        h1, h3, _ = score_report(report, str(row.root_cause))
        fusion_top1 += int(h1)
        fusion_top3 += int(h3)

    rows = [
        ('majority', majority_family, round(sum(1 for _, r in truth.iterrows() if r['root_cause'] == majority_family) / n * 100, 1), None),
        ('exact-pattern', None, round(exact_top1 / n * 100, 1), None),
        ('jaccard (steps)', None, round(jac_top1 / n * 100, 1), round(jac_top3 / n * 100, 1)),
        ('tfidf-only (history=1)', None, round(tfidf_top1 / n * 100, 1), round(tfidf_top3 / n * 100, 1)),
        ('current fusion (shipped)', None, round(fusion_top1 / n * 100, 1), round(fusion_top3 / n * 100, 1)),
    ]

    print("BASELINES — instance holdout (blind, 100 boards), frozen split")
    print("=" * 64)
    print(f"  {'method':<28} {'top-1':>7} {'top-3':>7}")
    for name, _, t1, t3 in rows:
        print(f"  {name:<28} {t1:>6.1f}% {('' if t3 is None else f'{t3:>6.1f}%')}")
    print(f"  (exact-pattern abstains on {abstains}/{n} boards with no exact family match)")

    report = {
        'split': 'blind (100 boards, frozen)',
        'baselines': {
            'majority_top1': rows[0][2],
            'exact_pattern_top1': rows[1][2],
            'exact_pattern_abstains': abstains,
            'jaccard_top1': rows[2][2],
            'jaccard_top3': rows[2][3],
            'tfidf_only_top1': rows[3][2],
            'tfidf_only_top3': rows[3][3],
            'current_fusion_top1': rows[4][2],
            'current_fusion_top3': rows[4][3],
        },
        'note': ('Headline parity with jaccard/exact-pattern is EXPECTED on the '
                 'instance holdout (families are pattern-separable). The '
                 'discriminating benchmark is where fusion must separate.'),
    }
    (ROOT / 'validation' / 'baseline_report.json').write_text(
        json.dumps(report, indent=2), encoding='utf-8')
    print("\n✅ baseline_report.json written.")
    return report


if __name__ == '__main__':
    main()
