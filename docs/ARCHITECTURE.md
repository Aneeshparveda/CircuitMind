# CircuitMind Architecture

## Overview

CircuitMind is a deterministic PCB fault diagnosis engine. It takes ICT/FCT test failure logs and a component list, finds similar historical failures, and tells the engineer which component is probably broken and why — with a confidence score, the evidence behind it, and a downloadable triage report.

**Key design principle:** Zero LLM dependency. Every diagnosis is reproducible, auditable, and works offline.

## 5-Layer Pipeline

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Signature Extraction                          │
│  Input: Raw test log CSV                                │
│  Output: Failure DNA (deviations, domains, severity)    │
├─────────────────────────────────────────────────────────┤
│  Layer 2: Causal Topology (NetworkX DAG)                │
│  Input: Failed nets from Layer 1                        │
│  Output: Primary vs cascade nets, causal paths          │
├─────────────────────────────────────────────────────────┤
│  Layer 3: Semantic Memory (TF-IDF + Cosine)             │
│  Input: Failure signature from Layer 1                  │
│  Output: Top-K historical matches with similarity scores│
├─────────────────────────────────────────────────────────┤
│  Layer 4: Evidence Fusion (5 weighted streams)          │
│  Input: Layers 1-3 outputs                              │
│  Output: Ranked candidates with evidence explanations   │
├─────────────────────────────────────────────────────────┤
│  Layer 5: Narrative Generation                          │
│  Input: Full report from Layers 1-4                     │
│  Output: Human-readable forensic summary                │
└─────────────────────────────────────────────────────────┘
```

## Layer Details

### Layer 1: Signature Extraction (`engine/signature_extractor.py`)

Reads the standardized test log and computes:
- **Deviation score** for each failed test: `(measured - midpoint) / half_range`
- **Domain severity**: POWER, DIGITAL, COMMS, ANALOG, OTHER
- **Severity label**: CRITICAL (≥3.0×), HIGH (≥2.0×), MEDIUM (≥1.0×), LOW
- **Error code normalization**: NaN → empty string, never literal "NAN"

### Layer 2: Causal Topology (`engine/topology_dag.py`)

Three graph layers:
- **Layer A — Electrical connectivity** (component ↔ net via pin roles): answers "what is physically connected?"
- **Layer B — Functional dependency** (component → dependent components): answers "what function depends on what?"
- **Layer C — Test observability** (test step → net/component/function): answers "what does this test actually tell us?"

The directed DAG (Layer A) drives primary/cascade classification. The functional layer (Layer B) drives mechanism-based expected-vs-observed reasoning.

### Layer 3: Semantic Memory (`engine/semantic_memory.py`)

- TF-IDF vectorization over 150+ repair cases
- Cosine similarity retrieval (top-K matches)
- PCA projection for 2D Pattern Space visualization
- Signal tokens: deviation severity + error codes per failure pattern

### Layer 4: Evidence Fusion (`engine/evidence_fusion.py`)

Five weighted evidence streams (weights below are the SUPERSEDED hand-set policy; the shipped learned policy is history 0.60 · net 0.35 · topology 0.05 · criticality 0 · category 0 in config/diagnostic_weights.json):
1. **History** (0.35, hand-set): TF-IDF similarity to known repair cases
2. **Net** (0.30, hand-set): Component on observed failing net
3. **Topology** (0.20, hand-set): Upstream/downstream position in DAG
4. **Criticality** (0.10): BOM critical flag
5. **Category** (0.05): Component type priors (IC > Connector > Transistor > ...)

Additional layers:
- **Coverage analysis**: Which failures each candidate explains by mechanism
- **Multi-fault solver**: Sparse set-cover with parsimony penalty
- **OOD/Novelty detection**: Pattern familiarity axis independent of ranking
- **Next Best Test**: Mechanism-aware test selection with risk/effort penalties

### Layer 5: Narrative Generation (`engine/narrative_generator.py`)

Template-based narrative (zero LLM):
- Opening by failure count
- Causal chain description
- Evidence reasoning with confidence tier
- Historical precedent citation
- Recommendation (Next Best Test or direct inspection)

## Data Flow

```
CSV Upload → schema_adapter.py → SignatureExtractor → TopologyDAG
                                                    → SemanticMemory
                                                    → EvidenceFusion → ranked suspects
                                                    → MultiFaultSolver
                                                    → OOD Detector
                                                    → DataQuality Gate
                                                    → TestIntegrity Check
                                                    → NarrativeGenerator
                                                    → Report JSON → React Console
```

## Key Design Decisions

1. **Deterministic**: Same input always produces same output. No randomness, no LLM temperature.
2. **Offline**: Zero cloud dependency. Runs on air-gapped factory networks.
3. **Auditable**: Every diagnosis has an evidence ledger with source attribution.
4. **Honest uncertainty**: The system says "I don't know" when evidence is insufficient (ABSTAIN state).
5. **Verified memory**: Only triple-gate verified repairs enter the learning loop (retest PASS + technician confirmation).

## File Structure

```
engine/
├── orchestrator.py          # Master pipeline controller
├── signature_extractor.py   # Layer 1: Failure DNA
├── topology_dag.py          # Layer 2: Causal DAG (3 layers)
├── semantic_memory.py       # Layer 3: TF-IDF retrieval
├── evidence_fusion.py       # Layer 4: 5-stream scoring
├── narrative_generator.py   # Layer 5: Report narrative
├── fault_modes.py           # Mechanism-based fault modes
├── multi_fault_solver.py    # Sparse set-cover solver
├── ood.py                   # Out-of-distribution detection
├── data_quality.py          # Input quality gating
├── test_integrity.py        # Fleet-level analysis
├── repair_memory.py         # Verified learning loop
└── versions.py              # Reproducibility identity
```
