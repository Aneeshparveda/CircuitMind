"""Final untouched evaluation on the RESERVE test set.

The reserve set (seed 20260731, BRD_0500+) was generated AFTER the model was
frozen and has never influenced any selection or retention decision. This is
the single final number reported for the shipped configuration.

The engine runs with its shipped configuration: the retrieval corpus and
pattern-signal statistics are read from the shipped files, which contain zero
reserve boards. This evaluates the actual shipped system on never-seen boards.

Metrics: top-1, top-3, top-5, MRR, NDCG@3, domain accuracy, latency.

Run: python3 validation/validate_reserve.py
"""

import json
import math
import os
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.orchestrator import CircuitMindOrchestrator  # noqa: E402
from data.schema_adapter import standardize_dataframe  # noqa: E402

DOMAIN_BY_ROOT = {
    'J1': 'POWER', 'F1': 'POWER', 'U3': 'POWER', 'L1': 'POWER', 'C1': 'POWER', 'U2': 'POWER', 'C2': 'POWER',
    'U1': 'DIGITAL', 'U5': 'DIGITAL', 'U6': 'DIGITAL', 'R1': 'DIGITAL',
    'U4': 'COMMS', 'A1': 'COMMS',
    'R12': 'ANALOG', 'Q1': 'ANALOG',
}


def rank_metrics(report, truth):
    """Return (top1, top3, top5, mrr, ndcg3) for a report vs the truth."""
    refs = [s['refdes'] for s in report.get('suspects', [])]
    top1 = top3 = top5 = False
    mrr = 0.0
    ndcg = 0.0
    if truth in refs:
        rank = refs.index(truth) + 1
        mrr = 1.0 / rank
        if rank <= 3:
            ndcg = 1.0 / math.log2(rank + 1)  # DCG@3 with a single relevant item; IDCG = 1
    top1 = bool(refs and refs[0] == truth)
    top3 = truth in refs[:3]
    top5 = truth in refs[:5]
    return top1, top3, top5, mrr, ndcg


def run_reserve():
    print("RESERVE SET — final untouched evaluation (never used for selection)")
    print("==================================================================\n")

    df_truth = pd.read_csv(ROOT / 'validation' / 'ground_truth_reserve.csv')
    df_logs = standardize_dataframe(pd.read_csv(ROOT / 'data' / 'test_logs_reserve.csv'))

    engine = CircuitMindOrchestrator()  # shipped config; reserve boards not in its corpus/signals

    totals = {'n': 0, 'top1': 0, 'top3': 0, 'top5': 0, 'domain': 0, 'mrr': 0.0, 'ndcg': 0.0}
    # Calibration: empirical top-1 accuracy per confidence tier. These are
    # measured frequencies on the untouched reserve set, never a probability
    # claim — "Strong Evidence" boards resolve correctly in X% of cases here.
    tiers = {}
    times = []
    for row in df_truth.itertuples(index=False):
        start = time.perf_counter()
        report = engine.analyze(str(row.board_id), df_logs)
        times.append(time.perf_counter() - start)
        if report['status'] == 'PASS':
            continue
        top1, top3, top5, mrr, ndcg = rank_metrics(report, str(row.root_cause))
        totals['n'] += 1
        totals['top1'] += int(top1)
        totals['top3'] += int(top3)
        totals['top5'] += int(top5)
        totals['mrr'] += mrr
        totals['ndcg'] += ndcg
        tier = report.get('confidence_tier', 'Insufficient Evidence')
        t = tiers.setdefault(tier, {'n': 0, 'top1': 0})
        t['n'] += 1
        t['top1'] += int(top1)
        true_domain = DOMAIN_BY_ROOT.get(str(row.root_cause))
        if true_domain and report.get('signature', {}).get('primary_domain') == true_domain:
            totals['domain'] += 1

    n = totals['n']
    times.sort()
    calibration = {
        tier: {'n': v['n'], 'empirical_top1_pct': round(v['top1'] / v['n'] * 100, 1)}
        for tier, v in sorted(tiers.items())
    }
    summary = {
        'dataset': 'Reserve Test — boards never seen by any split (seed 20260731, BRD_0500+)',
        'instances': n,
        'top1_accuracy': round(totals['top1'] / n * 100, 1),
        'top3_accuracy': round(totals['top3'] / n * 100, 1),
        'top5_accuracy': round(totals['top5'] / n * 100, 1),
        'mrr': round(totals['mrr'] / n, 4),
        'ndcg_at_3': round(totals['ndcg'] / n, 4),
        'domain_accuracy': round(totals['domain'] / n * 100, 1),
        'calibration_by_tier': calibration,
        'median_inference_seconds': round(times[len(times) // 2], 6),
        'p95_inference_seconds': round(times[int(len(times) * 0.95) - 1], 6),
    }
    with open(ROOT / 'validation' / 'reserve_metrics.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)

    print(f"Instances:   {n}")
    print(f"Top-1:       {summary['top1_accuracy']:.1f}%")
    print(f"Top-3:       {summary['top3_accuracy']:.1f}%")
    print(f"Top-5:       {summary['top5_accuracy']:.1f}%")
    print(f"MRR:         {summary['mrr']:.4f}")
    print(f"NDCG@3:      {summary['ndcg_at_3']:.4f}")
    print(f"Domain:      {summary['domain_accuracy']:.1f}%")
    for tier, v in calibration.items():
        print(f"  tier {tier}: n={v['n']}  empirical top-1 {v['empirical_top1_pct']:.1f}% (frequency, not probability)")
    print(f"Latency:     median {summary['median_inference_seconds']*1000:.1f} ms  p95 {summary['p95_inference_seconds']*1000:.1f} ms")
    print("\n✅ reserve_metrics.json written. This is the final untouched test number.")
    return summary


if __name__ == '__main__':
    run_reserve()
