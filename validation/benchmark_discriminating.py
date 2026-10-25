"""Benchmark F — the discriminating set: same failed tests, different root causes.

Every board in a cluster shares its failed-test SET with the other boards in
the cluster; only the measured error code / deviation magnitude (and the
mechanism those imply) differ. A pattern-only classifier must guess; the full
evidence pipeline should separate.

Compares:
  exact-pattern   — family whose canonical failed-step set matches exactly
  jaccard         — nearest family by failed-step Jaccard similarity
  current fusion  — the shipped CircuitMind pipeline

Run: python3 validation/benchmark_discriminating.py
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from data.generate_synthetic import SCENARIOS  # noqa: E402
from engine.orchestrator import CircuitMindOrchestrator  # noqa: E402
from data.schema_adapter import standardize_dataframe  # noqa: E402

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


def pattern_predict(failed_steps):
    """Exact-pattern guess: the family whose canonical failed set matches."""
    for family, pattern in FAMILY_PATTERNS.items():
        if failed_steps == pattern:
            return family
    return None


def jaccard_ranking(failed_steps):
    """All families ranked by failed-step Jaccard similarity."""
    return sorted(FAMILY_PATTERNS, key=lambda f: -jaccard(failed_steps, FAMILY_PATTERNS[f]))


def run_discriminating():
    logs = standardize_dataframe(pd.read_csv(ROOT / 'validation' / 'discriminating' / 'logs.csv'))
    truth = pd.read_csv(ROOT / 'validation' / 'discriminating' / 'ground_truth.csv')
    engine = CircuitMindOrchestrator()

    exact_top1 = jac_top1 = jac_top3 = eng_top1 = eng_top3 = 0
    per_cluster = {}
    n = len(truth)

    for row in truth.itertuples(index=False):
        board_id = str(row.board_id)
        root = str(row.root_cause)
        cluster = board_id.split('_')[1]
        board_logs = logs[logs['board_id'] == board_id]
        steps = failed_steps_for(board_logs)

        # Pattern baselines
        exact = pattern_predict(steps)
        exact_top1 += int(exact == root)
        ranking = jaccard_ranking(steps)
        jac_top1 += int(ranking[0] == root)
        jac_top3 += int(root in ranking[:3])

        # Full pipeline
        report = engine.analyze(board_id, logs)
        refs = [s['refdes'] for s in report.get('suspects', [])]
        eng_top1 += int(bool(refs and refs[0] == root))
        eng_top3 += int(root in refs[:3])

        cluster = per_cluster.setdefault(cluster, {'n': 0, 'exact': 0, 'jac1': 0, 'eng1': 0, 'eng3': 0})
        cluster['n'] += 1
        cluster['exact'] += int(exact == root)
        cluster['jac1'] += int(ranking[0] == root)
        cluster['eng1'] += int(bool(refs and refs[0] == root))
        cluster['eng3'] += int(root in refs[:3])

    print("DISCRIMINATING BENCHMARK — same failed tests, different root causes")
    print("=" * 68)
    print(f"  {'cluster':<9} {'n':>3}  exact  jaccard-1  engine-1  engine-3")
    for c in sorted(per_cluster):
        d = per_cluster[c]
        print(f"  {c:<9} {d['n']:>3}  {d['exact']/d['n']*100:4.0f}%  {d['jac1']/d['n']*100:7.0f}%  "
              f"{d['eng1']/d['n']*100:8.0f}%  {d['eng3']/d['n']*100:8.0f}%")
    print(f"  OVERALL    {n:>3}  {exact_top1/n*100:4.0f}%  {jac_top1/n*100:7.0f}%  "
          f"{eng_top1/n*100:8.0f}%  {eng_top3/n*100:8.0f}%")
    print("  (exact: failed-set exactly matches a family; jaccard: nearest family by step overlap)")

    summary = {
        'boards': n,
        'exact_pattern_top1': round(exact_top1 / n * 100, 1),
        'jaccard_top1': round(jac_top1 / n * 100, 1),
        'jaccard_top3': round(jac_top3 / n * 100, 1),
        'engine_top1': round(eng_top1 / n * 100, 1),
        'engine_top3': round(eng_top3 / n * 100, 1),
    }
    import json
    (ROOT / 'validation' / 'discriminating_metrics.json').write_text(
        json.dumps(summary, indent=2), encoding='utf-8')
    return {'name': 'Discriminating (same failed tests, different roots)', 'summary': summary}


if __name__ == '__main__':
    run_discriminating()
