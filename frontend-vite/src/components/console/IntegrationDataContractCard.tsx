export default function IntegrationDataContractCard() {
  return (
    <div className="exec-card bento-tilt">
      <div className="exec-card__header"><b>INTEGRATION &amp; DATA CONTRACT</b><small>MVP SPECIFICATION</small></div>

      <div style={{ marginBottom: 12 }}>
        <b style={{ color: '#67e6e7', fontSize: 11 }}>REQUIRED FIELDS</b>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
          {['board_id', 'test_step', 'pass_fail', 'measured_value', 'expected_min/max', 'error_code'].map(f => (
            <span key={f} className="data-field-tag">{f}</span>
          ))}
        </div>
      </div>

      <div style={{ marginBottom: 12 }}>
        <b style={{ color: '#67e6e7', fontSize: 11 }}>OPTIONAL / HIGH-VALUE</b>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
          {['timestamp', 'station_id', 'fixture_id', 'board_revision', 'program_rev'].map(f => (
            <span key={f} className="data-field-tag data-field-tag--optional">{f}</span>
          ))}
        </div>
      </div>

      <div style={{ marginBottom: 12 }}>
        <b style={{ color: '#67e6e7', fontSize: 11 }}>PIPELINE</b>
        <div className="pipeline-diagram">
          <span>ATE Logs</span>
          <span className="pipeline-arrow">→</span>
          <span className="pipeline-cm">CircuitMind</span>
          <span className="pipeline-arrow">→</span>
          <span>Ranked suspects + Next test + Export report</span>
        </div>
      </div>

      <div>
        <b style={{ color: '#67e6e7', fontSize: 11 }}>ROADMAP INPUTS</b>
        <ul style={{ listStyle: 'none', padding: 0, margin: '4px 0 0' }}>
          <li style={{ color: '#cbd5e1', fontSize: 11, lineHeight: 1.6 }}>• MES connector (OPC-UA / REST)</li>
          <li style={{ color: '#cbd5e1', fontSize: 11, lineHeight: 1.6 }}>• IPC-2581 / ODB++ netlist import</li>
          <li style={{ color: '#cbd5e1', fontSize: 11, lineHeight: 1.6 }}>• Revision-aware BOM mapping</li>
        </ul>
      </div>
    </div>
  );
}
