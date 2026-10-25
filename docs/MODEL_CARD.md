# CIRCUITMIND — MODEL CARD

## What is the "model"?

CircuitMind is a **deterministic, interpretable diagnostic pipeline** — not a
neural network. The learned component is a **ranking-policy weight vector**
fitted by grid search; everything else is symbolic reasoning over a board
dependency graph and a retrieval index.

| Layer | What it is | Learned? |
|-------|-----------|----------|
| Signature extraction | Deviation/severity/domain profile of failing tests | No |
| Retrieval | TF-IDF + cosine over the repair-history corpus (150 cases) | No (standard TF-IDF) |
| Evidence fusion | `score = Σ raw_stream × weight` per candidate component | **Yes — weights learned** |
| Fault modes | Role-aware mechanism lookup per component category | No |
| Topology DAG | Electrical + functional + observability layers | No |
| Multi-fault solver | Sparse set-cover with parsimony penalty over mechanism coverage | No |
| OOD / novelty | Similarity thresholds + match-count rules | No |
| Data-quality gate | Rule-based GREEN/AMBER/RED + VALID/DEGRADED/ABSTAIN | No |
| Test-integrity gate | Status classification + tester-vs-board fleet analysis | No |
| Narrative | Deterministic template generation (no LLM anywhere) | No |

## The learned policy (the one trained component)

- **Objective:** maximize top-1 ranking accuracy on a 100-board holdout.
- **Training data:** 300 labeled synthetic boards (`ground_truth_train.csv`),
  generated with deterministic seeds and explicit ground truth.
- **Method:** exhaustive grid search over the weight simplex
  (history, net, topology, criticality, category) with 0.05 steps.
- **Selection:** 100-board holdout (`ground_truth_val.csv`). The blind TEST
  set is **report-only** — selection AND retention happen on VAL, and the
  selection function structurally cannot read the blind file
  (`tests/test_learning_protocol.py`). A fresh **reserve set** (seed
  20260731, BRD_0500+) generated after the model was frozen is the final
  untouched evaluation.
- **Result:** history 0.60 · net 0.35 · topology 0.05 · criticality 0 · category 0.
- **Reproducibility:** `python3 validation/learn_weights.py` re-derives the
  vector from the training boards (full-simplex search, no top-k filter) and
  reports the blind numbers. No RNG. Hand-set policy preserved as documented
  fallback (`data/evidence_policy.json`).

## Performance (measured, reproducible)

- Blind set (100 boards): **top-1 88.0%, top-3 100.0%, top-5 100.0%, domain
  96.0%**, MRR 0.92, NDCG@3 0.94, 0 misses outside top-3, 0 silent misses.
- Reserve set (100 boards, fresh seed, never seen by anything): **top-1 85.0%,
  top-3 100.0%, domain 99.0%**, MRR 0.90, NDCG@3 0.925 — the final untouched
  test number.
- Family-holdout (unseen families): **top-1 49.0%, top-3 84.7%** — an honest
  generalization gap, disclosed everywhere it is quoted. (Benchmarked
  structural-only variant: 61.2%/90.8%, at the cost of instance holdout
  88→60% — not shipped; CLAIMS.md #51.)
- Baselines on the same blind split: majority 6%, exact-pattern 88%, Jaccard
  88%, retrieval-only 62%, current fusion 88%. The headline alone proves
  nothing; the retrieval stream alone is 62%, and the discriminating benchmark
  (same failed tests, different roots) shows fusion 56% vs 44% chance with
  100% top-3.
- Calibration tiers (score buckets, NOT probabilities): Strong = 91.8% top-1
  on blind, 87.3% on the untouched reserve (validation/reserve_metrics.json: Strong n=63); Likely = 60% (n=5); Inconclusive
  = 87% (n=46).
- Latency: median ~5 ms, p95 ~10 ms per board (this machine).

## Known limitations (say these in the room)

1. **Synthetic-to-synthetic.** All benchmarks measure consistency with our own
   generator, not generalization to real factory logs.
2. **No learned ML model in the decision path.** Deliberate: hallucinated
   hardware advice has real cost; every score is reconstructible by hand from
   the evidence ledger. This is case-based reasoning + symbolic fusion, not a
   black box.
3. **Scores are diagnostic/ranking scores, not calibrated probabilities.**
   Tiers carry measured benchmark accuracy per bucket, but never "88% chance."
4. **Real multi-fault, intermittent, and tester-caused failures** are modeled
   and benchmarked on synthetic families; real-world coverage is unproven.
5. **Structural generalization trades against known-family accuracy** — the
   adaptive/structural policy experiment (family 49→61, instance 88→60) is a
   documented negative result, not shipped.
6. **Retrieval tokens are pattern-level, not step-attributed** — a benchmarked
   step-attribution variant (Failure-DNA 2.0) improved pattern-ambiguous
   separation but cost 4 points on the instance holdout (88→84) and was
   reverted; the discriminating benchmark (56% vs 44% chance, 100% top-3)
   remains the honest boundary of measurement-based separation.
