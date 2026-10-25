"""Data-quality gate.

Inspects a board's standardized log *before* diagnosis and reports a
GREEN / AMBER / RED status with specific issues. The engine never silently
guesses: anything the model cannot map is surfaced here.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
DEFAULT_ERROR_CODES = {'VAL', 'FNC', 'OPN', 'SHT', ''}


def _known_error_codes() -> set:
    """Recognized error codes for the active test program, from the diagnostic
    configuration when present (audit B2: the set is config-driven, not
    hardcoded — a different factory's codes extend config, not code)."""
    try:
        cfg = json.loads((CONFIG_DIR / 'diagnostic_weights.json').read_text(encoding='utf-8'))
        codes = cfg.get('known_error_codes')
        if codes:
            return {str(c).strip().upper() for c in codes} | {''}
    except (OSError, json.JSONDecodeError):
        pass
    return DEFAULT_ERROR_CODES


KNOWN_ERROR_CODES = _known_error_codes()


def analyze_board_log(
    board_rows,
    test_map,
    signature: Dict[str, Any],
    unknown_nets_ratio_threshold: float = 0.5,
) -> Dict[str, Any]:
    """Return {status, issues, summary} for one board.

    ``board_rows`` — the standardized DataFrame rows for the board under test.
    ``test_map`` — dict test_step -> row from data/test_net_map.csv.
    ``signature`` — the SignatureExtractor output for the same board.
    """
    issues: List[Dict[str, str]] = []
    known_steps = set(test_map.keys())
    total_tests = len(board_rows)

    failed = signature.get('failed_tests', [])
    failed_steps = [t['test_step'] for t in failed]
    unknown_steps = [step for step in failed_steps if step not in known_steps]
    if unknown_steps:
        issues.append({
            'level': 'AMBER',
            'message': (
                f"{len(unknown_steps)} failing test step(s) are not in the test map "
                f"({', '.join(unknown_steps[:3])}{' …' if len(unknown_steps) > 3 else ''}). "
                "Their evidence cannot be attributed to a net."
            ),
        })

    unmapped_failed = [t for t in failed if t.get('net') == 'UNKNOWN']
    if unmapped_failed:
        ratio = len(unmapped_failed) / max(len(failed), 1)
        level = 'RED' if ratio >= unknown_nets_ratio_threshold else 'AMBER'
        issues.append({
            'level': level,
            'message': (
                f"{len(unmapped_failed)}/{len(failed)} failing tests map to no net "
                f"({', '.join(t['test_step'] for t in unmapped_failed[:3])}). "
                "Coverage and ranking for those failures rest on partial evidence."
            ),
        })

    missing_measured = 0
    malformed_ranges = 0
    novel_codes = set()
    for _, row in board_rows.iterrows():
        measured = row.get('measured_value')
        emin = row.get('expected_min')
        emax = row.get('expected_max')
        status = str(row.get('pass_fail', '')).upper()
        if status == 'FAIL' and (measured is None or _is_nan(measured)):
            missing_measured += 1
        if emin is not None and emax is not None and not _is_nan(emin) and not _is_nan(emax):
            if emin >= emax and not (emin == emax == 1):
                malformed_ranges += 1
        code = _clean_error_code(row.get('error_code'))
        if code and code not in KNOWN_ERROR_CODES:
            novel_codes.add(code)
    if missing_measured:
        issues.append({
            'level': 'AMBER',
            'message': f"{missing_measured} failing test(s) have no measured value — deviation is estimated, not measured.",
        })
    if malformed_ranges:
        issues.append({
            'level': 'AMBER',
            'message': f"{malformed_ranges} test(s) have inverted or degenerate expected ranges.",
        })
    if novel_codes:
        issues.append({
            'level': 'AMBER',
            'message': f"Unrecognized error code(s): {', '.join(sorted(novel_codes))} — treated as novel signals.",
        })

    dupes = 0
    seen = set()
    for _, row in board_rows.iterrows():
        key = str(row.get('test_step', ''))
        if key in seen:
            dupes += 1
        seen.add(key)
    if dupes:
        issues.append({
            'level': 'AMBER',
            'message': f"{dupes} duplicate test row(s) in the log.",
        })

    # Only PHYSICALLY IMPLAUSIBLE readings are a data-quality problem. A dead
    # rail at 0.63 V on a 5 V rail is the fault itself (deviation ~20-35); the
    # measured corpus never exceeds ~33 for real failures. Absurd readings
    # (e.g. 500 V on a 5 V rail -> deviation ~2500) start well above 50, so
    # that threshold catches bad data without flagging legitimate fault
    # signatures (Phase 3 domain audit).
    extreme = [t['test_step'] for t in failed if t.get('deviation', 0) and t['deviation'] > 50]
    if extreme:
        issues.append({
            'level': 'AMBER',
            'message': f"Physically implausible deviation(s) on {', '.join(extreme[:3])} — verify the measurement before trusting it.",
        })

    if total_tests == 0:
        issues.insert(0, {'level': 'RED', 'message': 'The log contains no test rows for this board.'})

    # Overall status: any RED wins; else any AMBER; else GREEN.
    if any(issue['level'] == 'RED' for issue in issues):
        status = 'RED'
    elif issues:
        status = 'AMBER'
    else:
        status = 'GREEN'

    labels = {
        'GREEN': 'Complete investigation input',
        'AMBER': 'Partial evidence — diagnosis proceeds with known gaps',
        'RED': 'Insufficient evidence for a reliable diagnosis',
    }
    return {
        'status': status,
        'label': labels[status],
        'issues': issues,
        'summary': {
            'total_tests': total_tests,
            'failed_tests': len(failed),
            'unmapped_failed_tests': len(unmapped_failed),
            'unknown_failed_steps': len(unknown_steps),
        },
    }


def _is_nan(value: Any) -> bool:
    try:
        return value != value  # NaN check
    except Exception:
        return False


def _clean_error_code(value: Any) -> str:
    """Normalize an error-code cell to a clean uppercase string.

    Empty / missing / NaN cells must become '' — never the literal string
    'NAN' (a NaN float is truthy, so `value or ''` is NOT sufficient).
    """
    if value is None:
        return ''
    if isinstance(value, float) and value != value:  # NaN
        return ''
    text = str(value).strip().upper()
    if text in {'', 'NAN', 'NONE', 'NULL', 'NA'}:
        return ''
    return text
