# Problem Statement — PS01 (PCB Fault Diagnosis)

> Faithful digest of the official problem brief distributed at the event
> (AI Domain-X Challenge 2026, Problem PS01). The upload naming is fixed:
> **`PS01 – Dragons`** (Problem Number – Team Name).
> `docs/` + `HANDOFF.md` cross-reference this document; every requirement below
> maps to an implemented, tested capability (see the coverage map at the end).

---

## The problem

A factory builds printed circuit boards (PCBs). After manufacture, every board
passes through **ICT** (in-circuit test — checks individual components: resistor
values, shorts, part placement) and **FCT** (functional test — checks the board
as a whole: power-up, outputs, communication). When a board fails, the tester
emits failure data: which test step failed, measured vs expected value, error
code.

A human engineer must then read that data and determine what is physically
wrong. Today that process is:

1. **Manual** — reading logs, the board design, the BOM, and old repair records;
2. **Slow** — especially for complex boards;
3. **Inconsistent** — two engineers can reach different conclusions;
4. **Expertise-dependent** — when the experienced engineer leaves, the knowledge
   leaves with them.

**The task:** build an AI system that (a) recognizes failure patterns from the
test log, (b) matches them to similar historical failures, and (c) proposes
probable fault locations — with **reasoning** (why this component) and
**confidence** (how sure).

## Data

| Source | Contents | Example |
|---|---|---|
| **Test log** (main input) | one row per test step per board: `board_id`, `test_step`, `measured_value`, `expected_range`, `pass_fail`, `error_code`, `timestamp` | "R12_resistance measured 1050 vs expected 990–1010 → FAIL, ERR_VALUE_HIGH" |
| **BOM extract** | `refdes`, `part_number`, `value`, `package`, `net_name` | R12 = 1K resistor, 0603, on net VCC_3V3 |
| **Historical repair notes** (optional) | free text | "replaced R12", "cold solder at U3", "solder bridge between pins 3–4 of U7" |
| **Failure type labels** (optional) | open / short / wrong part / solder | — |

A **net** is an electrical connection shared by components: if R12, R15 and C8
all fail and all sit on VCC_3V3, the problem may be the net itself.

## Solution expectations

1. **Parse logs and identify failure signatures** — load the CSV, filter FAIL
   entries, find the top failing steps, compute deviations (how far measured is
   from expected), build a per-board failure fingerprint.
2. **Retrieve top-K similar past failures** — either embedding similarity
   (vector store) or rule-based matching; return the K most similar historical
   cases.
3. **Recommend likely components/nets with evidence** — map failed tests to
   components via the BOM, detect net-level patterns, fold in what similar past
   cases repaired, and rank suspects with evidence and confidence.
4. **Produce a short triage report** — board ID, failure summary, similar
   cases, recommended fault locations with evidence and confidence, and safe
   next diagnostic steps; downloadable as **PDF/CSV**, shown in a **simple UI**.

## Constraints

1. **No real/proprietary data** — synthetic (but realistic) data only.
2. **"Probable, not guaranteed"** — always show confidence; never a definitive
   claim that could send a technician to replace the wrong part.
3. **Safe diagnostic steps only** — "measure R12 with a multimeter", "visually
   inspect U3's solder joints" — never anything that could damage hardware.
4. **"MVP scope only; production hardening not required."**

## Suggested tools (suggestions, not mandates)

Python + pandas · Azure OpenAI (summaries/reasoning) · embeddings + vector
store (FAISS / Azure AI Search) · Streamlit UI · optional rules engine.
CircuitMind's mapping: pandas ✅ · **no LLM** (benchmarked decision — see
`docs/MODEL_CARD.md`; a hallucinated component on physical hardware has real
cost) · **TF-IDF + cosine retrieval** instead of embeddings (offline,
deterministic, matched pattern baselines — see `docs/VALIDATION_REPORT.md`) ·
Streamlit + React ✅ · rules engine ✅ (fault modes, mechanism rules,
test-integrity rules).

## Evaluation structure (as briefed)

**Round 1 (11:00) — Theory & Design, 25 marks**
| Criterion | Marks | What they ask |
|---|---|---|
| Problem Understanding & Analysis | 10 | Why is manual diagnosis bad? What data? ICT/FCT, BOM, failure types |
| AI Approach & Solution Design | 10 | What AI techniques? End-to-end flow — draw the flowchart |
| Innovation & Feasibility | 5 | What's unique? Can it work in the real world? |

**Round 2 (14:00) — Working Demo, 25 marks**
| Criterion | Marks | What they ask |
|---|---|---|
| Implementation & Functionality | 10 | Does it run? Working code + sample data, end-to-end |
| AI Performance & Effectiveness | 10 | How accurate? Does similarity search work? Show correct identifications, confidence scores, comparison against known answers |
| Demo, Presentation & Team Response | 5 | Smooth demo; every team member can answer |

## CircuitMind coverage map (Round-1 reference)

| Requirement | Where in CircuitMind | Evidence |
|---|---|---|
| Parse ICT/FCT logs | `engine/schema_adapter.py` + `signature_extractor.py` (Failure DNA: deviations, domains, severity) | tests + `demo_boards/` |
| Failure signature | Failure DNA per board; primary domain; severity tiers | `tests/test_engine.py` |
| Similar historical failures | `engine/semantic_memory.py` — TF-IDF + cosine over 150 repair cases, top-K retrieval | `validation/` baselines |
| BOM mapping | `data/components.csv` — refdes, desc, net | tests |
| Component **and** net ranking | `evidence_fusion.py` — net evidence stream + electrical coverage | hero case U3 |
| Same-net strengthening | net evidence + mechanism blast radius (U3 explains 4/4) | `benchmark_discriminating.py` |
| Reasoning / evidence | 5 evidence streams, evidence ledger, WHY THIS / WHY NOT | React console |
| Confidence | diagnostic score + empirical tier calibration (Strong 87.3% on untouched reserve, validation/reserve_metrics.json) | `docs/VALIDATION_REPORT.md` |
| Probable, not guaranteed | "probable root-cause hypothesis" language; abstention states | claim audit |
| Safe diagnostic steps | Next Best Test with risk/effort labels; verification actions from `fault_modes.json` | console NBT panel |
| Triage report PDF/CSV | `pdf_generator.py` + `csv_generator.py` with case number + version identity | tests |
| Simple UI | Streamlit host + React forensic console | live demo |
| Synthetic data | `data/generate_synthetic.py` — deterministic seeds, ground truth, causal consistency | `DATA_CARD.md` |
| Benchmark vs known answers | instance/reserve/family/adversarial/OOD/multi-fault/intermittent/tester | `run_all_benchmarks.py` |

**The one-line summary:** CircuitMind is an AI investigation engine that takes
PCB test failure logs and a component list, finds similar past failures, and
tells the engineer which component is probably broken and why — with a
confidence score, the evidence behind it, and a downloadable triage report.
