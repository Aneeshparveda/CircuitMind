export default function GovImpactCard() {
  return (
    <div className="exec-card bento-tilt">
      <div className="exec-card__header"><b>GOVERNMENT FUNDING RATIONALE</b><small>WHY THIS DESERVES SUPPORT</small></div>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        <li style={{ padding: '8px 0', borderBottom: '1px solid #2c3a3e' }}>
          <b style={{ color: '#67e6e7', fontSize: 11 }}>Reduce e-waste &amp; scrap</b>
          <span style={{ display: 'block', color: '#cbd5e1', fontSize: 11, lineHeight: 1.5 }}>Avoid wrong rework and false failures; fewer boards scrapped means less electronic waste.</span>
        </li>
        <li style={{ padding: '8px 0', borderBottom: '1px solid #2c3a3e' }}>
          <b style={{ color: '#67e6e7', fontSize: 11 }}>Improve FPY &amp; reduce downtime</b>
          <span style={{ display: 'block', color: '#cbd5e1', fontSize: 11, lineHeight: 1.5 }}>Faster triage means the line keeps moving; first-pass yield improves when engineers fix the right board the first time.</span>
        </li>
        <li style={{ padding: '8px 0', borderBottom: '1px solid #2c3a3e' }}>
          <b style={{ color: '#67e6e7', fontSize: 11 }}>Preserve expert knowledge</b>
          <span style={{ display: 'block', color: '#cbd5e1', fontSize: 11, lineHeight: 1.5 }}>Verified repair memory captures institutional know-how so it walks out the door when a senior engineer retires.</span>
        </li>
        <li style={{ padding: '8px 0', borderBottom: '1px solid #2c3a3e' }}>
          <b style={{ color: '#67e6e7', fontSize: 11 }}>Enable MSMEs</b>
          <span style={{ display: 'block', color: '#cbd5e1', fontSize: 11, lineHeight: 1.5 }}>Runs offline/on-prem with low IT footprint; small manufacturers get diagnostic intelligence without cloud vendor lock-in.</span>
        </li>
        <li style={{ padding: '8px 0' }}>
          <b style={{ color: '#67e6e7', fontSize: 11 }}>Supports Make-in-India</b>
          <span style={{ display: 'block', color: '#cbd5e1', fontSize: 11, lineHeight: 1.5 }}>Builds domestic capability in electronics manufacturing intelligence; aligned with national scale-up goals.</span>
        </li>
      </ul>
    </div>
  );
}
