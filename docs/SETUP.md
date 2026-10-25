# CircuitMind Setup

## Prerequisites

- Python 3.9+
- Node.js 18+ (for frontend build)
- 4 GB RAM minimum

## Quick Start

### 1. Clone and install dependencies

```bash
git clone https://github.com/Aneeshparveda/CircuitMind.git && cd CircuitMind
pip install -r requirements.txt
cd frontend-vite && npm install && npm run build && cd ..
```

### 2. Generate synthetic data (if not present)

```bash
python data/generate_synthetic.py
```

### 3. Run the application

```bash
streamlit run app.py --server.port 8510 --server.headless true
```

Open `http://localhost:8510` in your browser.

## Docker (One-Command)

```bash
docker build -t circuitmind .
docker run -p 8510:8510 circuitmind
```

## What's Included

| Component | Description |
|---|---|
| `app.py` | Streamlit host for the React forensic console |
| `engine/` | Deterministic diagnosis engine (5-stage pipeline + safety layers) |
| `data/` | Synthetic test logs, BOM, repair history |
| `frontend-vite/` | React forensic console UI |
| `validation/` | 8 benchmark sections (A–H) in validation/run_all_benchmarks.py |
| `tests/` | 103 test functions across 5 test files |

## Running Tests

```bash
python -m pytest tests/ -v
```

## Running Benchmarks

```bash
cd validation
python run_all_benchmarks.py
```

## Dependencies

### Python (`requirements.txt`)
- pandas, numpy — data processing
- scikit-learn — TF-IDF vectorization, cosine similarity
- networkx — circuit topology DAG
- streamlit — web host
- fpdf2 — PDF report generation

### Frontend (`frontend-vite/package.json`)
- React 19, Vite 8, TypeScript
- motion (Framer Motion) — animations
- streamlit-component-lib — Streamlit integration

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the pipeline design.

## Benchmark Results

See [BENCHMARKS.md](./BENCHMARKS.md) for validated accuracy numbers.
