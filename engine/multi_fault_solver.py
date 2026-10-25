"""Sparse multi-fault hypothesis selection.

Turns the multi-fault *detector* into a multi-fault *solver*:

1. The leading hypothesis explains a set of failures *by mechanism*
   (expected-vs-observed, not electrical reachability).
2. The residual — failures no mechanism of the leader can explain — is the
   real signal. The solver searches the entire candidate pool for the single
   component that best covers that residual (a low absolute evidence score
   must not hide a clean second fault).
3. A parsimony penalty keeps the system from inventing second faults; the
   verdict states explicitly when two independent faults are justified,
   possible-but-unproven, or unwarranted.
"""

from typing import Any, Dict, List, Optional


def solve_multi_fault(
    candidates: List[Dict[str, Any]],
    failed_steps: Optional[List[str]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Evaluate best single vs best two-fault explanations.

    ``candidates`` — ranked suspects carrying ``expected_vs_observed``
    (mechanism coverage) and/or ``explained_failures`` (electrical coverage).
    ``failed_steps`` — the failed test steps under investigation (optional;
    reconstructed from candidates when absent).
    """
    cfg = config or {}
    pair_top_n = int(cfg.get('pair_search_top_n', 5))
    parsimony_penalty = float(cfg.get('parsimony_penalty', 6.0))
    min_improvement = float(cfg.get('pair_improvement_min', 15.0))
    coverage_threshold = float(cfg.get('coverage_threshold', 0.70))

    if not candidates:
        return {'analyzable': False, 'reason': 'No candidates available.'}

    def pct(count: int, total: int) -> float:
        return round(count / max(total, 1) * 100, 1)

    def mechanism_explained(candidate: Dict[str, Any]) -> set:
        """Mechanism coverage is authoritative when present — an EMPTY
        mechanism list means the fault mode explains nothing (connectivity
        does not equal causality). Electrical reachability is only a fallback
        when the mechanism layer never ran for this candidate."""
        evo = candidate.get('expected_vs_observed')
        if isinstance(evo, dict) and 'explained' in evo:
            return set(evo.get('explained') or [])
        return set(candidate.get('explained_failures', []))

    def unexplained_by(candidate: Dict[str, Any]) -> set:
        evo = candidate.get('expected_vs_observed')
        if isinstance(evo, dict) and 'unexpected' in evo:
            return set(evo.get('unexpected') or [])
        return set(candidate.get('unexplained_failures', []))

    best_single = candidates[0]
    single_explained = mechanism_explained(best_single)
    single_unexplained = unexplained_by(best_single)

    # Reconstruct the failure universe: failed test steps under investigation.
    if failed_steps:
        universe = set(failed_steps)
    else:
        universe = single_explained | single_unexplained
        for cand in candidates:
            universe |= mechanism_explained(cand) | unexplained_by(cand)

    total = max(len(universe), 1)
    residual = universe - single_explained
    single = {
        'components': [best_single['refdes']],
        'coverage_pct': pct(len(single_explained), total),
        'explained_count': len(single_explained),
        'total': len(universe),
    }

    # Complement search — over ALL candidates, not just the top-ranked: find
    # the component whose mechanism best covers the residual (failures the
    # leader cannot explain). This is how a low-scoring but mechanically clean
    # second fault (e.g. R12 on a resistor prior) is found.
    complement = None
    best_residual_cover = 0
    for cand in candidates:
        if cand['refdes'] == best_single['refdes']:
            continue
        cover = len(mechanism_explained(cand) & residual)
        if cover > best_residual_cover:
            best_residual_cover = cover
            complement = cand

    pair = None
    if complement is not None and best_residual_cover > 0:
        pair_explained = single_explained | mechanism_explained(complement)
        pair = {
            'components': [best_single['refdes'], complement['refdes']],
            'coverage_pct': pct(len(pair_explained), total),
            'explained_count': len(pair_explained),
            'total': len(universe),
            'residual_covered': best_residual_cover,
            'residual_total': len(residual),
        }
    elif len(candidates) >= 2:
        # Fallback: generic pair scan over the top-ranked pool (no mechanism
        # residual signal, e.g. pre-mechanism data).
        from itertools import combinations
        pool = candidates[:pair_top_n]
        best_pair = None
        best_pair_explained = set()
        for a, b in combinations(pool, 2):
            explained = mechanism_explained(a) | mechanism_explained(b)
            if len(explained) > len(best_pair_explained):
                best_pair_explained = explained
                best_pair = (a, b)
        if best_pair is not None:
            pair = {
                'components': [best_pair[0]['refdes'], best_pair[1]['refdes']],
                'coverage_pct': pct(len(best_pair_explained), total),
                'explained_count': len(best_pair_explained),
                'total': len(universe),
            }

    improvement = round((pair['coverage_pct'] if pair else single['coverage_pct']) - single['coverage_pct'], 1)

    # Parsimony-adjusted decision.
    if pair is not None and pair['coverage_pct'] >= 100 and single['coverage_pct'] < 100:
        gain = pair['coverage_pct'] - single['coverage_pct']
        residual_clean = bool(
            pair.get('residual_total') is not None
            and pair['residual_total'] > 0
            and pair.get('residual_covered', 0) == pair['residual_total']
        )
        if single['coverage_pct'] < coverage_threshold * 100 or residual_clean or gain >= min_improvement:
            verdict = 'MULTI_FAULT_LIKELY'
            verdict_text = (
                f"A single fault ({single['components'][0]}) explains only "
                f"{single['coverage_pct']:.0f}% of failures by mechanism; "
                f"{', '.join(sorted(residual))[:120]} cannot be explained by any mechanism of "
                f"{single['components'][0]}. {pair['components'][1]} is the only candidate that "
                f"explains them ({' + '.join(pair['components'])} reaches {pair['coverage_pct']:.0f}%). "
                "Parsimony-adjusted: two independent faults are justified because the residual "
                "is mechanically clean — a single-fault model cannot cover it."
            )
        else:
            verdict = 'SECOND_FAULT_POSSIBLE'
            verdict_text = (
                f"A two-fault explanation ({' + '.join(pair['components'])}) improves mechanism coverage "
                f"from {single['coverage_pct']:.0f}% to {pair['coverage_pct']:.0f}%. "
                "A second independent fault is possible but not proven — verify before replacing."
            )
    elif pair is not None and pair['coverage_pct'] > single['coverage_pct']:
        verdict = 'SINGLE_FAULT_SUFFICIENT'
        verdict_text = (
            f"The best two-fault combination ({' + '.join(pair['components'])}) reaches "
            f"{pair['coverage_pct']:.0f}% vs {single['coverage_pct']:.0f}% for "
            f"{single['components'][0]} alone — but the residual is marginal "
            "and the parsimony penalty favors the single fault. Verify first."
        )
    else:
        verdict = 'SINGLE_FAULT_SUFFICIENT'
        verdict_text = (
            f"No combination improves on {single['components'][0]} — "
            "a single-fault explanation covers the evidence."
        )

    return {
        'analyzable': True,
        'best_single': single,
        'best_pair': pair,
        'improvement_pct': improvement,
        'verdict': verdict,
        'verdict_text': verdict_text,
        'parsimony_penalty': parsimony_penalty,
        'unexplained_after_single': sorted(residual),
    }
