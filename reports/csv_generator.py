"""CSV export of the ranked diagnostic results."""

import csv
from io import StringIO
from typing import Any, Dict

from engine.diagnostic_receipt import extract_diagnostic_receipt


def generate_csv_bytes(report: Dict[str, Any]) -> bytes:
    """
    Return an in-memory CSV of the ranked diagnostic results.

    Includes a case summary row followed by the full ranked candidate list
    with per-candidate evidence, so the export stands alone as a triage record.
    """
    buffer = StringIO()
    writer = csv.writer(buffer)

    signature = report.get('signature', {})
    writer.writerow(['case_number', 'board_id', 'status', 'severity', 'primary_domain', 'confidence_tier',
                     'pattern_state', 'data_quality', 'engine_version'])
    ood = report.get('ood_state', {})
    dq = report.get('data_quality', {})
    versions = report.get('versions', {})
    writer.writerow([
        report.get('case_number', ''),
        report.get('board_id', ''),
        report.get('status', ''),
        signature.get('severity_label', ''),
        signature.get('primary_domain', ''),
        report.get('confidence_tier', ''),
        ood.get('state', ''),
        dq.get('status', ''),
        versions.get('engine', ''),
    ])

    repair_notes = report.get('repair_notes', '')
    if repair_notes:
        writer.writerow(['repair_notes', repair_notes])

    for issue in dq.get('issues', []):
        writer.writerow(['data_quality_' + str(issue.get('level', '')).lower(), issue.get('message', '')])

    multi = report.get('multi_fault_analysis', {})
    if multi:
        writer.writerow(['multi_fault_verdict', multi.get('verdict_text', '')])
        best = multi.get('best_single')
        if best:
            writer.writerow(['best_single_fault', ' + '.join(best.get('components', [])) if best.get('components') else '',
                             'coverage', best.get('coverage_pct')])
        best2 = multi.get('best_pair')
        if best2:
            writer.writerow(['best_two_fault', ' + '.join(best2.get('components', [])) if best2.get('components') else '',
                             'coverage', best2.get('coverage_pct')])

    writer.writerow([])
    writer.writerow(['failing_tests', 'net', 'domain', 'deviation', 'error_code'])
    for test in signature.get('failed_tests', []):
        writer.writerow([
            test.get('test_step', ''),
            test.get('net', ''),
            test.get('domain', ''),
            test.get('deviation', ''),
            test.get('error_code', ''),
        ])

    writer.writerow([])
    writer.writerow(['rank', 'refdes', 'description', 'category', 'net', 'fault_mode', 'score',
                     'positive_evidence', 'negative_evidence'])

    for rank, candidate in enumerate(report.get('suspects', []), start=1):
        fault_mode = candidate.get('fault_mode') or {}
        writer.writerow([
            rank,
            candidate.get('refdes', ''),
            candidate.get('desc', ''),
            candidate.get('cat', ''),
            candidate.get('net', ''),
            fault_mode.get('label', ''),
            candidate.get('score', 0.0),
            ' | '.join(candidate.get('positive_evidence', [])),
            ' | '.join(candidate.get('negative_evidence', [])),
        ])

    # ── DIAGNOSTIC RECEIPT ──
    receipt = extract_diagnostic_receipt(report)
    if receipt:
        writer.writerow([])
        writer.writerow(['diagnostic_receipt_version', receipt['receipt_version']])
        writer.writerow(['receipt_timestamp', receipt['timestamp']])
        writer.writerow(['receipt_inferred_refdes', receipt['inferred']['leading_refdes']])
        writer.writerow(['receipt_inferred_desc', receipt['inferred']['leading_desc']])
        writer.writerow(['receipt_inferred_score', receipt['inferred']['evidence_score']])
        writer.writerow(['receipt_inferred_coverage_pct', receipt['inferred']['mechanism_coverage_pct']])
        writer.writerow(['receipt_inferred_fault_mode', receipt['inferred']['fault_mode'] or ''])
        writer.writerow(['receipt_inferred_confidence_tier', receipt['inferred']['confidence_tier']])
        writer.writerow(['receipt_inferred_diagnosis_state', receipt['inferred']['diagnosis_state']])
        writer.writerow(['receipt_recommended_action', receipt['recommended']['action']])
        writer.writerow(['receipt_recommended_target', receipt['recommended']['target']])
        writer.writerow(['receipt_verification_state', receipt['verification']['state']])
        writer.writerow(['receipt_verification_disclaimer', receipt['verification']['disclaimer']])
        for i, alt in enumerate(receipt['rejected']):
            writer.writerow([
                f'receipt_rejected_{i + 1}',
                alt['refdes'], alt['desc'], alt['score'],
                alt['mechanism_coverage_pct'], alt['rejection_reason'],
                alt['evidence_gap'],
            ])

    return buffer.getvalue().encode('utf-8')
