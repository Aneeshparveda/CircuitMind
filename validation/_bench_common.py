"""Shared helpers for the extended validation benchmarks."""

import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.signature_extractor import SignatureExtractor  # noqa: E402
from engine.topology_dag import TopologyDAG  # noqa: E402
from engine.semantic_memory import SemanticMemory  # noqa: E402
from engine.evidence_fusion import EvidenceFusion  # noqa: E402
from engine.orchestrator import CircuitMindOrchestrator  # noqa: E402

DOMAIN_BY_ROOT = {
    'J1': 'POWER', 'F1': 'POWER', 'U3': 'POWER', 'L1': 'POWER', 'C1': 'POWER', 'U2': 'POWER', 'C2': 'POWER',
    'U1': 'DIGITAL', 'U5': 'DIGITAL', 'U6': 'DIGITAL', 'R1': 'DIGITAL',
    'U4': 'COMMS', 'A1': 'COMMS',
    'R12': 'ANALOG', 'Q1': 'ANALOG',
}


def score_report(report, truth: str):
    """Return (top1, top3, domain) for a report against a truth component."""
    suspects = report.get('suspects', [])
    refs = [s['refdes'] for s in suspects]
    top1 = top3 = domain = False
    if refs:
        top1 = refs[0] == truth
        top3 = truth in refs[:3]
    true_domain = DOMAIN_BY_ROOT.get(truth)
    if true_domain and report.get('signature', {}).get('primary_domain') == true_domain:
        domain = True
    return top1, top3, domain


def build_light_pipeline(comps_path=None, history_path=None, logs_path=None, weights=None):
    """Build pipeline pieces directly (for perturbation-specific setups)."""
    extractor = SignatureExtractor()
    dag = TopologyDAG(comps_path=comps_path)
    memory = SemanticMemory(history_path=history_path, logs_path=logs_path)
    fusion = EvidenceFusion(comps_path=comps_path)
    if weights:
        fusion.weights = dict(weights)
    return extractor, dag, memory, fusion


def light_analyze(extractor, dag, memory, fusion, board_id, logs):
    from engine.orchestrator import CircuitMindOrchestrator
    sig = extractor.extract(logs[logs['board_id'] == board_id])
    if sig['severity_label'] == 'PASS':
        return {'status': 'PASS', 'signature': sig, 'suspects': []}
    failed_nets = [t['net'] for t in sig['failed_tests'] if t['net'] != 'UNKNOWN']
    dag_res = dag.analyze_cascades(failed_nets)
    mem_res = memory.search(sig)
    suspects = fusion.score_candidates(sig, dag_res, mem_res)
    fusion.compute_coverage(suspects, sig, dag)
    return {'status': 'FAIL', 'signature': sig, 'suspects': suspects, 'dag_analysis': dag_res}
