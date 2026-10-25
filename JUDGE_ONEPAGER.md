# CIRCUITMIND — FAILURE INVESTIGATION DOSSIER
## Case No: CM-2026-08-BRDU3CASCADE-U3 · Status: LEADING HYPOTHESIS IDENTIFIED
## Don't diagnose the symptom. Reconstruct the failure.

An offline, deterministic PCB failure-investigation engine. ICT/FCT test logs +
circuit topology + repair history in; competing root-cause hypotheses with a
sourced evidence chain out. No LLM, no API keys, no internet — same input always
gives the same output. We call it **structured evidence reasoning**.

---

### THE CASE (demo board BRD_U3_CASCADE_001)

**Failure Fingerprint:** `P100-D100 | 4F | 1R | 2C`
(POWER 100, DIGITAL 100 · 4 failed tests · 1 primary rail · 2 cascade nets)

**Known investigation gaps (confessed, not hidden):** the closest historical
match points to F1, not U3 — a supporting precedent for U3 exists but ranks
below it, so the retrieval stream leans against the leader.

**Leading hypothesis:** **U3 — TPS54331 Buck** · 74.0 / 100 diagnostic evidence score
(history · net · topology · criticality · category — weights LEARNED from 300
labeled boards, each stream still inspectable)

**The story:** 4 failed tests — a 5 V rail at 3.7 V, a 3.3 V rail at 2.68 V,
a dead MCU, dead SPI flash — trace to ONE upstream fault: the failing 5 V rail
killing everything downstream of it.

### THE COUNTERFACTUAL — how we eliminate alternatives

| Hypothesis | Failures explained | Verdict |
|---|---|---|
| **U3** | 4 / 4 (100%) | Supported by precedent REP-6B88C8 + net + topology |
| **L1** | 4 / 4 (100%) | Same wires, no precedent — outweighed 34.6 pts |
| **C1** | 4 / 4 (100%) | Same wires, no precedent — outweighed even further |

*"If this component were healthy, what would still be broken?"* — here every
suspect explains the failures *electrically*, so the system ranks by evidence,
not connectivity: connectivity says who *could* have done it, the evidence
streams say who did. When the top two are genuinely close, it recommends the
next test that could prove the leader wrong.

### VALIDATION — 100 blind synthetic boards (instance holdout)

| Metric | Value |
|---|---|
| Top-1 accuracy | **88%** |
| Top-3 accuracy | **100%** |
| Domain accuracy | **96%** |
| Inference time | **~5 ms / board** (median), fully offline |

**Why it's honest:** the 100 boards are an instance holdout — new boards from
the same 15 fault families as training, never seen by the retrieval corpus. We
do not claim generalization to unseen fault types. Every one of the 12 top-1
misses still ranked the truth in the top-3 (visible in the arena with its
evidence) — **zero silent misses, zero truth-outside-top-3**. Every diagnosis
is labeled "probable — physical verification required."

### WHY THIS IS DIFFERENT

- **Evidence is named and ablatable** — 5 weighted streams, editable policy, live re-ranking
- **Contradictions are surfaced** — alibi checks: the system shows why #2 and #3 were cleared
- **It confesses what it doesn't know** — a Known Investigation Gaps panel on every case
- **Cannot hallucinate** — it only references components that exist on the board
- **Deterministic + offline** — audit every claim, run it on an air-gapped floor
- **Two outputs, two audiences** — engineer's dossier + plain-language technician handoff

*CircuitMind: structured evidence reasoning for PCB failure investigation.*
