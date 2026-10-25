"""Fault-mode library and mechanism-based expected-vs-observed reasoning.

Assigns a concrete *fault mode* to every candidate hypothesis (``U3 / output
undervoltage`` rather than ``U3``) from the observed evidence, and computes
which nets that mechanism would be *expected* to affect. This is the
"connectivity is not causality" layer: a candidate explains an observed
failure when the failure is on a net its fault mode plausibly reaches, not
merely when it is electrically connected.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_fault_modes(path: Optional[str] = None) -> Dict[str, Any]:
    """Load the fault-mode library JSON."""
    path = path or str(DATA_DIR / "fault_modes.json")
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"rules": [], "default_fallback": {"code": "DEGRADED", "label": "degraded / suspect"}}


def _direction(failed_tests: List[Dict[str, Any]]) -> Optional[str]:
    """Overall measured direction across value-type failures: 'low', 'high', or None."""
    low = high = 0
    for test in failed_tests:
        if test.get('measured') is None or test.get('expected_min') is None:
            continue
        if test['measured'] < test['expected_min']:
            low += 1
        elif test.get('expected_max') is not None and test['measured'] > test['expected_max']:
            high += 1
    if low and not high:
        return 'low'
    if high and not low:
        return 'high'
    return None


def assign_fault_mode(
    category: str,
    failed_tests: List[Dict[str, Any]],
    library: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Deterministically assign the best-supported fault mode for a component.

    Matches on the error codes and domains of the failing tests *associated
    with the component* (its own net plus functional downstream nets — the
    caller passes the relevant failed tests). The first library mode whose
    criteria match wins; otherwise the category fallback (or the global
    default) is used.
    """
    library = library or load_fault_modes()
    codes = {str(t.get('error_code') or '').strip().upper() for t in failed_tests}
    codes.discard('')
    domains = {str(t.get('domain') or '').upper() for t in failed_tests}
    direction = _direction(failed_tests)

    def match(mode: Dict[str, Any]) -> bool:
        m = mode.get('match') or {}
        if m.get('error_codes'):
            if not (codes & set(m['error_codes'])):
                return False
        if m.get('domains'):
            if not (domains & set(m['domains'])):
                return False
        if m.get('direction') and direction != m['direction']:
            return False
        return True

    rule = next((r for r in library.get('rules', []) if category in r.get('categories', [])), None)
    if rule:
        for mode in rule.get('fault_modes', []):
            if match(mode):
                return {
                    'code': mode['code'],
                    'label': mode['label'],
                    'verification': mode.get('verification', ''),
                    'mechanism': mode.get('mechanism', ''),
                }
        fallback = rule.get('fallback')
        if fallback:
            return {
                'code': fallback['code'],
                'label': fallback['label'],
                'verification': fallback.get('verification', ''),
                'mechanism': fallback.get('mechanism', ''),
            }
    fb = library.get('default_fallback', {})
    return {
        'code': fb.get('code', 'DEGRADED'),
        'label': fb.get('label', 'degraded / suspect'),
        'verification': fb.get('verification', 'Isolate the component and verify its characteristic behavior'),
        'mechanism': fb.get('mechanism', 'component behavior is outside specification'),
    }


def expected_affected_nets(
    own_net: str,
    functional_downstream_nets: Set[str],
) -> Set[str]:
    """Nets a fault in ``refdes`` would plausibly affect, by mechanism.

    - The component's own net is always expected.
    - Active components additionally affect every net of their functional
      downstream dependents (power/data dependency chains).
    - Passive components (no functional dependents) affect only their own net:
      propagating a failure past an active device would require assuming that
      device is also affected, which the mechanism layer refuses to do.
      Electrical reachability alone therefore never proves causality.
    """
    expected = {own_net} if own_net else set()
    expected.update(functional_downstream_nets)
    return expected


def expected_vs_observed(
    expected_nets: Set[str],
    failed_tests: List[Dict[str, Any]],
    passing_nets: Set[str],
) -> Dict[str, Any]:
    """Compare a mechanism's expected effects against what was actually observed.

    Returns:
      explained          — failed tests on expected nets
      unexpected         — failed tests NOT on expected nets (the hypothesis
                           has no plausible mechanism for them)
      expected_but_passed — nets the mechanism predicts should fail that were
                           observed passing (a weakening/contradiction signal)
      coverage_pct       — explained / total failed tests
    """
    explained = []
    unexpected = []
    for test in failed_tests:
        net = test.get('net', '')
        (explained if net in expected_nets else unexpected).append(test['test_step'])
    expected_but_passed = sorted(expected_nets & passing_nets)
    total = max(len(failed_tests), 1)
    return {
        'explained': explained,
        'unexpected': unexpected,
        'expected_but_passed': expected_but_passed,
        'coverage_pct': round(len(explained) / total * 100),
    }
