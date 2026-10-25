# CircuitMind — PS01 PCB Fault Diagnosis
**AI Domain-X Challenge 2026 · Team Dragons (#6)**
*Don't diagnose the symptom. Reconstruct the failure.*

---

## 1. The problem
ICT/FCT test logs tell a factory **what** failed — not **why**.
- 11 test steps, 4 electrical domains, 20 components
- When the engineer who understood the board retires, the knowledge leaves
- Every failed board costs rework hours; every wrong call costs parts and trust

**The question:** can AI reconstruct *why* a board failed from what the test
machine measured?

---

## 2. The AI approach
**Case-Based Reasoning (Aamodt & Plaza, 1994)** — deterministic, auditable AI:
1. **Retrieve** — TF-IDF over 150 historical repair cases (steps + deviation
   severity + error codes)
2. **Reuse** — five named evidence streams fused: history · net · topology ·
   BOM criticality · category
3. **Revise** — contradiction engine, abstention, Next-Best-Test
4. **Retain** — verified repairs only (repair + retest PASS + technician
   confirmation)

One learned component: the fusion weights (grid search on 300 labeled boards,
selected on a 100-board holdout — blind set never touches selection).

**Why not an LLM as the authority?** A hallucinated component on physical
hardware has real cost. Every CircuitMind score is reconstructible by hand.

---

## 3. Architecture
```
CSV test log
 → Schema adapter          (ICT/FCT variants)
 → Failure signature       (Failure DNA: deviations, domains, severity)
 → Topology DAG            (electrical + functional dependency + observability)
 → Semantic memory         (TF-IDF retrieval + pattern signals)
 → Evidence fusion         (ranked hypotheses, 5 streams)
 → Fault modes             (component + mechanism; connectivity ≠ causality)
 → Multi-fault / OOD / DQ  (solve, abstain, gate)
 → Next Best Test          (cheapest safe separating measurement)
 → Narrative + PDF/CSV + React console
```

---

## 4. Results (all reproducible)
| Benchmark | Top-1 | Top-3 | Notes |
|---|---|---|---|
| Instance holdout (blind, 100) | **88.0%** | **100%** | MRR 0.92 · NDCG@3 0.94 · 0 silent misses |
| Reserve test (untouched, 100) | **85.0%** | **100%** | fresh seed; never seen by anything |
| Family holdout (unseen faults) | 49.0% | 84.7% | the honest generalization boundary |
| Adversarial/OOD | — | — | NOVEL → abstains; ABORT ≠ board failure |
| Latency | **~5 ms / board** | — | median 5.0 ms, p95 10.0 ms, fully offline |

Baselines on the same blind split: majority 6% · exact-pattern 88% ·
Jaccard 88% · retrieval-only 52% — parity with pattern matching is disclosed,
and the discriminating benchmark (same failed tests, different roots) is where
the evidence architecture separates: 56% vs 44% chance, 100% top-3.

---

## 5. What's different
- **Connectivity ≠ causality** — a component explains a failure only when its
  *mechanism* reaches it (U3 explains 4/4 by mechanism; L1/C1 only 1/4)
- **Alibi system** — the system argues against its own runner-up and shows the
  cleared suspects
- **Abstention** — NOVEL / RED data quality / close hypotheses → "I don't
  know", plus the safest next measurement
- **Failure or tester?** — fleet patterns separate a bad board from a bad
  fixture ("don't rework the board yet")
- **Verified learning** — the memory grows only from confirmed repairs
- **Minimum accusation principle** — never invent extra faults without cause

---

## 6. Validation honesty
- Clean protocol: **train → fit · validation → select · test → report only**;
  a fresh reserve set (seed 20260731) is the final untouched number
- No leakage: blind boards never enter the retrieval corpus; the
  signal-derivation check is measured (88.0/100.0 identical with them excluded)
- Stale-claim audit: every number in this deck traces to a reproducible
  command in `validation/`
- Confidence is a **diagnostic score**, calibrated empirically by tier
  (Strong 86% on the untouched reserve), never claimed as probability

---

## 7. The investigation loop (demo)
```
FAILED BOARD → TEST INTEGRITY → FAILURE DNA → CAUSAL RECONSTRUCTION
→ HYPOTHESES → HISTORICAL PRECEDENT → MECHANISM CHECK
→ WHY THIS / WHY NOT → WHAT WOULD CHANGE MY MIND? → NEXT BEST TEST
→ COUNTERFACTUAL → VERIFY REPAIR → VERIFIED MEMORY
```

Live demo beats: 60-second race · "U3 has no alibi" · Beat-the-Machine
(server-gated truth) · failure-or-tester lot · the novel board that abstains.

---

## 8. Why judges should believe it
- 47 regression tests (29 → 47 this week), every claimed feature verified
- Deterministic + offline: same input → same output, every machine
- Evidence-ledger: every score decomposes into named, inspectable streams
- The claim registry (CLAIMS.md) — every number traces to a command
- Honest about limits: synthetic data, family holdout 49%, discriminating
  benchmark — all disclosed, none hidden

**CircuitMind doesn't stop at ranking a component. It explains why, argues
against the runner-up, tells you what would change its mind, and knows when it
doesn't know.**
