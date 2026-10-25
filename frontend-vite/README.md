# CircuitMind — PCB Forensics Mission Control

The React console for CircuitMind, an offline PCB root-cause forensics
prototype. It runs as a Streamlit custom component (`app.py` in the project
root serves the build in `dist/`).

CircuitMind performs **structured evidence reasoning**: it parses ICT/FCT
test logs, traces failures through a causal dependency graph, retrieves
similar historical repairs, and fuses named evidence streams (history, net,
topology, criticality, category) into a ranked, confidence-labelled
hypothesis — all deterministically, with no LLM, no API keys, and no
internet dependency. Every claim is traceable to a source-backed evidence
ledger and labelled as a probable match requiring physical verification.

## Features

- Failure-signature extraction (deviation, severity, domain)
- Causal root-cause vs. cascade separation over a topology DAG
- TF-IDF historical retrieval with deviation + error-code signals
- Weighted evidence fusion with per-candidate why/why-not explanations
- Hypothesis ranking with confidence tiers (Strong match / Likely / Inconclusive)
- Repair counterfactual simulator
- PDF and CSV report export

## Build

```bash
npm install
npm run build
```

The built component is served by `python3 -m streamlit run app.py` from the
project root.
