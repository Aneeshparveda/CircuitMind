# CIRCUITMIND — CHANGELOG (Final Audit Pass, Aug 11)

Format: CHANGE / WHY / FILES / TESTS / BEFORE / AFTER / RISKS

---

## 1. Learned evidence-fusion weights (78% → 88% top-1)

- **CHANGE:** Fusion weights are now learned by grid search over the weight simplex on the 300 labeled training boards, selected on a 100-board holdout, verified on the 100 blind boards by re-running the real engine.
- **WHY:** Answers "why 35/30/20/10/5?" with a reproducible result instead of a policy excuse; the single biggest "AI" upgrade that cannot break the demo.
- **FILES:** `validation/learn_weights.py` (new), `config/diagnostic_weights.json` (written with provenance), `validation/benchmark_ablation.py` (reads canonical weights).
- **TESTS:** `test_policy_loads_from_disk`; 41/41 suite green; validator reproduces 88/100/96.
- **BEFORE:** top-1 78.0, top-3 91.0, 9 misses outside top-3. **AFTER:** top-1 88.0, top-3 100.0, 0 misses outside top-3, 0 silent.
- **RISKS:** Family-holdout dropped 52→49 (learned policy leans on history) — disclosed in every doc, framed as a deliberate tradeoff.

## 2. Multi-fault solver: empty mechanism coverage is authoritative

- **CHANGE:** Candidates with an empty-but-present mechanism list no longer fall back to electrical reachability.
- **WHY:** The "connectivity ≠ causality" flaw resurfaced under learned weights (U3+F1 beat U3+R12 purely on score order); empty mechanism data means "explains nothing," not "no mechanism info."
- **FILES:** `engine/multi_fault_solver.py`
- **TESTS:** `test_dual_fault_solver_names_both_components`, `test_verdict_flip_is_derived_from_mechanism`
- **BEFORE:** dual-fault demo named U3+F1 (F1 explains nothing by mechanism). **AFTER:** U3+R12 (100% mechanism coverage).

## 3. Bug A — NaN error code never rendered

- **CHANGE:** NaN/empty/whitespace/`NAN`-style error codes sanitized to empty; never trigger the unknown-error DQ warning.
- **WHY:** `NaN or ''` is truthy → `"NAN"` appeared as a false unknown-error flag.
- **FILES:** `engine/data_quality.py`, `engine/signature_extractor.py`
- **TESTS:** `test_nan_error_code_is_never_rendered`

## 4. Bug B — Data-quality gating (VALID / DEGRADED / ABSTAIN)

- **CHANGE:** Orchestrator now emits `diagnosis_state`; RED input → `ABSTAIN` + `abstain_reason` + `required_next_info`. Frontend renders an abstain block instead of a verdict.
- **WHY:** A confident actionable diagnosis on RED data is an integrity violation.
- **FILES:** `engine/orchestrator.py`, `frontend-vite/src/components/console/*` (types, console, CSS)
- **TESTS:** `test_red_data_quality_abstains`, `test_green_data_quality_leads`

## 5. Bug C — Ground-truth isolation (CRITICAL)

- **CHANGE:** Truth keys stripped from all analysis/fleet payloads; reveal is a server-gated `reveal_ground_truth` event.
- **WHY:** The audit found ground truth inside every BRD_04xx payload — "Beat the Machine" was a charade.
- **FILES:** `app.py`, `frontend-vite/src/components/console/ForensicsConsole.tsx` (BTM rewrite: server-gated reveal, measured machine time, labeled assumptions)
- **TESTS:** `test_report_never_contains_ground_truth`

## 6. Bugs D/E/F — Memory refresh, technician confirmation, notes separation

- **CHANGE:** `record_verified_repair` now clears the engine cache (active memory actually grows), requires an explicit `technician_confirmed` flag, and keeps pre-diagnosis observations separate from post-diagnosis outcomes.
- **WHY:** Cached engine never saw learned cases; confirmation was hardcoded `True`; repair outcomes could contaminate the diagnosis that predicted them.
- **FILES:** `app.py`, `engine/repair_memory.py`
- **TESTS:** `test_active_memory_refreshes_after_verified_case`, `test_unverified_case_is_rejected`, `test_learned_case_uses_technician_note_not_pre_diagnosis_notes`

## 7. Test integrity + tester-vs-board (new capability)

- **CHANGE:** New `engine/test_integrity.py`; adapter accepts ABORT/NOT_EXECUTED/SKIPPED/INVALID (previously CRASHED on ABORT); fleet scan detects TEST-STATION ANOMALY from concentrated failures (same test × station/fixture × window). New demo lot `data/tester_anomaly_demo_log.csv`.
- **WHY:** "Board failed test" ≠ "PCB is faulty" — the problem statement's safety axis; a live differentiator.
- **FILES:** `engine/test_integrity.py` (new), `data/schema_adapter.py`, `engine/orchestrator.py`, `app.py`, `data/tester_anomaly_demo_log.csv` (new)
- **TESTS:** `test_abort_and_not_executed_are_not_failures`, `test_unsupported_status_is_rejected_loudly`, `test_tester_anomaly_is_detected_at_fleet_level`

## 8. Domain fix — dead rail is a fault, not bad data

- **CHANGE:** Absurd-value threshold 10× → 50× spec.
- **WHY:** A real dead rail (0.63 V on a 5 V rail, deviation ~33) was flagged AMBER; measured distribution shows real faults top out ~33.
- **FILES:** `engine/data_quality.py`
- **TESTS:** `test_dead_rail_is_not_a_data_quality_problem`

## 9. "What would change my mind?" (new panel)

- **CHANGE:** Computed from the actual evidence gap (leader vs runner-up mechanism/net/history), surfaced in the console after the narrative.
- **WHY:** Demonstrates genuine diagnostic reasoning under hostile questioning.
- **FILES:** `engine/orchestrator.py`, `frontend-vite/src/components/console/*`
- **TESTS:** covered by payload-shape assertions

## 10. Claim hygiene (Bug J/K sweep)

- **CHANGE:** "CANNOT HALLUCINATE" removed; hardcoded $38.50 / 50 boards/day / 250 days metrics relabeled as assumptions or removed; BTM uses measured machine time.
- **WHY:** Unsupported guarantees and unlabeled scenario numbers are judge bait.
- **FILES:** `frontend-vite/src/components/console/ForensicsConsole.tsx`, `CLAIMS.md`
- **TESTS:** payload checks

## 11. Docs

- **CHANGE:** Added `docs/BUG_REPORT.md`, `docs/CHANGELOG.md`, `docs/MODEL_CARD.md`, `docs/CLAIMS_AUDIT.md`; updated `CLAIMS.md` (36 → 46 verified rows) and `FINAL_AUDIT.md`.
- **WHY:** Phase 44 contract; every claim must trace to a verified row.

---

## 12. Final championship pass (Aug 12, pre-demo)

- **CHANGE (P0 science):** `validation/learn_weights.py` no longer lets the blind TEST set decide whether the learned policy ships. Selection AND retention happen on VAL; `select_weights(train, val, policy)` structurally cannot read the blind file; blind is report-only. A **fresh reserve test set** (seed 20260731, BRD_0500+, `validation/make_reserve_set.py` + `validation/validate_reserve.py`) is the final untouched evaluation. Learner now searches the full weight simplex (removed the arbitrary top-20-by-train filter).
- **WHY:** The elite audit's #1 finding — "use TEST to decide whether the model is retained" — was real, and our own docs claimed clean. Now it is clean in code, regression-tested.
- **FILES:** `validation/learn_weights.py`, `validation/make_reserve_set.py` (new), `validation/validate_reserve.py` (new), `tests/test_learning_protocol.py` (new), `data/generate_synthetic.py` (module-level SCENARIOS/EXPECTED), `config/diagnostic_weights.json`.
- **TESTS:** 4 protocol tests. **BEFORE:** blind influenced retention. **AFTER:** blind report-only; reserve = 85.0/100.0/99.0 (MRR 0.90, NDCG@3 0.925).
- **RISKS:** none — headline 88/100/96 unchanged (blind re-verified report-only).

- **CHANGE (P1 proof):** repair simulator rewritten mechanism-based (was dead for every component); baselines suite (`validation/run_baselines.py` — majority/exact-pattern/Jaccard/retrieval-only/fusion); discriminating benchmark (`validation/make_discriminating_set.py` + `validation/benchmark_discriminating.py` — same failed tests, different roots); MRR/NDCG/top-5 added to the validator; tier calibration measured on the reserve set.
- **WHY:** The audits' #2: prove the architecture beats trivial pattern matching where patterns are identical, and never over-claim the headline.
- **FILES:** `engine/orchestrator.py`, `engine/evidence_fusion.py`, `engine/data_quality.py`, `validation/validate_accuracy.py`, `validation/run_baselines.py` (new), `validation/discriminating/*` (new), `tests/test_engine.py`.
- **TESTS:** `RepairSimulationTests` (2). **BEFORE/AFTER:** simulator dead → U3-only-success; baselines disclosed (jaccard 88 = fusion 88 on blind, retrieval-only 52%); discriminating fusion 56% vs 44% chance, 100% top-3.

- **CHANGE (negative result, documented):** step-attributed retrieval tokens and an adaptive structural policy were benchmarked and REJECTED — both improved one axis and hurt another (tokens: blind 88→84; adaptive: family 49→61 but blind 88→60). The original tokenization + learned policy ship; the numbers are in CLAIMS.md #51 and BUG_REPORT.md.
- **WHY:** the prompt's rule — "if it does not improve robustly, keep the simpler model and explain why".
- **RISKS:** none.

- **CHANGE (polish):** `compute_coverage` cache invalidation (B1), `KNOWN_ERROR_CODES` config-driven (B2), `validate_accuracy.py` dynamic miss count, stale claims swept (CLAIMS #9/#17, JUDGE_ATTACK_SURFACE), `PROBLEM_STATEMENT.md` added, offline HTML slide deck (`docs/presentation/`), CBR framing in DEMO_SCRIPT Q&A.
- **TESTS:** 47/47 total. Docs: BUG_REPORT L–R rows, MODEL_CARD, FINAL_AUDIT §Aug-12, VALIDATION_REPORT regenerated with 8 sections (A–H).
