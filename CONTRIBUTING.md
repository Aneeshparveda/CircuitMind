# Contributing to CircuitMind

CircuitMind is a deterministic, offline PCB fault-diagnosis prototype
built for the AI Domain X Challenge 2026 (team Dragons). Every benchmark
number in the README comes from the project's own synthetic data — see
`data/DATA_CARD.md` — and proves internal consistency, not real-world
factory accuracy. Contributions must keep that honesty intact.

## Setup

```bash
git clone https://github.com/Aneeshparveda/CircuitMind.git
cd CircuitMind
pip install -r requirements.txt
cd frontend-vite && npm install && npm run build && cd ..
streamlit run app.py --server.port 8510 --server.headless true
```

The frontend **must** be built first: `app.py` stops with an error if
`frontend-vite/dist/` does not exist. That build output is intentionally
not committed.

## Tests

```bash
python3 -m pytest tests/ -v
```

## Rules for contributions

- **Synthetic data only.** Do not add real factory logs, BOMs, or repair
  histories. Any new data must be synthetic and documented in the data
  card, with its generation method and seed.
- **Numbers need provenance.** A benchmark number may only be quoted
  from a frozen file under `validation/`; never re-measure it in prose
  and never quote a bare accuracy without its dataset name.
- **Diagnoses are probable, not confirmed.** Do not change wording that
  presents a ranked root cause as a confirmed fault.
- **Confidence tiers are score buckets**, not probabilities. Do not
  present a tier as a percentage chance.
- **One change per pull request** where practical, with what changed,
  why, and how it was verified.
- Do not commit `frontend-vite/dist/`, credentials, or API keys.

## Reporting a problem

Use the issue templates. Include the component (engine, frontend,
validation, reports), the input (synthetic only), the steps to
reproduce, and the log output.
