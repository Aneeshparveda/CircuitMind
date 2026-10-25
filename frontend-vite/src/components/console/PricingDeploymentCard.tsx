export default function PricingDeploymentCard() {
  return (
    <div className="exec-card bento-tilt">
      <div className="exec-card__header"><b>PRICING &amp; DEPLOYMENT</b><small>EXAMPLE PRICING MODEL · NOT FINAL</small></div>
      <div className="pricing-tiers">
        <div className="pricing-tier">
          <b>PILOT</b>
          <small>4–6 weeks</small>
          <span>One-time integration + configuration fee. Provides value on your data before commitment.</span>
        </div>
        <div className="pricing-tier">
          <b>PRO (Annual)</b>
          <small>Per line / station license</small>
          <span>Annual subscription includes support, updates, and priority integration assistance.</span>
        </div>
        <div className="pricing-tier">
          <b>ENTERPRISE</b>
          <small>Multi-site</small>
          <span>MES/tester connectors, audit/RBAC, SLA, dedicated support. Custom pricing.</span>
        </div>
      </div>
      <div style={{ marginTop: 12 }}>
        <b style={{ color: '#67e6e7', fontSize: 11 }}>HOW WE MAKE MONEY</b>
        <p style={{ color: '#cbd5e1', fontSize: 11, margin: '4px 0 0' }}>Annual license + integration services + support + enterprise connectors.</p>
      </div>
      <div style={{ marginTop: 10 }}>
        <b style={{ color: '#67e6e7', fontSize: 11 }}>DEPLOYMENT</b>
        <ul style={{ listStyle: 'none', padding: 0, margin: '4px 0 0' }}>
          <li style={{ color: '#cbd5e1', fontSize: 11, lineHeight: 1.6 }}>• Runs offline/on-prem (no cloud required)</li>
          <li style={{ color: '#cbd5e1', fontSize: 11, lineHeight: 1.6 }}>• Ingests CSV today + exports PDF/CSV</li>
          <li style={{ color: '#cbd5e1', fontSize: 11, lineHeight: 1.6 }}>• Roadmap: MES connector + IPC-2581/ODB++ netlist import</li>
        </ul>
      </div>
      <div style={{ marginTop: 10, padding: '6px 10px', background: 'rgba(103,230,231,.06)', borderRadius: 6, borderLeft: '3px solid #67e6e7' }}>
        <small style={{ color: '#67e6e7', fontSize: 10 }}>TCS fit: Deliverable as a managed integration + customization offering.</small>
      </div>
    </div>
  );
}
