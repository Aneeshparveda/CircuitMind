export default function MarketOpportunityCard() {
  const stats = [
    { icon: '💻', label: 'Runs On', value: 'Any Laptop', sub: 'No GPU, no cloud' },
    { icon: '🔒', label: 'Data Stays', value: 'On-Premise', sub: 'Zero data leaving the factory' },
    { icon: '⚡', label: 'Deploy Time', value: '< 1 Day', sub: 'Single pip install + build' },
    { icon: '🧠', label: 'AI Type', value: 'Deterministic', sub: 'Same input → same output, always' },
  ];

  return (
    <div className="exec-card bento-tilt">
      <div className="exec-card__header"><b>DEPLOYMENT STORY</b><small>HOW IT ACTUALLY RUNS</small></div>
      <div className="market-stat-grid">
        {stats.map((s, i) => (
          <div key={i} className="market-stat">
            <span className="market-stat__icon">{s.icon}</span>
            <span className="market-stat__value">{s.value}</span>
            <span className="market-stat__label">{s.label}</span>
            <span className="market-stat__sub">{s.sub}</span>
          </div>
        ))}
      </div>
      <div style={{ marginTop: 14, padding: '10px 14px', border: '1px solid #27454d', borderRadius: 8, background: 'rgba(10,26,31,.6)' }}>
        <b style={{ color: '#67e6e7', fontSize: 11 }}>WHAT'S UNDER THE HOOD</b>
        <p style={{ color: '#a8c0c5', fontSize: 11, margin: '6px 0 0', lineHeight: 1.6 }}>
          CircuitMind is a deterministic reasoning engine: Signature Extraction → Causal Topology (NetworkX DAG) → TF-IDF Historical Retrieval → Evidence Fusion (5 weighted streams) → Narrative Generation, plus diagnostic safety layers (OOD detection, multi-fault solver, next-best-test, verified repair memory). No LLM, no cloud, no GPU. Runs offline on Python 3.9+ with scikit-learn and pandas.
        </p>
      </div>
      <small style={{ display: 'block', marginTop: 10, color: '#5a7a80', fontSize: 10 }}>All claims backed by 10 benchmark categories (instance, reserve, family, adversarial, OOD, multi-fault, discriminating, ablation, baselines, intermittent). Numbers in BENCHMARKS.md.</small>
    </div>
  );
}
