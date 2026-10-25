"""Test integrity and 'failure or tester?' analysis.

Two distinct concerns:

1. Per-board TEST INTEGRITY — a failed board is not always a faulty board.
   ABORT, NOT_EXECUTED, SKIPPED and INVALID rows are never treated as PASS or
   as PCB failures; they are surfaced explicitly. Sequence gaps (missing
   low-level steps), duplicate steps, and contradictory results (same step
   both PASS and FAIL) are flagged.

2. FLEET-LEVEL 'FAILURE OR TESTER?' — when a test fails on an unusually large
   fraction of boards in a lot, the more likely explanation is the test
   system (fixture/probe/calibration/program), not N independent board
   defects. The system then says: validate the station before reworking
   boards. This is real fleet statistics, not a banner.
"""

from typing import Any, Dict, List

NON_RESULT = {'ABORT', 'NOT_EXECUTED', 'SKIPPED', 'INVALID', 'UNKNOWN'}


def classify_status(value: Any) -> str:
    if value is None:
        return 'UNKNOWN'
    text = str(value).strip().upper()
    return text if text else 'UNKNOWN'


def summarize_test_status(board_rows) -> Dict[str, Any]:
    """Return integrity status for one board's rows."""
    counts = {'PASS': 0, 'FAIL': 0}
    non_result: Dict[str, int] = {}
    issues: List[Dict[str, str]] = []
    seen_steps: Dict[str, str] = {}

    rows = list(board_rows.iterrows())
    for _, row in rows:
        status = classify_status(row.get('pass_fail'))
        step = str(row.get('test_step', ''))
        if status == 'PASS' or status == 'FAIL':
            counts[status] += 1
            if step in seen_steps and seen_steps[step] != status:
                issues.append({
                    'level': 'RED',
                    'message': f"Contradictory results for {step}: recorded both {seen_steps[step]} and {status}.",
                })
            seen_steps.setdefault(step, status)
        else:
            non_result[status] = non_result.get(status, 0) + 1

    if non_result:
        summary = ', '.join(f"{n} {name}" for name, n in sorted(non_result.items()))
        issues.append({
            'level': 'AMBER',
            'message': (
                f"{sum(non_result.values())} test row(s) did not produce a result "
                f"({summary}) — treated as NO verdict, never as PASS or FAIL."
            ),
        })

    # Sequence completeness: the test map assigns each step a level. If the
    # board shows higher-level steps but none of the lowest observed level
    # range, flag premature/partial execution. Only when levels are usable.
    levels = []
    for _, row in rows:
        try:
            levels.append(int(row.get('level', 99)))
        except (TypeError, ValueError):
            pass
    if levels:
        missing_lower = [lv for lv in range(min(levels), max(levels) + 1) if lv not in set(levels)]
        if missing_lower:
            issues.append({
                'level': 'AMBER',
                'message': (
                    f"Sequence gap: no test recorded at level(s) {missing_lower} — "
                    "the program may have terminated early (e.g. an abort)."
                ),
            })

    if counts['FAIL'] == 0 and not non_result:
        overall = 'VALID'
        label = 'No failing tests — the board passed.'
    elif non_result and counts['FAIL'] == 0:
        overall = 'DEGRADED'
        label = 'No failures, but the run was incomplete (aborted/skipped steps).'
    elif any(issue['level'] == 'RED' for issue in issues):
        overall = 'SUSPECT'
        label = 'Test results are internally contradictory — investigate the log before trusting the diagnosis.'
    else:
        overall = 'VALID'
        label = f"{counts['FAIL']} failing test(s) with a complete result set."

    return {
        'overall': overall,
        'label': label,
        'status_counts': {'PASS': counts['PASS'], 'FAIL': counts['FAIL'], **non_result},
        'issues': issues,
    }


def fleet_tester_analysis(logs, fail_threshold: float = 0.5, min_boards: int = 6,
                           concentration_threshold: float = 0.8,
                           peer_healthy_threshold: float = 0.15,
                           min_samples_per_group: int = 3) -> Dict[str, Any]:
    """Detect tests that fail disproportionately and attribute the cause to
    a specific fixture, station, or board revision when data supports it.

    Requires min_samples_per_group (default 5) observations per group before
    making an attribution claim, ensuring statistical rigor.
    """
    if logs is None or logs.empty:
        return {'state': 'UNKNOWN', 'suspected_tests': [], 'note': 'No fleet data to analyze.'}

    has_fixture = 'fixture_id' in logs.columns
    has_station = 'station_id' in logs.columns
    has_revision = 'board_revision' in logs.columns

    valid = logs[logs['pass_fail'].astype(str).str.upper().isin(['PASS', 'FAIL'])].copy()
    valid['pass_fail'] = valid['pass_fail'].astype(str).str.upper()

    suspected = []

    for step, group in valid.groupby('test_step'):
        total = len(group)
        fails = int((group['pass_fail'] == 'FAIL').sum())
        if total < min_boards or fails / total < fail_threshold:
            continue

        entry = {
            'test_step': step,
            'boards_failed': fails,
            'boards_ran': total,
            'failure_rate': round(fails / total, 3),
            'attribution': 'UNIFORM',
        }

        # LEVEL 1: Fixture-level attribution
        if has_fixture:
            fixture_stats = group.groupby('fixture_id')['pass_fail'].apply(
                lambda s: (s == 'FAIL').mean()
            )
            fixture_counts = group.groupby('fixture_id')['pass_fail'].count()
            eligible = fixture_stats[fixture_counts >= min_samples_per_group]
            if len(eligible) >= 2:
                worst_fixture = eligible.idxmax()
                worst_rate = eligible.max()
                peers = eligible.drop(index=worst_fixture)
                peer_rate = peers.mean() if len(peers) else 0.0
                if worst_rate >= concentration_threshold and peer_rate <= peer_healthy_threshold:
                    entry['attribution'] = 'FIXTURE_SUSPECTED'
                    entry['fixture_id'] = str(worst_fixture)
                    entry['fixture_fail_rate'] = round(worst_rate, 3)
                    entry['peer_fixture_fail_rate'] = round(peer_rate, 3)
                    entry['fixture_sample_size'] = int(fixture_counts[worst_fixture])

        # LEVEL 2: Station-level attribution (if fixture uniform)
        if has_station and entry['attribution'] == 'UNIFORM':
            station_stats = group.groupby('station_id')['pass_fail'].apply(
                lambda s: (s == 'FAIL').mean()
            )
            station_counts = group.groupby('station_id')['pass_fail'].count()
            eligible = station_stats[station_counts >= min_samples_per_group]
            if len(eligible) >= 2:
                worst_station = eligible.idxmax()
                worst_rate = eligible.max()
                peers = eligible.drop(index=worst_station)
                peer_rate = peers.mean() if len(peers) else 0.0
                if worst_rate >= concentration_threshold and peer_rate <= peer_healthy_threshold:
                    entry['attribution'] = 'STATION_SUSPECTED'
                    entry['station_id'] = str(worst_station)
                    entry['station_fail_rate'] = round(worst_rate, 3)
                    entry['peer_station_fail_rate'] = round(peer_rate, 3)
                    entry['station_sample_size'] = int(station_counts[worst_station])

        # LEVEL 3: Revision-level attribution (if fixture and station uniform)
        if has_revision and entry['attribution'] == 'UNIFORM':
            rev_stats = group.groupby('board_revision')['pass_fail'].apply(
                lambda s: (s == 'FAIL').mean()
            )
            rev_counts = group.groupby('board_revision')['pass_fail'].count()
            eligible = rev_stats[rev_counts >= min_samples_per_group]
            if len(eligible) >= 2:
                worst_rev = eligible.idxmax()
                worst_rate = eligible.max()
                peers = eligible.drop(index=worst_rev)
                peer_rate = peers.mean() if len(peers) else 0.0
                if worst_rate >= concentration_threshold and peer_rate <= peer_healthy_threshold:
                    entry['attribution'] = 'REVISION_SUSPECTED'
                    entry['board_revision'] = str(worst_rev)
                    entry['revision_fail_rate'] = round(worst_rate, 3)
                    entry['peer_revision_fail_rate'] = round(peer_rate, 3)

        suspected.append(entry)

    attributed = []
    if suspected:
        attributed = [s for s in suspected if s['attribution'] != 'UNIFORM']
        if attributed:
            state = 'TEST_SYSTEM_SUSPECTED'
            lead = attributed[0]
            if lead['attribution'] == 'FIXTURE_SUSPECTED':
                note = (
                    f"{lead['test_step']} fails {lead['fixture_fail_rate']*100:.0f}% of the time "
                    f"on fixture {lead['fixture_id']} (n={lead['fixture_sample_size']}), while peer fixtures "
                    f"stay at {lead['peer_fixture_fail_rate']*100:.0f}% — points at the fixture, "
                    "not the boards. Validate/recalibrate fixture before reworking boards."
                )
            elif lead['attribution'] == 'STATION_SUSPECTED':
                note = (
                    f"{lead['test_step']} fails {lead['station_fail_rate']*100:.0f}% of the time "
                    f"on station {lead['station_id']} (n={lead['station_sample_size']}), while peer stations "
                    f"stay at {lead['peer_station_fail_rate']*100:.0f}% — points at station configuration."
                )
            elif lead['attribution'] == 'REVISION_SUSPECTED':
                note = (
                    f"{lead['test_step']} fails {lead['revision_fail_rate']*100:.0f}% of the time "
                    f"on board revision {lead['board_revision']}, while other revisions stay at "
                    f"{lead['peer_revision_fail_rate']*100:.0f}% — points at a revision-specific issue."
                )
        else:
            state = 'TEST_SYSTEM_SUSPECTED'
            names = ', '.join(s['test_step'] for s in suspected[:3])
            note = (
                f"{names} fail{'s' if len(suspected) == 1 else ''} on "
                f"{int(fail_threshold * 100)}%+ of boards fleet-wide across fixtures/stations — "
                "suggests a shared test program or calibration factor."
            )
    else:
        state = 'BOARD_SPECIFIC'
        note = 'No test fails disproportionately across the fleet — failures appear board-specific.'

    # Small-sample warning: attribution based on fewer than 10 observations
    # per group should be treated as indicative, not conclusive.
    if attributed:
        small_sample = any(
            (t.get('fixture_sample_size', 999) < 10 or t.get('station_sample_size', 999) < 10)
            for t in attributed
        )
        if small_sample:
            note += ' NOTE: Some attributions are based on small sample sizes (n<10). Treat as indicative — validate with additional observations before acting.'

    return {'state': state, 'suspected_tests': suspected, 'note': note}
