# CIRCUITMIND — CLAIMS AUDIT

Audit date: Aug 11 (final senior pass). Method: every numeric/superlative claim
in the pitch-facing docs was mapped to a verified row in `CLAIMS.md` and its
evidence command re-run. The authoritative registry is `CLAIMS.md` (46 verified
rows); this file is the audit trail.

## Audit result

| Source | Claims checked | Mapped to registry | Unsupported found |
|--------|---------------|--------------------|-------------------|
| `PITCH.md` | all numbers | ✅ | 0 (swept after 78→88 move) |
| `JUDGE_ONEPAGER.md` | all numbers | ✅ | 0 |
| `DEMO_SCRIPT.md` | all numbers | ✅ | 0 (78% answers rewritten) |
| `STUDY_GUIDE.md` | all numbers | ✅ | 0 |
| `docs/DEMO_CASES.md` | all numbers | ✅ | 0 |
| `docs/JUDGE_ATTACK_SURFACE.md` | Q&A answers | ✅ | 0 |
| `data/DATA_CARD.md` | all numbers | ✅ | 0 |
| `docs/history/BASELINE.md` | all numbers | ✅ | 0 |
| `FINAL_AUDIT.md` | all numbers | ✅ | 0 |
| Frontend UI copy | metrics/claims | ✅ | 0 (hardcoded metrics removed/relabeled, "CANNOT HALLUCINATE" removed) |

## Claims actively removed or rewritten this pass

| Old claim | New wording |
|-----------|-------------|
| "CANNOT HALLUCINATE" | "BOM-bounded / evidence-bounded / traceable — no generative component invention" |
| "$38.50 per board saved" (unlabeled) | labeled as scenario assumption or removed |
| "50 boards/day, 250 days" projection | labeled as scenario assumption |
| "7 ms" Beat-the-Machine number | measured machine time of the live round |
| ground truth visible pre-reveal | server-gated reveal; payloads verified truth-free |

## Standing rule

If a sentence cannot be mapped to a verified `CLAIMS.md` row, do not say it.
Re-run `python3 validation/validate_accuracy.py` and the 41-test suite before
the event; rebuild `frontend-vite/dist` after any edit.
