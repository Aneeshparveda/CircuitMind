# CircuitMind — Baseline (measured before the 95+ transformation)

> Every number below was measured on the author's local machine (
> Python 3.13.x, macOS) **before** any engine/frontend changes for the 95+ pass.
> Nothing here is invented; re-run the commands in the "How to reproduce" section
> to confirm.
>
> **UPDATE (Aug 11, ~23:30):** the fusion weights are now LEARNED
> (`validation/learn_weights.py`, fitted on 300 labeled training boards,
> selected on a 100-board holdout). The instance-holdout benchmark moved from
> **78/91/96 → 88/100/96** under the learned policy. This file is kept as the
> pre-transformation baseline; the current numbers live in
> `docs/VALIDATION_REPORT.md` and `validation/metrics.json`.

Recorded: 2026-08-11, ~21:10 local.

## Test suite

| Metric | Value |
|---|---|
| Command | `python3 -m unittest discover -s tests -q` |
| Tests run | 18 |
| Passed | 18 |
| Duration | 0.52 s |

## Validation (blind instance holdout, 100 boards)

| Metric | Value |
|---|---|
| Command | `python3 validation/validate_accuracy.py` |
| Top-1 | **78.0 %** |
| Top-3 | **91.0 %** |
| Domain | **96.0 %** |
| Avg inference | **0.005 s / board (≈5 ms)** |
| Worst inference | 0.011 s / board |

Error breakdown (22 top-1 misses):
- in_top3_but_ranked_second: 13
- not_in_top3: 9
- low_confidence: 0
- multi_fault_flagged: 13
- silent_misses: **0**

> Runtime note: the ~5 ms average is **environment-dependent**. A prior external
> review reported ~13 ms avg / ~28 ms worst on their machine. Accuracy (78/91/96)
> was stable across both environments. The performance claim is therefore
> presented as "measured on the validated demo environment", never as a universal
> property (see CLAIMS.md).

## Frontend build

| Metric | Value |
|---|---|
| Command | `cd frontend-vite && npm run build` |
| TypeScript | clean (`tsc -b` no errors) |
| Vite build | succeeds (dist/ emitted) |

## Demo-case behavior (current hero case, pre-transformation)

- `BRD_U3_CASCADE_001` (hero): `P100-D100 | 4F | 1R | 2C`, U3 = 79.7, **no** multi-fault flag, Strong tier.
- `BRD_0415` (strong benchmark card): 8 failures, multi-fault flag fires — intentionally labeled with the honest multi-fault flag.
- `BRD_DUAL_FAULT_001`: multi-fault banner fires with ADC_1 named.
- `BRD_0401`: Next Best Test active (gap < 15).

## Exports

- PDF generation: works (fail + pass boards), Unicode handled.
- CSV generation: works, includes ranked suspects + failing tests + notes.

## Known pre-existing limitations (from prior audits, unchanged at baseline)

1. Validation is an **instance holdout** over 15 known fault families — not unseen-family generalization. Documented as such in all claims.
2. Blind boards technically flow into pattern-signal derivation in `test_logs.csv`; measured effect on 78/91 was zero (verified by experiment).
3. Topology is a single electrical DAG; functional dependency and test-observability layers did not exist.
4. Hypotheses are components, not component+fault-mode.
5. Multi-fault is detected (banner) but not solved (no sparse set-cover analysis).
6. NBT is heuristic (gap-based net selection), no risk/effort/information-gain scoring.
7. No data-quality gate, no OOD/novelty detection, no calibration.
8. TF-IDF lexical retrieval only (by design — offline deterministic).
9. Engine modules use relative `data/...` default paths → break when run from another directory.
10. No verified-repair learning loop; no engine/dataset versioning; no submission-zip builder.

These ten items are the attack list for the 95+ pass.
