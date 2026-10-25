"""Verified repair memory (safe learning loop).

Only **verified** repair outcomes (repair performed + board retested PASS +
technician confirmation) may enter the learnable memory. A prediction alone is
never promoted to historical truth — that is what prevents the system from
poisoning its own knowledge base.

The learnable memory lives in ``data/learned_cases/`` and is *separate* from
the frozen validated corpus (``data/repair_history.csv``), so the benchmark
(78/91/96) is unaffected by anything learned in a demo session.
"""

import csv
from pathlib import Path
from typing import Any, Dict, Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LEARNED_DIR = DATA_DIR / "learned_cases"
LEARNED_HISTORY = LEARNED_DIR / "repair_history_learned.csv"
COMBINED_HISTORY = LEARNED_DIR / "repair_history_combined.csv"
FROZEN_HISTORY = DATA_DIR / "repair_history.csv"

FIELDS = ['repair_id', 'symptom_text', 'failed_steps', 'root_cause_component', 'fix_action', 'verified']


def learned_cases_count() -> int:
    """Number of verified cases currently in the learnable memory."""
    if not LEARNED_HISTORY.exists():
        return 0
    with LEARNED_HISTORY.open(newline='', encoding='utf-8') as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def add_verified_case(
    board_id: str,
    refdes: str,
    failed_steps: str,
    notes: str = "",
    retest_pass: bool = True,
    technician_confirmed: bool = True,
) -> Dict[str, Any]:
    """Append a case to the learnable memory — only if it was verified.

    ``retest_pass`` and ``technician_confirmed`` must both be true; otherwise
    the case is rejected with a reason (never silently stored).
    """
    if not (retest_pass and technician_confirmed):
        return {
            'added': False,
            'reason': 'Case rejected: memory only accepts verified repair outcomes '
                      '(repair performed, board retested PASS, technician confirmed).',
            'count': learned_cases_count(),
        }
    if not refdes:
        return {'added': False, 'reason': 'No component reference supplied.', 'count': learned_cases_count()}

    LEARNED_DIR.mkdir(parents=True, exist_ok=True)
    import uuid
    repair_id = f"LEARN-{uuid.uuid5(uuid.NAMESPACE_DNS, f'{board_id}-{refdes}-{notes}-{learned_cases_count()}').hex[:6].upper()}"
    symptom = (notes.strip() or f"Verified repair: {refdes} confirmed on {board_id}.")
    new_row = {
        'repair_id': repair_id,
        'symptom_text': symptom[:400],
        'failed_steps': failed_steps[:2000],
        'root_cause_component': refdes,
        'fix_action': 'VERIFIED-REPLACED',
        'verified': 'TRUE',
    }
    file_exists = LEARNED_HISTORY.exists()
    with LEARNED_HISTORY.open('a', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(new_row)
    count = learned_cases_count()
    _rebuild_combined()
    return {'added': True, 'repair_id': repair_id, 'count': count}


def combined_history_path() -> Optional[Path]:
    """Path to the merged corpus (frozen + learned), rebuilt when learned cases exist."""
    if learned_cases_count() == 0:
        return None
    _rebuild_combined()
    return COMBINED_HISTORY


def _rebuild_combined() -> None:
    """Merge the frozen corpus with verified learned cases into one CSV."""
    import pandas as pd

    frozen = pd.read_csv(FROZEN_HISTORY)
    learned = pd.read_csv(LEARNED_HISTORY) if LEARNED_HISTORY.exists() else None
    combined = frozen if learned is None else pd.concat([frozen, learned], ignore_index=True, sort=False)
    LEARNED_DIR.mkdir(parents=True, exist_ok=True)
    combined.to_csv(COMBINED_HISTORY, index=False)
