export default function SecurityPrivacyCard() {
  return (
    <div className="exec-card bento-tilt">
      <div className="exec-card__header"><b>SECURITY &amp; PRIVACY</b><small>ENTERPRISE POSTURE</small></div>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        <li style={{ padding: '8px 0', borderBottom: '1px solid #2c3a3e' }}>
          <b style={{ color: '#67e6e7', fontSize: 11 }}>Offline-first architecture</b>
          <span style={{ display: 'block', color: '#cbd5e1', fontSize: 11, lineHeight: 1.5 }}>No API keys, no external calls, no data leaves the factory network. Runs entirely on-prem.</span>
        </li>
        <li style={{ padding: '8px 0', borderBottom: '1px solid #2c3a3e' }}>
          <b style={{ color: '#67e6e7', fontSize: 11 }}>Air-gapped deployment</b>
          <span style={{ display: 'block', color: '#cbd5e1', fontSize: 11, lineHeight: 1.5 }}>Designed for secure factory environments with no internet connectivity required.</span>
        </li>
        <li style={{ padding: '8px 0', borderBottom: '1px solid #2c3a3e' }}>
          <b style={{ color: '#67e6e7', fontSize: 11 }}>No generative hallucination path; diagnosis remains evidence-bounded</b>
          <span style={{ display: 'block', color: '#cbd5e1', fontSize: 11, lineHeight: 1.5 }}>Deterministic evidence fusion — every diagnosis is reproducible and auditable. No LLM, no vector DB.</span>
        </li>
        <li style={{ padding: '8px 0' }}>
          <b style={{ color: '#67e6e7', fontSize: 11 }}>Roadmap</b>
          <span style={{ display: 'block', color: '#cbd5e1', fontSize: 11, lineHeight: 1.5 }}>RBAC + audit logs + retention controls (out of MVP scope, planned for production).</span>
        </li>
      </ul>
    </div>
  );
}
