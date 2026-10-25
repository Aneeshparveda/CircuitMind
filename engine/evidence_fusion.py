import json
import re
from pathlib import Path
from typing import Dict, List, Optional

import networkx as nx
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


DEFAULT_POLICY = {
    'weights': {
        'history': 0.35,
        'net': 0.30,
        'topology': 0.20,
        'criticality': 0.10,
        'category': 0.05,
    },
    'category_weights': {
        'IC': 100,
        'Connector': 90,
        'Transistor': 80,
        'Inductor': 70,
        'Capacitor': 50,
        'Resistor': 30,
    },
    'uncertainty_gap': 15.0,
    'notes_bonus': 10.0,
}

DEFAULT_KNOBS = {
    'multi_fault': {
        'coverage_threshold': 0.70,
        'min_primary_nets': 2,
        'min_domains': 3,
        'pair_search_top_n': 5,
        'parsimony_penalty': 6.0,
        'pair_improvement_min': 15.0,
    },
    'ood': {
        'known_threshold': 0.45,
        'partially_novel_threshold': 0.25,
        'min_matches_for_known': 2,
    },
    'next_best_test': {
        'risk_penalty': {'LOW': 1.0, 'MEDIUM': 1.5, 'HIGH': 2.5},
        'effort_penalty': {'LOW': 1.0, 'MEDIUM': 1.5, 'HIGH': 2.0},
        'separation_both_expected': 30.0,
        'separation_one_expected': 100.0,
        'separation_net_probe': 55.0,
    },
}


def _load_policy(policy_path: str) -> Dict:
    """Load the evidence policy, falling back to the validated defaults."""
    path = Path(policy_path)
    if not path.exists():
        return DEFAULT_POLICY
    try:
        loaded = json.loads(path.read_text(encoding='utf-8'))
        merged = dict(DEFAULT_POLICY)
        for key, value in loaded.items():
            merged[key] = value
        return merged
    except (json.JSONDecodeError, OSError):
        return DEFAULT_POLICY


def _load_knobs(config_path: str) -> Dict:
    """Load the diagnostic tuning knobs from config/diagnostic_weights.json."""
    path = Path(config_path)
    if not path.exists():
        return DEFAULT_KNOBS
    try:
        loaded = json.loads(path.read_text(encoding='utf-8'))
        merged = dict(DEFAULT_KNOBS)
        for key, value in loaded.items():
            merged[key] = value
        return merged
    except (json.JSONDecodeError, OSError):
        return DEFAULT_KNOBS


class EvidenceFusion:
    """Fuse named, inspectable evidence streams into a 0-100 evidence score.

    The stream weights, category priors, uncertainty gap, and notes bonus are
    defined in ``data/evidence_policy.json`` so the policy is visible, tunable
    without code edits, and can be surfaced in the UI and exports.
    """

    WEIGHTS = DEFAULT_POLICY['weights']
    CATEGORY_WEIGHTS = DEFAULT_POLICY['category_weights']

    def __init__(
        self,
        comps_path: str = None,
        test_map_path: str = None,
        policy_path: str = None,
        config_path: str = None,
        uncertainty_gap: Optional[float] = None,
    ):
        comps_path = comps_path or str(DATA_DIR / 'components.csv')
        test_map_path = test_map_path or str(DATA_DIR / 'test_net_map.csv')
        policy_path = policy_path or str(DATA_DIR / 'evidence_policy.json')
        config_path = config_path or str(CONFIG_DIR / 'diagnostic_weights.json')
        self.df_comps = pd.read_csv(comps_path).set_index('refdes')
        self.test_map = pd.read_csv(test_map_path)
        self.policy = _load_policy(policy_path)
        self.knobs = _load_knobs(config_path)
        # Weights resolve through config/diagnostic_weights.json when present
        # (the canonical diagnostic configuration); evidence_policy.json remains
        # the validated snapshot and the fallback. Values are identical, so the
        # validated ranking is unchanged.
        cfg_weights = self.knobs.get('weights') or {}
        self.weights = {**self.policy['weights'], **cfg_weights}
        self.category_weights = dict(self.policy['category_weights'])
        cfg_gap = self.knobs.get('uncertainty_gap')
        cfg_bonus = self.knobs.get('notes_bonus')
        self.uncertainty_gap = uncertainty_gap if uncertainty_gap is not None else float(cfg_gap if cfg_gap is not None else self.policy['uncertainty_gap'])
        self.notes_bonus = float(cfg_bonus if cfg_bonus is not None else self.policy['notes_bonus'])
        # Risk/effort columns may be absent on older copies of the test map.
        if 'risk' not in self.test_map.columns:
            self.test_map['risk'] = 'LOW'
        if 'effort' not in self.test_map.columns:
            self.test_map['effort'] = 'LOW'

    def get_policy(self) -> Dict:
        """Return the effective evidence policy for display and exports."""
        return {
            'weights': dict(self.weights),
            'uncertainty_gap': self.uncertainty_gap,
            'notes_bonus': self.notes_bonus,
            'knobs': {
                'multi_fault': dict(self.knobs.get('multi_fault', {})),
                'ood': dict(self.knobs.get('ood', {})),
                'next_best_test': dict(self.knobs.get('next_best_test', {})),
            },
        }

    def _history_score(self, refdes: str, matches: List[Dict]) -> tuple[float, Optional[Dict]]:
        supporting = [match for match in matches if match.get('root_cause_component') == refdes]
        if not supporting:
            return 0.0, None
        best = max(supporting, key=lambda match: float(match.get('similarity', 0)))
        return float(best.get('similarity', 0)), best

    def score_candidates(self, signature: Dict, dag_analysis: Dict, memory_results: Dict, notes: str = "") -> List[Dict]:
        """Calculate transparent candidate scores and data-derived explanations.

        ``notes`` is optional session free text (for example "replaced R12").
        Components it explicitly names receive a small, transparent boost and a
        positive-evidence line. With no notes the scoring is identical to the
        validated baseline.
        """
        failed_nets = {test['net'] for test in signature['failed_tests'] if test['net'] != 'UNKNOWN'}
        primary_nets = set(dag_analysis.get('primary_nets', []))
        cascade_nets = set(dag_analysis.get('cascade_nets', []))
        primary_suspects = set(dag_analysis.get('primary_suspects', []))
        matches = memory_results.get('matches', [])
        mentioned_refs = set(re.findall(r'\b[A-Za-z]\d{1,3}\b', notes or ''))
        mentioned_refs = {ref.upper() for ref in mentioned_refs}
        candidates = []

        for refdes, comp_data in self.df_comps.iterrows():
            component_net = comp_data['net']
            positive_evidence: List[str] = []
            negative_evidence: List[str] = []

            history, match = self._history_score(refdes, matches)
            if match:
                positive_evidence.append(
                    f"Historical case {match['repair_id']} identifies {refdes} ({history:.0f}% symptom match)."
                )
            elif matches:
                negative_evidence.append(
                    f"Closest historical case points to {matches[0]['root_cause_component']}, not {refdes}."
                )

            net = 100.0 if component_net in failed_nets else 0.0
            if net:
                positive_evidence.append(f"Located on observed failing net {component_net}.")
            else:
                negative_evidence.append(f"Its assigned net {component_net} is not in the observed failure set.")

            topology = 0.0
            if refdes in primary_suspects:
                topology = 100.0
                positive_evidence.append("Topology places this component upstream of a primary failing net.")
            elif component_net in primary_nets:
                topology = 70.0
                positive_evidence.append("Component is directly associated with a primary failing net.")
            elif component_net in cascade_nets:
                topology = 20.0
                negative_evidence.append("Topology places its net in a downstream cascade path.")
            else:
                negative_evidence.append("No current dependency path independently supports this candidate.")

            criticality = 100.0 if bool(comp_data['critical']) else 30.0
            if bool(comp_data['critical']):
                positive_evidence.append("Marked critical in the board BOM.")
            category = float(self.CATEGORY_WEIGHTS.get(comp_data['cat'], 50))

            raw_scores = {
                'history': history,
                'net': net,
                'topology': topology,
                'criticality': criticality,
                'category': category,
            }
            contributions = {
                key: round(raw_scores[key] * self.weights[key], 2)
                for key in self.weights
            }
            notes_bonus = 0.0
            if refdes in mentioned_refs:
                notes_bonus = self.notes_bonus
                positive_evidence.append(f"Repair notes explicitly name {refdes}.")
            total_score = round(sum(contributions.values()) + notes_bonus, 2)
            candidates.append({
                'refdes': refdes,
                'desc': comp_data['desc'],
                'cat': comp_data['cat'],
                'net': component_net,
                'score': total_score,
                'raw_evidence': raw_scores,
                'evidence_contributions': contributions,
                'hist_score': contributions['history'],
                'net_score': contributions['net'],
                'topo_score': contributions['topology'],
                'criticality_score': contributions['criticality'],
                'category_score': contributions['category'],
                'positive_evidence': positive_evidence,
                'negative_evidence': negative_evidence,
            })

        candidates.sort(key=lambda candidate: candidate['score'], reverse=True)
        return candidates

    def compute_coverage(self, candidates: List[Dict], signature: Dict, dag) -> List[Dict]:
        """Enrich each candidate with failure coverage: which observed failing
        tests would it explain if it were the faulty component?

        A component explains a failing test when the test's net is electrically
        reachable from the component through the circuit. Unlike the directed
        DAG (which models evidence for topology scoring), coverage uses
        undirected electrical connectivity: passive components like inductors
        and capacitors are through-path devices, and a faulty component affects
        every net on its connected subgraph regardless of edge direction in the
        DAG.
        """
        failed_tests = signature.get('failed_tests', [])
        total = max(len(failed_tests), 1)

        # Build an undirected connectivity lookup: for each component, the set
        # of all nets reachable via any electrical path (ignoring DAG direction).
        # Rebuilt per call so a shared instance can never serve stale coverage
        # for a different board/topology (audit B1: the previous instance-level
        # cache was never invalidated).
        self._undirected_nets = {}
        if dag and hasattr(dag, 'G'):
            undirected = dag.G.to_undirected()
            for node in list(dag.G.nodes):
                if dag.G.nodes[node].get('type') == 'component':
                    reachable = set()
                    for target in nx.descendants(undirected, node):
                        if dag.G.nodes[target].get('type') == 'net':
                            reachable.add(target)
                        # Also include the component's own assigned net
                        self._undirected_nets[node] = reachable

        for cand in candidates:
            refdes = cand['refdes']
            reachable_nets = self._undirected_nets.get(refdes, set())
            # Also include the component's own net from components.csv
            own_net = cand.get('net', '')
            if own_net:
                reachable_nets.add(own_net)

            explained = []
            unexplained = []
            for test in failed_tests:
                net = test.get('net', '')
                if net == 'UNKNOWN':
                    unexplained.append(test['test_step'])
                elif net in reachable_nets:
                    explained.append(test['test_step'])
                else:
                    unexplained.append(test['test_step'])

            cand['explained_failures'] = explained
            cand['unexplained_failures'] = unexplained
            cand['coverage'] = round(len(explained) / total, 3)
            cand['coverage_pct'] = round(len(explained) / total * 100)

        return candidates

    def get_next_best_test(self, candidates: List[Dict], signature: Dict) -> Dict:
        """Next Best Test 2.0 — select the safe, low-effort test with the highest
        expected separation between the two leading hypotheses.

        Separation is mechanism-aware: a test on a net that exactly one of the
        top-2 candidates' fault modes predicts will be affected has maximum
        information value, because its outcome directly moves the ranking.
        Utility = separation / (risk penalty x effort penalty), so the system
        provably prefers the cheapest safe high-value test first.

        The activation gate (evidence-score gap) is unchanged from the
        validated baseline; only the *selection* and the explanation grew.
        """
        if len(candidates) < 2:
            return {'active': False, 'reason': 'Fewer than two candidates are available.'}

        top, runner_up = candidates[:2]
        gap = round(top['score'] - runner_up['score'], 2)
        if gap >= self.uncertainty_gap:
            return {
                'active': False,
                'gap': gap,
                'reason': 'The leading candidate has a sufficient evidence-score separation.',
            }

        top_expected = set(top.get('expected_nets') or [])
        runner_expected = set(runner_up.get('expected_nets') or [])
        nbt_cfg = self.knobs.get('next_best_test', {})
        risk_penalty = nbt_cfg.get('risk_penalty', {'LOW': 1.0, 'MEDIUM': 1.5, 'HIGH': 2.5})
        effort_penalty = nbt_cfg.get('effort_penalty', {'LOW': 1.0, 'MEDIUM': 1.5, 'HIGH': 2.0})

        failed_steps = {test['test_step'] for test in signature['failed_tests']}
        available = self.test_map[~self.test_map['test_step'].isin(failed_steps)]

        def separation(net: str) -> float:
            in_top = net in top_expected
            in_runner = net in runner_expected
            if in_top != in_runner:
                return float(nbt_cfg.get('separation_one_expected', 100.0))
            if in_top and in_runner:
                return float(nbt_cfg.get('separation_both_expected', 30.0))
            return float(nbt_cfg.get('separation_net_probe', 55.0))

        scored = []
        for _, row in available.iterrows():
            net = str(row['net_name'])
            risk = str(row.get('risk', 'LOW')).upper()
            effort = str(row.get('effort', 'LOW')).upper()
            sep = separation(net)
            util = sep / (float(risk_penalty.get(risk, 1.5)) * float(effort_penalty.get(effort, 1.5)))
            scored.append({
                'test_step': str(row['test_step']),
                'net': net,
                'level': int(row.get('level', 99)),
                'separation': round(sep, 1),
                'risk': risk,
                'effort': effort,
                'utility': round(util, 2),
            })

        if scored:
            scored.sort(key=lambda item: (-item['utility'], -item['separation'], item['level']))
            choice = scored[0]
        else:
            # No unmapped candidate test: synthesize a safe manual measurement.
            net = runner_up['net'] if runner_up['net'] != top['net'] else top['net']
            choice = {
                'test_step': f'Measure {net} under rated load',
                'net': net,
                'level': 99,
                'separation': 55.0,
                'risk': 'LOW',
                'effort': 'MEDIUM',
                'utility': round(55.0 / 1.0, 2),
            }

        test_name = choice['test_step']
        net = choice['net']
        sep = choice['separation']
        info_gain = 'HIGH' if sep >= 80 else ('MEDIUM' if sep >= 50 else 'LOW')

        in_top = net in top_expected
        in_runner = net in runner_expected
        if in_top and not in_runner:
            why = (
                f"{net} is inside {top['refdes']}'s expected blast radius but outside "
                f"{runner_up['refdes']}'s — its outcome splits the two hypotheses directly."
            )
        elif in_runner and not in_top:
            why = (
                f"{net} is inside {runner_up['refdes']}'s expected blast radius but outside "
                f"{top['refdes']}'s — its outcome splits the two hypotheses directly."
            )
        elif in_top and in_runner:
            why = (
                f"Both leading hypotheses predict {net} is affected, so this measurement "
                f"confirms shared impact but separates them weakly."
            )
        else:
            why = (
                f"{net} probes the failing region without repeating an already-failed test, "
                f"adding independent evidence about {top['refdes']} vs {runner_up['refdes']}."
            )

        return {
            'active': True,
            'gap': gap,
            'test': test_name,
            'net': net,
            'purpose': f"Distinguish {top['refdes']} from {runner_up['refdes']}.",
            'candidates_distinguished': [top['refdes'], runner_up['refdes']],
            'reason': (
                f"The evidence-score gap is only {gap:.1f} points. {why} "
                f"Risk {choice['risk']}, effort {choice['effort']}, separation {sep:.0f}/100."
            ),
            'why_this_test': why,
            'info_gain': info_gain,
            'separation': sep,
            'risk': choice['risk'],
            'effort': choice['effort'],
            'utility': choice['utility'],
            'expected_outcomes': {
                top['refdes']: f"If {net} remains abnormal, evidence for {top['refdes']} strengthens.",
                runner_up['refdes']: f"If {net} is nominal, inspect {runner_up['refdes']} and its local path."
            },
        }
