"""Benchmarks C & D — Adversarial robustness and OOD/novelty handling.

Runs the full pipeline against the deterministic adversarial set and reports,
per perturbation family:

  noise / unknown_test / novel_code / missing_value — top-1 / top-3 vs truth
  missing_bom                                    — top-1 with a reduced BOM
  multi_fault                                    — detector flag rate, solver
                                                  verdict, named-pair accuracy
  ood                                            — novelty-flag rate and whether
                                                  the system avoids confident
                                                  certainty on novel patterns
"""

import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from validation._bench_common import ROOT, score_report, build_light_pipeline, light_analyze  # noqa: E402
from engine.orchestrator import CircuitMindOrchestrator  # noqa: E402
from data.schema_adapter import standardize_dataframe  # noqa: E402


def run_adversarial() -> dict:
    logs = standardize_dataframe(pd.read_csv(ROOT / 'validation' / 'adversarial' / 'logs.csv'))
    meta = pd.read_csv(ROOT / 'validation' / 'adversarial' / 'ground_truth.csv')
    engine = CircuitMindOrchestrator()

    results = {}
    for perturbation in ['noise', 'unknown_test', 'novel_code', 'missing_value']:
        boards = meta[meta['perturbation'] == perturbation]
        top1 = top3 = 0
        for row in boards.itertuples(index=False):
            report = engine.analyze(str(row.board_id), logs)
            hit1, hit3, _ = score_report(report, str(row.truth))
            top1 += int(hit1)
            top3 += int(hit3)
        n = len(boards)
        results[perturbation] = {
            'boards': n,
            'top1': round(top1 / n * 100, 1),
            'top3': round(top3 / n * 100, 1),
        }

    # missing_bom — reduced BOM via a temporary components file.
    comps = pd.read_csv(ROOT / 'data' / 'components.csv')
    drop = ['Y1', 'U7', 'R2', 'R13', 'J2']
    reduced = comps[~comps['refdes'].isin(drop)]
    boards = meta[meta['perturbation'] == 'missing_bom']
    with tempfile.TemporaryDirectory() as tmp:
        comps_path = f"{tmp}/components.csv"
        reduced.to_csv(comps_path, index=False)
        extractor, dag, memory, fusion = build_light_pipeline(comps_path=comps_path)
        top1 = top3 = 0
        for row in boards.itertuples(index=False):
            report = light_analyze(extractor, dag, memory, fusion, str(row.board_id), logs)
            hit1, hit3, _ = score_report(report, str(row.truth))
            top1 += int(hit1)
            top3 += int(hit3)
        n = len(boards)
        results['missing_bom'] = {
            'boards': n,
            'top1': round(top1 / n * 100, 1),
            'top3': round(top3 / n * 100, 1),
        }

    # multi_fault — detector flag rate + solver naming accuracy.
    boards = meta[meta['perturbation'] == 'multi_fault']
    flagged = named = solver_likely = 0
    for row in boards.itertuples(index=False):
        report = engine.analyze(str(row.board_id), logs)
        flagged += int(bool(report.get('multi_fault', {}).get('multi_fault_likely', False)))
        solver = report.get('multi_fault_analysis', {})
        solver_likely += int(solver.get('verdict') in ('MULTI_FAULT_LIKELY', 'SECOND_FAULT_POSSIBLE'))
        pair = (solver.get('best_pair') or {}).get('components') or []
        truth_parts = str(row.truth).replace('MULTI:', '').split('+')
        named += int(all(part in pair for part in truth_parts))
    n = len(boards)
    results['multi_fault'] = {
        'boards': n,
        'detector_flagged_pct': round(flagged / n * 100, 1),
        'solver_flagged_pct': round(solver_likely / n * 100, 1),
        'solver_named_both_pct': round(named / n * 100, 1),
    }

    # ood — novelty handling.
    boards = meta[meta['perturbation'] == 'ood']
    novelty_flagged = 0
    avoided_confident = 0
    for row in boards.itertuples(index=False):
        report = engine.analyze(str(row.board_id), logs)
        ood = report.get('ood_state', {})
        novelty_flagged += int(ood.get('state', 'KNOWN') != 'KNOWN')
        tier = report.get('confidence_tier', '')
        # A novel pattern must not receive a confident 'Strong Evidence' tier.
        avoided_confident += int(not (ood.get('state') == 'NOVEL' and tier == 'Strong Evidence'))
    n = len(boards)
    results['ood'] = {
        'boards': n,
        'novelty_flagged_pct': round(novelty_flagged / n * 100, 1),
        'no_confident_novel_pct': round(avoided_confident / n * 100, 1),
    }

    print("ADVERSARIAL + OOD BENCHMARK")
    print("=" * 64)
    for key in ['noise', 'unknown_test', 'novel_code', 'missing_value', 'missing_bom']:
        r = results[key]
        print(f"  {key:<14} n={r['boards']:>3}  top-1 {r['top1']:5.1f}%  top-3 {r['top3']:5.1f}%")
    r = results['multi_fault']
    print(f"  multi_fault      n={r['boards']:>3}  detector {r['detector_flagged_pct']:.0f}%  "
          f"solver {r['solver_flagged_pct']:.0f}%  named-both {r['solver_named_both_pct']:.0f}%")
    r = results['ood']
    print(f"  ood              n={r['boards']:>3}  novelty flagged {r['novelty_flagged_pct']:.0f}%  "
          f"no confident novel {r['no_confident_novel_pct']:.0f}%")

    return {'name': 'Adversarial + OOD', 'results': results}


if __name__ == '__main__':
    run_adversarial()
