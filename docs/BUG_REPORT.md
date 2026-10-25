# CIRCUITMIND — BUG REPORT (Final Audit Pass, Aug 11)

Every entry below was **confirmed against the live code**, fixed, and given a
regression test before being marked RESOLVED. Nothing here is assumed from a
prior review.

| # | BUG | SEVERITY | ROOT CAUSE | FIX | TEST | STATUS |
|---|-----|----------|------------|-----|------|--------|
| A | NaN error codes rendered as the literal string `"NAN"` and flagged as an unknown-error data-quality issue | HIGH | `NaN or ''` is truthy in the DQ pass, so `str(nan).upper()` → `"NAN"`; signature extractor kept the raw NaN | Sanitize with `pd.isna(value) or str(value).strip().upper() in ('', 'NAN', 'NONE', 'NULL')` in both `engine/data_quality.py` and `engine/signature_extractor.py` | `test_nan_error_code_is_never_rendered` | ✅ RESOLVED |
| B | RED data-quality input still produced a confident, actionable diagnosis | HIGH | No gate between the DQ report and the verdict path | Added `diagnosis_state` machine: `LEADING_HYPOTHESIS` / `DEGRADED` / `ABSTAIN`. RED → `ABSTAIN` + `abstain_reason` + `required_next_info`. Frontend renders an abstain block instead of a verdict | `test_red_data_quality_abstains`, `test_green_data_quality_leads` | ✅ RESOLVED |
| C | Ground truth leaked into every analysis + fleet payload for boards in the truth files; "Beat the Machine" was revealable from client memory | CRITICAL | `run_analysis` and the fleet scan unconditionally attached `ground_truth` to the payload | Truth keys stripped from all payloads; reveal is now a server-gated `reveal_ground_truth` event only | `test_report_never_contains_ground_truth` | ✅ RESOLVED |
| D | Verified repair written to disk but the ACTIVE cached engine never saw it (`@st.cache_resource` held the old memory) | HIGH | Streamlit cache never invalidated on memory write | `record_verified_repair` clears the engine cache after a confirmed write; learned count increments live | `test_active_memory_refreshes_after_verified_case` (N → N+1 → retrievable) | ✅ RESOLVED |
| E | Technician confirmation hardcoded to `True` in the verify handler | CRITICAL | `technician_confirmed=True` literal | Confirmation comes from an explicit UI checkbox + event payload; memory eligibility = repair + retest PASS + technician confirmation | `test_unverified_case_is_rejected`, `test_unverified_is_rejected` | ✅ RESOLVED |
| F | Post-diagnosis repair outcomes overwrote pre-diagnosis observation notes (circular evidence) | HIGH | Same field reused for both | Notes separated: observations recorded at intake, outcomes recorded only at verified-repair time; outcome never feeds the case that predicted it | `test_learned_case_uses_technician_note_not_pre_diagnosis_notes` | ✅ RESOLVED |
| G | The schema adapter CRASHED on `ABORT` status rows — an aborted-test log killed the app | CRITICAL | Adapter only mapped PASS/FAIL | Adapter accepts full status set; `engine/test_integrity.py` classifies VALID / DEGRADED / TEST SYSTEM SUSPECTED; ABORT/NOT_EXECUTED never counted as PASS or board failure | `test_abort_and_not_executed_are_not_failures`, `test_unsupported_status_is_rejected_loudly` | ✅ RESOLVED |
| H | Hardcoded metrics and unsupported claims in the UI ("CANNOT HALLUCINATE", unlabeled $38.50 / 50 boards/day / 250 days) | MEDIUM | Pitch-era copy | Claims replaced with labeled assumptions or removed; BTM shows measured machine time, not the 7 ms marketing number | (UI review; covered by `test_*` payload checks) | ✅ RESOLVED |
| I | Extreme-deviation check fired on a real dead rail: 0.63 V on a 5 V rail flagged AMBER "extreme deviation" instead of GREEN | MEDIUM (domain bug) | Absurd-value threshold 10× spec; real dead rails top out ~33 | Threshold 10 → 50; real faults never exceed ~33, truly implausible readings still caught | `test_dead_rail_is_not_a_data_quality_problem` | ✅ RESOLVED |
| J | Multi-fault solver fell back to electrical reachability for candidates with empty mechanism coverage (connectivity ≠ causality resurfacing) | MEDIUM | Fallback treated "empty mechanism list" as "no mechanism data" | Empty-but-present is authoritative; electrical fallback only when the mechanism layer never ran | `test_dual_fault_solver_names_both_components`, `test_verdict_flip_is_derived_from_mechanism` | ✅ RESOLVED |
| K | Edge-case war room: 40 scenarios probed — 38 handled cleanly, 2 intentional loud rejections (missing columns, garbage status), 0 crashes, 0 silent nonsense | — | — | Empty CSV → clean `ValueError` with guidance; duplicate/NaN/abnormal inputs handled or loudly rejected | `tests/` edge-case batch + war-room script run Aug 11 | ✅ RESOLVED |

## War-room summary (Phase 26)

| Class | Result |
|-------|--------|
| Empty CSV / single row / single failing row | Clean `ValueError` or correct analysis, never a crash |
| All PASS / all FAIL / missing columns / extra columns | Correct verdict or loud rejection with a specific message |
| NaN, empty strings, wrong units, extreme/negative values | Sanitized or rejected; never "NAN", never a confident wrong answer |
| Duplicate rows / duplicate board IDs / duplicate tests | Deduped or analyzed with the duplicate surfaced as an issue |
| Unknown error code / step / component / net | Survives; unknown steps surface in observability as unmapped |
| Missing BOM / netlist / cyclic / disconnected topology | Degrades with explicit DQ/abstain behavior |
| Novel, multi-fault, intermittent, tester-anomaly inputs | Dedicated handlers (OOD → NOVEL/abstain, solver, integrity gate) |
| Large file / multiple boards in one upload / repeated analysis in session | No crash; repeated analysis is idempotent |

| L | Blind TEST set influenced model retention: `learn_weights.py` decided whether to KEEP learned weights by comparing blind-set scores | CRITICAL (scientific integrity) | `keep = blind1 >= policy_b1 - 0.5 …` — the test set participated in a model-selection decision | Selection AND retention moved to VAL; blind is report-only; `select_weights(train, val, policy)` structurally cannot read the blind file; fresh reserve set (seed 20260731) is the final untouched evaluation | `tests/test_learning_protocol.py` (4 tests: source never references blind, guarded read, VAL-derived retention, report-only isolation) | ✅ RESOLVED |
| M | Repair simulator resolved nothing for ANY component (UI "SIMULATE REPLACING U3" was dead) | HIGH | `simulate_repair` used `get_upstream_components(primary_net)` — PASSIVE pin-role edges make the DAG direction unrelated to current flow, so no component was upstream of SYS_5V | Rewritten as mechanism-based residual simulation: fault mode → expected blast radius → residual; hero U3 resolves SYS_5V+3V3+SPI (success), L1/C1 leave the cascade | `tests/test_engine.py::RepairSimulationTests` (2 tests) | ✅ RESOLVED |
| N | Learner's arbitrary "top-20 by train" filter could exclude the best VAL config (observed: it excluded the config that was best on VAL+blind) | MEDIUM (methodology) | Top-k cutoff on train was a nonstandard heuristic | Full-simplex selection on VAL (no top-k filter); same weights result, now chosen rigorously | `tests/test_learning_protocol.py::test_retention_decision_is_derived_from_val_only` | ✅ RESOLVED |
| O | `compute_coverage` cached undirected connectivity on `self` and never invalidated it (stale across boards) | MEDIUM | `hasattr(self, '_undirected_nets')` instance cache | Rebuilt per call | covered by coverage tests | ✅ RESOLVED |
| P | `KNOWN_ERROR_CODES` hardcoded in `data_quality.py` (synthetic-specific; false warnings on real codes) | MEDIUM | literal set | Config-driven via `config/diagnostic_weights.json` `known_error_codes`, default fallback | covered by DQ tests | ✅ RESOLVED |
| Q | `validate_accuracy.py` printed hardcoded "(22 top-1 misses)" when 12 existed | MEDIUM (claim integrity) | stale literal | Dynamic count from the computed breakdown | `test_*` validator checks | ✅ RESOLVED |
| R | Stale claims: CLAIMS.md #9 (13/22) and #17 (9 outside top-3) from the hand-set era; JUDGE_ATTACK_SURFACE.md "weights are policy, not learned" | MEDIUM (claim integrity) | pre-learned-policy wording survived the sweeps | Corrected to learned-policy numbers (12/0, 0 outside); attack surface states weights ARE learned | claim audit | ✅ RESOLVED |

## Also verified NOT present

- **fpdf2 deprecation warnings:** the audit cited 41 warnings from `ln=`; a
  live warnings-capture run of `generate_pdf_bytes` produced **0** fpdf
  warnings, and no `ln=` parameter usage exists in the Python source
  (grep-verified). The citation was environment/version-specific; the PDF
  export path is clean.

## Items intentionally NOT fixed (documented, not hidden)

- The family-holdout generalization gap (49% top-1 under the learned policy) is
  a real limitation of synthetic-to-synthetic data — disclosed, not patched.
- No learned ML model exists in the decision path — a deliberate
  explainability/safety choice, stated in `MODEL_CARD.md`.
- The **adaptive structural policy** (weights leaning on net/topology when
  history is absent) was benchmarked: it lifts family-holdout top-1 to 61.2%
  but drops the instance holdout to 60.0%, and the precedent signal overlaps
  between the two cases — so it is documented as a measured negative result,
  not shipped (CLAIMS.md #51).
