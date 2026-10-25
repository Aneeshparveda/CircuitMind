# CircuitMind — PCB Fault Diagnosis from Test Logs, BOM, and Repair History

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](requirements.txt)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Tests](https://img.shields.io/badge/Tests-pytest-blue.svg)

> **Status — read this first:** CircuitMind is a deterministic,
> offline PCB fault-diagnosis prototype built for the AI Domain X
> Challenge 2026 (team Dragons, problem PS01). It is **not** a
> production factory tool. Every benchmark number below comes from
> the project's own synthetic data (see [data/DATA_CARD.md](data/DATA_CARD.md)),
> so it proves internal consistency and reproducible ranking —
> **not** real-world factory accuracy. Diagnoses are labelled as
> probable matches that require physical verification, never as
> confirmed faults.

## Contents

- [What it is](#what-it-is)
- [How it works](#how-it-works)
- [Validation results (synthetic data only)](#validation-results-synthetic-data-only)
- [Quickstart](#quickstart)
- [Usage](#usage)
- [Project structure](#project-structure)
- [Data](#data)
- [Tests and benchmarks](#tests-and-benchmarks)
- [Limitations](#limitations)
- [Docs](#docs)

## What it is

CircuitMind takes ICT/FCT test failure logs for a printed circuit
board, plus the board's bill of materials (BOM), electrical
topology, and a corpus of past repair cases, and returns a ranked
list of probable root-cause components — each with the evidence
behind it, a confidence tier, and a downloadable triage report.

Key design principles, as built:

- **Deterministic and offline.** No LLM, no API keys, no internet
  dependency at diagnosis time. The same log always gives the same
  ranking.
- **Evidence-led, not a black box.** Every candidate is explained
  by named evidence streams (past-repair history, net/topology,
  criticality, category) with why/why-not reasoning.
- **Honest about uncertainty.** Candidates carry confidence tiers
  (Strong match / Likely / Inconclusive) that are score buckets
  with measured benchmark frequencies per tier — not statistical
  probabilities. Novel or out-of-distribution boards are flagged
  instead of guessed at.

The system was built around one canonical synthetic board: a
USB-powered board with a 5 V buck regulator (U3), 3.3 V LDO (U2),
STM32 MCU (U1), SPI flash (U5), ESP32 Wi-Fi (U4), I2C sensors
(U6/U7), and analog/output sections — 20 components, 15 fault
families. See [data/DATA_CARD.md](data/DATA_CARD.md) for the full
board model and generation method.

## How it works

A five-stage pipeline in [engine/](engine/):

```text
Test log CSV
  └─► 1. Signature extraction (engine/signature_extractor.py)
      │    Failure DNA: deviations, domains, severity, error codes
      └─► 2. Causal topology (engine/topology_dag.py)
          │    NetworkX DAG: primary vs. cascade nets, causal paths
          └─► 3. Semantic memory (engine/semantic_memory.py)
              │    TF-IDF retrieval over 150 past repair cases
              └─► 4. Evidence fusion (engine/evidence_fusion.py)
                  │    Learned weights: history 0.60 · net 0.35 ·
                  │    topology 0.05 (config/diagnostic_weights.json)
                  └─► 5. Narrative generation (engine/narrative_generator.py)
                      Ranked hypotheses + evidence ledger + report
```

Supporting layers: multi-fault solving
([engine/multi_fault_solver.py](engine/multi_fault_solver.py)),
novelty / out-of-distribution detection
([engine/ood.py](engine/ood.py)), test-integrity and fleet checks
([engine/test_integrity.py](engine/test_integrity.py)), data-quality
checks, fault-mode reasoning, and a repair-learning protocol
([engine/repair_memory.py](engine/repair_memory.py)) that only
accepts verified learned cases.

The user interface is a React forensic console
([frontend-vite/](frontend-vite/)) served as a Streamlit custom
component by [app.py](app.py). It accepts uploaded test-log CSVs
(up to 5 MB), shows built-in demo boards, runs fleet scans, and
exports PDF and CSV triage reports ([reports/](reports/)).

## Validation results (synthetic data only)

All numbers below are from the frozen files in
[validation/](validation/) — they are **not** re-measured here,
and they describe synthetic-vs-synthetic performance only. Read
them with their dataset names attached; a bare "88% accurate"
would be misleading.

| Benchmark (dataset) | Top-1 | Top-3 | Notes |
|---|---:|---:|---|
| Instance holdout — known fault families, 100 blind boards ([validation/metrics.json](validation/metrics.json)) | 88.0% | 100.0% | Top-5 100%, MRR 0.92, domain 96%, median inference ~5.1 ms |
| Reserve test — boards never seen by any split, 100 boards, seed 20260731 ([validation/reserve_metrics.json](validation/reserve_metrics.json)) | 85.0% | 100.0% | Domain 99%, MRR 0.90 |
| Fault-family holdout — unseen families, 98 boards, 14 families ([validation/benchmark_report.json](validation/benchmark_report.json)) | 49.0% (weighted) | 84.7% (weighted) | The honest generalisation gap — disclosed deliberately, not hidden |
| Discriminating — same failed tests, different root causes, 27 boards ([validation/discriminating_metrics.json](validation/discriminating_metrics.json)) | 55.6% | 100.0% | Exact-pattern matching falls to 22.2% here; the engine keeps the truth in the top 3 |
| Baselines, same frozen blind split ([validation/baseline_report.json](validation/baseline_report.json)) | — | — | Majority 6%, exact-pattern 88%, Jaccard 88%, TF-IDF-only 62%, current fusion 88% top-1 — the headline alone proves nothing |

Also verified in the audit notes ([CLAIMS.md](CLAIMS.md)):
multi-fault benchmark boards name both true components (U3+R12);
adversarial/novel boards are flagged rather than confidently
misdiagnosed. Confidence tiers are reported as measured
frequencies per tier, never as probabilities.

## Quickstart

Prerequisites: Python 3.9+, Node.js 18+ (for the frontend build).

```bash
git clone https://github.com/Aneeshparveda/CircuitMind.git
cd CircuitMind
pip install -r requirements.txt
cd frontend-vite && npm install && npm run build && cd ..
streamlit run app.py --server.port 8510 --server.headless true
```

Open http://localhost:8510.

> The frontend **must** be built first: `app.py` stops with an
> error if `frontend-vite/dist/` does not exist. The `dist/`
> build output is intentionally not committed — rebuild it with
> `npm run build`.

Docker (builds the frontend inside the image):

```bash
docker build -t circuitmind .
docker run -p 8510:8510 circuitmind
```

## Usage

- **Run the app:** `streamlit run app.py` (see Quickstart).
- **Diagnose a board:** upload a test-log CSV in the app, or pick
  a built-in demo board (U3 cascade, dual-fault, novel board).
- **Regenerate the synthetic corpus (seed 42):**
  `python3 data/generate_synthetic.py`
- **Run the tests:** `python3 -m pytest tests/ -v`
- **Run one benchmark:** `python3 validation/validate_accuracy.py`
- **Run the full benchmark suite:**
  `python3 validation/run_all_benchmarks.py`
  (writes `validation/benchmark_report.json` and
  `docs/VALIDATION_REPORT.md`)
- **Re-derive the learned weights:**
  `python3 validation/learn_weights.py`

Input log format: CSV rows of `board_id, test_step,
measured_value, expected_min, expected_max, unit, pass_fail,
error_code` (see [data/test_logs.csv](data/test_logs.csv) and
[data/DATA_CARD.md](data/DATA_CARD.md)). Uploads in the app are
capped at 5 MB.

## Project structure

```text
app.py                  Streamlit host for the React forensic console
engine/                 Deterministic diagnosis pipeline (5 stages + safety layers)
data/                   Synthetic BOM, topology, test logs, repair history, data card
  learned_cases/        Verified learned repair cases (demo-scoped)
config/                 Learned fusion weights (diagnostic_weights.json)
validation/             Benchmarks, ground truth, and frozen metric JSONs
tests/                  pytest suite (103 test functions, 5 files)
reports/                PDF and CSV triage-report generators
tools/                  Scripts that render the one-pager / code PDFs
frontend-vite/          React forensic console (Vite + TypeScript)
  src/                  Console components (built with npm run build)
  public/               Static assets served with the build
docs/                   Architecture, model card, validation report, benchmarks,
                        claims audit, setup, demo cases, presentation
```

## Data

**All data in this repository is synthetic.** No organiser-provided
dataset existed for this problem, and no proprietary or confidential
factory data is used anywhere. Full inventory, generation method
(seed 42), splits, and leakage controls are in
[data/DATA_CARD.md](data/DATA_CARD.md).

| File | Contents |
|---|---|
| `data/components.csv` | 20-component BOM |
| `data/net_connections.csv` | Pin-level electrical connectivity |
| `data/functional_dependencies.csv` | Component dependency edges |
| `data/test_observability.csv` | Test step → what it observes |
| `data/test_net_map.csv` | Test step → net/domain/level |
| `data/test_logs.csv` | 500 synthetic boards × 11 test steps |
| `data/test_logs_reserve.csv` | 100 reserve boards (BRD_0500+) |
| `data/repair_history.csv` | 150 historical repair cases (10 per fault family) |
| `data/evidence_policy.json` | Hand-set fusion policy (fallback) |
| `config/diagnostic_weights.json` | Learned fusion weights (canonical) |
| `validation/ground_truth_*.csv` | Board → root cause + scenario + split |

Known residual, stated plainly in the data card: all 500 boards
(including the 100 blind boards) live in `test_logs.csv`, which
feeds per-pattern signal statistics; root-cause labels never enter
those signals. The correct wording is "instance holdout, known
families" — never "zero leakage".

## Tests and benchmarks

- Tests: `python3 -m pytest tests/ -v` — 103 test functions
  across `tests/test_engine.py`, `tests/test_refinements.py`,
  `tests/test_diagnostic_contract.py`,
  `tests/test_diagnostic_receipt.py`, and
  `tests/test_learning_protocol.py`, covering the engine,
  diagnostic contract and receipt, refinements, and the learning
  protocol (including the rule that the blind test set never
  influences weight selection).
- Benchmarks: `validation/run_all_benchmarks.py` produces eight
  sections (A–H): instance holdout, family holdout,
  adversarial + OOD, ablation, reserve, baselines, and
  discriminating. Frozen results are committed under
  `validation/*.json` so numbers can be checked without rerunning
  anything.

## Limitations

- **Synthetic only.** One canonical board topology, 15 fault
  families, uniform-random measurements within fixed windows. No
  temperature, ageing, intermittent-fault, or board-revision
  dynamics are modelled.
- **Known-family performance does not transfer for free.**
  Unseen-family top-1 is 49.0% (weighted) — real accuracy on real
  repair history would need to be measured from scratch.
- **Confidence tiers are score buckets**, not posterior
  probabilities. Do not quote a tier as "X% chance".
- **Diagnoses require physical verification.** The engine
  recommends a probable root cause and next checks; it does not
  confirm a fault.
- **Multi-fault** handling is demonstrated on the benchmark's
  dual-fault family; general real-world multi-fault diagnosis
  remains an open problem.
- Runtime figures (~5 ms median on the validated demo
  environment) are environment-dependent.
- **Platform notes.** The PDF helper scripts in `tools/` use
  macOS-only font paths and will fail on Linux/Windows; the PDF
  report footer renders three version fields as `?` because the
  version keys it reads are not provided; and
  `validation/validate_accuracy.py` only works when run from the
  project root (the other validators are path-relative).

## Docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — pipeline design
- [docs/MODEL_CARD.md](docs/MODEL_CARD.md) — what the "model" is
  and its limits
- [docs/VALIDATION_REPORT.md](docs/VALIDATION_REPORT.md) — full
  benchmark report (A–H)
- [docs/BENCHMARKS.md](docs/BENCHMARKS.md) — benchmark summary
- [docs/SETUP.md](docs/SETUP.md) — setup reference
- [data/DATA_CARD.md](data/DATA_CARD.md) — dataset provenance
- [CLAIMS.md](CLAIMS.md) — every public claim, with its
  reproduction command and audit status
- [docs/CLAIMS_AUDIT.md](docs/CLAIMS_AUDIT.md) — claims that were
  removed or rewritten during audit
- [docs/presentation/slides.md](docs/presentation/slides.md) —
  hackathon presentation
- [PROBLEM_STATEMENT.md](PROBLEM_STATEMENT.md) — original PS01
  problem statement (AI Domain X Challenge 2026, team Dragons)

## License

MIT — see [LICENSE](LICENSE). This was a team hackathon project
(team Dragons, AI Domain X Challenge 2026); the copyright line
names Aneesh Parveda as the repository publisher and should be
confirmed before any wider redistribution.
