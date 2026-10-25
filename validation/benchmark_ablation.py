"""Benchmark E — Ablation study.

Runs the instance-holdout blind set with individual evidence streams zeroed to
measure each stream's contribution to ranking accuracy. The weights used here
are diagnostic configurations, not claims about production tuning.

Configurations:
  history-only / net-only / topology-only — each stream alone at full weight
  no-history  / no-net / no-topology     — each stream removed from the fusion
  full (baseline)                        — the validated 0.35/0.30/0.20/0.10/0.05
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from validation._bench_common import ROOT, score_report  # noqa: E402
from engine.orchestrator import CircuitMindOrchestrator  # noqa: E402
from data.schema_adapter import standardize_dataframe  # noqa: E402

def _canonical_weights() -> dict:
    """Load the canonical weights from config/diagnostic_weights.json
    (learned from labeled training boards), falling back to the validated
    hand-set policy."""
    import json
    cfg_path = ROOT / 'config' / 'diagnostic_weights.json'
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
            if cfg.get('weights'):
                return dict(cfg['weights'])
        except (json.JSONDecodeError, OSError):
            pass
    return {'history': 0.35, 'net': 0.30, 'topology': 0.20, 'criticality': 0.10, 'category': 0.05}


FULL = _canonical_weights()
STREAMS = ['history', 'net', 'topology', 'criticality', 'category']


def _config(name: str) -> dict:
    if name == 'full':
        return dict(FULL)
    if name.endswith('-only'):
        stream = name[:-5]
        return {s: (FULL[s] if s == stream else 0.0) for s in STREAMS}
    if name.startswith('no-'):
        stream = name[3:]
        return {s: (0.0 if s == stream else FULL[s]) for s in STREAMS}
    raise ValueError(name)


def run_ablation() -> dict:
    logs = standardize_dataframe(pd.read_csv(ROOT / 'data' / 'test_logs.csv'))
    truth = pd.read_csv(ROOT / 'validation' / 'ground_truth_blind.csv')
    engine = CircuitMindOrchestrator()

    configs = ['full', 'history-only', 'net-only', 'topology-only', 'no-history', 'no-net', 'no-topology']
    rows = []
    for name in configs:
        engine.fusion.weights = _config(name)
        top1 = top3 = 0
        for row in truth.itertuples(index=False):
            report = engine.analyze(str(row.board_id), logs)
            hit1, hit3, _ = score_report(report, str(row.root_cause))
            top1 += int(hit1)
            top3 += int(hit3)
        n = len(truth)
        rows.append({
            'config': name,
            'top1': round(top1 / n * 100, 1),
            'top3': round(top3 / n * 100, 1),
        })
    # Restore the canonical weights.
    engine.fusion.weights = dict(FULL)

    print("ABLATION STUDY (instance-holdout blind set)")
    print("=" * 60)
    for r in rows:
        print(f"  {r['config']:<16} top-1 {r['top1']:5.1f}%  top-3 {r['top3']:5.1f}%")

    return {'name': 'Ablation', 'configs': rows}


if __name__ == '__main__':
    run_ablation()
