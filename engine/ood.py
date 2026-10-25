"""Out-of-distribution / novelty detection.

Produces a structured pattern-familiarity state:
  KNOWN            — the failure pattern is well represented in history
  PARTIALLY_NOVEL  — partial precedent or weak support; treat as provisional
  NOVEL            — no sufficient precedent; the system should NOT issue a
                     confident diagnosis without additional evidence

This is an independent axis from the evidence ranking: a board can rank a
candidate strongly while still being flagged NOVEL on pattern familiarity.
Both are surfaced honestly in the UI.
"""

from typing import Any, Dict, List, Optional


def detect_novelty(
    signature: Dict[str, Any],
    memory_results: Dict[str, Any],
    leader: Optional[Dict[str, Any]],
    cited_precedent: Optional[Dict[str, Any]],
    multi_fault_likely: bool,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return {state, max_similarity, indicators}."""
    cfg = config or {}
    known_threshold = float(cfg.get('known_threshold', 0.45))
    partial_threshold = float(cfg.get('partially_novel_threshold', 0.25))
    min_matches = int(cfg.get('min_matches_for_known', 2))

    matches = memory_results.get('matches') or []
    similarities = [float(m.get('similarity', 0)) for m in matches]
    max_sim = max(similarities) / 100.0 if similarities else 0.0
    n_matches = len(matches)

    leader_coverage = float((leader or {}).get('coverage', 0) or 0)
    failed_tests = signature.get('failed_tests', [])
    unmapped = [t for t in failed_tests if t.get('net') == 'UNKNOWN']
    unmapped_ratio = len(unmapped) / max(len(failed_tests), 1)

    indicators: List[Dict[str, str]] = []

    # A board whose failing tests are mostly unmapped (novel test names) has
    # no representable pattern in the map or the corpus — treat as novel even
    # when a couple of known steps still match some history.
    if max_sim >= known_threshold and n_matches >= min_matches and unmapped_ratio <= 0.4:
        state = 'KNOWN'
    elif max_sim >= known_threshold and cited_precedent and unmapped_ratio <= 0.4:
        state = 'KNOWN'
    elif max_sim < partial_threshold and not cited_precedent or unmapped_ratio > 0.5:
        state = 'NOVEL'
    else:
        state = 'PARTIALLY_NOVEL'

    if max_sim < known_threshold:
        indicators.append({
            'label': 'Low historical similarity',
            'detail': (
                f"The closest repair-history match scores only {max_sim * 100:.0f}% similarity — "
                "no strongly analogous precedent exists for this failure pattern."
            ),
        })
    if not cited_precedent and not matches:
        indicators.append({
            'label': 'No historical precedent',
            'detail': 'The retrieval corpus contains no case matching this failure signature.',
        })
    if leader and leader_coverage < 0.7:
        indicators.append({
            'label': 'Weak failure coverage',
            'detail': (
                f"The leading hypothesis {leader.get('refdes')} explains only "
                f"{leader_coverage * 100:.0f}% of observed failures."
            ),
        })
    if unmapped_ratio > 0:
        indicators.append({
            'label': 'Unmapped evidence',
            'detail': f"{len(unmapped)} failing test(s) could not be attributed to a net.",
        })
    if multi_fault_likely:
        indicators.append({
            'label': 'Possible independent faults',
            'detail': 'The pattern spans multiple domains/nets with no single upstream cause.',
        })

    return {
        'state': state,
        'max_similarity': round(max_sim, 3),
        'n_matches': n_matches,
        'indicators': indicators,
        'is_novel': state != 'KNOWN',
    }
