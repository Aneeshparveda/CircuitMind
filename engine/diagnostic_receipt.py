"""Diagnostic Receipt — pure formatter / extractor.

Reads ``report["diagnostic_contract"]`` and produces a compact,
serializable receipt structure for audit, PDF, CSV, and UI consumption.

This module MUST NOT:
- perform diagnosis or scoring
- rank candidates or filter hypotheses
- recalculate mechanism coverage
- create new rejection reasons
- access retrieval, topology, or counterfactual engines
"""

from typing import Any, Dict, List, Optional

RECEIPT_VERSION = "1.0.0"


def extract_diagnostic_receipt(report: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract a compact diagnostic receipt from the report's diagnostic contract.

    Returns ``None`` when no diagnostic contract is present (e.g. PASS boards).
    Every field is read directly from the contract — no new reasoning is applied.
    """
    contract = report.get('diagnostic_contract')
    if not contract:
        return None

    observed = contract.get('observed', {})
    inferred = contract.get('inferred', {})
    rejected_raw: List[Dict[str, Any]] = contract.get('rejected', [])
    recommended = contract.get('recommended', {})
    verification = contract.get('verification', {})

    # ── OBSERVED ──
    receipt_observed = {
        'failed_test_count': observed.get('failed_test_count', 0),
        'primary_domain': str(observed.get('primary_domain', 'UNKNOWN')),
        'severity': str(observed.get('severity', 'UNKNOWN')),
        'deviation_range': observed.get('deviation_range', [0.0, 0.0]),
        'failed_tests': list(observed.get('failed_tests', [])),
        'fingerprint': str(observed.get('fingerprint', '')),
    }

    # ── INFERRED ──
    receipt_inferred = {
        'leading_refdes': str(inferred.get('leading_refdes', '')),
        'leading_desc': str(inferred.get('leading_desc', '')),
        'evidence_score': float(inferred.get('evidence_score', 0.0)),
        'fault_mode': inferred.get('fault_mode'),
        'mechanism_coverage_pct': int(inferred.get('mechanism_coverage_pct', 0)),
        'mechanism_explained': list(inferred.get('mechanism_explained', [])),
        'mechanism_unexplained': list(inferred.get('mechanism_unexplained', [])),
        'confidence_tier': str(inferred.get('confidence_tier', '')),
        'diagnosis_state': str(inferred.get('diagnosis_state', '')),
        'ood_state': str(inferred.get('ood_state', 'UNKNOWN')),
    }

    # ── REJECTED ──
    receipt_rejected: List[Dict[str, Any]] = []
    for alt in rejected_raw:
        receipt_rejected.append({
            'refdes': str(alt.get('refdes', '')),
            'desc': str(alt.get('desc', '')),
            'score': float(alt.get('score', 0.0)),
            'mechanism_coverage_pct': int(alt.get('mechanism_coverage_pct', 0)),
            'rejection_reason': str(alt.get('rejection_reason', '')),
            'evidence_gap': str(alt.get('evidence_gap', '')),
        })

    # ── RECOMMENDED ──
    receipt_recommended = {
        'action': str(recommended.get('action', '')),
        'target': str(recommended.get('target', '')),
        'rationale': str(recommended.get('rationale', '')),
        'next_best_test': recommended.get('next_best_test'),
    }

    # ── VERIFICATION (preserved as-is, nested) ──
    receipt_verification = {
        'state': str(verification.get('state', 'PENDING_VERIFICATION')),
        'technician_confirmed': bool(verification.get('technician_confirmed', False)),
        'physical_repair_recorded': bool(verification.get('physical_repair_recorded', False)),
        'retest_passed': bool(verification.get('retest_passed', False)),
        'verified_repair': bool(verification.get('verified_repair', False)),
        'repair_memory_admitted': bool(verification.get('repair_memory_admitted', False)),
        'disclaimer': str(verification.get('disclaimer', 'Physical verification still required.')),
    }

    return {
        'receipt_version': RECEIPT_VERSION,
        'case_number': str(contract.get('case_number', '')),
        'board_id': str(contract.get('board_id', '')),
        'timestamp': str(contract.get('timestamp', '')),
        'observed': receipt_observed,
        'inferred': receipt_inferred,
        'rejected': receipt_rejected,
        'recommended': receipt_recommended,
        'verification': receipt_verification,
    }
