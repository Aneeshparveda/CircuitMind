"""Benchmark B — Fault-Family Holdout.

For every fault family (root-cause component) present in the blind set, the
entire family is removed from BOTH the retrieval corpus (repair history) and
the pattern-signal derivation (test logs), then the pipeline diagnoses the
blind boards of that family.

This measures genuine generalization to unseen fault *types* — the honest
boundary of the instance-holdout numbers (88/100/96). Numbers here are expected
to be lower; they are reported, never hidden.
"""

import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from validation._bench_common import ROOT, score_report  # noqa: E402
from engine.orchestrator import CircuitMindOrchestrator  # noqa: E402
from data.schema_adapter import standardize_dataframe  # noqa: E402


def run_family_holdout() -> dict:
    history = pd.read_csv(ROOT / 'data' / 'repair_history.csv')
    logs_raw = pd.read_csv(ROOT / 'data' / 'test_logs.csv')
    logs = standardize_dataframe(logs_raw)
    truth = pd.read_csv(ROOT / 'validation' / 'ground_truth_blind.csv')

    families = sorted(truth['root_cause'].unique())
    rows = []
    for family in families:
        family_boards = truth[truth['root_cause'] == family]
        n = len(family_boards)
        if n < 3:
            continue
        # Family's boards must be absent from retrieval candidates AND from
        # pattern-signal statistics (all splits).
        keep_history = history[history['root_cause_component'] != family]
        all_truth = pd.concat([
            pd.read_csv(ROOT / 'validation' / 'ground_truth_train.csv'),
            pd.read_csv(ROOT / 'validation' / 'ground_truth_val.csv'),
            truth,
        ], ignore_index=True)
        excluded_boards = set(all_truth[all_truth['root_cause'] == family]['board_id'].astype(str))
        keep_logs = logs[~logs['board_id'].astype(str).isin(excluded_boards)]

        with tempfile.TemporaryDirectory() as tmp:
            hist_path = f"{tmp}/history.csv"
            logs_path = f"{tmp}/logs.csv"
            keep_history.to_csv(hist_path, index=False)
            keep_logs.to_csv(logs_path, index=False)
            engine = CircuitMindOrchestrator(memory_history_path=hist_path, memory_logs_path=logs_path)

            top1 = top3 = 0
            for row in family_boards.itertuples(index=False):
                report = engine.analyze(str(row.board_id), logs)
                hit1, hit3, _ = score_report(report, str(row.root_cause))
                top1 += int(hit1)
                top3 += int(hit3)
        rows.append({
            'family': family,
            'boards': n,
            'top1': round(top1 / n * 100, 1),
            'top3': round(top3 / n * 100, 1),
        })

    total_boards = sum(r['boards'] for r in rows)
    weighted_top1 = round(sum(r['top1'] * r['boards'] for r in rows) / total_boards, 1)
    weighted_top3 = round(sum(r['top3'] * r['boards'] for r in rows) / total_boards, 1)
    unweighted_top1 = round(sum(r['top1'] for r in rows) / len(rows), 1)
    unweighted_top3 = round(sum(r['top3'] for r in rows) / len(rows), 1)

    print("FAULT-FAMILY HOLDOUT (family absent from memory + signals)")
    print("=" * 60)
    for r in rows:
        print(f"  {r['family']:<5} n={r['boards']:>3}  top-1 {r['top1']:5.1f}%  top-3 {r['top3']:5.1f}%")
    print(f"  WEIGHTED  top-1 {weighted_top1:.1f}%  top-3 {weighted_top3:.1f}%  (n={total_boards})")
    print(f"  UNWEIGHTED top-1 {unweighted_top1:.1f}%  top-3 {unweighted_top3:.1f}%  (families={len(rows)})")
    print("  Note: this measures generalization to UNSEEN fault families; the")
    print("  instance-holdout benchmark (88/100/96) measures known families.")

    return {
        'name': 'Fault-Family Holdout',
        'families': rows,
        'weighted_top1': weighted_top1,
        'weighted_top3': weighted_top3,
        'unweighted_top1': unweighted_top1,
        'unweighted_top3': unweighted_top3,
        'total_boards': total_boards,
    }


if __name__ == '__main__':
    run_family_holdout()
