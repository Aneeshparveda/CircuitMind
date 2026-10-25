export default function PositioningStatementCard() {
  return (
    <div className="exec-card bento-tilt" style={{ marginBottom: 18 }}>
      <div className="exec-card__header"><b>WHERE WE STAND</b><small>POSITIONING STATEMENT</small></div>
      <blockquote style={{ margin: 0, padding: '12px 16px', borderLeft: '3px solid #67e6e7', background: 'rgba(103,230,231,.04)', borderRadius: '0 8px 8px 0', color: '#e2e8f0', fontSize: 12, lineHeight: 1.7, fontStyle: 'italic' }}>
        There are three categories of solutions in this market: Enterprise MES giants provide traceability but not diagnosis. Test analytics platforms show yield trends but not root causes. In many electronics manufacturing facilities, especially MSMEs, root-cause diagnosis still relies heavily on spreadsheets, custom scripts, and senior engineer memory.
      </blockquote>
      <p style={{ margin: '12px 0 0', color: '#f8fafc', fontSize: 12, lineHeight: 1.6, fontWeight: 600 }}>
        CircuitMind doesn't compete with Siemens or Keysight. We complement them. We compete with tribal knowledge — and we win, because we're auditable, reproducible, deployable in a day, and we work offline on MSME budgets.
      </p>
      <div style={{ marginTop: 16 }}>
        <b style={{ color: '#67e6e7', fontSize: 12 }}>Our Wedge</b>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginTop: 8 }}>
          <div className="wedge-card"><b>Diagnostic sidecar</b><span style={{ color: '#cbd5e1' }}>Not another MES — we sit alongside existing systems and add root-cause reasoning.</span></div>
          <div className="wedge-card"><b>Evidence-based reasoning</b><span style={{ color: '#cbd5e1' }}>Not statistical dashboards — every diagnosis is traceable to specific evidence with provenance.</span></div>
          <div className="wedge-card"><b>Deployable on MSME budgets</b><span style={{ color: '#cbd5e1' }}>Not enterprise-only — runs offline on a factory laptop in days, not months.</span></div>
        </div>
      </div>
    </div>
  );
}
