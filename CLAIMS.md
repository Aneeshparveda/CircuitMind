# CIRCUITMIND — CLAIM REGISTRY

Every claim made in the pitch, demo script, one-pager, Q&A, or docs must
correspond to an entry here with evidence and a status. **If a sentence cannot
be mapped to a verified entry, do not say it.** Run a claim audit before the
event: every PPT line, concept note, website, demo script, README, one-pager,
PDF, and Q&A answer must trace to this table.

## Verified claims (safe to say, with evidence)

| # | Claim | Evidence | Status |
|---|-------|----------|--------|
| 1 | 88% Top-1 accuracy (learned-policy headline; hand-set baseline was 78%) | `python3 validation/validate_accuracy.py` reproduces `metrics.json` | ✅ VERIFIED Aug 10/11 |
| 2 | 100% Top-3 accuracy (learned-policy headline; hand-set baseline was 91%) | same validator | ✅ VERIFIED |
| 3 | 96% Domain accuracy | same validator | ✅ VERIFIED |
| 4 | ~5 ms / board inference | validator records `average_inference_seconds` ≈ 0.005 | ✅ VERIFIED |
| 5 | 100 held-out synthetic board instances | `validation/ground_truth_blind.csv` (BRD_0400–0499) | ✅ VERIFIED |
| 6 | Instance holdout, known fault families (NOT unseen-type generalization) | generator samples same 15 scenarios for all splits; audit Aug 11 | ✅ VERIFIED — say it this way, never "non-leaked" |
| 7 | Excluding blind boards from pattern-signal derivation changes nothing (88.0/100.0 identical under the learned policy) | measured Aug 11 (SemanticMemory logs_path experiment) | ✅ VERIFIED |
| 8 | Retrieval corpus is 150 repair cases; blind boards never retrieval candidates | `SemanticMemory.__init__` reads `repair_history.csv`; validator reads `ground_truth_blind.csv` only for labels | ✅ VERIFIED |
| 9 | Zero silent misses (12 top-1 misses; ALL 12 still ranked the truth in top-3; 0 outside top-3; 0 silent) | validator `error_breakdown` incl. `in_top3_but_ranked_second: 12`, `not_in_top3: 0`, `silent_misses: 0` | ✅ VERIFIED — say "zero silent misses" with the breakdown, never "zero confident wrong guesses" |
| 10 | Calibration (learned policy): Strong tier **91.8%** top-1 (45/49) on blind; **87.3%** (63 boards in Strong tier) on the untouched reserve set (corrected to validation/reserve_metrics.json); Likely 60% (3/5) / Inconclusive 87% (40/46) on blind. Frequencies per tier — never probabilities | measured Aug 11–12 under `config/diagnostic_weights.json` learned weights (`validation/validate_reserve.py` reports tier accuracy on the reserve set) | ✅ VERIFIED — "measured frequency in this tier", never "X% chance" |
| 11 | 103 test functions across 5 test files (counted; pass count not re-recorded in this curation) | `python3 -m pytest tests/ -v` | Count verified; run the suite to record a pass count |
| 23 | Fault-mode-aware hypotheses: leader carries a mechanism (e.g. U3 / output undervoltage) with safe verification steps | `engine/fault_modes.py` + `data/fault_modes.json`; hero board assigns `output undervoltage` to U3 | ✅ VERIFIED |
| 24 | Three-layer reasoning: electrical topology + functional dependencies + test observability | `data/functional_dependencies.csv`, `data/test_observability.csv`, `TopologyDAG` exposes `functional_downstream()` and `analyze_observability()` | ✅ VERIFIED |
| 25 | Multi-fault SOLVER names both true components on 100% of dual-fault benchmark boards | `validation/benchmark_adversarial.py` `multi_fault` batch: best-pair = U3+R12 on every dual board | ✅ VERIFIED — sparse set-cover over mechanism coverage; say "names both faults in the benchmark", never "solves all real multi-fault boards" |
| 26 | Counterfactual is mechanism-based: a hypothesis explains only failures its fault mode plausibly causes (connectivity ≠ causality) | `expected_vs_observed` in `engine/fault_modes.py`; hero: U3 explains 4/4 by mechanism, L1/C1 only 1/4 | ✅ VERIFIED |
| 27 | Next Best Test carries information-gain + risk + effort meta | `evidence_fusion.get_next_best_test` + `data/test_net_map.csv` risk/effort columns | ✅ VERIFIED |
| 28 | OOD/novelty detector: NOVEL patterns are never presented as Strong; tier demoted to Inconclusive | `engine/ood.py` + orchestrator demotion rule; novel demo board → NOVEL + Inconclusive | ✅ VERIFIED |
| 29 | Data-quality gate reports GREEN/AMBER/RED with specific issues before diagnosis | `engine/data_quality.py`; novel demo board → RED with 4 issues | ✅ VERIFIED |
| 30 | Verified repair memory: only confirmed repairs (retest PASS + technician confirmation) enter learnable memory; predictions never do | `engine/repair_memory.py`; learnable cases live in `data/learned_cases/` SEPARATE from the frozen benchmark corpus | ✅ VERIFIED |
| 31 | Engine/version identity recorded per report for reproducibility | `engine/versions.py` → `report['versions']` | ✅ VERIFIED |
| 32 | Family-holdout benchmark: held-out fault families drop to 49% Top-1 / 84.7% Top-3 under the learned policy — an honest generalization gap, disclosed | `validation/benchmark_family_holdout.py` | ✅ VERIFIED — present the gap, don't hide it |
| 33 | Adversarial benchmark: novel/OOD boards 100% flagged; missing-BOM and noisy boards degrade gracefully (no crash, uncertainty surfaced) | `validation/benchmark_adversarial.py` | ✅ VERIFIED |
| 34 | Ablation study: ranking responds to evidence-policy changes (weights are tunable, not black-box) | `validation/benchmark_ablation.py` + in-browser Evidence Ablation sliders | ✅ VERIFIED |
| 35 | Inference: median 5 ms, p95 ~11–13 ms per board on this machine | validator records median/p95 | ✅ VERIFIED — quote "~5 ms median / ~11 ms p95 on our demo environment", never a single universal number |
| 36 | Learned fusion weights reproduce: `python3 validation/learn_weights.py` re-derives the weight vector from the 300 training boards and re-verifies 88/100 on blind | deterministic grid search, no RNG; results written to `config/diagnostic_weights.json` with provenance note | ✅ VERIFIED — say "learned from 300 labeled boards, +10 top-1 over the hand-set policy on the blind set" |
| 12 | Fully offline, deterministic, no API keys, no internet | architecture: no network calls anywhere in engine/app | ✅ VERIFIED |
| 37 | NaN error codes are never rendered as the literal string "NAN" and never trigger a false data-quality warning | `engine/data_quality.py` + `engine/signature_extractor.py` sanitize NaN/empty/whitespace; regression test `test_nan_error_code_is_never_rendered` | ✅ VERIFIED |
| 38 | RED data-quality input → ABSTAIN state with an explicit "insufficient evidence / what's needed next" block, never a confident diagnosis | `engine/orchestrator.py` `diagnosis_state` machine (LEADING_HYPOTHESIS / DEGRADED / ABSTAIN); regression test `test_red_data_quality_abstains` | ✅ VERIFIED |
| 39 | Ground truth never ships in the analysis/fleet payload — the frontend reveal is a server-gated action | `app.py` `analyze_board` strips truth keys; `reveal_ground_truth` event is the only path | ✅ VERIFIED — audit found truth in every BRD_04xx payload; now server-gated |
| 40 | Verified-repair memory refresh is real: after a confirmed case is written, the ACTIVE cached engine rebuilds its memory (cache cleared) — learned count visibly increments | `app.py` clears the engine cache in `record_verified_repair`; regression test `test_memory_refresh_after_verified_case` | ✅ VERIFIED |
| 41 | Technician confirmation is explicit, never hardcoded: memory eligibility requires repair performed + retest PASS + technician confirmation | `app.py` `record_verified_repair` + `engine/repair_memory.py`; regression test rejects unconfirmed writes | ✅ VERIFIED |
| 42 | Repair notes are time-ordered: pre-diagnosis observations can never be overwritten by post-diagnosis repair outcomes (no circular evidence) | app splits observation vs outcome fields; regression test `test_notes_separation` | ✅ VERIFIED |
| 43 | Test-integrity gate: ABORT / NOT_EXECUTED / SKIPPED / INVALID statuses are parsed (never crash, never counted as PASS or board failure); output is VALID / DEGRADED / TEST SYSTEM SUSPECTED | `engine/test_integrity.py` + adapter accepts the full status set; regression tests | ✅ VERIFIED — the old adapter CRASHED on ABORT rows |
| 44 | Tester-vs-board fleet logic: concentrated failures (same test × same station/fixture × same window) raise TEST-STATION ANOMALY, not board rework | `app.py` fleet scan + `data/tester_anomaly_demo_log.csv`; regression test | ✅ VERIFIED — "don't rework the board yet; validate the tester" |
| 45 | "What would change my mind?" is computed, not canned: generated from the actual evidence gap between leader and runner-up | `engine/orchestrator.py` `mind_change` block; surfaced in the console | ✅ VERIFIED |
| 46 | Dead-rail deviations are a fault signal, not bad data: absurd-value threshold set at 50× spec (real faults never exceed ~33) so 0.63 V on a 5 V rail is GREEN input, not AMBER | `engine/data_quality.py` threshold 10→50; regression test `test_dead_rail_is_not_a_data_quality_problem` | ✅ VERIFIED |
| 13 | Schema adapter normalizes COMMON ICT/FCT column variants | `data/schema_adapter.py` alias map | ✅ VERIFIED — never say "any factory CSV" |
| 14 | Same input → same output (deterministic) | engine is pure functions over fixed data; no RNG in analysis | ✅ VERIFIED |
| 15 | Hero demo case is a clean single-fault cascade: 4 failures, 1 primary rail (SYS_5V), 0 multi-fault indicators | `BRD_U3_CASCADE_001` analyzed Aug 11: fingerprint `P100-D100 | 4F | 1R | 2C`, U3 74.0 Strong, 34.6 clear of #2 (learned-weight scale) | ✅ VERIFIED |
| 16 | Dual-fault case exists and the solver names both true components (U3 + R12) with a parsimony-adjusted verdict | `BRD_DUAL_FAULT_001` → multi-fault analysis best-pair U3+R12 covers 100% vs single 86% | ✅ VERIFIED — see #25 for the benchmark-wide claim |
| 17 | Reserve test set (fresh seed 20260731, BRD_0500+, never seen by any split): **85.0% top-1 / 100% top-3 / 100% top-5 / 99% domain**, MRR 0.900, NDCG@3 0.925, 0 misses outside top-3 | `python3 validation/validate_reserve.py` → `validation/reserve_metrics.json` | ✅ VERIFIED — this is the single final untouched-test number |
| 18 | Counterfactual is topology-based, NOT physical/SPICE simulation | `evidence_fusion.compute_coverage` + documented answer | ✅ VERIFIED — always qualify "simulation" |
| 19 | Evidence weights are **LEARNED**, not hand-set: history 0.60 · net 0.35 · topology 0.05 · criticality 0 · category 0 | `validation/learn_weights.py` — grid search over the FULL weight simplex on 300 labeled training boards, selected and retained on a 100-board holdout; the blind TEST set is report-only and never influences selection (structural, enforced by `tests/test_learning_protocol.py`). Lifted blind top-1 78%→88%, top-3 91%→100%. The hand-set policy remains the documented fallback (`data/evidence_policy.json`) | ✅ VERIFIED |
| 47 | Clean scientific protocol: TRAIN → fit · VALIDATION → select/retain · TEST → report only; the blind set cannot influence selection (regression-tested) | `tests/test_learning_protocol.py`: selection function cannot read `ground_truth_blind.csv`; retention derived from VAL only | ✅ VERIFIED — the one scientific issue the elite audit found (blind set used in the keep/reject decision) is structurally fixed |
| 48 | Baseline table disclosed: on the same frozen blind split — majority 6%, exact-pattern 88%, Jaccard 88%, retrieval-only 62%, current fusion 88% | `python3 validation/run_baselines.py` → `validation/baseline_report.json` | ✅ VERIFIED — say "the headline alone proves nothing; retrieval-only is 62%, so the net/topology streams do real work" |
| 49 | Discriminating benchmark (same failed tests, different root causes): Jaccard falls to 44%, exact 22% (chance); CircuitMind 56% top-1 and **100% top-3**; ambiguous single-reading cases surface with NBT active instead of a guess | `python3 validation/benchmark_discriminating.py` → `validation/discriminating_metrics.json` | ✅ VERIFIED — the honest "not a lookup table" evidence: truth never lost from top-3 |
| 50 | Repair simulator is mechanism-based: the true root cause (hero U3) is the ONLY candidate whose mechanism covers every failure (resolved SYS_5V+3V3+SPI, success True); passives/downstream leave residuals | `engine/orchestrator.py` `simulate_repair`; `tests/test_engine.py::RepairSimulationTests` | ✅ VERIFIED — previously the UI button resolved nothing for ANY component (graph-direction bug, elite audit) |
| 51 | Adaptive structural policy was benchmarked and NOT shipped: structural weights lift family-holdout top-1 to 61.2% but drop instance holdout to 60.0%; the precedent signal overlaps, so the learned policy ships and both numbers are documented | experiment Aug 12 (structural vs learned weights on both benchmarks) | ✅ VERIFIED — a measured negative result, per "keep the simpler model and explain why" |
| 20 | Case number, fingerprint, evidence ledger all derived from report (one computed object) | `orchestrator.analyze()` single pass; `_resolve_cited_precedent` used everywhere | ✅ VERIFIED |
| 21 | Reports export as PDF + CSV with case number and chain of evidence | `reports/` + verified exports Aug 10 | ✅ VERIFIED |
| 22 | Demo works fully offline | all assets local; streamlit headless | ✅ VERIFIED (WiFi-off toggle is a demo-day checklist item) |

## Claims to NEVER make (removed or unsupported)

| Claim | Why not | Replaced by |
|-------|---------|-------------|
| "Zero leakage" / "non-leaked" blind set | blind boards do feed a severity aggregation in semantic memory (effect measured zero, but the word overclaims) | "instance holdout, known fault families" (#6, #7) |
| "Zero confident wrong guesses" | false as worded — 4/12 misses had Strong tier under the learned policy (Strong tier = 91.8% top-1) | "zero silent misses + every miss still in top-3" with breakdown (#9) |
| "CircuitMind is the first system to..." | prior CBR circuit-diagnosis work exists (ScienceDirect); unsubstantiated | "CircuitMind treats that evidence the way it deserves to be treated" |
| "Normalizes ANY factory CSV schema" | adapter handles known/common aliases only | "normalizes common ICT/FCT CSV schema variants" (#13) |
| "Production accuracy" / real-factory generalization | benchmark is synthetic-to-synthetic | "architecture is data-agnostic; real accuracy needs real repair history" |
| "Calibrated probabilities" (as statistical probabilities) | tiers are score buckets, not posterior probabilities | "score tiers with measured benchmark accuracy per tier" (#10) |
| "We solve multi-fault diagnosis" (as a general claim) | the solver handles the benchmark's dual-fault family; real-world multi-fault remains open | "names both faults on 100% of our dual-fault benchmark boards; real multi-fault remains an open investigation problem" (#25) |

## How to run the audit

1. `grep` the pitch/demo/one-pager for every numeric or superlative claim.
2. For each, find the registry row and re-run its evidence command.
3. Any claim without a row: either add a verified row or remove the sentence.
4. Rebuild + restart + re-verify the live demo after ANY change to engine, data,
   or frontend (see `.freebuff/run.md`).
