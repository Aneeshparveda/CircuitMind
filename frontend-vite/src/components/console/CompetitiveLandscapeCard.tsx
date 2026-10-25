export default function CompetitiveLandscapeCard() {
  return (
    <div className="exec-card bento-tilt">
      <div className="exec-card__header"><b>COMPETITIVE LANDSCAPE</b><small>WHERE WE FIT, NOT WHAT WE REPLACE</small></div>

      <div className="landscape-grid">
        <div className="landscape-cat">
          <b>Enterprise MES / Traceability</b>
          <small>Siemens Opcenter · Aegis FactoryLogix · Critical Manufacturing</small>
          <span style={{ display: 'block', marginTop: 4 }}>We complement these — they handle factory-wide execution and yield. We handle board-level root-cause evidence.</span>
        </div>
        <div className="landscape-cat">
          <b>Test Data Analytics</b>
          <small>Keysight PathWave · Cimetrix · Cogiscan</small>
          <span style={{ display: 'block', marginTop: 4 }}>Statistical analytics on test data. We add deterministic causal reasoning on top.</span>
        </div>
        <div className="landscape-cat landscape-cat--highlight">
          <b>What We Actually Replace</b>
          <small>Excel spreadsheets + Senior engineer memory</small>
          <small>Custom Python scripts (Tier-1 only)</small>
          <span style={{ display: 'block', marginTop: 4 }}>This is the real competition — tribal knowledge that walks out the door.</span>
        </div>
      </div>

      <table className="comparison-table">
        <thead>
          <tr><th>Capability</th><th className="cm-col">CircuitMind</th><th>Excel + Tribal</th><th>Enterprise MES</th></tr>
        </thead>
        <tbody>
          <tr><td>Board-Level Root-Cause</td><td className="cm-col">✅ Deterministic evidence chain</td><td>⚠️ Manual (senior engineer)</td><td>⚠️ Factory-level, not board-level</td></tr>
          <tr><td>Counterfactual "Why not X?"</td><td className="cm-col">✅ Per-component mechanism analysis</td><td>❌</td><td>❌ Not at board level</td></tr>
          <tr><td>Fixture vs Board Attribution</td><td className="cm-col">✅ Multi-level (fixture/station/revision)</td><td>❌</td><td>⚠️ Separate tool</td></tr>
          <tr><td>Verified Repair Memory</td><td className="cm-col">✅ Closed-loop, triple-gate verification</td><td>❌ Walks out the door</td><td>⚠️ Data only, no verification</td></tr>
          <tr><td>OOD / Abstention</td><td className="cm-col">✅ "I don't know" when evidence is insufficient</td><td>❌</td><td>❌</td></tr>
          <tr><td>Offline / Air-Gapped</td><td className="cm-col">✅ Zero cloud dependency</td><td>✅</td><td>⚠️ Some require cloud</td></tr>
          <tr><td>Deployment</td><td className="cm-col">⚡ Single laptop, days</td><td>⚡ Immediate (poor quality)</td><td>🐢 6-18 months, dedicated infrastructure</td></tr>
          <tr><td>Cost</td><td className="cm-col">💰 Low (MSME budget)</td><td>💰 Free (expensive labor)</td><td>💰💰💰💰 Enterprise pricing</td></tr>
          <tr><td>Auditability</td><td className="cm-col">✅ Every claim sourced in evidence ledger</td><td>❌</td><td>⚠️ Varies</td></tr>
        </tbody>
      </table>

      <small style={{ display: 'block', marginTop: 8, color: '#cbd5e1', fontSize: 11, lineHeight: 1.5 }}>Honest framing: Enterprise MES and test analytics platforms (Siemens, Keysight, Aegis) are excellent at what they do — factory-wide traceability and statistical yield analysis. CircuitMind is a focused diagnostic sidecar that automates the board-level root-cause step these platforms don't cover. We complement them; we don't replace them.</small>
    </div>
  );
}
