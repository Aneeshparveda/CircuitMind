export default function LimitationsSafetyCard() {
  return (
    <div className="exec-card bento-tilt">
      <div className="exec-card__header"><b>KNOWN LIMITATIONS</b><small>SAFETY &amp; HONEST BOUNDS</small></div>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        <li style={{ padding: '8px 0', borderBottom: '1px solid #2c3a3e' }}>
          <b style={{ color: '#f6cb85', fontSize: 11 }}>Probable Outputs &amp; Confidence</b>
          <span style={{ display: 'block', color: '#cbd5e1', fontSize: 11, lineHeight: 1.5 }}>Outputs reflect evidence strength scores, not calibrated probabilities. A 'Strong Evidence' label indicates complete supporting precedent and net evidence, not a guaranteed statistical probability.</span>
        </li>
        <li style={{ padding: '8px 0', borderBottom: '1px solid #2c3a3e' }}>
          <b style={{ color: '#f6cb85', fontSize: 11 }}>Safe Next Actions (Human-in-the-Loop)</b>
          <span style={{ display: 'block', color: '#cbd5e1', fontSize: 11, lineHeight: 1.5 }}>Diagnostic recommendations are risk-tiered (Low/Medium/High risk). Physical verification and human technician approval are required before any hardware rework or component replacement.</span>
        </li>
        <li style={{ padding: '8px 0', borderBottom: '1px solid #2c3a3e' }}>
          <b style={{ color: '#f6cb85', fontSize: 11 }}>Deterministic Integrity</b>
          <span style={{ display: 'block', color: '#cbd5e1', fontSize: 11, lineHeight: 1.5 }}>Operates 100% offline with zero cloud LLM or external API dependencies, ensuring fully reproducible, auditable results for factory safety.</span>
        </li>
        <li style={{ padding: '8px 0' }}>
          <b style={{ color: '#f6cb85', fontSize: 11 }}>Open-World Generalization</b>
          <span style={{ display: 'block', color: '#cbd5e1', fontSize: 11, lineHeight: 1.5 }}>Optimized for known fault family holdout (88% top-1 / 100% top-3). On novel fault families, top-1 accuracy is 49% (84.7% top-3); the system actively flags low-confidence signatures to abstain and prompt human investigation.</span>
        </li>
      </ul>
    </div>
  );
}
