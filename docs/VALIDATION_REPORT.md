# CircuitMind — Validation Report

Generated: 2026-08-12 11:02:03 · Full suite in 11.7s.

## A. Instance holdout — known fault families (the headline benchmark)

100 held-out synthetic board **instances** drawn from the **15 known fault families**.

| Metric | Value |
| --- | --- |
| Top-1 | 88.0% |
| Top-3 | 100.0% |
| Top-5 | 100.0% |
| MRR | 0.9200 |
| NDCG@3 | 0.9400 |
| Domain | 96.0% |
| Inference (avg / median / p95) | 6.0 / 5.1 / 10.8 ms |
| Silent misses | 0 |

This is an *instance* holdout: new boards, known failure families. It is
**not** a claim of generalization to unseen fault types (see B).

## B. Fault-family holdout — unseen fault families

Each family is removed entirely from the retrieval corpus **and** the
pattern-signal statistics before diagnosing its blind boards.

| Family | Boards | Top-1 | Top-3 |
| --- | ---: | ---: | ---: |
| A1 | 7 | 100.0% | 100.0% |
| C1 | 6 | 0.0% | 100.0% |
| F1 | 9 | 0.0% | 0.0% |
| J1 | 9 | 0.0% | 100.0% |
| L1 | 4 | 0.0% | 100.0% |
| Q1 | 7 | 100.0% | 100.0% |
| R1 | 6 | 0.0% | 100.0% |
| R12 | 10 | 100.0% | 100.0% |
| U1 | 7 | 0.0% | 100.0% |
| U2 | 6 | 100.0% | 100.0% |
| U3 | 3 | 0.0% | 100.0% |
| U4 | 6 | 0.0% | 0.0% |
| U5 | 10 | 100.0% | 100.0% |
| U6 | 8 | 100.0% | 100.0% |

**Weighted top-1 49.0% · top-3 84.7%** over 98 boards, 14 families.

These are the honest numbers for generalization to **unseen fault types** —
they are lower than the instance holdout and are reported deliberately. The
defensible engineering statement: factories encounter the same failure
families repeatedly; reproducible diagnosis of known families (A) is the
real operating scenario, and B defines the boundary of that claim.

## C/D. Adversarial + OOD

Deterministically generated hostile cases (seed 2026).

| Perturbation | Boards | Top-1 | Top-3 |
| --- | ---: | ---: | ---: |
| noise | 10 | 90.0% | 100.0% |
| unknown_test | 10 | 30.0% | 30.0% |
| novel_code | 10 | 80.0% | 100.0% |
| missing_value | 10 | 70.0% | 100.0% |
| missing_bom | 10 | 90.0% | 100.0% |

- **Multi-fault**: detector flagged 100% of dual-fault boards; solver surfaced a second fault on 100% and named **both** true components on 100%.
- **OOD/novel**: 100% of novel boards were flagged (KNOWN/PARTIALLY_NOVEL/NOVEL state); the system avoided a confident "Strong match" on 100% of NOVEL boards.

## E. Ablation — each evidence stream's contribution

| Configuration | Top-1 | Top-3 |
| --- | ---: | ---: |
| full | 88.0% | 100.0% |
| history-only | 62.0% | 67.0% |
| net-only | 60.0% | 85.0% |
| topology-only | 43.0% | 85.0% |
| no-history | 60.0% | 85.0% |
| no-net | 64.0% | 92.0% |
| no-topology | 82.0% | 100.0% |

## F. Reserve test — the final untouched split

100 boards generated with a **fresh seed** (20260731, BRD_0500+) after the
model was frozen. These boards were never seen by training, validation,
retrieval, or pattern-signal statistics — this is the single final number
reported for the shipped configuration.

| Metric | Value |
| --- | --- |
| Top-1 | 85.0% |
| Top-3 | 100.0% |
| Top-5 | 100.0% |
| MRR | 0.9000 |
| NDCG@3 | 0.9250 |
| Domain | 99.0% |
| Inference (median / p95) | 5.0 / 11.5 ms |

## G. Baselines — why the headline alone proves nothing

On the SAME frozen blind split, trivial methods are measured so the claim
is never overstated. Parity with pattern-matching on the instance holdout
is EXPECTED — those families are pattern-separable. The discriminating
benchmark (H) is where the evidence architecture must separate.

| Method | Top-1 | Top-3 |
| --- | ---: | ---: |
| Majority class | 6.0% | — |
| Exact failed-pattern | 88.0% | — |
| Jaccard (failed steps) | 88.0% | 100.0% |
| Retrieval-only (TF-IDF, history=1) | 62.0% | 67.0% |
| **Current fusion (shipped)** | **88.0%** | **100.0%** |

Retrieval-only (62%) vs full fusion (88%) shows the net/topology streams
do real work; the instance holdout alone cannot claim superiority over
pattern matching (both 88%). That proof lives in benchmark H.

## H. Discriminating — same failed tests, different root causes

27 boards across 4 clusters where every board in a cluster shares its
failed-test SET; only the measured error code / deviation differs.
Pattern-only classifiers must guess (Jaccard 44%, exact 22%); the fusion
separates above chance and never loses the truth from the top-3.

| Method | Top-1 | Top-3 |
| --- | ---: | ---: |
| Exact failed-pattern | 22.2% | — |
| Jaccard (failed steps) | 44.4% | 100.0% |
| **Current fusion (shipped)** | **55.6%** | **100.0%** |

Where the failed-test pattern is identical, pattern matching collapses to
chance; the evidence architecture (measurements + history + topology +
mechanism) separates above chance and keeps every truth in the top-3.
Genuinely ambiguous single-reading cases surface with Next-Best-Test
active — the system asks for evidence rather than guessing.

Every score in this report is reproducible: `python3 validation/run_all_benchmarks.py`.
